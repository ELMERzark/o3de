"""transform.* handler —— 变换操作

工具：
    - transform.set_translation      set world translation (Vector3)
    - transform.set_rotation_euler   set world rotation from Euler angles (degrees)
    - transform.set_scale            set local scale (uniform or per-axis)
    - transform.get                  get current world translation + euler + scale
"""

from __future__ import annotations

import math as _math_mod

from ..ids import parse_entity_id
from ..serialize import deserialize, serialize
from ..threading_bridge import call_on_main


async def set_translation(entity_id: str, translation: dict, local: bool = False) -> dict:
    """translation: {"__type":"Vector3","x":..,"y":..,"z":..}
    local=True 用 SetLocalTranslation。
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components

        eid = parse_entity_id(entity_id)
        vec = deserialize(translation)
        method = "SetLocalTranslation" if local else "SetWorldTranslation"
        components.TransformBus(bus.Event, method, eid, vec)
        return True

    await call_on_main(_do)
    return {"entity_id": entity_id, "translation": translation, "local": local}


async def set_rotation_euler(
    entity_id: str,
    euler_deg: dict,
    local: bool = False,
) -> dict:
    """euler_deg: {"x":<pitch>, "y":<roll>, "z":<yaw>} in degrees
    转成 Quaternion 再调 SetWorldRotation/SetLocalRotation。
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components
        import azlmbr.math as math_mod

        eid = parse_entity_id(entity_id)
        x = _math_mod.radians(float(euler_deg.get("x", 0.0)))
        y = _math_mod.radians(float(euler_deg.get("y", 0.0)))
        z = _math_mod.radians(float(euler_deg.get("z", 0.0)))

        # Quaternion from euler: 优先用 azlmbr.math 的静态工厂
        q = None
        for ctor_name in ("CreateFromEulerRadians", "CreateFromEulerAnglesRadians"):
            ctor = getattr(math_mod.Quaternion, ctor_name, None)
            if callable(ctor):
                try:
                    vec = math_mod.Vector3(x, y, z)
                    q = ctor(vec)
                    break
                except Exception:
                    try:
                        q = ctor(x, y, z)
                        break
                    except Exception:
                        pass
        if q is None:
            # 手算 ZYX Euler -> Quaternion（右手坐标，Z 上）
            cx, sx = _math_mod.cos(x / 2), _math_mod.sin(x / 2)
            cy, sy = _math_mod.cos(y / 2), _math_mod.sin(y / 2)
            cz, sz = _math_mod.cos(z / 2), _math_mod.sin(z / 2)
            qw = cx * cy * cz + sx * sy * sz
            qx = sx * cy * cz - cx * sy * sz
            qy = cx * sy * cz + sx * cy * sz
            qz = cx * cy * sz - sx * sy * cz
            q = math_mod.Quaternion(qx, qy, qz, qw)

        method = "SetLocalRotationQuaternion" if local else "SetWorldRotationQuaternion"
        components.TransformBus(bus.Event, method, eid, q)
        return True

    await call_on_main(_do)
    return {"entity_id": entity_id, "euler_deg": euler_deg, "local": local}


async def set_scale(entity_id: str, scale: float | dict) -> dict:
    """scale 可以是：
        - float：均匀缩放
        - {"__type":"Vector3", ...}: 非均匀（传入的 _type 会被 serialize 处理）
    """
    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components
        import azlmbr.math as math_mod

        eid = parse_entity_id(entity_id)
        if isinstance(scale, (int, float)):
            components.TransformBus(bus.Event, "SetLocalUniformScale", eid, float(scale))
        else:
            vec = deserialize(scale)
            # 非均匀缩放 API 视 O3DE 版本可能叫 SetLocalScale 或 SetLocalNonUniformScale
            for method in ("SetLocalNonUniformScale", "SetLocalScale"):
                try:
                    components.TransformBus(bus.Event, method, eid, vec)
                    return True
                except Exception:
                    continue
            # 最后退到均匀缩放用 x 分量
            components.TransformBus(
                bus.Event, "SetLocalUniformScale", eid,
                float(vec.GetX() if hasattr(vec, "GetX") else vec.x),
            )
        return True

    await call_on_main(_do)
    return {"entity_id": entity_id, "scale": scale}


async def get(entity_id: str) -> dict:
    """返回 world translation + euler + scale。"""
    def _do():
        import azlmbr.bus as bus
        import azlmbr.components as components

        eid = parse_entity_id(entity_id)
        translation = components.TransformBus(bus.Event, "GetWorldTranslation", eid)
        scale_u = None
        try:
            scale_u = components.TransformBus(bus.Event, "GetLocalUniformScale", eid)
        except Exception:
            pass

        # Euler：把 Quaternion 转过来
        euler = None
        try:
            q = components.TransformBus(bus.Event, "GetWorldRotationQuaternion", eid)
            # q -> euler
            for getter_name in ("GetEulerDegrees", "GetEulerRadians"):
                get_euler = getattr(q, getter_name, None)
                if callable(get_euler):
                    try:
                        v = get_euler()
                        euler = {
                            "x": float(v.x) if getter_name.endswith("Degrees") else _math_mod.degrees(float(v.x)),
                            "y": float(v.y) if getter_name.endswith("Degrees") else _math_mod.degrees(float(v.y)),
                            "z": float(v.z) if getter_name.endswith("Degrees") else _math_mod.degrees(float(v.z)),
                        }
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "translation": translation,
            "euler_deg": euler,
            "uniform_scale": scale_u,
        }

    result = await call_on_main(_do)
    return {
        "entity_id": entity_id,
        "translation": serialize(result["translation"]),
        "euler_deg": result["euler_deg"],
        "uniform_scale": result["uniform_scale"],
    }
