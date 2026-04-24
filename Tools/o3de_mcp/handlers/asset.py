"""asset.* handler —— 资产查询

工具：
    - asset.find_by_path  通过相对路径查 AssetId
"""

from __future__ import annotations

from ..errors import CODE_ASSET_NOT_FOUND, MCPToolError
from ..ids import stringify_asset_id
from ..threading_bridge import call_on_main


async def find_by_path(path: str, auto_register: bool = False) -> dict:
    """按 catalog 中的相对路径查 AssetId。

    path: 例如 "assets/objects/foliage/cedar.fbx.azmodel"
    auto_register: True 时找不到会让 catalog 注册一次（慢，v1 再说）。
    """
    def _do():
        import azlmbr.asset as asset_mod
        import azlmbr.bus as bus
        import azlmbr.math as math_mod

        # GetAssetIdByPath(path, typeHint, autoRegister)
        aid = asset_mod.AssetCatalogRequestBus(
            bus.Broadcast,
            "GetAssetIdByPath",
            path,
            math_mod.Uuid(),            # type hint：空 UUID = 任意类型
            bool(auto_register),
        )

        if aid is None or (hasattr(aid, "IsValid") and not aid.IsValid()):
            raise MCPToolError(
                CODE_ASSET_NOT_FOUND,
                f"Asset not found in catalog: {path!r}",
                path=path,
            )
        return aid

    aid = await call_on_main(_do)
    return {"path": path, "asset_id": stringify_asset_id(aid)}
