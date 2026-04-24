"""
MVP 文件工具。所有工具都是**纯同步 Python 函数**，MAF 会在需要时自动包成
tool-call。签名、类型、docstring 决定 MAF 如何向模型描述工具。

扩展时在这里加新工具（shell_run / cmake_build / ap_batch 等）。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from config import REPO_ROOT
from safety import (
    UnsafePathError,
    check_writable,
    resolve_safe_path,
)

log = logging.getLogger(__name__)


# 返回值截断，防止大文件 / 大搜索结果塞爆 context
_MAX_READ_BYTES = 200 * 1024         # 200 KB
_MAX_GREP_LINES = 200
_MAX_LIST_ENTRIES = 300


# 写入日志：记录 agent 都改了哪些文件（人工 audit 用）
_WRITE_LOG: list[dict] = []


def fs_read(path: str) -> str:
    """
    读仓库内一个文本文件的内容。路径相对仓库根（例如 'Code/Framework/AzCore/AzCore/Component/Component.h'）。
    太大的文件会被截断到前 200 KB。
    """
    abs_path = resolve_safe_path(path)
    if not abs_path.exists():
        return f"[fs_read] ERROR: 文件不存在: {path}"
    if not abs_path.is_file():
        return f"[fs_read] ERROR: 不是文件: {path}"

    try:
        data = abs_path.read_bytes()
    except PermissionError as e:
        return f"[fs_read] ERROR: 无读取权限: {path} ({e})"

    truncated = False
    if len(data) > _MAX_READ_BYTES:
        data = data[:_MAX_READ_BYTES]
        truncated = True

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return f"[fs_read] ERROR: 不是 utf-8 文本文件: {path}"

    log.info("fs_read path=%s bytes=%d truncated=%s", path, len(data), truncated)
    header = f"# {path} (rel to repo root)\n"
    if truncated:
        header += f"# [TRUNCATED after {_MAX_READ_BYTES} bytes]\n"
    return header + text


def fs_list(path: str = ".") -> str:
    """
    列一个目录下的条目（非递归）。path 相对仓库根。
    返回格式：每行 '<d|f> <name> [<size>]'。
    """
    abs_path = resolve_safe_path(path)
    if not abs_path.exists():
        return f"[fs_list] ERROR: 路径不存在: {path}"
    if not abs_path.is_dir():
        return f"[fs_list] ERROR: 不是目录: {path}"

    entries: list[str] = []
    for child in sorted(abs_path.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
        if len(entries) >= _MAX_LIST_ENTRIES:
            entries.append(f"... (truncated at {_MAX_LIST_ENTRIES} entries)")
            break
        if child.is_dir():
            entries.append(f"d  {child.name}/")
        else:
            try:
                size = child.stat().st_size
                entries.append(f"f  {child.name}  {size}B")
            except OSError:
                entries.append(f"f  {child.name}")
    log.info("fs_list path=%s count=%d", path, len(entries))
    return "\n".join(entries) if entries else "[empty dir]"


def fs_grep(pattern: str, path_glob: str = "**/*") -> str:
    """
    在仓库内做 ripgrep 文本搜索。
    pattern: 正则模式（ripgrep 语法）
    path_glob: 路径 glob，例如 '**/*.cpp' / 'Code/**/*.h'
    返回前 200 行 'file:line:content'。
    """
    # 优先用系统 rg（速度快）；装了 ripgrep 的系统都能找到
    cmd = [
        "rg", "-n", "--color=never",
        "--glob", path_glob,
        pattern,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        )
    except FileNotFoundError:
        return (
            "[fs_grep] ERROR: ripgrep (rg) 未安装。\n"
            "Ubuntu 24.04: `sudo apt install ripgrep`\n"
            "Windows: 装 Scoop/Choco 后 `scoop install ripgrep`"
        )
    except subprocess.TimeoutExpired:
        return "[fs_grep] ERROR: 搜索超时 (30s)"

    lines = proc.stdout.splitlines()
    truncated = len(lines) > _MAX_GREP_LINES
    shown = lines[:_MAX_GREP_LINES]

    log.info(
        "fs_grep pattern=%s glob=%s hits=%d truncated=%s",
        pattern, path_glob, len(lines), truncated,
    )

    if not shown:
        if proc.returncode not in (0, 1):   # rg: 0=found, 1=nothing found, >=2 error
            return f"[fs_grep] ERROR: rg exit {proc.returncode}\n{proc.stderr}"
        return "[fs_grep] no matches"

    header = f"# pattern={pattern!r} glob={path_glob!r} hits={len(lines)}"
    if truncated:
        header += f" (showing first {_MAX_GREP_LINES})"
    return header + "\n" + "\n".join(shown)


def fs_write(path: str, content: str) -> str:
    """
    写一个文本文件（新建或覆盖）。path 相对仓库根。

    **注意**：本函数本身不做 HITL 确认；HITL 逻辑在 workflow.py 的 approval 层包装。
    直接调会立即写入。

    Returns:
        "[fs_write] OK: <path> (<bytes> bytes)" 或错误信息。
    """
    try:
        abs_path = resolve_safe_path(path)
        check_writable(abs_path)
    except UnsafePathError as e:
        return f"[fs_write] BLOCKED: {e}"

    abs_path.parent.mkdir(parents=True, exist_ok=True)

    is_new = not abs_path.exists()
    try:
        abs_path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as e:
        return f"[fs_write] ERROR: {e}"

    status = "created" if is_new else "overwritten"
    size = len(content.encode("utf-8"))
    log.info("fs_write path=%s status=%s bytes=%d", path, status, size)

    _WRITE_LOG.append({"path": path, "status": status, "bytes": size})
    return f"[fs_write] OK ({status}): {path} ({size} bytes)"


# ========= Helpers =========


def get_write_log() -> list[dict]:
    """Workflow 结束时用，总结本次 run 改了哪些文件。"""
    return list(_WRITE_LOG)


def reset_write_log() -> None:
    _WRITE_LOG.clear()


# 导出给 MAF 作为 tools= 参数
ALL_TOOLS = [fs_read, fs_list, fs_grep, fs_write]
READ_ONLY_TOOLS = [fs_read, fs_list, fs_grep]
