"""EntityId / AssetId / 组件引用 的 JSON 字符串表示与解析。

约定：
    EntityId   <->  "Entity[0xABCDEF01]"
    AssetId    <->  "Asset[{uuid}:subId]"
    Component  <->  "Comp[{uuid}:{type_id}]"   由 EditorComponentAPIBus 返回的
                                                 ComponentInfo 里抽取 id + type

这些格式来自 azlmbr 各类型自然的 .ToString() 输出，保持对齐。
"""

from __future__ import annotations

import re
from typing import Any

from .errors import MCPToolError, CODE_INVALID_ARGUMENT


# ---- EntityId ----

_ENTITY_RE = re.compile(r"^Entity\[(0x[0-9a-fA-F]+|\d+)\]$")


def stringify_entity_id(eid: Any) -> str:
    """azlmbr.entity.EntityId -> 'Entity[0x...]'"""
    if eid is None:
        return "Entity[invalid]"
    try:
        s = str(eid)  # 多数情况直接 __str__ 就是 Entity[...]
    except Exception:
        s = "Entity[invalid]"
    if s.startswith("Entity["):
        return s
    # 备选：eid.ToString()
    to_string = getattr(eid, "ToString", None)
    if callable(to_string):
        return str(to_string())
    return s


def parse_entity_id(s: str | None):
    """'Entity[0x...]' -> azlmbr.entity.EntityId

    None -> invalid EntityId（代表根）
    """
    import azlmbr.entity as _entity  # type: ignore[import]

    if s is None or s == "" or s == "Entity[invalid]":
        return _entity.EntityId()
    m = _ENTITY_RE.match(s)
    if not m:
        raise MCPToolError(
            CODE_INVALID_ARGUMENT,
            f"Not a valid EntityId string: {s!r}",
            expected_format="Entity[0x...]",
        )
    raw = m.group(1)
    value = int(raw, 16) if raw.startswith("0x") else int(raw)
    return _entity.EntityId(value)


# ---- AssetId ----

_ASSET_RE = re.compile(r"^Asset\[([^\]:]+)(?::(\d+))?\]$")


def stringify_asset_id(aid: Any) -> str:
    """azlmbr.asset.AssetId -> 'Asset[{uuid}:0]'"""
    if aid is None:
        return "Asset[invalid]"
    # 优先试 .ToString()
    to_string = getattr(aid, "ToString", None)
    if callable(to_string):
        return "Asset[" + str(to_string()).strip("{}") + "]"
    return str(aid)


def parse_asset_id(s: str):
    """'Asset[{uuid}:subid]' -> azlmbr.asset.AssetId"""
    import azlmbr.asset as _asset  # type: ignore[import]
    import azlmbr.math as _math  # type: ignore[import]

    m = _ASSET_RE.match(s)
    if not m:
        raise MCPToolError(
            CODE_INVALID_ARGUMENT,
            f"Not a valid AssetId string: {s!r}",
            expected_format="Asset[{uuid}:subId]",
        )
    uuid_str = m.group(1)
    sub_id = int(m.group(2) or "0")
    try:
        uuid = _math.Uuid.CreateString(uuid_str)
    except Exception:
        uuid = _math.Uuid(uuid_str)
    try:
        return _asset.AssetId(uuid, sub_id)
    except Exception:
        # 某些 SDK 版本签名不同
        return _asset.AssetId(uuid)


# ---- Component 引用 ----
#
# EditorComponentAPIBus 返回的 component 实际上是一个带 EntityComponentIdPair 的 Python 对象。
# 我们 stringify 成 "Comp[{entity_id_hex}:{component_id}]"，parse 回去时重建这个 pair。
#
# 注意：这是我们自己约定的格式，不是引擎原生的。


_COMP_RE = re.compile(r"^Comp\[(0x[0-9a-fA-F]+|\d+):(\d+)\]$")


def stringify_component_ref(component: Any) -> str:
    """把 EditorComponentAPIBus 返回的 component 对象转字符串。

    尝试多种字段名（不同 MAF / O3DE 版本可能不同）。
    """
    # 先试最常见字段
    entity_id = None
    component_id = None
    for ename in ("entityId", "entity_id", "EntityId"):
        if hasattr(component, ename):
            entity_id = getattr(component, ename)
            break
    for cname in ("componentId", "component_id", "ComponentId"):
        if hasattr(component, cname):
            component_id = getattr(component, cname)
            break

    if entity_id is None or component_id is None:
        # 退化 fallback：直接 str()
        return f"Comp[unknown:{id(component):x}]"

    eid_str = stringify_entity_id(entity_id)
    # 从 "Entity[0xABC]" 抽出 0xABC
    m = _ENTITY_RE.match(eid_str)
    eid_hex = m.group(1) if m else "0x0"

    # component_id 可能是一个对象或 int
    cid_int = int(component_id) if isinstance(component_id, (int, str)) else int(str(component_id))
    return f"Comp[{eid_hex}:{cid_int}]"


def parse_component_ref(s: str):
    """'Comp[0xABC:123]' -> EntityComponentIdPair 可用的 azlmbr 对象。

    现阶段策略：parse 出 (entity_id, component_id) 两个值，由 handler 自己组装成
    EditorComponentAPIBus 接受的参数形式（多数场景是 component object，而不是 pair；
    这里保留两个 id，交由 handler 用 `EditorComponentAPIBus::GetComponentOfType` 反查）。
    """
    m = _COMP_RE.match(s)
    if not m:
        raise MCPToolError(
            CODE_INVALID_ARGUMENT,
            f"Not a valid Component ref: {s!r}",
            expected_format="Comp[0x...:<int>]",
        )
    raw_eid = m.group(1)
    eid_int = int(raw_eid, 16) if raw_eid.startswith("0x") else int(raw_eid)
    cid_int = int(m.group(2))

    import azlmbr.entity as _entity  # type: ignore[import]

    return {
        "entity_id": _entity.EntityId(eid_int),
        "component_id": cid_int,
    }
