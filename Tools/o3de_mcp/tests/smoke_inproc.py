"""In-process smoke test —— 作为 Editor --runpython 跑。

不经过 MCP 协议，直接调 handler。用于隔离"azlmbr handler 自己通不通"的问题。

用法：
    Editor --runpython Tools/o3de_mcp/tests/smoke_inproc.py --runpythontest main

预期：`[PASS] ...` 若干行；失败时 exit code != 0 让 --runpythontest 识别为 fail。
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path


_HERE = Path(__file__).resolve().parent.parent.parent  # Tools/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _run(coro):
    """跑一个 coroutine 到完成，返回其结果；捕异常并打印。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("smoke")

    from o3de_mcp import config, threading_bridge
    from o3de_mcp.handlers import asset, component, entity, query, transform

    config.load()
    threading_bridge.install()
    # 给 tick handler 预热一帧
    try:
        import azlmbr.legacy.general as _general  # type: ignore[import]
        _general.idle_wait_frames(1)
    except Exception:
        pass

    failures = []

    def check(label, fn):
        try:
            result = _run(fn())
            log.info("[PASS] %s -> %s", label, result)
        except Exception as e:
            log.exception("[FAIL] %s", label)
            failures.append((label, e))

    # --- 1. 建 entity
    created = {}

    async def step_create():
        r = await entity.create(parent=None, name="SmokeTestEntity")
        created["eid"] = r["entity_id"]
        return r
    check("entity.create", step_create)

    eid = created.get("eid")
    if not eid:
        log.error("entity not created, abort")
        return 2

    # --- 2. 加 Transform 组件（一般 CreateNewEntity 已有，但调一下验证）
    async def step_list_types():
        r = await component.list_types(entity_type="Game")
        assert len(r["types"]) > 0, "no component types found"
        return {"types_count": len(r["types"])}
    check("component.list_types", step_list_types)

    # --- 3. 加 Mesh 组件
    async def step_add_mesh():
        r = await component.add(entity_id=eid, component_type="Mesh")
        created["mesh_ref"] = r["component_ref"]
        return r
    check("component.add Mesh", step_add_mesh)

    # --- 4. 找一个 asset
    async def step_find_asset():
        # 用 O3DE 自带的一个 model 做测试；没有的话 change path
        # 这个路径在 AtomStarterGame / AutomatedTesting 里常见
        candidate_paths = [
            "objects/foliage/cedar.fbx.azmodel",
            "assets/objects/foliage/cedar.fbx.azmodel",
            "objects/_primitives/_box_1x1.azmodel",
        ]
        last_err = None
        for p in candidate_paths:
            try:
                return await asset.find_by_path(path=p)
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"No sample asset path worked; last error: {last_err}")
    check("asset.find_by_path", step_find_asset)

    # --- 5. 设 transform translation
    async def step_set_translation():
        return await transform.set_translation(
            entity_id=eid,
            translation={"__type": "Vector3", "x": 5.0, "y": 0.0, "z": 2.0},
        )
    check("transform.set_translation", step_set_translation)

    # --- 6. get transform 回读
    async def step_get_transform():
        r = await transform.get(entity_id=eid)
        return r
    check("transform.get", step_get_transform)

    # --- 7. query.find_by_name 回查
    async def step_find_by_name():
        r = await query.find_by_name(name="SmokeTestEntity", exact=True)
        assert eid in r["entities"], f"did not find our entity in results: {r}"
        return {"found_count": len(r["entities"])}
    check("query.find_by_name", step_find_by_name)

    # --- 8. scene_snapshot
    async def step_snapshot():
        r = await query.scene_snapshot(
            include_components=True, include_transforms=False, max_entities=50
        )
        assert r["total"] >= 1
        return {"total": r["total"], "returned": len(r["entities"])}
    check("query.scene_snapshot", step_snapshot)

    # --- 9. delete（需 ALLOW_DESTRUCTIVE）
    async def step_delete():
        import os
        os.environ["ALLOW_DESTRUCTIVE"] = "true"
        config.load()  # 重新读
        return await entity.delete(entity_id=eid, cascade=True)
    check("entity.delete (destructive)", step_delete)

    if failures:
        log.error("=== %d FAILURES ===", len(failures))
        for label, e in failures:
            log.error("  - %s: %s", label, e)
        return 1
    log.info("=== ALL GREEN (%d checks) ===", 8)
    return 0


if __name__ in ("__main__", "__builtin__", "builtins"):
    sys.exit(main())
