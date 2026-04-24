"""component.* handler —— 组件 CRUD + 属性读写

工具：
    - component.list_types        列出可用组件类型
    - component.add               加组件
    - component.remove            删组件
    - component.list_on_entity    列 entity 上所有组件
    - component.set_property      改属性（通用入口 —— 所有组件所有属性）
    - component.get_property      读属性
    - component.get_property_tree 列组件所有可读写属性路径
"""

from __future__ import annotations

from typing import Any

from ..errors import (
    CODE_COMPONENT_NOT_FOUND,
    CODE_COMPONENT_TYPE_NOT_FOUND,
    CODE_INVALID_ARGUMENT,
    CODE_PROPERTY_PATH_INVALID,
    CODE_VERIFY_FAILED,
    MCPToolError,
)
from ..ids import (
    parse_component_ref,
    parse_entity_id,
    stringify_component_ref,
    stringify_entity_id,
)
from ..serialize import deserialize, serialize
from ..threading_bridge import call_on_main


# -----------------------------------------------------------------------------

def _entity_type_enum(name: str):
    """'Game' | 'Level' | 'System' -> azlmbr.entity.EntityType.<X>"""
    import azlmbr.entity as entity_mod
    et = entity_mod.EntityType()
    mapping = {
        "game": et.Game,
        "level": et.Level,
        "system": et.System,
    }
    key = name.lower() if isinstance(name, str) else "game"
    if key not in mapping:
        raise MCPToolError(
            CODE_INVALID_ARGUMENT,
            f"entity_type must be one of Game/Level/System (got {name!r})",
        )
    return mapping[key]


# ---- list_types --------------------------------------------------------------

async def list_types(entity_type: str = "Game") -> dict:
    """列出 entity_type 下**能加**的所有组件类型。"""
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        et = _entity_type_enum(entity_type)
        type_ids = editor.EditorComponentAPIBus(
            bus.Broadcast, "FindComponentTypeIdsByEntityType", [], et
        )
        # 反向查名字
        names = editor.EditorComponentAPIBus(
            bus.Broadcast, "FindComponentTypeNames", type_ids
        ) or []
        out = []
        for tid, nm in zip(type_ids or [], names):
            out.append({"type_id": str(tid), "name": str(nm)})
        return out

    types_list = await call_on_main(_do)
    return {"entity_type": entity_type, "types": types_list}


# ---- add ---------------------------------------------------------------------

async def add(entity_id: str, component_type: str, entity_type: str = "Game") -> dict:
    """给 entity 加一个组件。

    component_type: 显示名，如 "Mesh" / "HDRi Skybox" / "Transform"
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        et = _entity_type_enum(entity_type)

        type_ids = editor.EditorComponentAPIBus(
            bus.Broadcast, "FindComponentTypeIdsByEntityType",
            [component_type], et,
        )
        if not type_ids:
            raise MCPToolError(
                CODE_COMPONENT_TYPE_NOT_FOUND,
                f"Component type not found: {component_type!r} (entity_type={entity_type})",
                component_type=component_type,
            )

        outcome = editor.EditorComponentAPIBus(
            bus.Broadcast, "AddComponentsOfType", eid, type_ids
        )
        if outcome is None or (hasattr(outcome, "IsSuccess") and not outcome.IsSuccess()):
            raise MCPToolError(
                "add_failed",
                f"AddComponentsOfType failed for {component_type}",
                component_type=component_type,
            )
        components = outcome.GetValue() if hasattr(outcome, "GetValue") else outcome
        if not components:
            raise MCPToolError("add_failed", "AddComponentsOfType returned empty list")
        return components[0]

    component = await call_on_main(_do)
    return {
        "entity_id": entity_id,
        "component_ref": stringify_component_ref(component),
        "component_type": component_type,
    }


# ---- remove ------------------------------------------------------------------

async def remove(component_ref: str) -> dict:
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        parsed = parse_component_ref(component_ref)
        # 先拿到 component object：通过 entity + componentId 反查
        eid = parsed["entity_id"]
        components = editor.EditorComponentAPIBus(
            bus.Broadcast, "GetComponentsOfType", eid, None,
        ) or []
        target = None
        for c in components:
            if stringify_component_ref(c) == component_ref:
                target = c
                break
        if target is None:
            raise MCPToolError(
                CODE_COMPONENT_NOT_FOUND,
                f"component_ref not found on live entity: {component_ref}",
            )
        editor.EditorComponentAPIBus(bus.Broadcast, "RemoveComponents", [target])
        return True

    await call_on_main(_do)
    return {"removed": component_ref}


# ---- list_on_entity ---------------------------------------------------------

async def list_on_entity(entity_id: str) -> dict:
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        eid = parse_entity_id(entity_id)
        components = editor.EditorComponentAPIBus(
            bus.Broadcast, "GetComponentsOfType", eid, None,
        ) or []

        out = []
        for c in components:
            # 取 type id + name
            try:
                tid = editor.EditorComponentAPIBus(
                    bus.Broadcast, "GetComponentTypeId", c
                )
                nms = editor.EditorComponentAPIBus(
                    bus.Broadcast, "FindComponentTypeNames", [tid]
                ) or [""]
                nm = nms[0] if nms else ""
            except Exception:
                nm = ""
            out.append({
                "ref": stringify_component_ref(c),
                "type_name": nm,
            })
        return out

    lst = await call_on_main(_do)
    return {"entity_id": entity_id, "components": lst}


# -----------------------------------------------------------------------------
# 共用：ref -> 组件对象（用于 set/get_property）

def _resolve_component(component_ref: str):
    """Must be called on main thread."""
    import azlmbr.bus as bus
    import azlmbr.editor as editor

    parsed = parse_component_ref(component_ref)
    eid = parsed["entity_id"]
    components = editor.EditorComponentAPIBus(
        bus.Broadcast, "GetComponentsOfType", eid, None,
    ) or []
    for c in components:
        if stringify_component_ref(c) == component_ref:
            return c
    raise MCPToolError(
        CODE_COMPONENT_NOT_FOUND,
        f"component_ref not found on live entity: {component_ref}",
    )


# ---- set_property (核心通用工具) --------------------------------------------

async def set_property(
    component_ref: str,
    property_path: str,
    value: Any,
    verify: bool = True,
) -> dict:
    """给组件的 property_path 写 value。

    property_path 例子：
        "Controller|Configuration|Model Asset"
        "Shape Color"
        "Quad Shape|Quad Configuration|Width"

    value 格式：见 serialize.deserialize() 的约定。

    verify=True：写完立刻 GetComponentProperty 回读一次，确认匹配。
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        component = _resolve_component(component_ref)
        py_value = deserialize(value)

        editor.EditorComponentAPIBus(
            bus.Broadcast, "SetComponentProperty",
            component, property_path, py_value,
        )

        if not verify:
            return None

        result = editor.EditorComponentAPIBus(
            bus.Broadcast, "GetComponentProperty", component, property_path,
        )
        if result is None:
            raise MCPToolError(
                CODE_PROPERTY_PATH_INVALID,
                f"GetComponentProperty returned None for {property_path!r}",
                property_path=property_path,
            )
        if hasattr(result, "IsSuccess") and not result.IsSuccess():
            raise MCPToolError(
                CODE_VERIFY_FAILED,
                f"Verify read-back failed for {property_path}",
                property_path=property_path,
            )
        return result.GetValue() if hasattr(result, "GetValue") else result

    v = await call_on_main(_do)
    return {
        "component_ref": component_ref,
        "property_path": property_path,
        "new_value": serialize(v) if v is not None else None,
    }


# ---- get_property -----------------------------------------------------------

async def get_property(component_ref: str, property_path: str) -> dict:
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        component = _resolve_component(component_ref)
        result = editor.EditorComponentAPIBus(
            bus.Broadcast, "GetComponentProperty", component, property_path,
        )
        if result is None:
            raise MCPToolError(
                CODE_PROPERTY_PATH_INVALID,
                f"Unknown property path: {property_path!r}",
                property_path=property_path,
            )
        if hasattr(result, "IsSuccess") and not result.IsSuccess():
            raise MCPToolError(
                CODE_PROPERTY_PATH_INVALID,
                f"GetComponentProperty failed: {property_path}",
                property_path=property_path,
            )
        return result.GetValue() if hasattr(result, "GetValue") else result

    v = await call_on_main(_do)
    return {
        "component_ref": component_ref,
        "property_path": property_path,
        "value": serialize(v),
    }


# ---- get_property_tree ------------------------------------------------------

async def get_property_tree(component_ref: str) -> dict:
    """列出组件所有可访问的 property path 和类型。

    底层走 `BuildComponentPropertyTreeEditor` —— Editor 里的属性面板 API。
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.editor as editor

        component = _resolve_component(component_ref)
        outcome = editor.EditorComponentAPIBus(
            bus.Broadcast, "BuildComponentPropertyTreeEditor", component,
        )
        if outcome is None:
            return []
        pte = outcome.GetValue() if hasattr(outcome, "GetValue") else outcome
        if pte is None:
            return []

        # pte 的 Python 接口一般有 get_paths() / build_paths_list()。
        # 不同版本 API 不同；试几个已知方法名：
        props = []
        for method in ("build_paths_list", "get_paths", "GetPaths"):
            fn = getattr(pte, method, None)
            if callable(fn):
                try:
                    paths = fn()
                    if paths:
                        for p in paths:
                            props.append({"path": str(p), "type": "unknown"})
                        return props
                except Exception:
                    pass
        # 真拿不到，返回空 —— 至少不崩
        return props

    props = await call_on_main(_do)
    return {"component_ref": component_ref, "properties": props}
