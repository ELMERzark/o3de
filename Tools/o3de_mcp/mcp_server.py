"""MCP Server —— 注册工具 + SSE transport。

使用官方 python-mcp SDK（https://github.com/modelcontextprotocol/python-sdk）。

API 版本兼容说明：
    mcp SDK 在 1.x 期间迭代较快；下面 import / 装饰器用法基于 1.0+。
    如果装的版本里 Server / Tool 结构不同，主要改两处：
        - `from mcp.server import Server` 路径
        - `@server.list_tools()` / `@server.call_tool()` 装饰器名

ASGI 部署：用 starlette 挂 SSE transport；uvicorn 起 server。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable

from . import config
from .errors import MCPToolError, wrap_exception
from .handlers import asset, component, entity, query, transform

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 工具 metadata 声明（MCP tool schema）

# 每一项：(mcp_tool_name, handler_callable, description, input_schema_json)
_TOOLS: list[tuple[str, Callable[..., Awaitable[dict]], str, dict]] = [
    # entity.*
    ("entity.create", entity.create,
     "Create a new entity, optionally with parent/name/position.",
     {
         "type": "object",
         "properties": {
             "parent": {"type": ["string", "null"], "description": "Parent EntityId string or null for level root"},
             "name": {"type": "string"},
             "position": {"type": "object", "description": "Vector3 JSON value"},
         },
     }),
    ("entity.delete", entity.delete,
     "Delete an entity. Destructive — requires ALLOW_DESTRUCTIVE=true.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {
             "entity_id": {"type": "string"},
             "cascade": {"type": "boolean", "default": True},
         },
     }),
    ("entity.set_parent", entity.set_parent,
     "Reparent an entity. new_parent=null moves to level root.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {
             "entity_id": {"type": "string"},
             "new_parent": {"type": ["string", "null"]},
         },
     }),
    ("entity.rename", entity.rename,
     "Rename an entity.",
     {
         "type": "object",
         "required": ["entity_id", "name"],
         "properties": {
             "entity_id": {"type": "string"},
             "name": {"type": "string"},
         },
     }),
    ("entity.list_children", entity.list_children,
     "List immediate children of an entity.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {
             "entity_id": {"type": "string"},
         },
     }),
    ("entity.get_info", entity.get_info,
     "Return name / parent / children / component count / transform of an entity.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {
             "entity_id": {"type": "string"},
         },
     }),

    # component.*
    ("component.list_types", component.list_types,
     "List component types available for a given entity_type (Game/Level/System).",
     {
         "type": "object",
         "properties": {
             "entity_type": {"type": "string", "enum": ["Game", "Level", "System"], "default": "Game"},
         },
     }),
    ("component.add", component.add,
     "Add a component of given type to an entity.",
     {
         "type": "object",
         "required": ["entity_id", "component_type"],
         "properties": {
             "entity_id": {"type": "string"},
             "component_type": {"type": "string", "description": "Display name, e.g. 'Mesh'"},
             "entity_type": {"type": "string", "enum": ["Game", "Level", "System"], "default": "Game"},
         },
     }),
    ("component.remove", component.remove,
     "Remove a component.",
     {
         "type": "object",
         "required": ["component_ref"],
         "properties": {"component_ref": {"type": "string"}},
     }),
    ("component.list_on_entity", component.list_on_entity,
     "List all components on an entity.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {"entity_id": {"type": "string"}},
     }),
    ("component.set_property", component.set_property,
     "Set a component property by path. Universal entry — covers all components/all properties.",
     {
         "type": "object",
         "required": ["component_ref", "property_path", "value"],
         "properties": {
             "component_ref": {"type": "string"},
             "property_path": {"type": "string", "description": "e.g. 'Controller|Configuration|Model Asset'"},
             "value": {"description": "JSON-native or typed value per serialize.py schema"},
             "verify": {"type": "boolean", "default": True},
         },
     }),
    ("component.get_property", component.get_property,
     "Read a component property by path.",
     {
         "type": "object",
         "required": ["component_ref", "property_path"],
         "properties": {
             "component_ref": {"type": "string"},
             "property_path": {"type": "string"},
         },
     }),
    ("component.get_property_tree", component.get_property_tree,
     "List all writable property paths on a component.",
     {
         "type": "object",
         "required": ["component_ref"],
         "properties": {"component_ref": {"type": "string"}},
     }),

    # transform.*
    ("transform.set_translation", transform.set_translation,
     "Set world (or local) translation.",
     {
         "type": "object",
         "required": ["entity_id", "translation"],
         "properties": {
             "entity_id": {"type": "string"},
             "translation": {"type": "object", "description": "Vector3"},
             "local": {"type": "boolean", "default": False},
         },
     }),
    ("transform.set_rotation_euler", transform.set_rotation_euler,
     "Set world (or local) rotation from Euler angles in degrees.",
     {
         "type": "object",
         "required": ["entity_id", "euler_deg"],
         "properties": {
             "entity_id": {"type": "string"},
             "euler_deg": {"type": "object", "description": "{x,y,z} degrees"},
             "local": {"type": "boolean", "default": False},
         },
     }),
    ("transform.set_scale", transform.set_scale,
     "Set local scale (uniform float or Vector3 dict).",
     {
         "type": "object",
         "required": ["entity_id", "scale"],
         "properties": {
             "entity_id": {"type": "string"},
             "scale": {"description": "Number or Vector3"},
         },
     }),
    ("transform.get", transform.get,
     "Get current world translation + euler_deg + uniform_scale.",
     {
         "type": "object",
         "required": ["entity_id"],
         "properties": {"entity_id": {"type": "string"}},
     }),

    # asset.*
    ("asset.find_by_path", asset.find_by_path,
     "Resolve an asset path (relative, catalog style) to an AssetId.",
     {
         "type": "object",
         "required": ["path"],
         "properties": {
             "path": {"type": "string"},
             "auto_register": {"type": "boolean", "default": False},
         },
     }),

    # query.*
    ("query.find_by_name", query.find_by_name,
     "Find entities by name (exact or substring).",
     {
         "type": "object",
         "required": ["name"],
         "properties": {
             "name": {"type": "string"},
             "exact": {"type": "boolean", "default": True},
         },
     }),
    ("query.find_by_component_type", query.find_by_component_type,
     "Find all entities bearing a given component type.",
     {
         "type": "object",
         "required": ["component_type"],
         "properties": {
             "component_type": {"type": "string"},
             "entity_type": {"type": "string", "enum": ["Game", "Level", "System"], "default": "Game"},
         },
     }),
    ("query.scene_snapshot", query.scene_snapshot,
     "Return a JSON snapshot of all entities (name / parent / components / transforms).",
     {
         "type": "object",
         "properties": {
             "include_components": {"type": "boolean", "default": True},
             "include_transforms": {"type": "boolean", "default": True},
             "max_depth": {"type": "integer", "default": 3},
             "max_entities": {"type": ["integer", "null"]},
         },
     }),
]


def list_tools() -> list[dict]:
    return [
        {"name": n, "description": d, "inputSchema": s}
        for (n, _fn, d, s) in _TOOLS
    ]


async def dispatch(tool_name: str, arguments: dict) -> dict:
    """找到 handler 调用；捕获 MCPToolError 和未预期异常。"""
    for (n, fn, _d, _s) in _TOOLS:
        if n == tool_name:
            try:
                if inspect.iscoroutinefunction(fn):
                    return await fn(**(arguments or {}))
                # 同步 handler 也兼容一下
                return fn(**(arguments or {}))
            except MCPToolError as e:
                return {"ok": False, "error": e.to_dict()}
            except BaseException as e:  # noqa: BLE001
                log.exception("tool %s failed", tool_name)
                return {"ok": False, "error": wrap_exception(e)}
    return {"ok": False, "error": {"code": "unknown_tool", "message": f"no tool named {tool_name!r}"}}


# -----------------------------------------------------------------------------
# MCP Server + SSE ASGI 搭建

def build_mcp_server():
    """构造 mcp.Server 实例并注册工具。

    兼容两种 mcp SDK：
      1) 新版（1.x）：`Server.list_tools` / `Server.call_tool` 装饰器
      2) 旧版：`Server.register_tool` 手动调用
    """
    from mcp.server import Server
    import mcp.types as mcp_types

    server = Server("o3de-editor")

    # 新式 API
    @server.list_tools()
    async def _list_tools():
        return [
            mcp_types.Tool(
                name=n,
                description=d,
                inputSchema=s,
            )
            for (n, _fn, d, s) in _TOOLS
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict | None):
        result = await dispatch(name, arguments or {})
        # 包成 MCP 文本 content
        import json as _json
        return [
            mcp_types.TextContent(
                type="text",
                text=_json.dumps(result, ensure_ascii=False, default=str),
            )
        ]

    return server


def build_asgi_app():
    """用 starlette 把 mcp Server + SSE transport 挂成 ASGI app。

    端点：
        GET  /sse       SSE 流（MCP spec 约定）
        POST /messages  MCP 消息
        GET  /health    简单 health check（非 MCP 工具）
    """
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Mount, Route
    except ImportError as e:
        raise RuntimeError(
            "starlette not installed. pip install starlette uvicorn"
        ) from e

    from mcp.server.sse import SseServerTransport

    server = build_mcp_server()
    sse_transport = SseServerTransport("/messages")

    async def sse_handler(request: Request):
        # 鉴权
        if not _check_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send,
        ) as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
        return JSONResponse({"ok": True})  # 实际不会到这里

    async def health_handler(request: Request):
        from . import threading_bridge as tb
        return JSONResponse({
            "ok": True,
            "pump_mode": tb.pump_mode(),
            "config": {
                "host": config.HOST,
                "port": config.PORT,
                "auto_approve": config.AUTO_APPROVE,
                "allow_destructive": config.ALLOW_DESTRUCTIVE,
                "allow_exec_python": config.ALLOW_EXEC_PYTHON,
            },
        })

    routes = [
        Route("/sse", endpoint=sse_handler),
        Mount("/messages", app=sse_transport.handle_post_message),
        Route("/health", endpoint=health_handler),
    ]
    return Starlette(routes=routes)


def _check_auth(request) -> bool:
    """检查 Authorization: Bearer <token> header。"""
    if not config.AUTH_TOKEN:
        # 没配 token = 开放（只本机 127.0.0.1 时接受）
        return True
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token == config.AUTH_TOKEN
    return False


async def serve() -> None:
    """在 worker 线程的 asyncio loop 里跑。永远不返回。"""
    import uvicorn

    app = build_asgi_app()
    server_cfg = uvicorn.Config(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        lifespan="off",
    )
    server = uvicorn.Server(server_cfg)
    await server.serve()
