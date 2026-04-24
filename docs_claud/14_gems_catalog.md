# 14 · Gems 功能目录

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。
>
> **特别提醒**：Gem 清单是漂移最快的部分 — 引擎频繁增删 Gem、改 `external_subdirectories`。本章列的 ~100 个 Gem 是本 commit 时的快照；若碰到本章未列的 Gem 或本章列的 Gem 已消失，以 [engine.json](../engine.json) 当前内容为准。

> 本章回答一个实用问题：**"我想做 X，要启用哪个 Gem？"**
>
> 仓库里 `Gems/` 下有 ~80+ 顶级 Gem 目录，加上嵌套子 Gem（如 `Atom/RHI`、`Atom/RPI` 各自独立）**共 ~100+ 个可启用 Gem**。本章按功能分类，对每个 Gem 给 1-2 行用途说明 + 主要组件/能力 + 典型依赖。
>
> 工作方式：先看"任务 → Gem"速查，再细读对应类别。所有 Gem 在 [engine.json](../engine.json) 的 `external_subdirectories` 里登记；项目用 [scripts/o3de.bat](../scripts/o3de.bat) `enable-gem` 加进 `project.json` 的 `gem_names`。

---

## 快速速查：任务 → Gem

| 我要做的 | 启用这些 | 备注 |
|---|---|---|
| 最基础"能跑起来"的项目 | `LmbrCentral` + `Atom_RHI` + `Atom_RPI` + `Atom_Feature_Common` + `Atom_Bootstrap` + `CommonFeaturesAtom` + `AtomLyIntegration` | 引擎默认项目的最小渲染堆栈 |
| 在场景里摆模型 | 上一行 + `Prefab` (内置) | Mesh Component 来自 `CommonFeaturesAtom` |
| 物理碰撞 / 刚体 | `PhysX5` (或 PhysX4) + `PhysXCommon` | 新项目选 PhysX5 |
| 布料 | `NvCloth` | 独立系统，不走 PhysX Scene |
| 角色动画（骨骼 / blend / ragdoll） | `EMotionFX` + `EMotionFX_Atom`（+ `PhysX5` 如果用 ragdoll） | |
| 过场 / 时间轴 | `Maestro` | 序列器 |
| 音频（用 MiniAudio，开箱即用） | `AudioSystem` + `MiniAudio` | MiniAudio 是轻量实现 |
| 音频（商用级 Wwise） | `AudioSystem` + 自行集成 Wwise Gem（非本 repo） | |
| 麦克风输入 | `Microphone` | |
| UI 界面 | `LyShine` (+ `TextureAtlas`, `UiBasics`) | |
| HUD / 调试 UI | `ImGui` + `ImguiAtom` | 运行时 overlay |
| 游戏逻辑用可视化脚本 | `ScriptCanvas` + `GraphCanvas` + `GraphModel` + `ScriptEvents` | |
| 游戏逻辑用 Lua | 不需要额外 Gem（AzCore 自带） | |
| Editor 用 Python 自动化 | `EditorPythonBindings` (+ `QtForPython` 如果要 PySide) | |
| 可视化脚本里写物理逻辑 | `ScriptCanvasPhysics` | |
| 相机控制（FPS / 第三人称） | `Camera` + `CameraFramework` + `StartingPointCamera` + `StartingPointInput` | Starting Point 是新手模板 |
| 联机 / 多人游戏 | `Multiplayer` + `CertificateManager` (+ `MultiplayerCompression`) | |
| 游戏里画调试线 / 球 / 文本 | `DebugDraw` | 运行时可见 |
| 性能剖析 | `Profiler` | 自带 Tracy / Superluminal hook |
| 资产流式加载 | `Streamer` | AzCore 的流式层激活 |
| 崩溃报告 | `CrashReporting` | 需配置上报端点 |
| 地形高度图 / 材质混合 | `Terrain` + `GradientSignal` + `SurfaceData` (+ `FastNoise`) | |
| 程序化植被 | `Vegetation` + `GradientSignal` + `SurfaceData` | |
| 景观工具（节点编辑） | `LandscapeCanvas` | Editor-only |
| 粒子 | `OpenParticleSystem` (预览版) | |
| 视频播放 | `VideoPlaybackFramework` | |
| AI 寻路 | `RecastNavigation` | 运行时 + Editor |
| 天空 / 星星 / 全局光照 | `SkyAtmosphere` + `Stars` + `DiffuseProbeGrid` | 各自独立 |
| 头发渲染（TressFX） | `AtomTressFX` | AMD 开源 |
| Meshlet 渲染优化 | `Meshlets` | 现代 GPU |
| 多 GPU 交替帧渲染 | `AFR` | 需命令行参数 |
| 手势识别（触屏） | `Gestures` | |
| 虚拟手柄（移动设备） | `VirtualGamepad` | |
| 成就 | `Achievements` | 平台无关接口 |
| 存档 | `SaveData` | 跨平台存档 |
| 在线状态 | `Presence` | |
| 内购 | `InAppPurchases` | |
| 游戏状态机（菜单 / 游戏中 / 暂停） | `GameState` (+ `GameStateSamples` 参考) | |
| 写自定义资产类型 | `CustomAssetExample` 参考 + 自己写 Gem | |
| 用 Python 写 AssetBuilder | `PythonAssetBuilder` | 无需 C++ 编译 |
| 白盒关卡（快速原型几何） | `WhiteBox` | |
| 节点编辑器框架（做自己的可视化工具） | `GraphCanvas` + `GraphModel` | 同 ScriptCanvas 用的底层 |
| 场景日志示例 | `SceneLoggingExample` | 学 Scene Pipeline 参考 |
| 数学表达式求值（运行时公式） | `ExpressionEvaluation` | |

---

## 几个"几乎必启"的 Gem

以下通常项目都会启（`Templates/MinimalProject` / `DefaultProject` 都默认启）：

- `LmbrCentral` — **核心 Gem**，几十个通用组件和服务；不启基本无法工作
- `Atom_RPI` + `Atom_RHI` + `Atom_Feature_Common` + `Atom_Bootstrap` + `CommonFeaturesAtom` — 渲染堆栈
- `PrimitiveAssets` — 基础几何体（Cube/Sphere/Cylinder…） 
- `DebugDraw` — 开发时非常有用
- `Profiler` — 性能监控几乎必需
- `TextureAtlas` — UI 和图标依赖

---

## 分类目录

下面按功能分类列出 Gem。每条格式：`Gem名 — 简介 [key classes/components] (依赖: X, Y)`。

---

### 1) 核心 / 框架

| Gem | 路径 | 作用 |
|---|---|---|
| **LmbrCentral** | `Gems/LmbrCentral/` | O3DE 最重要的基础 Gem。提供 `TransformComponent`、`MeshComponent`（通过 bus）、`SphereShapeComponent` / `BoxShapeComponent` / `CylinderShapeComponent` / `CapsuleShapeComponent` / `CompoundShapeComponent` / `SplineComponent`、`TagComponent`、`AudioListenerComponent` 等几十个通用组件；还包含 SliceBuilder、CopyDependencyBuilder 等核心 AssetBuilder。**几乎所有其它 Gem 隐式依赖它**。 |
| **Archive** | `Gems/Archive/` | O3AR 归档格式读写（类 `.pak`）；支持文件级压缩。`ArchiveSystemComponent`。 |
| **Compression** | `Gems/Compression/` | 通用压缩 API（内置 LZ4 实现）。给 Archive / 网络 / Asset 流水线提供选项。 |
| **ExpressionEvaluation** | `Gems/ExpressionEvaluation/` | 运行时数学表达式求值（字符串 → 值）。用于数据驱动的条件 / 公式。 |
| **ScriptEvents** | `Gems/ScriptEvents/` | `.scriptevents` 资产：跨 C++/Lua/SC 的"通讯契约"。见 [09_scripting.md](09_scripting.md)。 |
| **CertificateManager** | `Gems/CertificateManager/` | SSL/TLS 证书管理；联机加密连接的基础。 |
| **Prefab**（内置在 `AzToolsFramework` 中）| - | Prefab 系统本身在 Editor 框架；`Gems/Prefab/PrefabBuilder/` 提供把 `.prefab` 烘焙到 `.spawnable` 的 AssetBuilder。 |

---

### 2) 渲染（Atom 生态）

#### 核心层

| Gem | 路径 | 作用 |
|---|---|---|
| **Atom_RHI** | `Gems/Atom/RHI/` | 图形 API 抽象（Render Hardware Interface）。`Device`, `CommandList`, `FrameGraph`, `Image`, `Buffer`, `SwapChain`, `PipelineState`, `ShaderResourceGroup`。见 [08_rendering_atom.md](08_rendering_atom.md)。 |
| **Atom_RHI_DX12** / **Atom_RHI_Vulkan** / **Atom_RHI_Metal** / **Atom_RHI_Null** | `Gems/Atom/RHI/DX12` 等 | RHI 的各平台后端实现。Null 供 CI / headless 测试。**一般不需要手动启用**，由构建平台决定。 |
| **Atom_RPI** | `Gems/Atom/RPI/` | Render Pipeline Interface。`Scene`, `View`, `RenderPipeline`, `Pass`, `FeatureProcessor`, `Shader`, `ShaderResourceGroup (RPI)`, `Material`, `Model`。 |
| **Atom_Feature_Common** | `Gems/Atom/Feature/Common/` | PBR 管线、光照（Directional/Spot/Point/Area）、阴影、SSAO、SSR、Bloom、DOF、TAA、ToneMap、天空、`MeshFeatureProcessor` 等"看得见的东西"大多在这。 |
| **Atom_Bootstrap** | `Gems/Atom/Bootstrap/` | 启动时把 Atom 接入 AzFramework Window / ViewportContext。 |
| **Atom_Utils** | `Gems/Atom/Utils/` | 无依赖公共工具（ColorConversion、TangentSpace、TextureAtlas 等）。 |

#### 资产 Builder

| Gem | 路径 | 作用 |
|---|---|---|
| **AtomShader** | `Gems/Atom/Asset/Shader/` | `.azsl` → `.azshader`（azslc 编译包装）。 |
| **ImageProcessingAtom** | `Gems/Atom/Asset/ImageProcessingAtom/` | 纹理导入：`.png/.tif/.exr/.dds` → streaming image。压缩格式选择、mip 生成。 |

#### Atom 与 O3DE 集成

| Gem | 路径 | 作用 |
|---|---|---|
| **AtomLyIntegration**（伞 Gem）| `Gems/AtomLyIntegration/` | 一组 Atom 与 Editor / AzFramework 的胶水 Gem。|
| **CommonFeaturesAtom** | `Gems/AtomLyIntegration/CommonFeatures/` | `MeshComponent`、`MaterialComponent`、`DirectionalLightComponent`、`SpotLightComponent`、`PointLightComponent`、`AreaLightComponent`、`ReflectionProbeComponent`、`DecalComponent`、`PostFXLayerComponent`、`ExposureControlComponent`、`DepthOfFieldComponent`、`BloomComponent`、`ChromaticAberrationComponent`、`SsaoComponent`、`HDRiSkyboxComponent`… **写游戏基本都要启**。 |
| **AtomBridge** | `Gems/AtomLyIntegration/AtomBridge/` | 历史遗留渲染桥接（从老 CryEngine 渲染过渡）。新项目基本不碰。 |
| **AtomFont** | `Gems/AtomLyIntegration/AtomFont/` | 字体渲染。 |
| **AtomViewportDisplayInfo** | `Gems/AtomLyIntegration/AtomViewportDisplayInfo/` | 视口左上角 FPS / API / 分辨率 HUD。 |
| **AtomViewportDisplayIcons** | `Gems/AtomLyIntegration/AtomViewportDisplayIcons/` | Editor 视口里的组件图标（灯、相机等）。 |
| **AtomImGuiTools** | `Gems/AtomLyIntegration/AtomImGuiTools/` | Pass Tree / Material / Shader / FrameGraph 的 ImGui 调试面板。 |
| **ImguiAtom** | `Gems/AtomLyIntegration/ImguiAtom/` | ImGui 渲染集成（把 ImGui 画到 Atom pipeline）。 |
| **EMotionFX_Atom** | `Gems/AtomLyIntegration/EMotionFXAtom/` | EMotionFX 骨骼动画 → Atom mesh 渲染的桥。 |
| **AtomRenderOptions** | `Gems/AtomLyIntegration/AtomRenderOptions/` | 运行时渲染选项（画质档）。 |
| **EditorModeFeedback** | `Gems/AtomLyIntegration/EditorModeFeedback/` | Editor "选中模式 / Focus Mode" 等的视觉反馈（高亮、dim）。 |
| **DccScriptingInterface** | `Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/` | DCC 工具（Maya/Blender/3DS Max）与 O3DE 的 Python 脚本桥。 |

#### Atom 工具（Editor-only）

| Gem | 路径 | 作用 |
|---|---|---|
| **AtomToolsFramework** | `Gems/Atom/Tools/AtomToolsFramework/` | 给 Atom 系列工具（Material Editor 等）共享的 Qt 基建。 |
| **MaterialEditor** | `Gems/Atom/Tools/MaterialEditor/` | 独立 `.material` 属性编辑器（独立应用）。 |
| **MaterialCanvas** | `Gems/Atom/Tools/MaterialCanvas/` | 节点图生成 `.materialtype` 的工具。 |
| **PassCanvas** | `Gems/Atom/Tools/PassCanvas/` | `.pass` 可视化编辑。 |
| **ShaderManagementConsole** | `Gems/Atom/Tools/ShaderManagementConsole/` | Shader 变体管理（离线 supervariant 编译）。 |

#### Atom 高级 / 特效

| Gem | 路径 | 作用 |
|---|---|---|
| **AtomTressFX** | `Gems/AtomTressFX/` | AMD TressFX 头发/毛发模拟 + 渲染。 |
| **Meshlets** | `Gems/Meshlets/` | Meshlet 顶点簇渲染（DX12 Mesh Shader）。 |
| **DiffuseProbeGrid** | `Gems/DiffuseProbeGrid/` | 漫反射全局光照探针网格；大场景全局光的方案。 |
| **SkyAtmosphere** | `Gems/SkyAtmosphere/` | 物理天空模型（`SkyAtmosphereComponent`）。 |
| **Stars** | `Gems/Stars/` | 夜空星星渲染。 |
| **AFR** | `Gems/AFR/` | Alternate Frame Rendering，多 GPU 分帧（需命令行 `--afr <pipelinename> --device-count N`）。 |

#### Atom 内容 / 示例资产

| Gem | 路径 | 作用 |
|---|---|---|
| **AtomContent** | `Gems/AtomContent/` | 伞目录 |
| **Sponza** | `Gems/AtomContent/Sponza/` | Sponza 场景（渲染测试基准）。 |
| **ReferenceMaterials** | `Gems/AtomContent/ReferenceMaterials/` | PBR 参考材质库。 |
| **Atom_TestData** | `Gems/AtomContent/TestData/` | Atom 测试用资产。 |
| **DevTextures** | `Gems/DevTextures/` | 网格 / 测试棋盘 / 默认贴图。 |
| **PrimitiveAssets** | `Gems/PrimitiveAssets/` | Cube / Sphere / Cylinder / Cone / Plane 等基础几何体。 |

---

### 3) 物理 / 碰撞 / 布料

| Gem | 路径 | 作用 |
|---|---|---|
| **PhysXCommon** | `Gems/PhysX/Common/` | PhysX 跨版本公共部分（必启，和 Core 配合）。 |
| **PhysX5** | `Gems/PhysX/Core/PhysX5/` | 新项目选这个：PhysX SDK 5.x 后端。提供 `PhysXRigidBodyComponent`、`PhysXStaticRigidBodyComponent`、`PhysXColliderComponent`、`PhysXCharacterControllerComponent`、`PhysXRagdollComponent`、各种 `PhysX*JointComponent`、`PhysXForceRegionComponent`、`PhysXHeightfieldColliderComponent`。 |
| **PhysX4** | `Gems/PhysX/Core/PhysX4/` | 旧项目或 PhysX5 不兼容的后端。**与 PhysX5 互斥**。 |
| **PhysX5Debug** / **PhysXDebug** | `Gems/PhysX/Debug/PhysX5` / `Debug/PhysX4` | PVD 连接、debug draw。开发时启用。 |
| **NvCloth** | `Gems/NvCloth/` | NVIDIA NvCloth 布料模拟。**和 PhysX 独立**的 Scene；`ClothComponent` 挂到 Mesh 上。 |

---

### 4) 动画 / 骨骼 / 过场

| Gem | 路径 | 作用 |
|---|---|---|
| **EMotionFX** | `Gems/EMotionFX/` | 核心动画系统。`ActorComponent`、`AnimGraphComponent`、`SimpleMotionComponent`、`AnimAudioComponent`。支持骨骼 / 动画图 / blend tree / ragdoll / morph target。 |
| **EMotionFX_Atom** | `Gems/AtomLyIntegration/EMotionFXAtom/` | EMotionFX 的 Atom 渲染桥（上节已列）。 |
| **MotionMatching** | `Gems/MotionMatching/` | 动作匹配（motion matching）自动找最贴近目标动作片段。适合复杂角色移动。 |
| **Maestro** | `Gems/Maestro/` | 时间轴 / 过场系统（`SequenceComponent`），用于 cutscene、动画事件。 |
| **ScriptedEntityTweener** | `Gems/ScriptedEntityTweener/` | 属性补间动画（位置 / 颜色 / 缩放插值）；脚本调用。 |

---

### 5) 音频

| Gem | 路径 | 作用 |
|---|---|---|
| **AudioSystem** | `Gems/AudioSystem/` | O3DE 音频抽象层（ATL），提供 Audio Control Editor 和 `AudioTriggerComponent`、`AudioRtpcComponent`、`AudioSwitchComponent` 等。**需要配合下面某个后端**。 |
| **MiniAudio** | `Gems/MiniAudio/` | 轻量跨平台音频实现（基于 miniaudio 库）。开箱即用，默认首选。 |
| **Microphone** | `Gems/Microphone/` | 麦克风捕获；语音通信 / 录音基础。 |

> **注**：商用级 Wwise 集成通常由单独 Gem 仓库提供，不在主仓库里。

---

### 6) 输入 / 相机

| Gem | 路径 | 作用 |
|---|---|---|
| **Camera** | `Gems/Camera/` | 基础相机组件 `CameraComponent`（定义视锥 + 投影）。 |
| **CameraFramework** | `Gems/CameraFramework/` | 相机控制框架：`CameraRigComponent` 挂多个 `ICameraSubComponent`（目标跟随、轨道、FPS 等组合式相机）。 |
| **StartingPointCamera** | `Gems/StartingPointCamera/` | 即插即用相机行为：跟随、看向、旋转等 CameraFramework 的子组件实现。 |
| **StartingPointInput** | `Gems/StartingPointInput/` | "InputEventGroup" — 把硬件输入映射为语义 action（`"Jump"`/`"Fire"`）。见 [03_azframework.md](03_azframework.md) 输入节。 |
| **StartingPointMovement** | `Gems/StartingPointMovement/` | 基础移动控制示例（组合 StartingPointInput + StartingPointCamera）。 |
| **BarrierInput** | `Gems/BarrierInput/` | 输入过滤 / 拦截（UI 防穿透）。 |
| **Gestures** | `Gems/Gestures/` | 触屏手势：pinch、swipe、rotate 识别。 |
| **VirtualGamepad** | `Gems/VirtualGamepad/` | 屏幕虚拟摇杆/按钮（移动端）。 |

---

### 7) UI / HUD

| Gem | 路径 | 作用 |
|---|---|---|
| **LyShine** | `Gems/LyShine/` | O3DE UI 系统。`UiCanvasComponent`、`UiButtonComponent`、`UiTextComponent`、`UiImageComponent`、`UiSliderComponent`、`UiCheckBoxComponent`、`UiDropdownComponent` 等。含 Editor UI Canvas Editor。 |
| **LyShineExamples** | `Gems/LyShineExamples/` | LyShine 示例（学习资源）。 |
| **UiBasics** | `Gems/UiBasics/` | UI 默认字体 / icon / 模板资产。 |
| **TextureAtlas** | `Gems/TextureAtlas/` | Texture Atlas 管理（合并多张贴图以减少 draw call）。 |
| **ImGui** | `Gems/ImGui/` | ImGui 库集成 —— 开发者运行时调试面板的黄金标准。 |
| **ImguiAtom** | `Gems/AtomLyIntegration/ImguiAtom/` | ImGui 渲染到 Atom（已列在 Atom 集成）。 |
| **MessagePopup** | `Gems/MessagePopup/` | 游戏内弹窗系统（"是否保存"对话框等）。 |

---

### 8) 脚本

| Gem | 路径 | 作用 |
|---|---|---|
| **ScriptCanvas** | `Gems/ScriptCanvas/` | 可视化节点脚本。运行时 + Editor。 |
| **GraphCanvas** | `Gems/GraphCanvas/` | ScriptCanvas 底层的通用节点画布控件。Editor-only。 |
| **GraphModel** | `Gems/GraphModel/` | 通用节点图数据模型。被 ScriptCanvas、LandscapeCanvas、MaterialCanvas 共用。 |
| **ScriptCanvasDeveloper** | `Gems/ScriptCanvasDeveloper/` | ScriptCanvas 开发者扩展（更多节点、调试工具）。 |
| **ScriptCanvasPhysics** | `Gems/ScriptCanvasPhysics/` | ScriptCanvas 与 PhysX 集成：物理节点。 |
| **ScriptCanvasTesting** | `Gems/ScriptCanvasTesting/` | ScriptCanvas 测试框架。 |
| **ScriptEvents** | `Gems/ScriptEvents/` | `.scriptevents` 跨语言事件契约（已列在"核心"）。 |
| **EditorPythonBindings** | `Gems/EditorPythonBindings/` | Editor 内 Python 3 解释器；`azlmbr.*` 自动绑定（见 [09_scripting.md](09_scripting.md)）。 |
| **PythonAssetBuilder** | `Gems/PythonAssetBuilder/` | 用 Python 写 AssetBuilder。快速原型资产流水线。 |
| **QtForPython** | `Gems/QtForPython/` | Editor 中直接 `from PySide2 import QtWidgets` 做 UI 工具。 |
| **ScriptAutomation** | `Gems/ScriptAutomation/` | 脚本化自动化测试框架（自动跑场景、截图、断言）。 |

---

### 9) 网络 / 联机

| Gem | 路径 | 作用 |
|---|---|---|
| **Multiplayer** | `Gems/Multiplayer/` | 联机核心 Gem。见 [10_networking_physics.md](10_networking_physics.md)。`NetBindComponent`、`NetworkTransformComponent`、AutoComponent XML 系统。 |
| **Multiplayer_ScriptCanvas** | `Gems/Multiplayer/Multiplayer_ScriptCanvas/` | 从 ScriptCanvas 调 Multiplayer API。 |
| **MultiplayerCompression** | `Gems/MultiplayerCompression/` | UDP 包压缩插件（通过 `net_UdpCompressor` CVar 启用）。 |
| **CertificateManager** | `Gems/CertificateManager/` | DTLS/TLS 证书（已列在"核心"；联机加密需要）。 |
| **RemoteTools** | `Gems/RemoteTools/` | 远程控制台 + 调试工具协议（Lua IDE、远端 AP 连接等底层）。 |
| **Presence** | `Gems/Presence/` | 在线 / 好友 / 大厅状态抽象。 |
| **InAppPurchases** | `Gems/InAppPurchases/` | IAP 抽象接口（平台无关）。 |

---

### 10) 地形 / 植被 / 世界生成

| Gem | 路径 | 作用 |
|---|---|---|
| **Terrain** | `Gems/Terrain/` | 地形系统（实验版）。`TerrainHeightGradientListComponent`、`TerrainLayerSpawnerComponent`、`TerrainPhysicsColliderComponent`、`TerrainSurfaceMaterialsListComponent`、`TerrainWorldComponent`。基于高度图 + layer blending。 |
| **Vegetation** | `Gems/Vegetation/` | 程序化植被放置（`VegetationAreaComponent` + 过滤器 + placer）。 |
| **GradientSignal** | `Gems/GradientSignal/` | 梯度图 / 混合 / 反转 / 阈值等 "1D signal → 2D signal" 操作。是 Terrain 和 Vegetation 的分布"笔刷"来源。 |
| **SurfaceData** | `Gems/SurfaceData/` | "表面标签"系统。Mesh / Terrain 发出"这个点是 grass/rock/road"；Vegetation 订阅并据此分布。 |
| **FastNoise** | `Gems/FastNoise/` | 高性能 Perlin / Simplex / Cellular 噪声；给 GradientSignal 用。 |
| **LandscapeCanvas** | `Gems/LandscapeCanvas/` | 节点式景观编辑器；可视化编辑 Terrain/Vegetation/Gradient 之间的连线。Editor-only。 |

---

### 11) 资产 / 内容 / 工具

| Gem | 路径 | 作用 |
|---|---|---|
| **Prefab/PrefabBuilder** | `Gems/Prefab/PrefabBuilder/` | 把 `.prefab`（JSON）编译为 `.spawnable`（运行时）。**必启**。 |
| **SceneProcessing** | `Gems/SceneProcessing/` | FBX / GLTF 导入规则（定义 `MeshGroup` / `ActorGroup` / `MotionGroup` 等 Scene Manifest 类型 + 默认 processor）。**必启**。 |
| **AssetValidation** | `Gems/AssetValidation/` | 资产验证（bundle 前检查有没有孤儿引用 / 缺失依赖）。 |
| **TestAssetBuilder** | `Gems/TestAssetBuilder/` | AssetBuilder 测试参考实现（学习如何写 Builder 的样板）。 |
| **CustomAssetExample** | `Gems/CustomAssetExample/` | 最小自定义资产类型 + Handler + Builder 示例。**学 Asset 流水线必读**。 |
| **WhiteBox** | `Gems/WhiteBox/` | 白盒关卡：多边形拖拽快速搭原型几何（类似 Hammer 的 "brush"）。 |
| **SceneLoggingExample** | `Gems/SceneLoggingExample/` | Scene Pipeline 扩展示例（加自定义 Processor）。 |
| **DccScriptingInterface** | `Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/` | DCC 工具脚本桥（已列在 Atom 集成）。 |

---

### 12) AI / 导航

| Gem | 路径 | 作用 |
|---|---|---|
| **RecastNavigation** | `Gems/RecastNavigation/` | Recast + Detour 库集成。`RecastNavigationMeshComponent`（定义导航网格）+ `DetourNavigationComponent`（寻路查询）。AI / NPC 寻路基础。 |

> 行为树 / Behavior Tree 在主仓库中没有内置 Gem；可通过 ScriptCanvas 搭简易状态机，或自行集成外部库。

---

### 13) 云服务 / 玩家数据 / 游戏状态

| Gem | 路径 | 作用 |
|---|---|---|
| **SaveData** | `Gems/SaveData/` | 跨平台存档（PC 磁盘 / Xbox / PS saves 等统一接口）。 |
| **LocalUser** | `Gems/LocalUser/` | 本地用户身份（多账户、local profile）。 |
| **Achievements** | `Gems/Achievements/` | 成就抽象接口（Steam / PSN / Xbox Live 由具体实现 Gem 接入）。 |
| **GameState** | `Gems/GameState/` | 游戏状态栈（Splash → Menu → Game → Pause）抽象。 |
| **GameStateSamples** | `Gems/GameStateSamples/` | 上面的参考实现 / 模板状态。 |
| **Presence** | `Gems/Presence/` | 在线状态 / 好友（已列在网络）。 |
| **InAppPurchases** | `Gems/InAppPurchases/` | IAP（已列在网络）。 |

> AWS 相关 Gem（AWSCore、AWSGameLift 等）**已从主仓库迁出**到 [o3de-extras](https://github.com/o3de/o3de-extras)；主仓库里 `Gems/AWSCore` 只留一个 README 占位。

---

### 14) 调试 / 工具 / 性能

| Gem | 路径 | 作用 |
|---|---|---|
| **DebugDraw** | `Gems/DebugDraw/` | 运行时画 line / sphere / text / ray / aabb / obb。`DebugDrawLineComponent` 等。**开发时几乎必启**。 |
| **Profiler** | `Gems/Profiler/` | AZ_PROFILE_* 的后端（Tracy / Superluminal / 自带 ImGui profiler）。 |
| **Streamer** | `Gems/Streamer/` | 异步流式加载系统。 |
| **StreamerProfiler** | `Gems/Streamer/StreamerProfiler/` | Streamer 专属的性能面板。 |
| **RemoteTools** | `Gems/RemoteTools/` | 远程连接工具（已列在网络）。 |
| **CrashReporting** | `Gems/CrashReporting/` | 崩溃 minidump + 上报。 |
| **TickBusOrderViewer** | `Gems/TickBusOrderViewer/` | 可视化 `TickBus` 上所有 handler 的执行顺序；排 tick 依赖问题用。 |

---

### 15) 特效 / 粒子 / 视频

| Gem | 路径 | 作用 |
|---|---|---|
| **OpenParticleSystem** | `Gems/OpenParticleSystem/` | 粒子系统（标 Preview）；fire/smoke/dust 效果。 |
| **VideoPlaybackFramework** | `Gems/VideoPlaybackFramework/` | 视频播放抽象（具体编解码实现可能需额外 Gem）。 |

---

### 16) 示例 / 测试参考

这些 Gem 不是功能 Gem，而是**学习用**。启不启都可以，但读源码非常有价值：

| Gem | 读它学什么 |
|---|---|
| `Gems/CustomAssetExample/` | 如何写自定义 AssetData + AssetHandler + AssetBuilder |
| `Gems/TestAssetBuilder/` | 更深入的 Builder 示例（含 JobDependency） |
| `Gems/SceneLoggingExample/` | Scene Pipeline / FBX 处理扩展 |
| `Gems/LyShineExamples/` | LyShine UI 用法 |
| `Gems/GameStateSamples/` | GameState 状态机组合 |
| `Gems/StartingPointMovement/` | 最小可玩人物控制（组合 Camera + Input + Transform） |
| `Gems/ScriptCanvasDeveloper/` / `ScriptCanvasTesting/` | ScriptCanvas 节点写法 |

---

## 依赖关系与启用建议

### 必启组合（最小可玩项目）

```
LmbrCentral
Prefab/PrefabBuilder
SceneProcessing
PrimitiveAssets
Atom_RHI, Atom_RPI, Atom_Feature_Common, Atom_Bootstrap
Atom_Utils
AtomLyIntegration, CommonFeaturesAtom, AtomBridge
AtomFont, AtomViewportDisplayInfo, AtomViewportDisplayIcons
ImGui, ImguiAtom, AtomImGuiTools
TextureAtlas
DevTextures
LyShine, LyShineExamples（可选）
ImageProcessingAtom
AtomShader
Profiler, DebugDraw, Streamer
```

这是 `Templates/DefaultProject` 默认带的。

### 按项目类型加

- **3D 动作 / 冒险游戏**：+ `PhysX5` + `PhysXCommon` + `PhysX5Debug` + `EMotionFX` + `EMotionFX_Atom` + `Camera` + `CameraFramework` + `StartingPointCamera` + `StartingPointInput` + `StartingPointMovement`
- **联网对战**：+ `Multiplayer` + `MultiplayerCompression` + `CertificateManager` + `MessagePopup`
- **开放世界**：+ `Terrain` + `Vegetation` + `GradientSignal` + `SurfaceData` + `FastNoise` + `LandscapeCanvas` + `SkyAtmosphere` + `DiffuseProbeGrid` + `RecastNavigation`
- **VR**：+ OpenXR Gem（在 o3de-extras 或自建）
- **移动端**：+ `VirtualGamepad` + `Gestures` + `InAppPurchases`
- **影视 / 渲染演示**：+ `Sponza`（参考场景）+ `MaterialCanvas` + `MaterialEditor` + `AtomTressFX`

### Gem 间依赖链（常见陷阱）

- 所有 Atom 特性 → `Atom_Feature_Common` → `Atom_RPI` → `Atom_RHI`
- `CommonFeaturesAtom` → `Atom_Feature_Common` + `LmbrCentral`
- `EMotionFX_Atom` → `EMotionFX` + `Atom_RPI` + `CommonFeaturesAtom`
- `Multiplayer` → `AzNetworking`（框架层）+ `CertificateManager` + `Atom_Feature_Common`（debug 用）+ `ImGui`
- `Terrain` → `GradientSignal` + `SurfaceData` + `LmbrCentral`
- `Vegetation` → `GradientSignal` + `SurfaceData` + `LmbrCentral`
- `ScriptCanvas` → `ScriptEvents` + `ExpressionEvaluation` + `GraphCanvas` + `GraphModel`
- `PhysX5` 和 `PhysX4` **互斥**，只能选一个

---

## 快速找 Gem 的方法

1. **不知道现在启了哪些**：看 `<project>/project.json` 的 `gem_names` 数组。
2. **找某组件来自哪个 Gem**：Grep `class <ClassName>Component` 在 `Gems/*/Code/` 下。
3. **看 Gem 依赖谁**：读 `Gems/<Gem>/gem.json` 的 `dependencies` 字段。
4. **看 Gem 提供什么组件**：读 `Gems/<Gem>/Code/Source/*Module.cpp` 的 `m_descriptors.insert` 列表。

---

## 命令速查

```bash
# 注册 Gem 让引擎知道它存在（新下载的第三方 Gem）
scripts/o3de.bat register --gem-path <path>

# 项目启用 Gem
scripts/o3de.bat enable-gem -gn <GemName> -pp <project_path>

# 查看当前引擎注册的所有 Gem
scripts/o3de.bat get-registered --gems

# 禁用 Gem
scripts/o3de.bat disable-gem -gn <GemName> -pp <project_path>

# 查看某 Gem 信息
scripts/o3de.bat get-gem-info -gn <GemName>
```

---

继续：[05_gems_and_modules.md](05_gems_and_modules.md) 讲 Gem 结构与写法；[12_cookbook_recipes.md](12_cookbook_recipes.md) 的 R1 是"新建 Gem"的最短路径。
