"""
安全护栏：路径白名单 + 禁写清单。

所有 fs_* 工具必须先调 `resolve_safe_path()`。写操作额外调 `check_writable()`。
"""

from __future__ import annotations

from pathlib import Path

from config import REPO_ROOT


# 允许写的路径前缀必须是仓库根；额外针对 Windows 的大小写问题做 resolve。
# 下列目录下的文件禁止任何写操作（含新建）。
FORBIDDEN_WRITE_PREFIXES: list[str] = [
    ".git",
    "build",
    "Cache",
    "user",
    "3rdParty",
    # 第三方下载缓存（若存在）
    "o3de-packages",
    # Python 虚拟环境
    "tools/agents/.venv",
    "tools/agents/logs",  # 日志由 workflow 自己管
]

# 这些具体文件名禁止写（稳定 id / 元数据）
FORBIDDEN_WRITE_FILES: list[str] = [
    "engine.json",  # 引擎元数据，含 engine UUID 等
]

# 文件扩展名禁止（防写坏二进制）
FORBIDDEN_WRITE_EXTS: list[str] = [
    ".dll", ".so", ".dylib", ".exe",
    ".pdb", ".pak",
    ".fbx", ".dds", ".tif", ".tiff", ".exr",
    ".mp4", ".ogg", ".wav", ".mp3",
    ".ttf", ".otf",
]


class UnsafePathError(ValueError):
    """路径越界或禁写。"""


def resolve_safe_path(path: str | Path) -> Path:
    """
    把 path（可以是相对仓库根的字符串）resolve 成绝对路径，
    并确保它在 REPO_ROOT 下。

    Raises:
        UnsafePathError: 如果路径越出仓库根。
    """
    p = Path(path)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()

    try:
        p.relative_to(REPO_ROOT)
    except ValueError as e:
        raise UnsafePathError(
            f"路径越出仓库根: {p} (REPO_ROOT={REPO_ROOT})"
        ) from e
    return p


def check_writable(path: Path) -> None:
    """
    对已经 resolve 过的绝对路径检查是否允许写。
    写保护的目录 / 文件 / 扩展名会抛异常。
    """
    rel = path.relative_to(REPO_ROOT).as_posix()

    # 禁写目录前缀
    for pref in FORBIDDEN_WRITE_PREFIXES:
        if rel.startswith(pref.rstrip("/") + "/") or rel == pref:
            raise UnsafePathError(
                f"禁写目录 '{pref}' 下的文件: {rel}"
            )

    # 禁写具体文件名
    name = path.name
    if name in FORBIDDEN_WRITE_FILES:
        raise UnsafePathError(f"禁写受保护文件: {name}")

    # 禁写扩展名
    if path.suffix.lower() in FORBIDDEN_WRITE_EXTS:
        raise UnsafePathError(
            f"禁写二进制 / 生成类文件扩展名: {path.suffix}"
        )


def is_safe_path(path: str | Path) -> bool:
    """只读检查接口，不抛异常。"""
    try:
        resolve_safe_path(path)
        return True
    except UnsafePathError:
        return False
