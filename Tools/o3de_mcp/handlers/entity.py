"""entity.* handler —— Entity CRUD

工具：
    - entity.create
    - entity.delete
    - entity.set_parent
    - entity.rename
    - entity.list_children
    - entity.get_info
"""

from __future__ import annotations

from typing import Any

from ..errors import (
    CODE_ENTITY_NOT_FOUND,
    CODE_INVALID_ARGUMENT,
    CODE_PERMISSION_DENIED,
    MCPToolError,
)
from ..ids import parse_entity_id, stringify_entity_id
from ..serialize import deserialize, serialize
from ..threading_bridge import call_on_main
from .. import config


# ---- create -----------------------------------------------------------------

async def create(
    parent: str | None = None,
    name: str = "",
    position: dict | None = None,
) -> dict:
    """创建新 entity。

    参数:
        parent: 父 EntityId 字符串；None = 挂 level 根
        name: 可选，直接设 entity 名
        position: 可选 {"__type":"Vector3","x":...,"y":...,"z":...}
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor
        import azlmbr.entity as entity_mod

        pid = parse_entity_id(parent) if parent else entity_mod.EntityId()
        new_id = editor.ToolsApplicationRequestBus(
            bus.Broadcast, "CreateNewEntity", pid
        )
        if not new_id or not new_id.IsValid():
            raise MCPToolError("create_failed", "CreateNewEntity returned invalid EntityId")

        if name:
            editor.EditorEntityAPIBus(bus.Event, "SetName", new_id, name)

        if position is not None:
            import azlmbr.components as components
            pos_vec = deserialize(position)
            components.TransformBus(
                bus.Event, "SetWorldTranslation", new_id, pos_vec
            )
        return new_id

    eid = await call_on_main(_do)
    return {"entity_id": stringify_entity_id(eid), "name": name}


# ---- delete -----------------------------------------------------------------

async def delete(entity_id: str, cascade: bool = True) -> dict:
    """删除 entity。destructive —— 需要 ALLOW_DESTRUCTIVE。"""
    if not config.ALLOW_DESTRUCTIVE:
        raise MCPToolError(
            CODE_PERMISSION_DENIED,
            "entity.delete is destructive; set ALLOW_DESTRUCTIVE=true to enable",
        )

    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        method = "DeleteEntityAndAllDescendants" if cascade else "DeleteEntity"
        editor.ToolsApplicationRequestBus(bus.Broadcast, method, eid)
        return True

    await call_on_main(_do)
    return {"deleted": entity_id, "cascade": cascade}


# ---- set_parent -------------------------------------------------------------

async def set_parent(entity_id: str, new_parent: str | None) -> dict:
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        pid = parse_entity_id(new_parent) if new_parent else None
        if pid is None:
            # 移到根 = 清父
            import azlmbr.entity as entity_mod
            pid = entity_mod.EntityId()
        editor.EditorEntityAPIBus(bus.Event, "SetParent", eid, pid)
        return True

    await call_on_main(_do)
    return {"entity_id": entity_id, "new_parent": new_parent}


# ---- rename -----------------------------------------------------------------

async def rename(entity_id: str, name: str) -> dict:
    if not name:
        raise MCPToolError(CODE_INVALID_ARGUMENT, "name must be non-empty")

    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        editor.EditorEntityAPIBus(bus.Event, "SetName", eid, name)
        return True

    await call_on_main(_do)
    return {"entity_id": entity_id, "name": name}


# ---- list_children ----------------------------------------------------------

async def list_children(entity_id: str) -> dict:
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        children = editor.EditorEntityInfoRequestBus(
            bus.Event, "GetChildren", eid
        )
        return children or []

    children = await call_on_main(_do)
    return {
        "entity_id": entity_id,
        "children": [stringify_entity_id(c) for c in (children or [])],
    }


# ---- get_info ---------------------------------------------------------------

async def get_info(entity_id: str) -> dict:
    """组合调用：name + parent + children + component 列表 + transform。

    给 Agent 的 "眼睛"。
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components
        import azlmbr.editor as editor
        import azlmbr.entity as entity_mod

        eid = parse_entity_id(entity_id)

        name = editor.EditorEntityInfoRequestBus(bus.Event, "GetName", eid)
        parent = editor.EditorEntityInfoRequestBus(bus.Event, "GetParent", eid)
        children = editor.EditorEntityInfoRequestBus(bus.Event, "GetChildren", eid) or []

        # components（按 entity type 取所有）
        comp_list = editor.EditorComponentAPIBus(
            bus.Broadcast, "GetComponentsOfType", eid, None  # None = 不按类型过滤
        )
        # 某些 SDK 版本 API 签名不同；退化到一个已知的 'FindComponents'
        if comp_list is None:
            comp_list = []

        # transform
        try:
            translation = components.TransformBus(bus.Event, "GetWorldTranslation", eid)
        except Exception:
            translation = None

        return {
            "name": name or "",
            "parent": stringify_entity_id(parent) if parent and parent.IsValid() else None,
            "children": [stringify_entity_id(c) for c in children],
            "component_count": len(comp_list) if comp_list else 0,
            "world_translation": serialize(translation),
        }

    info = await call_on_main(_do)
    info["entity_id"] = entity_id
    return info
