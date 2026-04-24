"""MCP 工具 handler 集合。

每个 handler 模块暴露若干 async 函数；`mcp_server.py` 遍历并注册为 MCP tool。

约定：
    - 所有 handler 是 `async def xxx(**kwargs) -> dict`
    - 输入参数是 MCP SDK 反序列化好的 dict（值已是 JSON-native 类型）
    - 返回 JSON-native dict；抛 `MCPToolError` 用于业务错误
    - 任何 azlmbr 调用必须用 `threading_bridge.call_on_main(...)` 包住
"""

from . import entity, component, transform, asset, query

__all__ = ["entity", "component", "transform", "asset", "query"]
