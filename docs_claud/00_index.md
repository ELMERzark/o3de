# docs_claud — O3DE 开发者 AI 上下文包

> 本目录是为其他 AI 模型（GPT、Gemini、Copilot、本地 LLM 等）准备的、关于本仓库 O3DE (Open 3D Engine) 的"背景材料"。
>
> 把一个或多个文件粘贴到对方的 system / context 里，它就能在不读整个仓库的情况下，做出更贴近本项目实际结构和惯例的修改建议。

---

## 文档元数据（重要）

| 字段 | 值 |
|---|---|
| **编写日期** | `2026-04-24` |
| **引擎仓库** | `o3de/o3de` |
| **基于分支** | `development` |
| **基于 commit** | `aa2f89cb7eec48b7d1db3315b26220d48e252aff`（短：`aa2f89cb7e`） |
| **Engine 版本** | `0.1.0.0`（见 [engine.json](../engine.json) 的 `O3DEVersion`） |
| **显示版本** | `4.2.0` |
| **API 版本** | editor `1.0.0` · framework `1.2.1` · launcher `1.0.0` · tools `1.1.0` |
| **本地检出路径** | `g:/AXX/O3DE/o3de`（仅本次采集时所在位置，别处 clone 时路径不同） |

### 给读这份文档的 AI 的话

**重要**：这些文档引用了大量具体的**文件路径 / 类名 / API 签名 / CMake 宏 / CVar**。引擎每隔几周就有大 PR，以下内容可能漂移：

- 文件路径重命名 / 文件迁移
- 类被拆分 / 合并 / 重命名
- 新增 / 废弃 EBus
- AZ_* 宏增减
- Gem 新增 / 移除（尤其 `Gems/AWSCore` 类历史上被迁走）

### 怎么判断这份文档过不过时

1. **看仓库的 commit 日期 vs 本文档的 `编写日期`**：超过 3-6 个月建议交叉核对关键事实。
2. **抽查某条事实**：找文档里写的"`<路径>` 的 `<类>::<方法>` 签名是 X"，去实际文件里 grep 一下对得上吗。
3. **官方文档比对**：<https://www.o3de.org/docs/> 有引擎 API reference（但官方文档也常滞后）。

### 本文档被修订时请更新

如果你（或未来的自己）基于新 commit 重新核实了内容：

1. 改 `00_index.md` 顶部这张表的 **编写日期** 和 **commit**。
2. 如果某份子文档被大改，同步改它顶部的 `> 基于 O3DE ...` 戳记。
3. 改动大的章节在顶部加一行 "**更新记录**"。

> 现在每份子文档顶部都有一行短戳记（`> 基于 O3DE development @ aa2f89cb7e (2026-04-24)`）。看到文档和仓库不一致时，先把这行和实际 `git log` 对比一下。

## 这份材料的设计原则

1. **不重复官方文档** — 只写"打开仓库后对着代码能看到的那种"事实：目录布局、关键类、宏、EBus、CMake 习惯、扩展点。
2. **可单独拆用** — 每个 md 是自包含的，可以只塞其中一份（比如只做 UI 任务时只塞 `04_aztoolsframework.md` + `11_conventions_and_patterns.md`）。
3. **面向写代码的 AI** — 重点是"要改 X 去哪改、常用宏怎么写、坑在哪里"，而不是"引擎历史和愿景"。
4. **路径都用仓库相对路径** — 方便对方 AI 直接让用户打开对应文件。

## 文件清单

| 文件 | 作用 | 什么时候塞给 AI |
|---|---|---|
| [01_overview.md](01_overview.md) | 项目定位、分层架构、目录地图 | 所有任务都先塞一份 |
| [02_azcore.md](02_azcore.md) | `AzCore`: Component/Entity/EBus/RTTI/Memory/Serialization | 写任何 C++ 组件、EBus、反射 |
| [03_azframework.md](03_azframework.md) | `AzFramework`: Application、Input、Scene、Spawnable、Console | 运行时系统、输入、关卡加载 |
| [04_aztoolsframework.md](04_aztoolsframework.md) | `AzToolsFramework`: Editor、Prefab、ComponentMode、PropertyEditor | 写 Editor 端功能、工具 Gem |
| [05_gems_and_modules.md](05_gems_and_modules.md) | Gem 包结构、`Module` 生命周期、注册机制 | 新建 Gem / 加载 Gem / 排依赖 |
| [06_build_and_cmake.md](06_build_and_cmake.md) | `ly_add_target`、`*_files.cmake`、preset、monolithic | 改构建、加文件、加第三方依赖 |
| [07_asset_pipeline.md](07_asset_pipeline.md) | Asset Processor、AssetBuilder、AssetManager、Catalog | 写 Builder、加资产类型、调试 AP |
| [08_rendering_atom.md](08_rendering_atom.md) | Atom: RHI / RPI / Feature 三层、Pass、Material/Shader | 写渲染特性、改 pass、做材质 |
| [09_scripting.md](09_scripting.md) | ScriptCanvas、Lua、Python（Editor/AP） | 暴露 API 给脚本、写 Editor Python |
| [10_networking_physics.md](10_networking_physics.md) | Multiplayer Gem、AzNetworking、PhysX | 写联网组件、改物理集成 |
| [11_conventions_and_patterns.md](11_conventions_and_patterns.md) | `AZ_*` 宏、命名、智能指针、RAII、错误处理 | 给 AI 一份"风格守则" |
| [12_cookbook_recipes.md](12_cookbook_recipes.md) | 常见任务的最短可行步骤（加组件/EBus/Gem/资产类型…） | AI 做"从零写一个 X"任务 |
| [13_ai_context_guide.md](13_ai_context_guide.md) | 给其他 AI 提示用：读哪些文件、先问哪些问题、常见误区 | 作为 "meta prompt" 一起贴 |
| [14_gems_catalog.md](14_gems_catalog.md) | ~100 个内置 Gem 的分类目录 + "任务 → Gem" 速查 + 依赖链 | 选型、规划项目要启哪些 Gem |
| [15_debugging_toolkit.md](15_debugging_toolkit.md) | 按症状组织的调试路径：启动崩、EBus 不响应、渲染黑、AP 卡住、联机不同步… | 代码出问题时 |
| [16_performance_checklist.md](16_performance_checklist.md) | Profile 工具、帧预算、CPU/GPU/内存/资产/网络逐项优化清单 | 项目要提性能时 |
| [17_ci_cd_guide.md](17_ci_cd_guide.md) | GitHub Actions / Jenkins 模板、TIAF、打包、monolithic 构建、常见 CI 陷阱 | 建 CI pipeline / 上 release 流程 |
| [18_dcc_integration.md](18_dcc_integration.md) | Blender / Maya / Substance 等 DCC 工具链；FBX / Scene Manifest；DccScriptingInterface | 打通美术→引擎资产流水 |
| [19_new_project_checklist.md](19_new_project_checklist.md) | 从零装环境到 Editor 跑第一个 Entity 的完整步骤 + 第一周要做的事 | 新项目 kick-off / 新人上手 |

## 推荐的"打包组合"

- **最小必带**：`01_overview.md` + `11_conventions_and_patterns.md` + `13_ai_context_guide.md`
- **写运行时组件**：+ `02_azcore.md` + `03_azframework.md` + `12_cookbook_recipes.md`
- **写 Editor 工具**：+ `02_azcore.md` + `04_aztoolsframework.md` + `05_gems_and_modules.md`
- **新建 Gem**：+ `05_gems_and_modules.md` + `06_build_and_cmake.md` + `12_cookbook_recipes.md`
- **规划项目要启哪些 Gem**：+ `14_gems_catalog.md`
- **渲染相关**：+ `02_azcore.md` + `08_rendering_atom.md` + `14_gems_catalog.md`（找到相关 Gem）
- **资产/流水线**：+ `06_build_and_cmake.md` + `07_asset_pipeline.md`
- **出问题要 debug**：`15_debugging_toolkit.md` + 对应领域的深入文档
- **项目要提性能**：`16_performance_checklist.md`
- **上 CI / 发布**：`17_ci_cd_guide.md` + `06_build_and_cmake.md`
- **美术 / DCC 流水线**：`18_dcc_integration.md` + `07_asset_pipeline.md`
- **新项目 / 新人上手**：`19_new_project_checklist.md` + `01_overview.md`

## 落地设计文档（按子系统分类）

以上 19 份 md 是**引擎自身的参考资料**（"o3de 是什么样"）。下面是**基于这份参考构建的具体系统设计**（"我们在 o3de 之上要做什么"）。

| 子文件夹 | 主题 | 入口 |
|---|---|---|
| [practice/](practice/) | 多 Agent 总体架构 | [multi_agent_design.md](practice/multi_agent_design.md) |
| [editor_mcp/](editor_mcp/) | 通过 MCP 让 Agent 直接操作 O3DE Editor 做场景搭建 | [00_overview.md](editor_mcp/00_overview.md) |

新加子系统设计时开一个新子文件夹（推荐文件前缀 `00_overview.md` → `01_...` 编号，每份顶部也带 `> 基于 O3DE <branch> @ <commit> (<date>)` 戳记）。

## 快速事实（给 AI 的一行摘要）

- 引擎名 `o3de`，版本见 [engine.json](../engine.json)，语言以 **C++17** 为主，配 **Python 3** + **CMake ≥ 3.24**。
- 构建入口 [CMakeLists.txt](../CMakeLists.txt)；preset 在 [CMakePresets.json](../CMakePresets.json)；封装宏在 [cmake/LYWrappers.cmake](../cmake/LYWrappers.cmake)。
- 核心框架在 [Code/Framework/](../Code/Framework/) — `AzCore` → `AzFramework` → `AzToolsFramework` 是三层依赖递增关系。
- 全部游戏功能都是 **Gem**（[Gems/](../Gems/)），引擎自己也靠 Gem 组合使用（Atom、PhysX、ScriptCanvas…）。
- 实体-组件模型：`AZ::Entity` 持有多个 `AZ::Component`，组件间靠 **EBus**（事件总线）解耦。
