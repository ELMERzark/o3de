# 01 · O3DE 项目总览与仓库地图

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## 这是什么项目

**O3DE (Open 3D Engine)** — 开源、跨平台、实时 3D 引擎。Apache 2 / MIT 双协议。设计目标：AAA 游戏、影视、仿真。前身是 Amazon Lumberyard / CryEngine 血统，但运行时已经整体重写成当前的 `Az*` + Atom + Gem 架构。

- 引擎本体版本：见 [engine.json](../engine.json) 的 `version` 字段。
- 默认项目：[AutomatedTesting](../AutomatedTesting/)（自带的端到端测试项目，也是最好的"真实用例"参考）。

## 分层架构（自下而上）

```
┌───────────────────────────────────────────────────────────┐
│ Projects / Games          (AutomatedTesting, 用户项目)    │
├───────────────────────────────────────────────────────────┤
│ Gems                      (Atom, PhysX, ScriptCanvas…)   │
├───────────────────────────────────────────────────────────┤
│ AzToolsFramework          (Editor-only: Prefab, 操纵器)   │
├───────────────────────────────────────────────────────────┤
│ AzFramework               (运行时: App, Input, Scene)     │
├───────────────────────────────────────────────────────────┤
│ AzCore                    (Entity/Component, EBus, RTTI)  │
├───────────────────────────────────────────────────────────┤
│ 3rdParty + 平台抽象 (PAL) + CMake / Python 驱动            │
└───────────────────────────────────────────────────────────┘
```

依赖方向**严格向下**。Gem 可以依赖其它 Gem，但永远不要让 `AzFramework` 引用某个具体 Gem；`AzCore` 不知道 Qt / Editor / 渲染存在。

### 各层一句话职责

- **AzCore**：内存分配器、RTTI、反射（SerializeContext / EditContext / BehaviorContext）、EBus、`Entity` + `Component`、`Module` 基类、Jobs、Math。**不依赖 Qt，不依赖渲染。**
- **AzFramework**：`ComponentApplication` 派生出 `Application`（运行时入口）、输入、场景（`Scene` / `Spawnable`）、控制台变量、网络基础。**仍不依赖 Qt。**
- **AzToolsFramework**：Editor 进程专用。Qt 属性编辑器、Prefab 系统、操纵器 (Manipulators)、源码控制、Python Terminal。**依赖 Qt，但不依赖具体渲染后端。**
- **Gems**：所有可选功能。渲染器本身（Atom）、物理（PhysX / NvCloth）、脚本（ScriptCanvas / Lua）、音频、UI、联网 … 都是 Gem。项目选择启用哪些 Gem。

## 进程模型（记住这一点，能避开大量困惑）

一个 O3DE 项目实际上在开发时会并行跑**多个可执行**，共享同一套源码，靠宏和 CMake 配置区分：

| 进程 | 构建目标 | 谁编译 | 作用 |
|---|---|---|---|
| **Editor** | `Editor` | Tools 配置 | Qt 编辑器，加载所有 Editor-only 的 Gem 模块 (`*.Editor`) |
| **AssetProcessor** | `AssetProcessor` / `AssetProcessorBatch` | Tools 配置 | 后台编译源资产 → 运行时资产（见 07 文档） |
| **GameLauncher** | `<Project>.GameLauncher` | Client 配置 | 发布出去的纯运行时，只加载 `*.Client` / 通用模块 |
| **ServerLauncher** | `<Project>.ServerLauncher` | Server 配置 | 专用服务端（如果项目启用 Multiplayer） |
| **UnifiedLauncher** | `<Project>.UnifiedLauncher` | Unified | Client + Server 合一（便于本地调试联机） |

同一个 Gem 通常会被拆成 `<Name>.Static` / `<Name>.API` / `<Name>.Private` / `<Name>.Editor.*` / `<Name>.Tests` 等多个 CMake target，这是理解 [06_build_and_cmake.md](06_build_and_cmake.md) 的前提。

## 仓库顶层地图

```
o3de/
├── Code/
│   ├── Framework/         Az* 四件套核心框架
│   │   ├── AzCore/          — 基础层
│   │   ├── AzFramework/     — 运行时层
│   │   ├── AzToolsFramework/— Editor 层（Qt）
│   │   ├── AzGameFramework/ — Game 专用薄层（继承 AzFramework::Application）
│   │   ├── AzNetworking/    — 底层网络传输
│   │   ├── AzQtComponents/  — Qt 定制控件（Editor 主题等）
│   │   ├── AzTest/          — gtest 封装
│   │   └── AzManipulatorTestFramework/
│   ├── Editor/            Editor 可执行壳
│   ├── LauncherUnified/   GameLauncher/ServerLauncher/UnifiedLauncher 模板源码
│   ├── Legacy/            CryEngine 遗留代码（正在逐步淘汰，新代码别进）
│   └── Tools/             独立的开发工具
│       ├── AssetProcessor/   资产管线核心进程
│       ├── AssetBundler/     打包资产 bundle
│       ├── ProjectManager/   项目管理 GUI
│       ├── LuaIDE/           Lua 脚本调试 IDE
│       ├── SceneAPI/         FBX/GLTF 导入抽象
│       ├── SerializeContextTools/ 反射/序列化 dump CLI
│       └── TestImpactFramework/   变更影响的测试裁剪
│
├── Gems/                  全部"功能插件"所在地（见下）
├── Templates/             创建 Gem / Project / Component 的脚手架
├── Assets/                引擎自带的共享资产（Editor 图标、默认 material 等）
├── Registry/              Settings Registry 的默认 *.setreg
├── scripts/
│   ├── o3de.bat / o3de.sh   CLI 入口（create-project / register 等）
│   └── build/               构建辅助脚本
├── python/                 引擎自带的 Python runtime / pip 环境
├── cmake/                  所有 CMake 封装宏和平台抽象
├── Tools/                  更上游的杂项工具（不是 CMake 目标）
├── build/                  本地构建输出（默认 .gitignore）
├── Docker/                 Linux docker 构建脚本
├── AutomatedTesting/       默认自测项目
├── engine.json             引擎元数据（注册的 Gem、项目、版本）
├── CMakeLists.txt          顶层 CMake 入口
├── CMakePresets.json       预设 (windows-msvc / linux-gcc 等)
└── CONTRIBUTING.md
```

## Gems 地图（挑重点）

不是完整列表，这些是"碰到就要认识"的：

| Gem | 干啥的 | 关键依赖 |
|---|---|---|
| [Atom](../Gems/Atom/) | 渲染器本体，拆成 `RHI`（抽象）/`RPI`（Pipeline）/`Feature`（可用特性）/`Tools` | 所有渲染类 Gem |
| [AtomLyIntegration](../Gems/AtomLyIntegration/) | 把 Atom 装进 AzFramework 应用（启动时初始化、Viewport 集成） | Atom |
| [CommonFeaturesAtom](../Gems/AtomLyIntegration/CommonFeatures/) | 网格/灯光/相机组件等"用 Atom 看得见东西"的常用组件 | Atom |
| [PhysX](../Gems/PhysX/) | 物理，Core 下分 `PhysX4` / `PhysX5` | AzFramework / Atom (debug draw) |
| [LmbrCentral](../Gems/LmbrCentral/) | 大量"通用游戏类组件"与遗留兼容层（几乎所有项目都启用） | 大部分 Gem 隐式依赖它 |
| [ScriptCanvas](../Gems/ScriptCanvas/) + [GraphCanvas](../Gems/GraphCanvas/) + [GraphModel](../Gems/GraphModel/) | 可视化脚本：运行时 + 编辑器画布 + 图模型 | Editor 下能用 |
| [EMotionFX](../Gems/EMotionFX/) | 角色动画系统 | Atom |
| [Multiplayer](../Gems/Multiplayer/) + [MultiplayerCompression](../Gems/MultiplayerCompression/) | 基于 AzNetworking 的网络同步、快照、RPC | AzNetworking |
| [Prefab](../Gems/Prefab/) | Prefab 资产构建（运行时加载在 AzFramework 里） | — |
| [SceneProcessing](../Gems/SceneProcessing/) | FBX/GLTF 源资产处理器配置 | SceneAPI |
| [EditorPythonBindings](../Gems/EditorPythonBindings/) + [QtForPython](../Gems/QtForPython/) | Editor 端 Python 绑定，pyside2 接入 | Editor |

## 典型代码加载链（运行时）

```
GameLauncher(main)
  → AzGameFramework::GameApplication::Start()
    → 读 engine.json / project.json / *.setreg 配置
      → ModuleManager 加载每个启用 Gem 的动态库
        → Gem 的 AZ::Module 派生类被实例化
          → Module 构造时在列表里注册自己的 SystemComponent 类
            → 创建 System Entity，把这些 SystemComponent 激活
              → 每帧 TickBus → 你的 Component::Activate/Deactivate/OnTick
```

想理解这条链，读 [03_azframework.md](03_azframework.md) 的"应用生命周期"节。

## 平台抽象 (PAL)

每个需要平台分支的模块都有一份 `Platform/<OS>/` 子目录 + 一个 `Code/Framework/.../<Name>_Platform.inl` 包含夹层。相关 CMake 粘合在 [cmake/PAL.cmake](../cmake/PAL.cmake) 和各 Gem 的 `Platform/<OS>/PAL_*.cmake`。

**AI 动手改某模块时，必看是否有对应的 `Platform/Windows` / `Platform/Linux` / `Platform/Mac` 分支需要同步改**。

## 接下来读哪份

- 要改 **代码**：直接看 `02_azcore.md` → `03_azframework.md` → `11_conventions_and_patterns.md`。
- 要改 **构建**：跳到 `06_build_and_cmake.md`。
- 要 **新建东西**：先读 `12_cookbook_recipes.md`。
