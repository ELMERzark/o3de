"""
配置 —— 从 .env / 环境变量读取。

只读常量。启动时调 load() 一次。
"""

from __future__ import annotations

import os
from pathlib import Path


# ---- 网络 ----
HOST: str = "127.0.0.1"
PORT: int = 24601
AUTH_TOKEN: str = ""

# ---- 安全开关 ----
AUTO_APPROVE: bool = False
ALLOW_DESTRUCTIVE: bool = False
ALLOW_EXEC_PYTHON: bool = False

# ---- 限制 ----
TOOL_CALL_TIMEOUT_SEC: float = 30.0
MAX_PENDING_QUEUE: int = 50
MAX_ENTITIES_IN_SNAPSHOT: int = 2000

# ---- 日志 ----
LOG_LEVEL: str = "INFO"
LOG_DIR: Path = Path(__file__).resolve().parent / "logs"


def _load_env_file(path: Path) -> None:
    """超迷你 .env 解析，不依赖 python-dotenv（避免编辑器 Python 没装）。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _as_bool(s: str, default: bool) -> bool:
    if s is None:
        return default
    return s.strip().lower() in ("1", "true", "yes", "on")


def load() -> None:
    """读 .env + env var，覆盖模块级常量。"""
    global HOST, PORT, AUTH_TOKEN
    global AUTO_APPROVE, ALLOW_DESTRUCTIVE, ALLOW_EXEC_PYTHON
    global TOOL_CALL_TIMEOUT_SEC, MAX_PENDING_QUEUE, MAX_ENTITIES_IN_SNAPSHOT
    global LOG_LEVEL, LOG_DIR

    here = Path(__file__).resolve().parent
    _load_env_file(here / ".env")

    HOST = os.environ.get("MCP_HOST", HOST)
    PORT = int(os.environ.get("MCP_PORT", PORT))
    AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")

    AUTO_APPROVE = _as_bool(os.environ.get("AUTO_APPROVE"), AUTO_APPROVE)
    ALLOW_DESTRUCTIVE = _as_bool(os.environ.get("ALLOW_DESTRUCTIVE"), ALLOW_DESTRUCTIVE)
    ALLOW_EXEC_PYTHON = _as_bool(os.environ.get("ALLOW_EXEC_PYTHON"), ALLOW_EXEC_PYTHON)

    TOOL_CALL_TIMEOUT_SEC = float(os.environ.get("TOOL_CALL_TIMEOUT_SEC", TOOL_CALL_TIMEOUT_SEC))
    MAX_PENDING_QUEUE = int(os.environ.get("MAX_PENDING_QUEUE", MAX_PENDING_QUEUE))
    MAX_ENTITIES_IN_SNAPSHOT = int(os.environ.get("MAX_ENTITIES_IN_SNAPSHOT", MAX_ENTITIES_IN_SNAPSHOT))

    LOG_LEVEL = os.environ.get("LOG_LEVEL", LOG_LEVEL).upper()
    LOG_DIR = Path(os.environ.get("LOG_DIR", str(LOG_DIR)))
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def summary() -> str:
    return (
        f"MCP config:\n"
        f"  listen:              http://{HOST}:{PORT}\n"
        f"  auth:                {'set' if AUTH_TOKEN else 'MISSING'}\n"
        f"  AUTO_APPROVE:        {AUTO_APPROVE}\n"
        f"  ALLOW_DESTRUCTIVE:   {ALLOW_DESTRUCTIVE}\n"
        f"  ALLOW_EXEC_PYTHON:   {ALLOW_EXEC_PYTHON}\n"
        f"  tool timeout:        {TOOL_CALL_TIMEOUT_SEC}s\n"
        f"  max pending queue:   {MAX_PENDING_QUEUE}\n"
        f"  max snapshot ents:   {MAX_ENTITIES_IN_SNAPSHOT}\n"
        f"  log dir:             {LOG_DIR}"
    )
