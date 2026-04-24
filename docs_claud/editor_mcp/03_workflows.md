# 03 · Agent 工作流 & 实战 walkthrough

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 主题：Agent 拿到 MCP 工具后怎么**组织流程**做出高质量的场景设计

---

## 1. 总原则

1. **先看再改**：所有写操作前必 query.get_info / query.scene_snapshot
2. **小步前进**：一次只改 3-5 个 property；每改完 verify
3. **失败即回滚**：undo batch 包裹；一步出错整 batch 撤销
4. **可验证**：关键改动后 take_screenshot，证据留档
5. **拒绝幻觉**：找不到 asset / property_path → 停下问用户，不替用户"猜"

---

## 2. 三角色复用 [`tools/agents/`](../../tools/agents/) 的 Planner/Specialist/Reviewer，加一个 Scene Specialist

```
┌─────────────┐
│   Planner   │  R1 (deepseek-reasoner)
│  拆任务      │
└──────┬──────┘
       │ plan JSON
       ▼
┌─────────────┐     ┌────────────────┐
│ CPP Spec    │     │ Scene Spec     │  V3 (deepseek-chat)
│ 改代码       │     │ 改场景 (MCP)    │  现在才加
└──────┬──────┘     └────────┬───────┘
       │                     │
       │                     │
       ▼                     ▼
  fs_tools              MCP Client
                             │
                             ▼
                      MCP Server (内嵌于 Editor)
       │                     │
       └──────────┬──────────┘
                  ▼
           ┌─────────────┐
           │  Reviewer   │  R1 (挑刺)
           │  query.* +  │
           │  screenshot │
           └─────────────┘
```

**关键不同**：
- Scene Specialist 不写文件，只调 MCP 工具
- Reviewer 看 Scene Specialist 的产出时，调 `query.scene_snapshot` + `viewport.take_screenshot`，不是 `fs_read`

---

## 3. Plan JSON 扩展：加 `scene_ops`

Planner 的 JSON schema 里多一个可选字段：

```jsonc
{
  "task_summary": "...",
  "files": [...],           // 给 CPP Spec 的代码改动
  "scene_ops": [            // 给 Scene Spec 的场景改动（新）
    {
      "op": "set_skybox",
      "hdri_asset_path": "LightingPresets/studio_hdri.exr.streamingimage",
      "intent": "换到工作室环境光，模型表面能看清"
    },
    {
      "op": "add_mesh_entity",
      "name": "HeroModel",
      "model_asset": "Models/hero.fbx.azmodel",
      "position": {"x":0,"y":0,"z":0}
    }
  ],
  "verification": {
    "screenshots": [
      {"after":"scene_ops[0]", "name":"after_skybox.png"},
      {"after":"scene_ops[-1]", "name":"final.png"}
    ],
    "query_checks": [
      {"find_by_component_type":"HDRi Skybox", "expect_count":1}
    ]
  }
}
```

Planner **把语义意图写进 intent 字段** —— 让 Scene Specialist 在执行失败时知道原本目标是啥，可以换个路子。

---

## 4. Scene Specialist 的"套路"

### 4.1 进场：先看后做

```python
# Specialist 的每个 turn 固定开头
snapshot = mcp.call("query.scene_snapshot", {"max_depth": 2})
log.debug("current scene: %s", snapshot)
```

**不先 snapshot 就动手 = 瞎改**。Snapshot 返回 JSON 塞进 LLM 的 context，2KB 内搞定（控制 depth）。

### 4.2 操作单元：`scene_op` → 若干 MCP 工具调用

一个 `scene_op` = 一个 HITL 单元。内部多个 MCP 调用包在 `history.begin_batch` / `end_batch` 里。

```python
def execute_op(op: dict) -> dict:
    label = f"AI: {op['op']} — {op.get('intent','')[:40]}"
    mcp.call("history.begin_batch", {"label": label})
    try:
        handler = OP_HANDLERS[op["op"]]
        result = handler(op)
        mcp.call("history.end_batch", {})
        return {"ok": True, "result": result}
    except Exception as e:
        # 失败时 end batch + 自动 undo
        mcp.call("history.end_batch", {})
        mcp.call("history.undo", {})
        return {"ok": False, "error": str(e)}
```

### 4.3 宏的拆解：`set_skybox` 实例

Scene Specialist 收到 `{"op":"set_skybox", "hdri_asset_path":"..."}`：

```python
def handle_set_skybox(op):
    path = op["hdri_asset_path"]

    # 1. 找/建承载实体
    r = mcp.call("query.find_by_component_type", {"component_type":"HDRi Skybox"})
    if r["entities"]:
        eid = r["entities"][0]["entity_id"]
        comps = mcp.call("component.list_on_entity", {"entity_id": eid})
        skybox_comp = next(c for c in comps["components"] if c["type"]=="HDRi Skybox")
    else:
        e = mcp.call("entity.create", {"parent":None, "name":"Skybox"})
        eid = e["entity_id"]
        c = mcp.call("component.add", {"entity_id":eid, "component_type":"HDRi Skybox"})
        skybox_comp = {"ref": c["component_ref"]}

    # 2. 解析 asset
    a = mcp.call("asset.find_by_path", {"path": path})
    asset_id = a["asset_id"]

    # 3. 找正确的 property_path（先 list 再选）
    tree = mcp.call("component.get_property_tree", {"component_ref": skybox_comp["ref"]})
    cube_path = next(
        p["path"] for p in tree["properties"]
        if "Cubemap" in p["path"] and p["type"] == "AssetId"
    )

    # 4. set
    mcp.call("component.set_property", {
        "component_ref": skybox_comp["ref"],
        "property_path": cube_path,
        "value": {"__type":"AssetId", "asset_id": asset_id}
    })
    return {"entity_id": eid, "property": cube_path}
```

**关键技巧**：第 3 步**不硬编码** property_path "Controller|Configuration|Cubemap Texture"，而是 `get_property_tree` 找最匹配的。这样 O3DE 升级改字段名不会整套挂掉。

### 4.4 Editor 宏版本（MCP Server 侧的 `environment.set_skybox`）

上面这段代码其实已经封装成 **`environment.set_skybox` 一个 MCP 工具**。Scene Specialist 直接调 `environment.set_skybox(path=...)` 即可。

**原则**：**高频 / 固定模式**的操作全部在 MCP Server 侧聚合成一个工具。**低频 / 灵活**的操作让 Agent 自己用底层工具组。

---

## 5. Reviewer 的校验

Scene Spec 跑完，Reviewer 介入：

```python
def review_scene_ops(plan, spec_summary, history):
    findings = []

    # 5.1 检查计划里的每个 op 都有效果
    for op in plan["scene_ops"]:
        if op["op"] == "set_skybox":
            r = mcp.call("query.find_by_component_type", {"component_type":"HDRi Skybox"})
            if not r["entities"]:
                findings.append({
                    "severity":"blocking",
                    "rule":"set_skybox produced no HDRi Skybox component",
                    "op": op
                })
            else:
                comp = r["entities"][0]
                # verify 对应 AssetId 匹配
                ...

    # 5.2 query_checks
    for check in plan["verification"]["query_checks"]:
        ...

    # 5.3 截图产物检查
    for shot in plan["verification"]["screenshots"]:
        # 截图文件在不在？(Agent 如果有 vision，还能看看图)
        ...

    return {"findings": findings, "severity": _aggregate_sev(findings)}
```

**Reviewer 不改场景**，只看。发现问题让上游重跑。

---

## 6. 三个典型 walkthrough

### 6.1 场景 A：**"给 HeroModel 换成仓库里的 cedar 木纹材质"**

**用户输入**："把场景里 HeroModel 的材质换成仓库里那个 oak 木纹，要能看出是木头"

**Planner**：

```jsonc
{
  "task_summary": "把 HeroModel 的 Material slot 0 改成 oak 木纹",
  "scene_ops": [
    {
      "op": "assign_material",
      "target_entity_name": "HeroModel",
      "material_asset_path": "Materials/PresetMaterials/Wood/oak.material",
      "slot_index": 0
    }
  ],
  "verification": {
    "screenshots": [{"after":"scene_ops[0]", "name":"hero_oak.png"}],
    "query_checks": []
  },
  "decisions": [
    "Planner 不知道 oak.material 是不是真路径 —— Scene Spec 失败时让它用 asset.list_by_extension 搜"
  ]
}
```

**Scene Specialist**：

```python
# 先定位 entity
r = mcp.call("query.find_by_name", {"name":"HeroModel","exact":True})
eid = r["entities"][0]["entity_id"]

# 直接用高层工具
try:
    res = mcp.call("environment.assign_material", {
        "entity_id": eid,
        "material_asset_path": "Materials/PresetMaterials/Wood/oak.material",
        "slot_index": 0
    })
except MCPError as e:
    if e.code == "asset_not_found":
        # 搜一下同类名
        candidates = mcp.call("asset.list_by_extension", {
            "extension":".material", "name_contains":"oak"
        })
        # 人/Agent 挑一个，或者失败
        raise
```

**Reviewer**：`query.scene_snapshot` + `viewport.take_screenshot("hero_oak.png")`。

### 6.2 场景 B：**"用当前场景做一个环境灯光 probe：studio_hdri + 一个方向光 + 关闭雾"**

**Planner 产出**：

```jsonc
{
  "scene_ops": [
    {"op":"environment.set_skybox",
     "hdri_asset_path":"LightingPresets/studio_hdri.exr.streamingimage"},
    {"op":"environment.set_directional_light",
     "direction":{"x":-0.3,"y":-0.7,"z":-0.6},
     "color":{"r":1.0,"g":0.98,"b":0.95},
     "intensity":2.0},
    {"op":"environment.set_global_fog", "enabled":false}
  ],
  "verification": {
    "screenshots":[{"after":"scene_ops[-1]", "name":"probe.png"}]
  }
}
```

**Scene Specialist** 循环跑 3 个 op，都走高层工具。每个 op 自动包 undo batch。

**Reviewer** 截图 + 跑 `query.find_by_component_type("HDRi Skybox")` / `("Directional Light")` / `("Global Fog")` 确认存在性。

### 6.3 场景 C（复杂）：**"摆一排树：沿 X 轴 10m 间距放 5 个 pine_tree，每棵稍微错开朝向"**

这个任务考验 **数量级** 和 **参数化**。

**Planner 不展开 5 个 op**，而是产出一个 "batch op"：

```jsonc
{
  "scene_ops": [
    {
      "op": "batch_place_instances",
      "prefab_or_model": "Models/pine_tree.fbx.azmodel",
      "count": 5,
      "start_position": {"x":0,"y":0,"z":0},
      "step": {"x":10,"y":0,"z":0},
      "rotation_jitter_deg_y": 30,
      "parent_entity_name": "TreeLine"
    }
  ]
}
```

**Scene Specialist** 有个 `batch_place_instances` handler：

```python
def handle_batch_place(op):
    # 1. 保证 parent 存在
    p = mcp.call("query.find_by_name", {"name": op["parent_entity_name"], "exact":True})
    if not p["entities"]:
        pe = mcp.call("entity.create", {"name": op["parent_entity_name"]})
        parent_id = pe["entity_id"]
    else:
        parent_id = p["entities"][0]["entity_id"]

    # 2. 循环建 N 个
    created = []
    for i in range(op["count"]):
        pos = {
            "x": op["start_position"]["x"] + op["step"]["x"] * i,
            "y": op["start_position"]["y"] + op["step"]["y"] * i,
            "z": op["start_position"]["z"] + op["step"]["z"] * i,
        }
        e = mcp.call("entity.create", {
            "parent": parent_id,
            "name": f"PineTree_{i:02d}",
            "position": pos,
        })
        eid = e["entity_id"]
        # assign model
        mcp.call("environment.assign_model", {
            "entity_id": eid,
            "model_asset_path": op["prefab_or_model"]
        })
        # rotate
        if op.get("rotation_jitter_deg_y"):
            import random
            y_rot = random.uniform(-op["rotation_jitter_deg_y"], op["rotation_jitter_deg_y"])
            mcp.call("transform.set_rotation_euler_degrees", {
                "entity_id": eid, "euler_deg":{"x":0,"y":y_rot,"z":0}
            })
        created.append(eid)
    return {"entities": created}
```

整个批量在一个 `history.begin_batch("AI: place 5 trees")` 里，**用户一次 Undo 全撤** —— 比 5 个 Undo 友好得多。

---

## 7. 当 Agent 不确定时该怎么办

### 7.1 Asset path 不确定

**错误做法**：Agent 直接猜 `"Materials/oak.material"` 写进 op，跑时挂。

**正确做法**：
1. 先 `asset.list_by_extension` 把候选拉出来
2. 给用户看候选，让用户选
3. 或 Planner 就明确标 `"intent":"找 wood_oak 相近的"`，Scene Spec 做模糊匹配

### 7.2 Component property_path 不确定

**错误做法**：硬编码 `"Controller|Configuration|Material Asset"`。

**正确做法**：先 `component.get_property_tree` 拿全列表 → regex / fuzzy 找。

### 7.3 API 在这个版本叫啥不确定

**错误做法**：Agent 瞎 `SetCubemapTexture()` 结果不存在。

**正确做法**：
- handler 统一用 `EditorComponentAPIBus::SetComponentProperty(path, value)`，避免调具体 bus 方法
- 发现新 API 需求 → 先 fs_grep AutomatedTesting 里有没有现成例子
- 仍然不够 → 用 `system.exec_python` 逃生舱（L3）临时顶一下，用 ≥3 次后把它升级成正式工具（见 [04_safety_undo_hitl.md §15.6](04_safety_undo_hitl.md)）

---

## 8. 失败与重试策略

| 失败类型 | 自动重试 | 需要人介入 |
|---|---|---|
| `asset_not_found` | 否 | ✓（用户澄清 path） |
| `component_type_not_found` | 先 list → 模糊匹配 | 匹配不到则 ✓ |
| `property_path_invalid` | 先 tree → fuzzy | 仍失败则 ✓ |
| `editor_disconnected` | 等 5s retry 1 次 | ✓ |
| `timeout` | retry 1 次，超时翻倍 | ✓ |
| `python_traceback` | 不重试（有 bug） | ✓ |
| `permission_denied`（HITL 拒绝）| 跳过 | （用户已表态） |

每个工具调用记 trace，失败时把 trace 给下次重试的 Agent prompt 里——**Agent 看到上次错了什么，才不会再错**。

---

## 9. 人机协作模式

### 9.1 全自动（CI 用）

`AUTO_APPROVE=true`，所有 HITL 直接通过。**风险自负**，适合回归测试脚本（"给测试场景换这 5 种天空盒，各截一张图"）。

### 9.2 半自动（默认）

destructive 操作停下问；非 destructive 直接跑。改 component.property 通常直接放行，delete/ save_level 必问。

### 9.3 Dry Run

Planner 产出 plan 后 **不执行**，只打印。用户看了 OK 再 `run_plan.py plan.json` 真跑。和 `tools/agents/run.py --dry-run` 对齐。

### 9.4 Step Mode

每个 op 之前问一次。适合"教学 / 演示"场景。

---

## 10. 与已有 `tools/agents/workflow.py` 集成

修改点（伪代码）：

```python
# tools/agents/workflow.py
async def run_sequential_mvp(task: str) -> dict:
    ...
    plan = await _run_agent(planner, planner_input)

    # NEW: 按 plan 路由到不同 specialist
    coder_summary = ""
    scene_summary = ""
    if plan.get("files"):
        coder_summary = await _run_agent(cpp_spec, coder_input)

    if plan.get("scene_ops"):
        # 启动 / 复用 MCP 连接
        mcp = await get_or_start_mcp_client()
        scene_summary = await _run_agent(scene_spec, scene_input_with_mcp=mcp)

    # Reviewer 现在会看两边
    review = await _run_agent(reviewer, reviewer_input_combined)
    ...
```

Scene Specialist 的 MCP client **在 workflow 里持久** —— 不要每个工具调用重连。

---

## 11. 可观测性

所有 MCP 调用记录（客户端和 MCP Server 两侧各记一份，方便对账）：

```
tools/agents/logs/run_20260424_153012/
├── 01_planner.json
├── 02_coder.json
├── 03_scene_spec.json
├── 03_scene_spec_mcp_trace.jsonl   # 每行一个 MCP 调用
└── 04_reviewer.json
```

`03_scene_spec_mcp_trace.jsonl` 示例：

```json
{"t":"2026-04-24T15:30:15.001","dir":"out","method":"query.find_by_name","params":{"name":"HeroModel"},"id":"1"}
{"t":"2026-04-24T15:30:15.042","dir":"in","id":"1","result":{"entities":[{"entity_id":"Entity[0xA]"}]}}
{"t":"2026-04-24T15:30:15.043","dir":"out","method":"environment.assign_material","params":{...},"id":"2"}
...
```

Reviewer 把 trace 作为审查材料之一。

---

## 12. 下一步

- 场景 A/B/C 各做一个端到端 demo 脚本落到 `tools/o3de_mcp/examples/`
- Planner prompt 更新：加 `scene_ops` schema 的说明（见 [`tools/agents/prompts.py`](../../tools/agents/prompts.py)）
- Reviewer prompt 更新：多一条"看 screenshot 和 snapshot"
