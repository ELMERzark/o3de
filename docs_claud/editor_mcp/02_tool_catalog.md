# 02 · MCP 工具清单

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 本文档定义 Agent 通过 MCP 可调用的所有工具。每个工具都有签名、azlmbr 映射、错误清单、示例。

---

## 工具分组

| 分组 | 命名前缀 | 优先级 |
|---|---|---|
| Entity 基本 CRUD | `entity.*` | P0 |
| Transform | `transform.*` | P0 |
| Component CRUD + 属性 | `component.*` | P0 |
| Asset 查询 | `asset.*` | P0 |
| 场景查询 / 快照 | `query.*` | P0 |
| Prefab | `prefab.*` | P1 |
| Level | `level.*` | P1 |
| 环境 / 光照 / 天空 高层封装 | `environment.*` | P1 |
| 截屏 / 视口 | `viewport.*` | P1 |
| Undo 控制 | `history.*` | P1 |
| 编辑器外部动作 | `system.*` | P2 |

工具统一返回 `{ok: bool, ...}`。失败时 `{ok: false, error: {code, message, data?}}`。

---

## entity.* — 实体 CRUD

### entity.create

创建新实体。可选挂父节点、命名。

```jsonc
// params
{
  "parent": null | "Entity[0xABC]",   // null = 挂在 Level 根
  "name":   "MySpinner",              // 可选
  "position": {"x":0,"y":0,"z":0}     // 可选，默认 (0,0,0)
}
// result
{"entity_id": "Entity[0x12345]", "name": "MySpinner"}
```

- azlmbr: `editor.ToolsApplicationRequestBus(bus.Broadcast, 'CreateNewEntity', parent_id)`
- 如果带 name：`editor.EditorEntityAPIBus(bus.Event, 'SetName', new_id, name)`
- 错误：`parent_not_found`

### entity.delete

```jsonc
{"entity_id": "Entity[0x12345]", "cascade": true}
// result: {"deleted_count": 3}
```

- azlmbr: `ToolsApplicationRequestBus(Broadcast, 'DeleteEntity', eid)` / `DeleteEntityAndAllDescendants`
- **destructive → HITL 确认**

### entity.set_parent

```jsonc
{"entity_id": "Entity[0xA]", "new_parent": "Entity[0xB]"}
// result: {"ok": true}
```

- `editor.EditorEntityAPIBus(bus.Event, 'SetParent', child, new_parent)`

### entity.rename

```jsonc
{"entity_id":"Entity[0xA]", "name":"Hero"}
```

### entity.list_children

```jsonc
{"entity_id":"Entity[0xA]"}
// result
{"children": ["Entity[0xB]", "Entity[0xC]"]}
```

- `EditorEntityInfoRequestBus(bus.Event, 'GetChildren', eid)`

### entity.get_info

```jsonc
{"entity_id":"Entity[0xA]"}
// result
{
  "name":"Hero",
  "parent":"Entity[root]",
  "children":["Entity[0xB]"],
  "components":[
    {"id":"Comp[1]", "type":"Transform"},
    {"id":"Comp[2]", "type":"Mesh"}
  ],
  "transform": {
    "translation":{"x":0,"y":0,"z":0},
    "rotation_euler":{"x":0,"y":0,"z":0},
    "scale":{"x":1,"y":1,"z":1}
  }
}
```

组合调用：GetName + GetParent + GetChildren + GetComponents + TransformBus。
**这个工具是 Agent 的"眼睛"** —— 修改前先 get_info 看现状。

---

## transform.* — 变换

### transform.set_translation_world / local

```jsonc
{"entity_id":"Entity[0xA]", "translation":{"x":1,"y":2,"z":3}}
```

- `components.TransformBus(bus.Event, 'SetWorldTranslation', eid, vec)`
- local 版本用 `'SetLocalTranslation'`

### transform.set_rotation_euler_degrees

```jsonc
{"entity_id":"Entity[0xA]", "euler_deg":{"x":0,"y":0,"z":90}}
```

- 内部转 Quaternion → `SetWorldRotationQuaternion`

### transform.set_scale

```jsonc
{"entity_id":"Entity[0xA]", "scale":{"x":2,"y":2,"z":2}}
```

### transform.get

返回当前 Transform（上面三个之和）。

---

## component.* — 组件 CRUD + 属性

### component.list_types

列出**当前可加**的组件类型（按 entity type 过滤）。

```jsonc
{"entity_type":"Game" | "Level" | "System"}  // 默认 Game
// result
{"types":[{"type_id":"{UUID}", "name":"Transform"}, ...]}
```

- `EditorComponentAPIBus(Broadcast, 'FindComponentTypeIdsByEntityType', [], entity_type)`
- 这个工具让 Agent 先看**有哪些组件可用**，避免瞎猜

### component.add

```jsonc
{"entity_id":"Entity[0xA]", "component_type":"Mesh"}
// result
{"component_ref":"Comp[0xA:2]"}
```

- 流程：`FindComponentTypeIdsByEntityType([name])` → `AddComponentsOfType(eid, [type_id])`
- 错误：`component_type_not_found`、`already_has_required_service`

### component.add_many

批量加组件（一次 HITL 确认）。

```jsonc
{"entity_id":"Entity[0xA]", "types":["Mesh", "Material", "Rigid Body"]}
```

### component.remove

```jsonc
{"component_ref":"Comp[0xA:2]"}
```

- `EditorComponentAPIBus(Broadcast, 'RemoveComponents', [component])`

### component.list_on_entity

```jsonc
{"entity_id":"Entity[0xA]"}
// result
{"components":[{"ref":"Comp[0xA:1]","type":"Transform"}, ...]}
```

- `GetComponentsOfType` / `GetComponents`

### component.get_property_tree

**这个很重要**：列出一个组件所有可读写属性的路径，给 Agent 一份"可操作项清单"。

```jsonc
{"component_ref":"Comp[0xA:2]"}
// result
{
  "properties":[
    {"path":"Controller|Configuration|Model Asset","type":"AssetId"},
    {"path":"Controller|Configuration|Sort Key","type":"int"},
    {"path":"Controller|Configuration|Use Forward Pass IBL","type":"bool"},
    ...
  ]
}
```

- 基于 `BuildComponentPropertyTreeEditor` ([Editor_ComponentPropertyCommands_Works.py:60+](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_ComponentPropertyCommands_Works.py#L60))
- 遍历 pte，导出所有叶子节点

### component.set_property

```jsonc
{
  "component_ref":"Comp[0xA:2]",
  "property_path":"Controller|Configuration|Model Asset",
  "value": {"__type":"AssetId", "asset_id":"Asset[{uuid}:0]"}
}
// result: {"new_value": {...}}
```

- `SetComponentProperty(component, path, value)`
- value 必须按 `__type` 标注类型，handler 负责 marshal

### component.get_property

```jsonc
{"component_ref":"Comp[0xA:2]","property_path":"..."}
// result: {"value": ...}
```

---

## asset.* — 资产查询

### asset.find_by_path

```jsonc
{"path":"assets/objects/foliage/cedar.fbx.azmodel"}
// result: {"asset_id":"Asset[{uuid}:0]", "type_name":"Model"}
```

- `asset.AssetCatalogRequestBus(Broadcast, 'GetAssetIdByPath', path, Uuid(), False)`

### asset.list_by_extension

```jsonc
{"extension":".materialtype", "scan_folder":"Materials"}   // 均可选
```

**MVP 用外部 ripgrep/`os.walk` 扫 `Cache/`**（不走 azlmbr，避开 catalog enumerate API）。

### asset.get_info

```jsonc
{"asset_id":"Asset[{uuid}:0]"}
// result: {"path":"...", "type_name":"Material", "size_bytes":12345}
```

---

## query.* — 场景观察（Agent 的眼睛）

### query.list_entities

全场景扁平列表（或按 filter）。

```jsonc
{"filter":{"component_types":["Mesh"], "name_contains":"Tree"}}
// result
{"entities":[{"entity_id":"...","name":"TreeA","components":["Mesh","Transform"]}, ...]}
```

- `entity.SearchBus` with `SearchFilter`

### query.find_by_name

```jsonc
{"name":"MainCamera","exact":true}
```

### query.find_by_component_type

```jsonc
{"component_type":"HDRi Skybox"}
```

### query.scene_snapshot

**重要**：Agent 决策前的"看一眼全场景"。

```jsonc
{
  "include_components": true,
  "include_transforms": true,
  "max_depth": 3
}
// result: 整棵 entity 树 + 每个节点的 type list + transform
```

用法：Agent 在 Planner 阶段先调一次 snapshot 作为世界认知。

---

## prefab.* — Prefab 管理

### prefab.create_from_entities

```jsonc
{
  "entity_ids": ["Entity[0xA]","Entity[0xB]"],
  "prefab_path":"Prefabs/MyGroup.prefab"
}
// result
{"container_entity_id":"Entity[0xZ]"}
```

- `prefab.PrefabPublicRequestBus(Broadcast, 'CreatePrefabInMemory', entities, path)`
- 参考：[prefab_utils.py:221+](../../AutomatedTesting/Gem/PythonTests/EditorPythonTestTools/editor_python_test_tools/prefab_utils.py#L221)

### prefab.instantiate

```jsonc
{
  "prefab_path":"Prefabs/MyGroup.prefab",
  "parent":"Entity[0xA]",
  "position":{"x":0,"y":0,"z":0}
}
// result: {"container_entity_id":"Entity[0xW]"}
```

- `InstantiatePrefab(path, parent, pos)`

### prefab.save

将内存 Prefab 持久化到磁盘。

```jsonc
{"container_entity_id":"Entity[0xZ]"}
```

### prefab.delete_instance

- destructive → HITL

---

## level.* — 关卡

### level.get_current

```jsonc
{}
// result: {"level_entity_id":"Entity[root]", "path":"Levels/MyLevel.prefab"}
```

### level.save

**destructive → HITL 强制确认**。

```jsonc
{"path": null}  // null = save in place
```

### level.open

```jsonc
{"path":"Levels/TestLevel.prefab"}
```

- destructive（丢当前未存改动）→ HITL + 先检测 dirty

### level.new

新建空 level。destructive → HITL。

---

## environment.* — 高层封装（组合调用）

这些工具在 MCP Server 层实现，组合底层 entity/component/asset 工具。**Agent 的最常用入口**。

### environment.set_skybox

```jsonc
{
  "hdri_asset_path":"LightingPresets/studio_hdri.exr.streamingimage",
  "exposure": 0.0
}
```

实现拆解：
1. `query.find_by_component_type("HDRi Skybox")` 找到承载实体
2. 没有就 `entity.create(name="Skybox")` + `component.add("HDRi Skybox")`
3. `asset.find_by_path(hdri_asset_path)` → asset_id
4. `component.set_property("Cubemap Texture", asset_id)`
5. 可选：改 exposure

### environment.set_directional_light

```jsonc
{
  "entity_id": null,          // null = 找/建 Sun
  "direction":{"x":0,"y":-1,"z":-0.5},
  "color":{"r":1,"g":0.95,"b":0.9},
  "intensity": 1.5
}
```

### environment.set_global_fog

```jsonc
{"enabled":true, "density":0.05, "color":{"r":0.6,"g":0.7,"b":0.8}}
```

### environment.assign_material

```jsonc
{
  "entity_id":"Entity[0xA]",
  "material_asset_path":"Materials/wood_oak.material",
  "slot_index": 0
}
```

实现：找 entity 上的 Material Component（没有就 add）→ set `Material Slots|<N>|Material Asset`。

### environment.assign_model

```jsonc
{"entity_id":"Entity[0xA]", "model_asset_path":"Models/chair.fbx.azmodel"}
```

---

## viewport.* — 视口与截屏

### viewport.take_screenshot

```jsonc
{
  "out_path":"G:/tmp/shot.png",
  "width":1920, "height":1080,
  "include_ui": false
}
// result: {"path":"G:/tmp/shot.png","bytes":123456}
```

- MVP 走控制台命令 `r_getScreenshot`；v2 用 Atom 的 FrameCapture API

**这个工具让 Agent 能看自己的成果**。Reviewer 可以调这个再"看图说话"（如果模型支持 vision）。

### viewport.set_camera_to_entity

### viewport.set_viewport_resolution

---

## history.* — Undo 控制

### history.begin_batch

```jsonc
{"label":"AI: set up forest scene"}
```

- `ToolsApplicationRequestBus(Broadcast, 'BeginUndoBatch', label)`

### history.end_batch

### history.undo / history.redo

让 Agent 可以在失败时回滚 **当前 turn**。

### history.rollback_batch

简写：回到 begin_batch 之前状态，即 undo 到 label 匹配的那个点。

---

## system.* — 编辑器外操作（谨慎）

### system.rescan_assets

触发 AP 重扫。

### system.wait_for_ap_idle

### system.run_editor_console_command

任意控制台命令。**destructive 白名单之外的都 HITL**。

```jsonc
{"command":"r_getScreenshot 1"}
```

### system.exec_python（L3 逃生舱，默认关）

**当且仅当**结构化工具目录真的没覆盖、又来不及加新工具时使用。参见 [04_safety_undo_hitl.md §15](04_safety_undo_hitl.md)。

```jsonc
{
  "code":"import azlmbr.bus as bus\nimport azlmbr.editor as editor\n# ... 任意 python\nreturn {'ok': True}",
  "label":"AI exec: 临时做一个叫 X 的骚操作",
  "timeout_sec": 10
}
// result: {"value": <python 脚本返回的 JSON-serializable 结果>}
```

- safety_level: **L3**
- 默认禁用；需 `ALLOW_EXEC_PYTHON=true` + `AUTO_APPROVE=false`（强制 HITL）双开关
- 每次调用都打印完整 code 给用户 review 后再执行
- 结果必须 JSON-serializable；`return` 非 JSON 的抛错
- 审计日志里**完整保留** code 文本

**什么时候要考虑把 `exec_python` 的某次用法变成正式工具**：同一个 code pattern 用了 ≥3 次 → 写进 `handlers/` 里。

---

## 不做的工具（明确排除）

- `system.shell_run(任意 shell)` —— 风险太大，Agent 要跑 cmake / git 走别的路径
- `entity.delete_all` —— 拒绝超级操作
- `level.delete_level_file` —— 删磁盘文件走 fs_tools，不经 MCP
- 任何直接操作 `build/` / `Cache/` 的工具
- git 操作 —— 走专门的 git tool，不在编辑器 MCP 范围

---

## 用户定义的便捷工具（`environment.*` 范例）

一个 Scene Specialist 的常用"宏"：

### environment.create_scene_probe_setup

```jsonc
{
  "hdri_asset_path":"...",
  "directional_light":{...},
  "fog":{...}
}
```

一次性设置天空盒 + 主光 + 雾。底层是 5 个工具的组合，**但对 Agent 只是 1 个调用** —— 减少 token、减少出错面。

这种封装按项目实际场景累积，放在 `tools/o3de_mcp/handlers/environment.py`。

---

## 工具版本化

所有工具带 `api_version`（语义版本）。签名变时涨 minor；breaking 涨 major。MCP Server 启动时把版本塞进 `ServerInfo`，Agent 能据此适配。
