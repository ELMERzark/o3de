## 物理系统 (Physics)

概述:

- 包含刚体、碰撞、约束、物理材质与模拟 loop。可能存在后端适配层（如 PhysX）。

示例路径:

- [Gems/Physics](Gems/Physics)
- [Code/Framework/Physics](Code/Framework/Physics)

结构化占位:

- **SimulationLoop**: 物理步进函数与同步点（文件/类/函数）。
- **CollisionAPI**: raycast/overlap 查询入口函数与实现。
- **ExtractionTasks**:
  1. 列出 simulation tick 的调用顺序与回调注册点。
  2. 提取 collider/rigidbody 的创建与销毁代码路径。

关键组件与代表文件：
- AzPhysics 接口与场景：许多模块通过 `AzPhysics::SceneInterface`、`AzPhysics::SceneEvents` 与 `AzPhysics::SimulatedBodyHandle` 交互（示例：[Gems/EMotionFX/Code/Source/Integration/System/SystemComponent.cpp](Gems/EMotionFX/Code/Source/Integration/System/SystemComponent.cpp#L770)）。
- Physics 数据结构（配置/形状/关节）：在 `Gems/*` 中广泛定义（例如 `Physics::RagdollConfiguration`, `Physics::CharacterColliderConfiguration`），参见 [Gems/EMotionFX/Code/Source/Integration/Components/ActorComponent.h](Gems/EMotionFX/Code/Source/Integration/Components/ActorComponent.h#L1)
- 后端适配器与提供者（PhysX 提供者、模拟接口）：检索 Gems 中 `PhysX` / `AzPhysics` 提供者实现（示例：Gems/RecastNavigation 的 PhysX provider）。

自动化提取任务（建议）：
1. 在 `Gems/**` 查找 `AzPhysics::SceneInterface` 使用点并导出调用签名与行号。
2. 列出所有与 `RagdollConfiguration`、`ColliderConfiguration`、`JointConfiguration` 相关的类型定义与 Reflect(...) 函数位置（用于序列化/编辑器）。
3. 提取物理后端（PhysX）适配的初始化/配置代码（查找含 "PhysX" 的模块与 Gem）。

### Extracted usage examples (representative)

- From `Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp`:
  - `auto* sceneInterface = AZ::Interface<AzPhysics::SceneInterface>::Get();`
  - `AzPhysics::SceneHandle defaultScene = sceneInterface->GetSceneHandle(AzPhysics::DefaultPhysicsSceneName);`
  - `m_simulatedBodyHandle = sceneInterface->AddSimulatedBody(defaultScene, &bodyConfiguration);`
  - `sceneInterface->RemoveSimulatedBody(defaultScene, m_simulatedBodyHandle);`
  - `sceneInterface->GetSimulatedBodyFromHandle(defaultScene, m_simulatedBodyHandle);`

These calls show the common SceneInterface operations: obtain the scene handle, add/remove simulated bodies, and retrieve simulated body instances for transform updates.

### Next extraction step

- Enumerate all `AzPhysics::SceneInterface` call-sites across `Gems/**` and write line-numbered signatures into this doc; then extract `Reflect()` locations for core physics configuration structs.

### Line-numbered references (verified)

- From `Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp`:
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L65) — `auto* sceneInterface = AZ::Interface<AzPhysics::SceneInterface>::Get();`
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L72) — `AzPhysics::SceneHandle defaultScene = sceneInterface->GetSceneHandle(AzPhysics::DefaultPhysicsSceneName);`
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L106) — `m_simulatedBodyHandle = sceneInterface->AddSimulatedBody(defaultScene, &bodyConfiguration);`
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L117) — `m_simulatedBodyHandle = sceneInterface->AddSimulatedBody(defaultScene, &staticBodyConfiguration);`
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L138) — `sceneInterface->RemoveSimulatedBody(defaultScene, m_simulatedBodyHandle);`
  - [Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp](Gems/WhiteBox/Code/Source/Components/WhiteBoxColliderComponent.cpp#L158) — `sceneInterface->GetSimulatedBodyFromHandle(defaultScene, m_simulatedBodyHandle);`
