"""
全局配置。所有 agent / 工具 从这里读。
通过 .env 覆盖默认值。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ========= Paths =========
# 本文件所在目录 = tools/agents/
_AGENTS_DIR = Path(__file__).resolve().parent
# 仓库根 = tools/agents/../../ = repo root
REPO_ROOT: Path = (_AGENTS_DIR / ".." / "..").resolve()

DOCS_CLAUD: Path = REPO_ROOT / "docs_claud"
LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(_AGENTS_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ========= DeepSeek =========
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

MODEL_REASONER: str = os.getenv("MODEL_REASONER", "deepseek-reasoner")
MODEL_CHAT: str = os.getenv("MODEL_CHAT", "deepseek-chat")


# ========= Workflow / HITL =========
AUTO_APPROVE: bool = os.getenv("AUTO_APPROVE", "false").lower() == "true"
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))


# ========= Token budgets =========
MAX_PLANNER_TOKENS: int = int(os.getenv("MAX_PLANNER_TOKENS", "8000"))
MAX_CODER_TOKENS: int = int(os.getenv("MAX_CODER_TOKENS", "16000"))
MAX_REVIEWER_TOKENS: int = int(os.getenv("MAX_REVIEWER_TOKENS", "8000"))


# ========= Logging =========
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


def validate() -> None:
    """启动前的 sanity check。"""
    errors: list[str] = []
    if not DEEPSEEK_API_KEY:
        errors.append(
            "DEEPSEEK_API_KEY 未设置。复制 .env.example 为 .env 并填入 key。"
        )
    if not REPO_ROOT.exists():
        errors.append(f"REPO_ROOT 不存在: {REPO_ROOT}")
    if not DOCS_CLAUD.exists():
        errors.append(
            f"docs_claud/ 不存在: {DOCS_CLAUD}\n"
            "这个 agent 系统需要 docs_claud/ 作为知识底座。"
        )
    if errors:
        raise RuntimeError("配置错误:\n  - " + "\n  - ".join(errors))


def summary() -> str:
    """打印当前配置（不包含 api key）。"""
    return (
        f"REPO_ROOT     = {REPO_ROOT}\n"
        f"DOCS_CLAUD    = {DOCS_CLAUD}\n"
        f"LOG_DIR       = {LOG_DIR}\n"
        f"DEEPSEEK_URL  = {DEEPSEEK_BASE_URL}\n"
        f"MODEL_REASONER= {MODEL_REASONER}\n"
        f"MODEL_CHAT    = {MODEL_CHAT}\n"
        f"AUTO_APPROVE  = {AUTO_APPROVE}\n"
    )
