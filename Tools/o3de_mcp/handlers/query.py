"""query.* handler —— 场景观察（Agent 的眼睛）

工具：
    - query.find_by_name            按名字找
    - query.find_by_component_type  按组件类型找
    - query.scene_snapshot          整棵 entity 树的 JSON 快照
"""

from __future__ import annotations

from typing import Any

from .. import config
from ..errors import CODE_INVALID_ARGUMENT, MCPToolError
from ..ids import stringify_entity_id
from ..serialize import serialize
from ..threading_bridge import call_on_main


async def find_by_name(name: str, exact: bool = True) -> dict:
    """按 entity 名字搜。exact=False 用子串匹配。"""
    if not name and exact:
        raise MCPToolError(CODE_INVALID_ARGUMENT, "name required when exact=True")

    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor
        import azlmbr.entity as entity_mod

        # SearchBus API 不同版本签名不同；先试 SearchEntities(SearchFilter)
        SearchFilter = getattr(entity_mod, "SearchFilter", None)
        if SearchFilter is not None:
            flt = SearchFilter()
            # 各字段名/存在性视版本而定
            for fname in ("names", "Names"):
                if hasattr(flt, fname):
                    setattr(flt, fname, [name])
                    break

            try:
                results = entity_mod.SearchBus(bus.Broadcast, "SearchEntities", flt) or []
                return [e for e in results]
            except Exception:
                pass

        # 退化：遍历所有 entity 比 name
        all_ids = editor.ToolsApplicationRequestBus(
            bus.Broadcast, "GetAllEntities"
        ) or []
        out = []
        for eid in all_ids:
            n = editor.EditorEntityInfoRequestBus(bus.Event, "GetName", eid) or ""
            if (exact and n == name) or (not exact and name in n):
                out.append(eid)
        return out

    eids = await call_on_main(_do)
    return {
        "name": name,
        "exact": exact,
        "entities": [stringify_entity_id(e) for e in eids],
    }


async def find_by_component_type(component_type: str, entity_type: str = "Game") -> dict:
    """找所有挂了某个组件类型的 entity。"""
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor
        import azlmbr.entity as entity_mod

        # 组件 type_id
        et_enum = entity_mod.EntityType()
        et = getattr(et_enum, entity_type if isinstance(entity_type, str) else "Game", et_enum.Game)

        type_ids = editor.EditorComponentAPIBus(
            bus.Broadcast, "FindComponentTypeIdsByEntityType",
            [component_type], et,
        )
        if not type_ids:
            return []

        # 遍历所有 entity，检查是否含此 type
        all_ids = editor.ToolsApplicationRequestBus(
            bus.Broadcast, "GetAllEntities"
        ) or []
        out = []
        for eid in all_ids:
            has = False
            try:
                has = editor.EditorComponentAPIBus(
                    bus.Broadcast, "HasComponentOfType", eid, type_ids[0],
                )
            except Exception:
                # 退化：GetComponentsOfType + check
                comps = editor.EditorComponentAPIBus(
                    bus.Broadcast, "GetComponentsOfType", eid, None
                ) or []
                for c in comps:
                    tid = editor.EditorComponentAPIBus(
                        bus.Broadcast, "GetComponentTypeId", c
                    )
                    if str(tid) == str(type_ids[0]):
                        has = True
                        break
            if has:
                out.append(eid)
        return out

    eids = await call_on_main(_do)
    return {
        "component_type": component_type,
        "entity_type": entity_type,
        "entities": [stringify_entity_id(e) for e in eids],
    }


async def scene_snapshot(
    include_components: bool = True,
    include_transforms: bool = True,
    max_depth: int = 3,
    max_entities: int | None = None,
) -> dict:
    """返回整棵 entity 树的摘要。给 Agent 决策前看一眼。"""
    limit = max_entities if max_entities is not None else config.MAX_ENTITIES_IN_SNAPSHOT

    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components
        import azlmbr.editor as editor

        all_ids = editor.ToolsApplicationRequestBus(
            bus.Broadcast, "GetAllEntities",
        ) or []
        out = []
        for eid in all_ids[:limit]:
            entry: dict = {"entity_id": stringify_entity_id(eid)}

            try:
                entry["name"] = editor.EditorEntityInfoRequestBus(bus.Event, "GetName", eid) or ""
            except Exception:
                entry["name"] = ""

            try:
                parent = editor.EditorEntityInfoRequestBus(bus.Event, "GetParent", eid)
                entry["parent"] = (
                    stringify_entity_id(parent) if parent and parent.IsValid() else None
                )
            except Exception:
                entry["parent"] = None

            if include_components:
                try:
                    comps = editor.EditorComponentAPIBus(
                        bus.Broadcast, "GetComponentsOfType", eid, None
                    ) or []
                    names = []
                    for c in comps:
                        try:
                            tid = editor.EditorComponentAPIBus(
                                bus.Broadcast, "GetComponentTypeId", c
                            )
                            nms = editor.EditorComponentAPIBus(
                                bus.Broadcast, "FindComponentTypeNames", [tid]
                            ) or [""]
                            names.append(str(nms[0]) if nms else "")
                        except Exception:
                            names.append("?")
                    entry["components"] = names
                except Exception:
                    entry["components"] = []

            if include_transforms:
                try:
                    t = components.TransformBus(bus.Event, "GetWorldTranslation", eid)
                    entry["translation"] = serialize(t)
                except Exception:
                    entry["translation"] = None

            out.append(entry)

        truncated = len(all_ids) > limit
        return {"entities": out, "total": len(all_ids), "truncated": truncated}

    result = await call_on_main(_do)
    return result
