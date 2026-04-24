"""错误类型与 traceback 捕获。"""

from __future__ import annotations

import traceback
from typing import Any


class MCPToolError(Exception):
    """handler 可抛的结构化错误 —— 会被 mcp_server 转成 MCP error 回给客户端。

    code: 机器可读（'asset_not_found'）
    message: 人可读
    data: 额外 JSON-safe 的上下文
    """

    def __init__(self, code: str, message: str, **data: Any) -> None:
        super().__init__(message)
        self.code = code
        self.data = data

    def to_dict(self) -> dict:
        return {"code": self.code, "message": str(self), "data": self.data}


def wrap_exception(exc: BaseException) -> dict:
    """未预期异常 → 结构化 JSON。保留完整 traceback 给 Agent 做自愈。"""
    if isinstance(exc, MCPToolError):
        return exc.to_dict()
    return {
        "code": "internal_error",
        "message": f"{type(exc).__name__}: {exc}",
        "data": {
            "python_traceback": traceback.format_exc(),
        },
    }


# 常用 code 常量 —— 防手打错
CODE_ENTITY_NOT_FOUND = "entity_not_found"
CODE_COMPONENT_NOT_FOUND = "component_not_found"
CODE_COMPONENT_TYPE_NOT_FOUND = "component_type_not_found"
CODE_ASSET_NOT_FOUND = "asset_not_found"
CODE_PROPERTY_PATH_INVALID = "property_path_invalid"
CODE_PERMISSION_DENIED = "permission_denied"
CODE_TIMEOUT = "timeout"
CODE_INVALID_ARGUMENT = "invalid_argument"
CODE_VERIFY_FAILED = "verify_failed"
