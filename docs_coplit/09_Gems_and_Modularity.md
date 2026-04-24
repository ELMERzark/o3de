## Gems 与模块化扩展机制

概述:

- Gems 是 O3DE 的插件式扩展单元，包含 `Gem.json`、`Code/`、`Assets/` 等内容，用于在不改动核心引擎的前提下添加功能。

示例路径:

- [Gems](Gems)

结构化占位:

- **GemManifest**: 对每个 Gem，提取 `gem.json` 中的 metadata 与依赖。
- **ExposedAPIs**: 列出 Gem 对外提供的 Module/SystemComponent 与公开接口。
- **ExtractionTasks**:
  1. 遍历 `Gems/*/gem.json`，生成 Gem -> 依赖树 与 Module 列表。

关键点与代表文件：
- Gem 注册与模块化：每个 Gem 的 `gem.json` 声明依赖、模块与 entry points；模块内部通常通过 Module/ModuleManager 模式注册 SystemComponents（见 `Code/Framework/AzCore/Module/ModuleManager.h`）。
- SystemComponent 模式：许多 Gems 提供 `*SystemComponent` 来挂载运行时服务（示例：`Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h`、`Gems/Atom/RPI/Code/Source/RPI.Private/RPISystemComponent.h`）。

自动化提取任务（建议）：
1. 对每个 Gem 提取 `gem.json` 的 `Modules`、`Dependencies` 与 `AutoLoad` 配置，生成 CSV/表格。
2. 在每个 Gem 中定位 `*SystemComponent` 类并记录其文件路径、Reflect/Activate/Deactivate 签名（便于后续自动填充每个 Gem 的行为摘要）。

### Representative SystemComponent signatures

- From `Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h`:
  - `AZ_COMPONENT(WhiteBoxSystemComponent, "{BD393FD9-CF47-433D-B171-C44FE2F7069F}");`
  - `static void Reflect(AZ::ReflectContext* context);`
  - `WhiteBoxSystemComponent();`
  - `~WhiteBoxSystemComponent();`
  - `static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided);`
  - `void Activate() override;`
  - `void Deactivate() override;`
  - `AZStd::unique_ptr<RenderMeshInterface> CreateRenderMeshInterface(AZ::EntityId entityId) override;`

These illustrate the common Gem pattern: `Reflect()` exposes types, `Activate()`/`Deactivate()` manage runtime registration, and `GetProvidedServices()` describes dependency/compatibility.

### Next extraction step

- Iterate `Gems/*/gem.json` to build Gem -> Modules -> Dependencies table, then scan each Gem `Code/` for `*SystemComponent` classes and append Reflect/Activate signatures with line numbers.

### Line-numbered references (verified)

- From `Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h`:
  - [Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h](Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h#L29) — `AZ_COMPONENT(WhiteBoxSystemComponent, "{BD393FD9-CF47-433D-B171-C44FE2F7069F}");`
  - [Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h](Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h#L30) — `static void Reflect(AZ::ReflectContext* context);`
  - [Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h](Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h#L48) — `void Activate() override;`
  - [Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h](Gems/WhiteBox/Code/Source/WhiteBoxSystemComponent.h#L49) — `void Deactivate() override;`
