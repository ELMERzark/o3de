"""
MVP workflow: Planner → CPP Specialist → Reviewer（线性）

HITL（人在回路）：
    workflow 不修改 fs_tools.fs_write 本身，而是在 agent 执行期间
    通过一个 middleware 风格的包装：在 Specialist 执行前给它一个
    fs_write 的 "带确认" 版本。

    这个版本依赖 MAF ≥ 1.x 支持在运行时替换 tool list；若你的 MAF
    版本还没这能力，降级策略是：
      - 关掉 AUTO_APPROVE 时，让 Specialist 只产出 "意图" (markdown diff),
        人工看过后再调 apply_diff() 落盘（更保守，但慢）。
    本 MVP 用前一种方案；若不工作切到后者。
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import config
import fs_tools
from agents_mvp import AgentBundle, build_all_mvp
from safety import check_writable, resolve_safe_path

log = logging.getLogger(__name__)


# ========================= HITL ==============================================

def _ask_approval(prompt: str) -> bool:
    """终端 yes/no。空 = no。"""
    if config.AUTO_APPROVE:
        return True
    try:
        resp = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return resp in ("y", "yes")


def fs_write_with_approval(path: str, content: str) -> str:
    """
    人在回路版本的 fs_write：写入前先显示摘要 + 询问确认。

    会被 CPP Specialist agent 作为 tool 调用。签名和 fs_tools.fs_write 一致。
    """
    try:
        abs_path = resolve_safe_path(path)
        check_writable(abs_path)
    except Exception as e:  # UnsafePathError 或其它
        return f"[fs_write] BLOCKED: {e}"

    # 摘要显示给用户
    preview_lines = content.splitlines()
    total_lines = len(preview_lines)
    preview = "\n".join(preview_lines[:40])
    if total_lines > 40:
        preview += f"\n... ({total_lines - 40} more lines)"

    existing = ""
    if abs_path.exists():
        try:
            existing = abs_path.read_text(encoding="utf-8")
        except Exception:
            existing = "<binary or unreadable>"

    print("=" * 70)
    print(f"Agent 想写入: {path}  ({len(content)} bytes, {total_lines} lines)")
    print(f"   存在: {'yes (will overwrite)' if existing else 'no (create new)'}")
    print("-" * 70)
    print(preview)
    print("=" * 70)

    if not _ask_approval(f"批准写入 {path}?"):
        return f"[fs_write] DECLINED by user: {path}"

    return fs_tools.fs_write(path, content)


# ========================= Workflow ==========================================

def _agent_tools_with_hitl(bundle: AgentBundle) -> list:
    """
    返回 agent 该用的 tools，其中 fs_write 替换成 approval 版。
    """
    return [
        fs_tools.fs_read,
        fs_tools.fs_grep,
        fs_tools.fs_list,
        fs_write_with_approval,
    ]


async def _run_agent(bundle: AgentBundle, user_message: str) -> str:
    """
    跑一次 agent，返回它的文本响应。
    """
    log.info("[%s] running (model=%s)", bundle.name, bundle.model_id)
    # MAF API：如果你的版本 agent.run 参数名不同，调整此处
    result = await bundle.agent.run(user_message)

    # 取文本（MAF 不同版本属性不同：.text / .content / .messages[-1].text）
    for attr in ("text", "content"):
        v = getattr(result, attr, None)
        if isinstance(v, str) and v:
            return v
    # 最后 fallback：直接 str
    return str(result)


def _try_parse_json(text: str) -> Any:
    """
    Planner / Reviewer 要求输出 JSON。
    模型偶尔包一层 ```json ... ``` —— 做一次 tolerant parse。
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {"_raw": text, "_parse_error": str(e)}


# ========================= Logging ==========================================

def _save_run_log(task: str, run_dir: Path, step: str, payload: Any) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{step}.json"
    content = (
        payload
        if isinstance(payload, (dict, list))
        else {"raw": str(payload)}
    )
    path.write_text(
        json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("saved %s", path)


# ========================= Main ==============================================

async def run_sequential_mvp(task: str) -> dict:
    """
    主 workflow：Planner → CPP Specialist → Reviewer。

    返回 dict：
        {
            "task": str,
            "plan": dict | None,
            "coder_summary": str,
            "review": dict | None,
            "files_written": [{"path", "status", "bytes"}, ...],
            "log_dir": str,
        }
    """
    # 启动前检查
    config.validate()
    print(config.summary())

    # 本次 run 的日志目录
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.LOG_DIR / f"run_{ts}"

    fs_tools.reset_write_log()

    # ---- 建 agent（每次 run 建一次，MAF client 内部自己管 session）
    agents = build_all_mvp()

    # 把 Specialist 的 tools 替换成 HITL 版
    # 注：MAF 的 ChatAgent 一般允许在构造后换 tools；若不允许，需要在
    # agents_mvp.build_cpp_specialist 直接传 _agent_tools_with_hitl。
    agents["cpp_specialist"].agent.tools = _agent_tools_with_hitl(
        agents["cpp_specialist"]
    )

    # ---- Step 1: Planner
    print("\n" + "=" * 70)
    print("[Step 1] Planner（R1）拆解任务")
    print("=" * 70)
    planner_input = (
        f"任务：{task}\n\n"
        "按你 system prompt 里的 schema 输出严格 JSON 计划。"
    )
    planner_out = await _run_agent(agents["planner"], planner_input)
    plan = _try_parse_json(planner_out)
    _save_run_log(task, run_dir, "01_planner", plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    if isinstance(plan, dict) and "_parse_error" in plan:
        print("⚠  Planner 输出不是合法 JSON。检查 logs 并可能要重跑。")
        return {
            "task": task, "plan": plan, "coder_summary": "",
            "review": None, "files_written": [], "log_dir": str(run_dir),
        }

    if not _ask_approval("\n计划看起来 OK? 继续执行?"):
        print("用户中止。")
        return {
            "task": task, "plan": plan, "coder_summary": "",
            "review": None, "files_written": [], "log_dir": str(run_dir),
        }

    # ---- Step 2: CPP Specialist
    print("\n" + "=" * 70)
    print("[Step 2] CPP Specialist（V3）执行计划")
    print("=" * 70)
    coder_input = (
        "下面是 Planner 给你的 JSON 计划。按计划逐个 fs_read / fs_write 执行。\n\n"
        f"```json\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n```\n\n"
        "完成后输出中文 summary。"
    )
    coder_out = await _run_agent(agents["cpp_specialist"], coder_input)
    _save_run_log(task, run_dir, "02_coder", {"summary": coder_out})
    print(coder_out)

    written = fs_tools.get_write_log()
    print(f"\n共写入 {len(written)} 个文件:")
    for w in written:
        print(f"  {w['status']:12s} {w['path']} ({w['bytes']}B)")

    # ---- Step 3: Reviewer
    print("\n" + "=" * 70)
    print("[Step 3] Reviewer（R1）审查")
    print("=" * 70)
    reviewer_input = (
        "审查下列改动。\n\n"
        "## 原始计划\n"
        f"```json\n{json.dumps(plan, ensure_ascii=False, indent=2)}\n```\n\n"
        "## Specialist 的 summary\n"
        f"{coder_out}\n\n"
        "## 实际写入的文件\n"
        f"{json.dumps(written, ensure_ascii=False, indent=2)}\n\n"
        "按 system prompt 的 schema 输出 JSON。"
    )
    reviewer_out = await _run_agent(agents["reviewer"], reviewer_input)
    review = _try_parse_json(reviewer_out)
    _save_run_log(task, run_dir, "03_reviewer", review)
    print(json.dumps(review, ensure_ascii=False, indent=2))

    print(f"\n日志: {run_dir}")
    return {
        "task": task,
        "plan": plan,
        "coder_summary": coder_out,
        "review": review,
        "files_written": written,
        "log_dir": str(run_dir),
    }


def run(task: str) -> dict:
    """同步包装，给 CLI 用。"""
    return asyncio.run(run_sequential_mvp(task))
