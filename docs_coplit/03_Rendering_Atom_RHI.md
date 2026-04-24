## 渲染 (Atom / RPI / RHI)

概述:

- Atom 负责高层渲染流水线（RPI）；RHI 提供跨 API 的 GPU 抽象。文档旨在帮助 AI 理解资源到 GPU 的完整路径。

示例路径（起点）:

- [Gems/Atom](Gems/Atom)
- [Gems/AtomLyIntegration](Gems/AtomLyIntegration)

结构化占位:

- **ResourceFlow**: 列出从 asset -> stream -> RPI resource -> RHI resource 的关键函数与文件。
- **ShaderPipeline**: Shader 编译、变体和绑定的主要类与文件。
- **ExtractionTasks**:
  1. 抽取资源创建调用链（例如 Material -> Shader -> GPU buffer）。
  2. 为每个 RenderPass 列出输入/输出资源与依赖顺序。

---

MainClasses (sample extracted):

- `RPISystemComponent` (RPI 系统入口)
  - 文件: Gems/Atom/RPI/Code/Source/RPI.Private/RPISystemComponent.h
  - 说明: 包装 `RPISystem`，负责 RPI 的生命周期、系统 tick、设备丢失处理、性能采集与 XR 接口注册。
  - 关键方法: `Activate()`, `Deactivate()`, `OnSystemTick()`, `OnDeviceRemoved(RHI::Device*)`, `RegisterXRInterface()`, `UnRegisterXRInterface()`, `Reflect(ReflectContext*)`, `GetRequiredServices()`/`GetProvidedServices()`。

- `RPISystem` (渲染流水线核心，RPI 公共 API)
  - 文件（入口类型定义与主要 public API）: Gems/Atom/RPI/Code/Include/Atom/RPI.Public/RPISystem.h

- `RHI` 命名空间核心类型（Device / Buffer / Image / RenderPass / Pipeline）
  - 示例文件路径: Gems/Atom/RHI/Code/Include/Atom/RHI/** 和各平台实现如 Gems/Atom/RHI/Vulkan/Code/Source/RHI/*.h

KeyFiles (quick pointers):

- RPISystemComponent: Gems/Atom/RPI/Code/Source/RPI.Private/RPISystemComponent.h / .cpp
- RPI public headers: Gems/Atom/RPI/Code/Include/Atom/RPI.Public/**
- RHI core headers: Gems/Atom/RHI/Code/Include/Atom/RHI/** and platform backends under Gems/Atom/RHI/{Vulkan,DX12,Metal}/Code/Source/RHI
- Shader & Material: Gems/Atom/Asset/Shader and Gems/Atom/Feature/Common/Material

ExtractionTasks (concrete):
  1. 枚举 `Gems/Atom/RPI/Code/Include/Atom/RPI.Public` 下的 public types（`RPISystem`, `RenderPass`, `View`, `Material`），提取类名与头文件路径。
  2. 在 `Gems/Atom/RHI` 下列出 `Device`, `Buffer`, `Image`, `RenderPass` 等类型的声明与各平台实现文件，记录实现文件路径用于进一步行号链接。
  3. 从 `RPISystemComponent.cpp` 找到 `Activate()` 的实现并提取它调用的初始化序列（如创建 RPISystem、初始化资源池、注册性能采集器）。

