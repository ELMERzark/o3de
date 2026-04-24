#!/usr/bin/env python3
"""
CLI 入口。

示例：
    python run.py "给 Gems/MyGem 加一个 SpinnerComponent，每帧绕 Z 轴旋转"

选项：
    --dry-run          仅跑 Planner，不写文件
    --auto-approve     跳过所有 HITL 确认（**危险**，CI / 自动化脚本用）
    -v / --verbose     打印 DEBUG 日志
"""

from __future__ import annotations

import argparse
import logging
import sys

import config
from workflow import run


def main() -> int:
    parser = argparse.ArgumentParser(
        description="O3DE 多 Agent 开发 MVP（Planner → CPP Specialist → Reviewer）"
    )
    parser.add_argument("task", help="自然语言任务描述（用引号括起来）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只跑 Planner，不执行后续 Specialist / Reviewer",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="跳过所有人工确认。**危险**，仅用于 CI / 已知任务。",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="DEBUG 级日志",
    )
    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.auto_approve:
        config.AUTO_APPROVE = True
        logging.warning("AUTO_APPROVE = True（跳过人工确认）")

    if args.dry_run:
        # 只跑 Planner：直接构造一个 planner 跑
        import asyncio
        from agents_mvp import build_planner
        from workflow import _run_agent, _try_parse_json

        config.validate()
        planner = build_planner()
        planner_input = (
            f"任务：{args.task}\n\n按 system prompt 的 schema 输出严格 JSON 计划。"
        )
        out = asyncio.run(_run_agent(planner, planner_input))
        plan = _try_parse_json(out)
        import json
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    # 完整 workflow
    try:
        result = run(args.task)
    except KeyboardInterrupt:
        print("\n用户中断。")
        return 130
    except Exception as e:
        logging.exception("workflow 失败")
        return 1

    review = result.get("review")
    if isinstance(review, dict):
        sev = review.get("severity", "unknown")
        if sev == "blocking":
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
