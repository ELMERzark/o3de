## AzCore 与 ECS 基础

概述:

- `AzCore` 提供基础设施：内存分配、RTTI/反射、`Component`/`SystemComponent` 框架、`EBus` 事件总线与基础容器/实用库。

关键源文件（示例）:

- [Code/Framework/AzCore/Component/Component.h](Code/Framework/AzCore/Component/Component.h)
- [Code/Framework/AzCore/EBus/EBus.h](Code/Framework/AzCore/EBus/EBus.h)
- [Templates/UnifiedMultiplayerGem/Template/Code/Source/Unified/${Name}SystemComponent.h](Templates/UnifiedMultiplayerGem/Template/Code/Source/Unified/%24%7BName%7DSystemComponent.h)

结构化占位（供 AI 自动填充）:

- **Overview**: 简短一段，说明模块目的与上层依赖。
- **KeyFiles**: 列出 <path> 与简短一句话说明。
- **MainClasses**: 列表: `Component` 派生类名 + 所在文件 + constructor/Reflect/Activate/Deactivate 的签名行号链接。
- **ImportantEBuses**: EBus 名称与发布/订阅端示例文件。
- **ExtractionTasks**:
  1. 提取所有 `SystemComponent` 派生类的 `GetProvidedServices()`/`GetRequiredServices()` 返回值。
  2. 为每个 `Component` 记录 `Reflect()` 中注册的属性/方法。
  3. 生成组件依赖图（节点=组件, 边=依赖服务）。

---

MainClasses (sample extracted):

- Component (核心组件基类)
  - 文件: Code/Framework/AzCore/AzCore/Component/Component.h
  - 关键方法: `Init()` (可选初始化), `Activate()` (必须实现，激活时调用), `Deactivate()` (必须实现，停用时调用), `ReadInConfig(const ComponentConfig*)`, `WriteOutConfig(ComponentConfig*) const`。

- ModuleManager (模块加载与系统组件生命周期管理)
  - 文件: Code/Framework/AzCore/AzCore/Module/ModuleManager.h
  - 关键方法: `LoadDynamicModule(...)`, `LoadStaticModules(...)`, `AddModuleEntity(ModuleEntity*)`, `ActivateEntities(...)`, `DeactivateEntities()`, `UnloadModules()`。

- ModuleEntity
  - 文件: Code/Framework/AzCore/AzCore/Module/ModuleManager.h
  - 说明: 用于在运行时保存模块相关的实体、moduleClassId 与生命周期状态；包含 `Reflect(ReflectContext*)`。

KeyFiles (quick pointers):

- AzCore Component base: Code/Framework/AzCore/AzCore/Component/Component.h
- Reflection / RTTI utilities: Code/Framework/AzCore/AzCore/RTTI/*
- Module & ModuleManager: Code/Framework/AzCore/AzCore/Module/ModuleManager.h, ModuleManager.cpp
- EBus primitives: 搜索 `EBus.h` 在 `Code/Framework/AzCore` 下（用于事件总线定义与使用）

Notes for AI fill-in:

- Use `grep` for `class .*SystemComponent` 与 `class .*Component` 来枚举候选类。
- For each class, parse nearby methods for `Reflect`, `Activate`, `Deactivate`, `GetProvidedServices`, `GetRequiredServices` 并记录行号与文件路径以便生成行号链接。

