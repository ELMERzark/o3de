# Agent × MCP × O3DE Editor 设计总览

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 更新记录：2026-04-24 架构简化为"MCP Server 直接跑在 Editor 进程内"（原设计有独立 MCP Server + TCP Bridge 两进程）。
> 目标：让 AI Agent 通过 **MCP（Model Context Protocol）** 直接操作 O3DE 编辑器 ——
> 场景搭建、组件配置、材质指派、天空盒切换、Prefab 组装 …… 像一个"不知疲倦的 TA"。
> 配套：[`tools/agents/`](../../tools/agents/)（已有的多 Agent 骨架）；本系列文档补充 Editor 操纵层

---

## 1. 想解决的问题

以往 AI 协助 O3DE 开发**只能写文件**（.h / .cpp / .cmake）。
但游戏开发一大半工作是**在编辑器里点点拖拖**：

- 拖一个 mesh 进场景 → 调 Transform → 加 Material Component → 指派材质
- 调光：加 Directional Light → 改强度 / 方向 / 颜色
- 切天空盒：改 HDRi Skybox 的 Cubemap
- 组 Prefab：选中一组 entity → Create Prefab → 保存
- 调性能 / 摆 Lod 距离 / 跑 AP / 截图

这些今天对 AI 是黑箱。目标是把**编辑器每一个可点击操作都变成一个 MCP 工具**，让 Agent 能调用。

---

## 2. 关键事实（已验证）

| 事实 | 来源 | 含义 |
|---|---|---|
| 编辑器有 `EditorPythonBindings` Gem | [Gems/EditorPythonBindings/Code/Source/PythonSystemComponent.h:59-62](../../Gems/EditorPythonBindings/Code/Source/PythonSystemComponent.h#L59) | Python VM 跑在编辑器进程内 |
| `azlmbr.*` 暴露 BehaviorContext | [PythonReflectionComponent.cpp](../../Gems/EditorPythonBindings/Code/Source/PythonReflectionComponent.cpp) | 16+ 命名空间：editor/entity/components/asset/prefab/math/bus/... |
| 编辑器支持 `--runpython <file>` / `--runpythontest` | [Code/Editor/CryEdit.cpp:1461-1483](../../Code/Editor/CryEdit.cpp#L1461) | 可启动时塞一个 bootstrap 脚本 |
| **不存在** 原生 socket / RPC 监听 | — | 必须**自己写**一个 MCP 服务层 |
| 丰富的自动化脚本示例 | [AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/) | 30+ 脚本，azlmbr 用法模板 |

**结论**：O3DE 提供了**足够大的 Python 自动化面**，差的只是一个"接受外部 MCP 请求并派发到 azlmbr"的服务层。这层就跑在 Editor 进程内部，由 `--runpython` 加载。

---

## 3. 架构一句话

```
[Agent (MAF / Claude Desktop / Cursor / 任何 MCP Client)]
              │  MCP over HTTP/SSE (localhost:24601)
              ▼
[MCP Server (Python, 跑在 O3DE Editor 进程内)]
              │  azlmbr.*  (worker 线程 → 主线程 marshal)
              ▼
[O3DE Editor (scene / components / assets / prefabs)]
```

**单进程架构**：MCP Server 直接跑在 Editor 的 Python VM 里，通过 `Editor.exe --runpython boot_mcp.py` 启动。**没有**独立 MCP Server 进程，**没有** TCP 桥接层。

为什么是这个形状：
- 少一层跨进程 marshal → 每次工具调用省 1-5ms；一个回合几十次调用下来差别可观
- Claude Desktop 原生支持 HTTP/SSE transport，配置一行 URL 就连上
- 编辑器长时间运行（几小时起），MCP Server 跟它一起稳稳活着；独立重启的需求很弱
- **唯一代价**：asyncio HTTP server 在 Python worker 线程，azlmbr 调用要 marshal 回 Editor 主线程（EBus 不 thread-safe）——这个问题在双进程方案里也躲不掉，不如直接面对。细节见 [01_architecture.md §3](01_architecture.md)

---

## 4. 技术栈选型

| 组件 | 选型 | 备选 | 理由 |
|---|---|---|---|
| MCP Server 语言 | **Python 3.12**（和 Editor Python VM 一致） | — | 必须和 azlmbr 同语言 |
| MCP SDK | **`mcp` 官方 Python SDK** | 手写 SSE | 官方维护，tool/resource/prompt 原生支持 |
| 部署方式 | **Python 脚本（`--runpython boot.py` 加载到 Editor 内）** | 自研 Gem（C++） | 不用重编引擎；MVP 足够，v3 再 Gem 化 |
| MCP transport | **HTTP/SSE** | stdio | Editor 是长期 GUI 进程，stdio 不适用；HTTP 允许多客户端 |
| 线程模型 | **worker 线程跑 asyncio，主线程跑 azlmbr**，中间加 queue | 都挤主线程 | 不阻塞 Editor UI |
| Agent 框架 | 复用 [`tools/agents/`](../../tools/agents/) 的 MAF + DeepSeek | Claude Desktop 原生 | 已有骨架 |

---

## 5. 谁调谁：三个使用场景

### 场景 A：Claude Desktop / Cursor 直连

```
Claude Desktop  ──HTTP/SSE──▶  Editor (MCP Server 内置)
```

用户在 Claude 聊天："把当前场景天空盒改成 studio_hdri"。Claude 调 MCP 工具 `environment.set_skybox(hdri_asset_path="...")`，链路走完。

### 场景 B：自研 Agent（MAF / DeepSeek）驱动

```
tools/agents/workflow.py ──▶ MCP Client (SSE) ──HTTP──▶ Editor (MCP Server 内置)
```

多 Agent（Planner/Specialist/Reviewer）像调 `fs_tools` 一样调 MCP 工具。Planner 决定"要 5 步"，Scene Specialist 逐步调 MCP。

### 场景 C：CI / 自动化脚本

同样走 MCP HTTP/SSE 连到 Editor；或者退化用 `Editor.exe --runpython my_script.py --runpythontest main` 一次性跑完退出，不启动 MCP Server。

---

## 6. 功能面（按优先级）

| 优先级 | 工具域 | 代表工具 | 对应 azlmbr API |
|---|---|---|---|
| P0 MVP | **Entity CRUD** | create_entity, delete_entity, set_parent, rename_entity | `ToolsApplicationRequestBus`, `EditorEntityAPIBus` |
| P0 MVP | **Component CRUD** | add_component, remove_component, list_component_types | `EditorComponentAPIBus` |
| P0 MVP | **Component Property** | set_component_property, get_component_property | `EditorComponentAPIBus::SetComponentProperty` |
| P0 MVP | **Transform** | set_world_translation, set_world_rotation, set_local_scale | `components.TransformBus` |
| P0 MVP | **Asset Resolve** | find_asset_by_path | `asset.AssetCatalogRequestBus::GetAssetIdByPath` |
| P0 MVP | **Query** | list_entities, get_entity_info, find_by_component_type | `EditorEntityInfoRequestBus` |
| P1 | **Level** | save_level, open_level, get_current_level_entity_id | `ToolsApplicationRequestBus`, `EditorLevelBus`(?) |
| P1 | **Material / Mesh 便捷封装** | assign_model, assign_material, set_skybox | 组合 find_asset + set_component_property |
| P1 | **Prefab** | create_prefab, instantiate_prefab, save_prefab | `prefab.PrefabPublicRequestBus` |
| P1 | **Screenshot** | take_screenshot(path, width, height) | `general.run_console_command('r_getScreenshot ...')` 或 Atom API |
| P2 | **Undo / Redo** | begin_undo_batch, end_undo_batch, undo, redo | `ToolsApplicationRequestBus` |
| P2 | **AP 触发** | rescan_assets, wait_for_ap_idle | 外部调 AssetProcessorBatch |
| P2 | **Viewport** | set_camera_transform, align_to_entity | viewport API |
| P3 | **Build / Launch** | build_project(target), launch_game | 脱离编辑器，走 shell |

详细工具定义见 [`02_tool_catalog.md`](02_tool_catalog.md)。

---

## 7. 核心设计原则

1. **结构化工具优先**：Agent 调的是 `@mcp.tool()` 具名函数（有 schema），不是生成 Python 代码。`system.exec_python` 作为 L3 逃生舱，默认关。细节见 [04_safety_undo_hitl.md §15](04_safety_undo_hitl.md)
2. **所有工具幂等 or 可撤销**：任何修改都包进 `EditorCommand` undo batch；Agent 出错可一键回滚
3. **JSON-only 输入输出**：不传 Python 对象，Agent 看到的永远是 JSON。serialize 层负责 marshal
4. **字符串化 EntityId**：EntityId 在 JSON 里用 `"Entity[0x1234]"` 字符串；handler 内部解析回 `azlmbr.entity.EntityId`
5. **HITL 默认开**：destructive 操作（delete_entity, save_level, delete_prefab）默认要用户确认
6. **错误结构化**：handler 返回 `{ok: false, error: {code, message, python_traceback}}`，Agent 能读懂
7. **不做猜测**：找不到 asset 就返回明确错误，不 fallback 到"像的 asset"；幻觉留给 Agent 层处理
8. **单实例 MCP Server**：一个 Editor 进程里就一个 MCP Server；多 Editor 由端口区分

---

## 8. 为什么不直接用 `--runpython` 一次性跑

即"Agent 每次生成脚本，用 `Editor.exe --runpythontest script.py` 跑完退出"——看似简单，但：

- **冷启动 30-60s**：Editor 启动一次要读 engine、打开 level、初始化 Atom —— 每个工具调用都这样走不现实
- **无法增量**：每次脚本退出场景状态重置；Agent 没法"先摆一个，再调 transform"
- **不适合交互**：用户想在 Agent 操作过程中手动点一下再继续，做不到

所以必须常驻。

---

## 9. 风险预警（详见 [04_safety_undo_hitl.md](04_safety_undo_hitl.md)）

| 风险 | 缓解 |
|---|---|
| Agent 一次性 delete 100 个 entity | 所有 destructive 走 HITL + undo batch 包裹 |
| handler 把 Editor 搞崩 | 每个工具 `try/except`；崩了返回错误码；Editor 自身不退出 |
| 并发 Agent 踩踏 | 跨线程队列串行化；同一时间只有一个 azlmbr 调用在主线程 |
| Worker 线程阻塞主线程 | 用 future + tick-pump pattern，绝不在主线程 `await` |
| azlmbr API 跨版本改名 | handler 里用 `EditorComponentAPIBus::SetComponentProperty(path, value)` 这个通用入口，避免调具体 bus 方法 |
| 场景存成脏状态 | save_level 前强制跑一个 validate hook |

---

## 10. 文档索引

| 文件 | 讲什么 |
|---|---|
| `00_overview.md`（本文）| 大图、为什么、事实底座 |
| [`01_architecture.md`](01_architecture.md) | MCP Server 在 Editor 内的组织方式、线程模型、ADR |
| [`02_tool_catalog.md`](02_tool_catalog.md) | 所有 MCP 工具的签名 + 返回值 + 示例 |
| [`03_workflows.md`](03_workflows.md) | Agent 怎么组织（Planner→Executor→Verifier）；三个典型场景 walkthrough |
| [`04_safety_undo_hitl.md`](04_safety_undo_hitl.md) | 安全模型：undo 分组、HITL、禁操作清单、exec_python 逃生舱 |
| [`05_roadmap.md`](05_roadmap.md) | MVP / v2 / v3 分阶段交付物 |

---

## 11. 已锁定决策 vs 待拍板

### 已决定

1. ~~MCP Server 外部进程还是进 Editor~~ → **进 Editor**（Python 脚本 via `--runpython`，不用 Gem）
2. ~~Agent 发 Python 串还是结构化 tool call~~ → **结构化 tool call 为主**；`exec_python` 作为 L3 逃生舱
3. ~~Transport 协议~~ → **MCP over HTTP/SSE**（不用 stdio，不用自研 JSON-RPC）

### 还待拍板

4. **MCP Server 给谁用？** 只给自研 MAF agents / 也让 Claude Desktop 连 / 都要？（推荐：都要，HTTP transport 天然支持）
5. **多 Editor 实例支持？** MVP 单实例够用，v2 再说
6. **Undo 粒度**：每个工具一个 undo entry 还是每个 Agent "turn" 一个？（推荐 turn-level）
7. **场景快照**：`query.scene_snapshot() → JSON` 要不要做 MVP？（推荐要，见 [03_workflows.md](03_workflows.md)）

细节见各分册。
