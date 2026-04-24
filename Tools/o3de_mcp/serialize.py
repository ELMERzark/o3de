"""JSON ↔ azlmbr 类型 marshal。

约定（和 docs_claud/editor_mcp/01_architecture.md §7 对齐）：

    JSON                                              <->  Python (azlmbr)
    ---------------------------------------------------------------------
    "Entity[0x...]"                                        azlmbr.entity.EntityId
    "Asset[{uuid}:subId]"                                  azlmbr.asset.AssetId
    {"__type":"Vector3","x":1,"y":2,"z":3}                 azlmbr.math.Vector3
    {"__type":"Color","r":0,"g":1,"b":0,"a":1}             azlmbr.math.Color
    {"__type":"Quaternion","x":0,"y":0,"z":0,"w":1}        azlmbr.math.Quaternion
    {"__type":"Uuid","value":"550e..."}                    azlmbr.math.Uuid
    基本类型 (str/int/float/bool/list/dict)               自身

所有 handler 的入参 value / 出参 value 都要过这两个函数。
"""

from __future__ import annotations

from typing import Any

from .errors import MCPToolError, CODE_INVALID_ARGUMENT
from .ids import (
    parse_asset_id,
    parse_entity_id,
    stringify_asset_id,
    stringify_entity_id,
)


# ---- Python -> Azlmbr ----

def deserialize(value: Any) -> Any:
    """JSON 值 -> azlmbr 原生对象（或原样）。"""
    if isinstance(value, dict) and "__type" in value:
        t = value["__type"]
        import azlmbr.math as _math  # type: ignore[import]
        if t == "Vector3":
            return _math.Vector3(float(value["x"]), float(value["y"]), float(value["z"]))
        if t == "Vector2":
            return _math.Vector2(float(value["x"]), float(value["y"]))
        if t == "Vector4":
            return _math.Vector4(
                float(value["x"]), float(value["y"]),
                float(value["z"]), float(value["w"]),
            )
        if t == "Color":
            return _math.Color(
                float(value.get("r", 0.0)),
                float(value.get("g", 0.0)),
                float(value.get("b", 0.0)),
                float(value.get("a", 1.0)),
            )
        if t == "Quaternion":
            return _math.Quaternion(
                float(value["x"]), float(value["y"]),
                float(value["z"]), float(value["w"]),
            )
        if t == "Uuid":
            try:
                return _math.Uuid.CreateString(str(value["value"]))
            except Exception:
                return _math.Uuid(str(value["value"]))
        if t == "EntityId":
            return parse_entity_id(value.get("value"))
        if t == "AssetId":
            return parse_asset_id(value["value"])
        raise MCPToolError(
            CODE_INVALID_ARGUMENT,
            f"Unknown __type: {t!r}",
        )

    # 不带 __type 的字符串：尝试识别 "Entity[...]" / "Asset[...]"
    if isinstance(value, str):
        if value.startswith("Entity["):
            return parse_entity_id(value)
        if value.startswith("Asset["):
            return parse_asset_id(value)

    # 基本类型 / list / dict：原样（列表里递归）
    if isinstance(value, list):
        return [deserialize(v) for v in value]

    return value


# ---- Azlmbr -> Python ----

def serialize(value: Any) -> Any:
    """azlmbr 对象 -> JSON-serializable 值。"""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}

    # azlmbr 类型嗅探
    cls_name = type(value).__name__

    if cls_name == "EntityId":
        return stringify_entity_id(value)
    if cls_name == "AssetId":
        return stringify_asset_id(value)
    if cls_name == "Vector3":
        return {"__type": "Vector3", "x": _flt(value, "x"), "y": _flt(value, "y"), "z": _flt(value, "z")}
    if cls_name == "Vector2":
        return {"__type": "Vector2", "x": _flt(value, "x"), "y": _flt(value, "y")}
    if cls_name == "Vector4":
        return {
            "__type": "Vector4",
            "x": _flt(value, "x"), "y": _flt(value, "y"),
            "z": _flt(value, "z"), "w": _flt(value, "w"),
        }
    if cls_name == "Color":
        return {
            "__type": "Color",
            "r": _flt(value, "r"), "g": _flt(value, "g"),
            "b": _flt(value, "b"), "a": _flt(value, "a", default=1.0),
        }
    if cls_name == "Quaternion":
        return {
            "__type": "Quaternion",
            "x": _flt(value, "x"), "y": _flt(value, "y"),
            "z": _flt(value, "z"), "w": _flt(value, "w"),
        }
    if cls_name == "Uuid":
        to_string = getattr(value, "ToString", None)
        return {"__type": "Uuid", "value": str(to_string()) if callable(to_string) else str(value)}

    # 未知类型：退化 str()。不崩，但 Agent 收到后可能需要人工处理
    return {"__type": cls_name, "_repr": str(value)}


def _flt(obj: Any, attr: str, default: float = 0.0) -> float:
    """读 obj.attr / obj.Get<Attr>() / obj[attr]，都失败给 default。"""
    try:
        v = getattr(obj, attr)
        if callable(v):
            v = v()
        return float(v)
    except Exception:
        pass
    try:
        getter = getattr(obj, f"Get{attr.capitalize()}", None)
        if callable(getter):
            return float(getter())
    except Exception:
        pass
    try:
        return float(obj[attr])
    except Exception:
        return default
