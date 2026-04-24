## 模块与 SystemComponent 模式

概述:

- O3DE 中 `Module` 负责模块级初始化与组件注册；`SystemComponent` 承担运行时服务（生命周期：Init/Activate/Deactivate）。

示例文件:

- [Templates/UnifiedMultiplayerGem/Template/Code/Source/${Name}ModuleInterface.h](Templates/UnifiedMultiplayerGem/Template/Code/Source/%24%7BName%7DModuleInterface.h)
- [Gems/BarrierInput/Code/Source/BarrierInputSystemComponent.h](Gems/BarrierInput/Code/Source/BarrierInputSystemComponent.h)

结构化占位:

- **ModuleList**: 每个模块（Module）名、注册的 SystemComponent 列表、文件路径。
- **ComponentLifecycleIndex**: 针对每个 SystemComponent，记录 `Init()`/`Activate()`/`Deactivate()` 的源文件和行数。
- **ExtractionTasks**:
  1. 扫描 `Gems/**/Code` 与 `Code/**` 下的 `Module` 实现；列出 module -> components 映射。
  2. 生成模块依赖矩阵（模块间 service 依赖）。
