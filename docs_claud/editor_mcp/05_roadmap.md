# 05 · Roadmap：MVP → v2 → v3

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 更新记录：2026-04-24 按"MCP Server 跑在 Editor 内"的单进程架构重写阶段划分。
> 分阶段实施，每个阶段都有"可以真跑起来"的交付物。

---

## 里程碑总览

| 阶段 | 目标 | 典型用例 | 耗时估计 |
|---|---|---|---|
| **MVP (Week 1-2)** | 一条 MCP 链路打通；Claude Desktop 能连上 | "创建一个 Mesh entity 并指派模型" | 5-7 天 |
| **v1 (Week 3-4)** | 环境/材质/Prefab 高层工具 + 安全机制 | "换天空盒 + 摆 5 棵树 + 截图" | 5-7 天 |
| **v2 (Week 5-6)** | 与 [`tools/agents/`](../../tools/agents/) MAF 骨架集成；Scene Specialist 上线 | Agent workflow 自动完成场景任务 | 5-7 天 |
| **v3 (Week 7+)** | Gem 化 + 生产加固 + 团队使用 | 多人、多 Editor 实例 | 持续迭代 |

---

## MVP（Week 1-2）

### 目标

"从 MCP 客户端调 `entity.create` → Editor 里真出现一个 entity" 跑通，且 Claude Desktop 一行配置就能连上验证。

### 交付物

```
tools/o3de_mcp/                             <-- 唯一一个包
├── boot.py                                 <-- Editor --runpython 入口
├── pyproject.toml                          <-- mcp + aiohttp + asyncio-compat
├── config.py                               <-- 端口、auth token、AUTO_APPROVE
├── threading_bridge.py                     <-- worker ↔ main 线程 queue + future
├── mcp_server.py                           <-- mcp.Server + SSE transport
├── serialize.py                            <-- JSON ↔ azlmbr 类型
├── ids.py                                  <-- EntityId/AssetId ↔ 字符串
├── errors.py                               <-- 错误码 + traceback
├── handlers/
│   ├── entity.py                           <-- create / delete / list_children / get_info
│   ├── component.py                        <-- add / remove / list_types / set_property / get_property / get_property_tree
│   ├── transform.py                        <-- set_translation / set_rotation / set_scale
│   ├── asset.py                            <-- find_by_path
│   └── query.py                            <-- find_by_name / find_by_component_type
└── tests/
    └── smoke_inproc.py                     <-- 作为 --runpython 跑完全链路自测
```

### 功能范围（严格 MVP）

**做**：
- `--runpython boot.py` 起一个 SSE MCP Server 在 `localhost:24601`
- **12 个基础工具**（见 handlers/ 清单），全走 `EditorComponentAPIBus::SetComponentProperty` 通用入口
- 线程 marshal：asyncio worker → Editor tick pump → azlmbr → future
- Console-based HITL（`input()`）
- Claude Desktop 配置 `"url": "http://127.0.0.1:24601/sse"` 能连

**不做**：
- ❌ Undo batch 自动包裹（手动可，v1 自动化）
- ❌ 环境/材质高层工具（v1）
- ❌ 自动 Editor 启动（v2 launcher）
- ❌ 截图（v1）
- ❌ Prefab（v1）
- ❌ auth token 校验（v1 加）
- ❌ exec_python 逃生舱（v1）

### 验收

**Part A：Python smoke test（不靠 MCP Client）**

```bash
# 启动
./build/.../profile/Editor --runpython tools/o3de_mcp/boot.py

# 另一终端
cd tools/o3de_mcp
python -m tests.smoke_external
# 预期（作为 MCP client 连上）：
# ✓ MCP handshake OK
# ✓ list_tools → 12 tools discovered
# ✓ entity.create → Entity[0xA]
# ✓ component.add (Transform) → Comp[0xA:1]
# ✓ component.add (Mesh)  → Comp[0xA:2]
# ✓ asset.find_by_path cedar.fbx.azmodel → Asset[{..}:0]
# ✓ component.set_property Model Asset → verified roundtrip
# ✓ transform.set_translation (5, 0, 2)
# ✓ query.find_by_name HeroModel → matches
# ✓ entity.delete
# ALL GREEN.
```

视口里**肉眼可见**一棵 cedar 树短暂出现又消失。

**Part B：Claude Desktop 端到端**

加到 `~/.claude/claude_desktop_config.json`：
```json
{
  "mcpServers": {
    "o3de": {
      "url": "http://127.0.0.1:24601/sse"
    }
  }
}
```

Claude 里输入："查一下当前场景有多少个 entity"。
Claude 调 `query.find_by_name("", exact=false)` 或等价工具，回复数量。

### 风险 / 已知 blocker

| 风险 | 缓解 |
|---|---|
| azlmbr 类型 marshal 比想象复杂（AssetId/EntityId/Vector3） | 预留 1 天；直接从 [AutomatedTesting/.../tests/](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/) 抄 |
| EditorTickBus 的 Python 订阅方式不确定 | 先试 `azlmbr.tick.TickRequestBus(Broadcast, 'AddTickHandler', fn)`；不行退回 `general.idle_wait_frames(0)` |
| asyncio 在 Editor Python VM 的行为 | 先在 Python worker 线程里 `asyncio.new_event_loop()`；如果不能共存再改 |
| MCP SDK 的 SSE 需要 aiohttp / starlette | 直接用 `mcp.server.sse`；不够就自己撑一个 aiohttp 路由 |

---

## v1（Week 3-4）：高层工具 + 安全机制

### 目标

Scene Specialist **用户视角可用**：能说"给 HeroModel 换 oak 材质"、"换天空盒 + 截图"，一两句话落地。

### 新增交付物

**handlers/ 新增**：
- `prefab.py` —— create_from_entities / instantiate / save / delete_instance
- `level.py` —— get_current / save / open / get_dirty_state
- `viewport.py` —— take_screenshot
- `history.py` —— begin_batch / end_batch / undo / redo（自动包装装饰器）
- `system.py` —— exec_python（L3 逃生舱，默认关，见 [04 §15](04_safety_undo_hitl.md)）

**MCP Server 层高层工具**（`@mcp.tool()` 组合底层 handlers）：
- `environment.set_skybox(hdri_asset_path, exposure)`
- `environment.assign_material(entity_id, material_asset_path, slot_index)`
- `environment.assign_model(entity_id, model_asset_path)`
- `environment.set_directional_light(entity_id, direction, color, intensity)`
- `environment.batch_place_instances(model_asset_path, count, start_position, step, ...)`
- `query.scene_snapshot(max_depth, include_components)` —— Agent 看场景的"眼睛"

**安全机制**：
- 每个工具标 `safety_level` 字段（L0~L3）
- 4 级分类实装（`safety.py` + config 开关）
- 禁操作清单 `denied.py`（禁 Level Root / sys_* console cmd 等）
- dirty state 检测 + Specialist 开场拒绝
- Auth token 校验（Authorization header）
- 自动 undo batch（每个"turn"一个外层 batch，工具级子 batch 嵌套）

### 验收：3 个 demo（通过 Claude Desktop 跑）

```
tools/o3de_mcp/examples/
├── demo_01_change_skybox.md    # 一段对话：换天空盒 + 截图
├── demo_02_assign_material.md  # 换材质，Reviewer 回读 verify
└── demo_03_place_forest.md     # 批量摆 5 棵树 + rotation jitter
```

每个 demo 都跑完整路径，logs 里有完整 MCP audit trace + 截图。

### 风险

- HDRi Skybox 组件 property_path 和设想不同 → 用 `component.get_property_tree` 工具试探
- `r_getScreenshot` 在 headless 下行为不一致 → fallback Atom FrameCapture API
- Undo batch 嵌套可能坏 Editor 的 undo stack → 先做单层 batch，嵌套到 v2

---

## v2（Week 5-6）：和 MAF 骨架集成 + 自动启动

### 目标

[`tools/agents/`](../../tools/agents/) 的 Planner→CPP/Scene/Reviewer 多 agent 流程能自动调 MCP 完成场景任务。不再是 "一次只能和 Claude Desktop 聊一句"。

### 新增交付物

**MAF 集成**（修改 `tools/agents/`）：
- 新增 `mcp_client.py` —— SSE client 封装
- 新增 `scene_specialist.py` —— 像 cpp_specialist 一样但调 MCP
- `workflow.py` 加分支：plan 里有 `scene_ops` 就起 Scene Spec
- `prompts.py` 加 `SCENE_SPECIALIST_PROMPT`；Planner / Reviewer prompt 相应更新（产出 `scene_ops` schema；Reviewer 用 `query.scene_snapshot` + `viewport.take_screenshot` 回验）

**launcher 脚本** `tools/o3de_mcp/launch.py`：
```bash
python -m o3de_mcp.launch --project AutomatedTesting
# 一键：启动 Editor（后台）→ 轮询 http://127.0.0.1:24601/health
# → 就绪后返回 0，PID 打印到 stdout
```

**MCP Resources / Prompts**：
- `@mcp.resource("scene://current")` —— scene_snapshot 暴露为 resource（Claude Desktop 自动 prefetch）
- `@mcp.prompt("scene_design_template")` —— 场景搭建常用 prompt 模板

### 验收

**场景 1**：Claude Desktop 对话
```
User: 给当前场景换一个工作室环境光的天空盒，然后截个图给我看
Claude: [调 environment.set_skybox + viewport.take_screenshot]
        已经把天空盒换成 LightingPresets/studio_hdri.exr.streamingimage。截图：
        [png 显示]
```

**场景 2**：MAF workflow
```bash
cd tools/agents
python run.py "给 HealthTest level 加一排 5 棵松树，沿 X 轴 10m 间距"
# 跑完后 logs/run_*/ 有完整 Planner / Scene Spec / Reviewer JSON 和截图
```

### 风险

- Claude Desktop SSE 超时策略未知（某些操作 >30s）→ MCP SDK 里调 timeout；或 long-running 操作拆成多个工具
- MAF 的 ChatAgent 能否无缝包 MCP client → 必要时自己写 adapter

---

## v3（Week 7+）：生产加固

### 目标

从"一个人能跑"到"团队 5-10 个 dev 都能用"。

### 需要做的

**Gem 化（可选但推荐）**：把 boot.py 升级成 `Gems/EditorMcpServer`（C++ Gem）：
- 不再需要手敲 `Editor.exe --runpython ...`；装 Gem 自动启动 MCP Server
- 从 Editor 设置面板配置端口 / auth token
- 错误走 Editor Log / Notifications 面板
- 实现路径：C++ EditorSystemComponent Activate 里起 Python Thread + aiohttp，或直接 boost::asio socket + 调 `EditorPythonRunnerRequestBus::ExecuteByString`

**多 Editor 实例**：端口隔离（24601、24602…），launcher 分配。

**远程 Editor**：MCP Server 绑 0.0.0.0 + TLS + 强 token；团队共享 demo 机。**明确不是默认**——默认仍 127.0.0.1。

**Editor 内 UI**：弹 Panel 显示"AI 正在做 XX，有 N 个 pending HITL，[✓批准] [✗拒绝]"，比终端 `input()` 体验好得多。

**性能 / 可观测性**：审计日志接公司 log 系统；metrics（每工具时长、失败率）；dashboard。

**生态工具**：VS Code 扩展（侧栏可视 MCP 工具面）；场景模板 prompt library。

**多 Agent 协作**：Scene Spec + Asset Spec + CPP Spec 并行 —— 写工具仍串行（主线程），但 query 工具可并发。Supervisor / Magentic 调度。

---

## 跨阶段的非目标（明确不做）

即使 v3 也不：

- ❌ Agent 自己执行 `git commit` / `push`（代码提交永远人工）
- ❌ Agent 跑 `cmake --install` / 部署（CI 的事）
- ❌ Agent 动 engine.json / project.json 里 UUID 字段
- ❌ Agent 删除 `Gems/<name>/` 整个目录
- ❌ 默认允许非本机连接（远程是 v3 特例 + 显式配置）

边界在 [04_safety_undo_hitl.md](04_safety_undo_hitl.md)。

---

## 风险与应急（跨阶段）

| 风险 | 触发阶段 | 应急 |
|---|---|---|
| azlmbr API 跨版本改签名 | MVP | 用通用入口 `SetComponentProperty(path, value)`，避免调具体 method |
| Editor 主线程卡死 | MVP-v1 | 工具超时 30s → 返回 timeout；绝不阻塞主线程 |
| MCP Server 内存泄露 | v1-v2 | 每 N 小时主动 ping + reset 队列；真撑不住只能重启 Editor（接受代价） |
| MCP 协议 breaking change | v2 | pin SDK 版本；升级出 migration note |
| DeepSeek API 限流 / 故障 | v2 | Fallback 本地 Ollama；workflow 能短路降级 |
| 团队用户误操作 | v3 | 默认保守 config；管理员可放宽；每台机器独立 config |
| 单进程架构放大故障面（MCP bug 拖垮 Editor） | 全阶段 | 每 tool `try/except`；handler 抛异常绝不让 Editor 退出 |

---

## 写代码前的启动清单

```bash
# 1. 确认 Editor 可以跑 --runpython（基线）
cd o3de
./build/linux/bin/profile/Editor \
    --runpython AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_EntityCRUDCommands_Works.py \
    --runpythontest main
echo $?   # 0 = EditorPythonBindings 装好了

# 2. 确认 Python VM 有 asyncio
./build/linux/bin/profile/Editor --runpython <(echo 'import asyncio; print(asyncio.__version__)') --runpythontest main

# 3. 目录骨架
mkdir -p tools/o3de_mcp/handlers tools/o3de_mcp/tests

# 4. 第一个 commit："MVP bootstrap: HTTP SSE server + 3 handlers"
```

然后按 §MVP 的清单一个个文件写，目标是第一周就能让 `entity.create` 端到端跑通。

---

## 进度跟踪

建议每周更新本文件（append 一节）：

```
### Week 1 actuals (2026-04-24 ~ 2026-04-30)
- done: boot.py + threading_bridge.py + handlers/entity.py
- done: tests/smoke_inproc.py 验证 entity CRUD
- blocked: azlmbr.asset 的 AssetId marshal 要写自定义 encoder
- next: resolve AssetId marshal, finish component.py + asset.py
```

让协作方 / 未来的自己能看到**实际**进度而非计划。

---

## 关联文档

- [00_overview.md](00_overview.md) —— 为什么做这个
- [01_architecture.md](01_architecture.md) —— 怎么做（含线程模型细节）
- [02_tool_catalog.md](02_tool_catalog.md) —— 做成什么样
- [03_workflows.md](03_workflows.md) —— 怎么用
- [04_safety_undo_hitl.md](04_safety_undo_hitl.md) —— 边界 + exec_python 逃生舱
- [tools/agents/](../../tools/agents/) —— 已有 Agent 骨架，v2 集成目标
- [practice/multi_agent_design.md](../practice/multi_agent_design.md) —— 上层 Agent 架构原则
