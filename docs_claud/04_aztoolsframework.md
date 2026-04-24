# 04 · AzToolsFramework — Editor 层（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

路径：[Code/Framework/AzToolsFramework/AzToolsFramework/](../Code/Framework/AzToolsFramework/AzToolsFramework/)

**仅 Editor 进程加载**。基于 Qt 5/6 + Python (pyside2)，依赖 AzFramework。

## 核心事实（上手前必知）

1. Editor 的可执行是 **`ToolsApplication`**（派生 `AzFramework::Application`），启动时额外：
   - 给 `Settings Registry` 加 `"tools"` 和 `"editor"` specialization
   - 装入每个 Gem 的 `.Tools` / `.Builders` alias 下的模块（即 editor module）
   - 构造 `UndoStack`（容量 10）
   - 挂 30+ 专用 SystemComponent（ActionManager、PrefabSystem、EditorEntityContext、FocusMode…）
2. **不要**在 AzFramework / AzCore 里 include 任何 AzToolsFramework 头 —— 上下层反了会断编译（Editor-only 代码必须放在 Gem 的 editor 子模块里）。
3. Editor 端组件**成对出现**：`EditorXxxComponent`（Qt + EditContext 的 UI 模型）+ `XxxComponent`（runtime 数据模型）。Editor 组件在 Prefab 保存时会 `BuildGameEntity` 把自己烘焙成运行时组件。
4. Editor 和 AssetProcessor 是不同进程（两个 Qt app），通过 SocketConnection 通信。

## 子目录速查

| 子目录 | 职责 | 代表头文件 |
|---|---|---|
| `Application/` | `ToolsApplication` 启动 / SystemEntity 配置 | [ToolsApplication.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Application/ToolsApplication.h) |
| `ActionManager/` | 菜单 / 工具栏 / 快捷键统一注册 | `Action/ActionManagerInterface.h`, `HotKey/HotKeyManagerInterface.h` |
| `Entity/` | `EditorEntityContextComponent` + Editor 侧选中、可见性、锁 | `Entity/EditorEntityContextComponent.h` |
| `API/` | 对外公开 interface（`EditorEntityAPI` 等） | `API/EditorEntityAPI.h` |
| `Prefab/` | Prefab 系统：Template / Instance / Link / propagation | `Prefab/PrefabSystemComponent.h`, `Prefab/Instance/Instance.h` |
| `UI/PropertyEditor/` | RPE (Reflected Property Editor) | `UI/PropertyEditor/PropertyEditorAPI.h` |
| `Manipulators/` | 视口 3D 操纵器 | `Manipulators/BaseManipulator.h`（13 种子类） |
| `ComponentMode/` | 组件专属编辑模式 | `ComponentMode/EditorBaseComponentMode.h`, `ComponentModeDelegate.h` |
| `AssetBrowser/` | 资产浏览器 (tree + filter + preview + drag) | `AssetBrowser/Entries/AssetBrowserEntry.h` |
| `AssetEditor/` | 通用"反射对象编辑"独立窗口 | `AssetEditor/AssetEditorWidget.h` |
| `Thumbnails/` | 异步缩略图 | `Thumbnails/*` |
| `Commands/` | Undo/Redo 命令封装 | `Commands/SelectionCommand.h`, `Undo/UndoSystem.h` |
| `Picking/` | 视口拾取 | `Picking/*` |
| `ViewportInteraction/` | 视口输入抽象 | `ViewportInteraction/*` |
| `PythonTerminal/` | Editor 内嵌 Python REPL | `PythonTerminal/*` |
| `SQLite/` + `AssetDatabase/` | AP 资产库只读查询 | `AssetDatabase/AssetDatabaseConnection.h` |
| `SourceControl/` | 抽象 SCC 接口（可被 Perforce 等实现） | `SourceControl/*` |
| `FocusMode/`, `ContainerEntity/` | Editor 专属聚焦/容器 | `FocusMode/*`, `ContainerEntity/*` |
| `ToolsComponents/` | editor-only 组件公共基类 | `ToolsComponents/EditorComponentBase.h` |

---

## ToolsApplication 启动链

[ToolsApplication.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Application/ToolsApplication.h)：

```cpp
class ToolsApplication
    : public AzFramework::Application
    , private ToolsApplicationRequests::Bus::Handler
    , public AzToolsFramework::Prefab::PrefabPublicNotificationBus::Handler
{
public:
    void Start(const Descriptor&, const StartupParameters&) override;
    void Stop() override;

protected:
    // 1) 告诉 Settings Registry：我是 editor + tools
    void SetSettingsRegistrySpecializations(
        SettingsRegistryInterface::Specializations& s) override
    {
        AzFramework::Application::SetSettingsRegistrySpecializations(s);
        s.Append("tools");
        // "editor" 来自基类 AzFramework::Application 中的 editor spec
    }

    // 2) 加载 AzToolsFrameworkModule + AzFrameworkNativeUIModule
    void CreateStaticModules(AZStd::vector<AZ::Module*>& outModules) override
    {
        AzFramework::Application::CreateStaticModules(outModules);
        outModules.emplace_back(aznew AzFrameworkNativeUIModule());
        outModules.emplace_back(aznew AzToolsFrameworkModule());
    }

    // 3) 挂所有 editor-only SystemComponent
    AZ::ComponentTypeList GetRequiredSystemComponents() const override;

    // 4) 启动后建 UndoStack
    void StartCommon(AZ::Entity* systemEntity) override
    {
        Application::StartCommon(systemEntity);
        m_undoStack = new UndoSystem::UndoStack(10, nullptr);
    }

private:
    UndoSystem::UndoStack* m_undoStack = nullptr;
    EditorEntityManager m_editorEntityManager;
    EditorEntityAPI* m_editorEntityAPI = nullptr;
};
```

**`GetRequiredSystemComponents` 典型内容**（30+ 项，不是穷举）：

```cpp
return {
    azrtti_typeid<ActionManagerSystemComponent>(),
    azrtti_typeid<EditorEntityContextComponent>(),
    azrtti_typeid<Prefab::PrefabSystemComponent>(),
    azrtti_typeid<Prefab::ProceduralPrefabSystemComponent>(),
    azrtti_typeid<EditorEntityFixupComponent>(),
    azrtti_typeid<FocusModeSystemComponent>(),
    azrtti_typeid<ContainerEntitySystemComponent>(),
    azrtti_typeid<ReadOnlyEntitySystemComponent>(),
    azrtti_typeid<EditorInteractionSystemComponent>(),
    // ... 20 多项
};
```

### Specializations 对 setreg 加载的影响

```
基本 (AzFramework::Application)：  "common" + "editor"（若 IsEditor()）
Tools 额外追加：                   "tools"

→ 例：editor.windows.setreg 在 Editor 进程 + Windows 平台加载
→ tools.setreg 只在 Editor / AssetProcessor 等 tools 进程加载
```

---

## Editor 组件对 Runtime 组件（完整模式）

目标：**同一 Entity 在 Editor 和 Game 运行时有对齐但不同的行为**。

### 文件布局（推荐）

```
Gems/MyGem/
├── Code/
│   ├── Include/MyGem/
│   │   └── BlinkerComponentBus.h            // 共用 bus / 数据结构
│   ├── Source/
│   │   ├── BlinkerComponent.{h,cpp}         // Runtime（在 .Private）
│   │   ├── Tools/
│   │   │   └── EditorBlinkerComponent.{h,cpp}  // Editor（在 .Editor.Private）
│   │   ├── MyGemModule.cpp                  // runtime module
│   │   └── MyGemEditorModule.cpp            // editor module
│   ├── mygem_private_files.cmake            // 含 BlinkerComponent.*
│   └── mygem_editor_private_files.cmake     // 含 EditorBlinkerComponent.*
```

### Editor 组件骨架

[ToolsComponents/EditorComponentBase.h](../Code/Framework/AzToolsFramework/AzToolsFramework/ToolsComponents/EditorComponentBase.h)：

```cpp
#include <AzToolsFramework/ToolsComponents/EditorComponentBase.h>

class EditorBlinkerComponent
    : public AzToolsFramework::Components::EditorComponentBase
{
public:
    AZ_EDITOR_COMPONENT(EditorBlinkerComponent,
        "{EDITOR-UUID-不同于-runtime}",
        AzToolsFramework::Components::EditorComponentBase);

    static void Reflect(AZ::ReflectContext*);

    // 服务声明必须和 runtime 组件一致
    static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& s)
        { BlinkerComponent::GetProvidedServices(s); }
    static void GetRequiredServices(AZ::ComponentDescriptor::DependencyArrayType& s)
        { BlinkerComponent::GetRequiredServices(s); }
    static void GetIncompatibleServices(AZ::ComponentDescriptor::DependencyArrayType& s)
        { BlinkerComponent::GetIncompatibleServices(s); }

    void Activate() override;
    void Deactivate() override;

    // 烘焙为 runtime 组件（Prefab 保存时框架调）
    void BuildGameEntity(AZ::Entity* gameEntity) override
    {
        auto* runtime = gameEntity->CreateComponent<BlinkerComponent>();
        runtime->m_period = m_editorPeriod;
        // 资产引用转 ID：editor 端持 Asset<T>，runtime 持 AssetId
        runtime->m_curveId = m_curveAsset.GetId();
    }

private:
    float m_editorPeriod = 1.f;
    AZ::Data::Asset<CurveAsset> m_curveAsset;   // Editor 侧能预览
};
```

**EditContext 只在 Editor 组件里写**，`BehaviorContext` 也通常放 Editor（脚本驱动）。Runtime 组件只做 `SerializeContext`。

### 注册到 EditorModule

```cpp
// MyGemEditorModule.cpp
class MyGemEditorModule : public AZ::Module
{
public:
    AZ_RTTI(MyGemEditorModule, "{<editor-module-uuid>}", AZ::Module);
    MyGemEditorModule() {
        m_descriptors.insert(m_descriptors.end(), {
            EditorBlinkerComponent::CreateDescriptor(),
        });
    }
    AZ::ComponentTypeList GetRequiredSystemComponents() const override {
        return { azrtti_typeid<MyGemEditorSystemComponent>() };
    }
};
AZ_DECLARE_MODULE_CLASS(Gem_MyGem_Editor, MyGem::MyGemEditorModule)
```

---

## Prefab 系统完整架构

**两套 ID 空间 + JSON-patch 合成**。先理清核心数据类型。

### 核心 ID 类型

[PrefabIdTypes.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Prefab/PrefabIdTypes.h)：

```cpp
using TemplateId   = AZ::u64;  // 一个 Template（对应一个 .prefab 文件）
using LinkId       = AZ::u64;  // 一个 Template → 另一个 Template 的引用
using InstanceAlias = AZStd::string;  // 实例在父 template 中的字符串 id
using EntityAlias  = AZStd::string;   // 实体在所属 template 中的字符串 id

inline constexpr TemplateId InvalidTemplateId = AZStd::numeric_limits<TemplateId>::max();
inline constexpr LinkId     InvalidLinkId     = AZStd::numeric_limits<LinkId>::max();
```

### 三大数据类型

```
Template（模板，对应一个 .prefab 文件的加载态）
 ├─ PrefabDom m_prefabDom        // rapidjson::Document - 整个 .prefab 的 JSON
 ├─ AZStd::unordered_map<LinkId, ...> m_links   // 我引用了哪些其它 template
 ├─ bool m_isDirty
 ├─ bool m_isLoadedWithErrors
 └─ bool m_isProcedural                         // 由 builder 动态产的 prefab

Instance（实例，把一个 Template 在内存中展开）
 ├─ TemplateId m_templateId
 ├─ InstanceAlias m_instanceAlias
 ├─ AZStd::unordered_map<EntityAlias, AZ::Entity*> m_entities
 ├─ AZStd::unordered_map<InstanceAlias, AZStd::unique_ptr<Instance>> m_nestedInstances
 └─ Instance* m_parent

Link（"一个 template 里嵌套另一个 template 的位置"）
 ├─ LinkId m_linkId
 ├─ TemplateId m_sourceTemplateId    // 谁引用了
 ├─ TemplateId m_targetTemplateId    // 被引用者
 ├─ PrefabDom m_linkDom               // 嵌套位置 + override
 └─ AZStd::vector<PrefabOverrideMetadata> m_overrides  // JSON Merge Patch 列表
```

PrefabDom = `rapidjson::Document`（[PrefabDomTypes.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Prefab/PrefabDomTypes.h)）。**.prefab 文件的底层格式是 JSON**。

### 三大 Interface 分工

| Interface | 职责 | 典型 API |
|---|---|---|
| `PrefabPublicInterface` | **给 UI / Python / 脚本用**：创建、实例化、保存、查询 | `CreatePrefabAndSaveToDisk`, `InstantiatePrefab`, `SavePrefab`, `CreateEntity` |
| `PrefabSystemComponentInterface` | 内部管理 Template/Link 注册表 | `FindTemplate(id)`, `FindLink(id)`, `AddTemplate`, `RemoveTemplate` |
| `PrefabLoaderInterface` | 磁盘 IO | `LoadTemplateFromFile`, `SaveTemplate`, `LoadTemplateFromString` |

### PrefabPublicInterface 核心 API

[PrefabPublicInterface.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Prefab/PrefabPublicInterface.h)：

```cpp
class PrefabPublicInterface
{
public:
    AZ_RTTI(PrefabPublicInterface, "{...}");

    // 把选中 entities 变成一个 .prefab 存盘
    virtual CreatePrefabResult CreatePrefabAndSaveToDisk(
        const EntityIdList& entityIds, AZ::IO::PathView filePath) = 0;

    // 把某个 .prefab 实例化到场景 parent 下
    virtual InstantiatePrefabResult InstantiatePrefab(
        AZStd::string_view filePath,
        AZ::EntityId parentId,
        const AZ::Vector3& position) = 0;

    // 保存（现有 prefab 被编辑后）
    virtual PrefabOperationResult SavePrefab(AZ::IO::Path filePath) = 0;

    // 在某 prefab 下新建空 Entity
    virtual PrefabEntityResult CreateEntity(
        AZ::EntityId parentId, const AZ::Vector3& position) = 0;

    // Undo 联动
    virtual PrefabOperationResult GenerateUndoNodesForEntityChangeAndUpdateCache(
        AZ::EntityId entityId, UndoSystem::URSequencePoint* parentUndoBatch) = 0;
};
```

**调用方式**：

```cpp
auto* prefabPublic = AZ::Interface<AzToolsFramework::Prefab::PrefabPublicInterface>::Get();
auto result = prefabPublic->InstantiatePrefab("levels/hero.prefab", parentId, pos);
if (!result.IsSuccess()) AZ_Error("MyGem", false, "%s", result.GetError().c_str());
```

### Propagation（一处改，所有实例跟着变）

核心类：`Prefab::Instance::InstanceToTemplatePropagator`。

流程：

```
用户改了某个 Instance 上的 entity 的 Transform
    ↓
EditorEntity 监听 OnEntityPropertyChanged
    ↓
InstanceToTemplatePropagator::GenerateEntityDomBySerializing(dom, entity)
    ↓
GeneratePatch(newDom, oldDom) → JSON Merge Patch
    ↓
PatchEntityInTemplate(patch, entityId) — 更新 template 的 PrefabDom
    ↓
PrefabSystemComponent 找出 "谁引用了这个 template"
    ↓
对每个引用 Instance：ApplyPatchesToInstance(entityId, patch, instance)
    ↓
Entity 的 Transform 更新 → UI 刷新
```

**Override 机制**：一个 Link 上可以保存 "在这个嵌套位置额外的修改"（RFC 7386 JSON Merge Patch）。链表顺序应用（patchIndex 决定）。

### Prefab → Spawnable（运行时化）

- `.prefab`（源，JSON，Editor 编辑）→ **PrefabBuilder** → `.spawnable`（二进制产物，运行时加载）
- 根实体标为 `AliasType::EntryPoint`（可被 `SpawnableEntitiesInterface::SpawnAllEntities` 生成）
- 嵌套 Prefab 在 Builder 阶段已经展开成扁平 Entity 列表（不含 Template / Link 概念）

### Focus Mode

`AzToolsFramework::FocusModeInterface` — 临时锁定一个 Prefab 作为"可编辑范围"，其它 prefab 变 readonly。避免误改。关键 API：

```cpp
auto* focus = AZ::Interface<AzToolsFramework::FocusModeInterface>::Get();
focus->SetFocusedEntity(entityId);
focus->ClearFocusedEntity();
auto focused = focus->GetFocusedEntityId();
```

---

## ComponentMode — 组件专属编辑子模式

用法场景：选中一个 `BoxVolumeComponent` → 进入 "Box Volume" 模式 → 视口冒出 8 个角操纵器可拖拽调体积。退出模式前，其它 Entity / 组件都不响应。

### 三大类

[ComponentMode/](../Code/Framework/AzToolsFramework/AzToolsFramework/ComponentMode/)：

| 类 | 职责 |
|---|---|
| `EditorBaseComponentMode` | 子模式基类，负责 Action / Viewport UI / Manipulator 生命周期 |
| `ComponentModeDelegate` | 工厂 / 激活器；typically 做成 Editor 组件的成员 |
| `ComponentModeCollection` | 全局 ComponentMode 实例列表（同时激活多个 mode） |

### 声明组件支持 ComponentMode

Editor 组件的 EditContext 里：

```cpp
ec->Class<EditorBoxVolumeComponent>("Box Volume", "")
  ->ClassElement(AZ::Edit::ClassElements::EditorData, "")
  ->Attribute(AZ::Edit::Attributes::ComponentMode,
      AZStd::make_unique<AzToolsFramework::ComponentModeFramework::ComponentModeDelegate>());
```

Editor 组件保存一个 `ComponentModeDelegate` 成员，并在 Activate 里 `Connect`：

```cpp
class EditorBoxVolumeComponent : public AzToolsFramework::Components::EditorComponentBase
{
    void Activate() override {
        EditorComponentBase::Activate();
        m_modeDelegate.ConnectWithSingleComponentMode<
            EditorBoxVolumeComponent, BoxVolumeComponentMode>(
            AZ::EntityComponentIdPair(GetEntityId(), GetId()), nullptr);
    }
    void Deactivate() override {
        m_modeDelegate.Disconnect();
        EditorComponentBase::Deactivate();
    }

    AzToolsFramework::ComponentModeFramework::ComponentModeDelegate m_modeDelegate;
};
```

### 实现 `BoxVolumeComponentMode`

```cpp
class BoxVolumeComponentMode
    : public AzToolsFramework::ComponentModeFramework::EditorBaseComponentMode
{
public:
    BoxVolumeComponentMode(const AZ::EntityComponentIdPair& id, AZ::Uuid type);

    // 视口 UI / Manipulator
    AZStd::vector<AzToolsFramework::ActionOverride> PopulateActionsImpl() override;
    void Refresh() override;   // Entity transform 改变时

private:
    AZStd::shared_ptr<AzToolsFramework::TranslationManipulators> m_boxHandles;
};
```

构造时创建 Manipulators，注册到 `ManipulatorManagerId`；析构时自动 unregister。模式内可以 overwrite 快捷键（`PopulateActionsImpl` 返回 `ActionOverride` 列表，暂时接管 Editor 的菜单/快捷键）。

---

## Manipulators — 视口 3D 操纵器

### 基类 [BaseManipulator.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Manipulators/BaseManipulator.h)

```cpp
class BaseManipulator : public AZStd::enable_shared_from_this<BaseManipulator>
{
public:
    void Register(ManipulatorManagerId id);
    void Unregister();
    bool Registered() const;
    bool PerformingAction() const;

    // 鼠标事件（由 ViewportInteraction 分发）
    bool OnLeftMouseDown(const ViewportInteraction::MouseInteraction&,
                         float rayIntersectionDistance);
    void OnLeftMouseUp(const ViewportInteraction::MouseInteraction&);
    void OnMouseMove(const ViewportInteraction::MouseInteraction&);
    void OnMouseWheel(const ViewportInteraction::MouseInteraction&);
    bool OnMouseOver(ManipulatorId, const ViewportInteraction::MouseInteraction&);
};
```

### 13 个具体子类

| 类 | 用途 |
|---|---|
| `LinearManipulator` | 沿单轴拖 (1D) |
| `PlanarManipulator` | 沿平面拖 (2D) |
| `AngularManipulator` | 绕轴旋转 |
| `SurfaceManipulator` | 鼠标射线 snap 到表面 |
| `LineSegmentSelectionManipulator` | 点击线段 |
| `SplineSelectionManipulator` | 点击样条 |
| `TranslationManipulators` | 组合：X/Y/Z 轴 + 平面（经典 gizmo） |
| `RotationManipulators` | 三轴旋转 gizmo |
| `ScaleManipulators` | 三轴缩放 gizmo |
| `EditorVertexSelection` / `SelectionManipulator` | 点击选择 |
| `BoxManipulator` | 箱体 6 面拖 |
| `SphereManipulator` | 球半径 |
| `CapsuleManipulator` | 胶囊 |

### 最小使用范例

```cpp
auto manip = AzToolsFramework::LinearManipulator::MakeShared(worldFromLocal);
manip->AddEntityComponentIdPair(myId);
manip->SetAxis(AZ::Vector3::CreateAxisX());
manip->SetViews(AzToolsFramework::ManipulatorViews{ /* 箭头形状 */ });
manip->Register(g_mainManipulatorManagerId);

manip->InstallMouseMoveCallback([this](const AzToolsFramework::LinearManipulator::Action& a){
    // a.m_current.m_localPositionOffset / a.LocalPosition()
    // 更新组件状态
});

manip->InstallLeftMouseUpCallback([this](const auto& a){
    AzToolsFramework::ScopedUndoBatch undo("Move something");
    // 持久化状态
});
```

---

## PropertyTreeEditor (RPE) — 属性面板生成器

给一个反射过的 C++ 对象 → 自动长出属性面板。核心：EditContext 定义 → RPE 渲染 → PropertyHandler 处理控件。

### 自定义控件

[PropertyEditorAPI.h](../Code/Framework/AzToolsFramework/AzToolsFramework/UI/PropertyEditor/PropertyEditorAPI.h)：

```cpp
template<typename PropertyType, class WidgetType>
class PropertyHandler : public TypedPropertyHandler_Internal<PropertyType, WidgetType>
{
public:
    // 从 GUI 读值写到数据
    void WriteGUIValuesIntoProperty(
        size_t index, WidgetType* gui, PropertyType& instance,
        InstanceDataNode* node) override = 0;

    // 从数据填 GUI
    bool ReadValuesIntoGUI(
        size_t index, WidgetType* gui, const PropertyType& instance,
        InstanceDataNode* node) override = 0;

    // 创建 Qt 控件
    QWidget* CreateGUI(QWidget* parent) override = 0;

    // 处理 EditContext 上的 attribute（比如 Min/Max/Step）
    void ConsumeAttribute(WidgetType*, AZ::u32 attrib,
        PropertyAttributeReader* attrValue, const char* debugName) override {}
};
```

### 自定义控件注册流程

1. 创建 `class MyColorPickerHandler : public PropertyHandler<AZ::Color, MyColorWidget>`；
2. 实现 4 个方法；
3. 在 Editor SystemComponent 的 `Activate` 里：

```cpp
m_handler = aznew MyColorPickerHandler;
AzToolsFramework::PropertyTypeRegistrationMessages::Bus::Broadcast(
    &PropertyTypeRegistrationMessages::RegisterPropertyType, m_handler);
```

4. EditContext 里用：`->DataElement(AZ::Edit::UIHandlers::<你定义的 handler 名>, &Foo::m_color, ...)`

### 触发写回

自定义控件 change 时要：

```cpp
AzToolsFramework::PropertyEditorGUIMessages::Bus::Broadcast(
    &PropertyEditorGUIMessages::RequestWrite, widget);
```

不然 RPE 不知道值变了。

### AssetEditor — 独立的"反射对象编辑"窗口

[AssetEditor/AssetEditorWidget.h](../Code/Framework/AzToolsFramework/AzToolsFramework/AssetEditor/AssetEditorWidget.h)。给一个资产类型（已反射），就自动出一个 "New / Open / Save" + RPE 编辑面板的窗口。几分钟就能搭个 "资产编辑器"。

---

## ActionManager — 菜单/快捷键/工具栏统一注册

旧代码 `QMenu::addAction` 散落到处，查起来难。新代码**全部走 ActionManager**。

### 三大 Interface

[ActionManager/Action/ActionManagerInterface.h](../Code/Framework/AzToolsFramework/AzToolsFramework/ActionManager/Action/ActionManagerInterface.h):

```cpp
class ActionManagerInterface
{
public:
    AZ_RTTI(ActionManagerInterface, "{...}");

    // 先注册 Context（作用域：某个视口 / Editor 全局 / 某个工具）
    virtual ActionManagerOperationResult RegisterActionContext(
        const AZStd::string& contextIdentifier,
        const ActionContextProperties& properties) = 0;

    // 注册 Action（普通）
    virtual ActionManagerOperationResult RegisterAction(
        const AZStd::string& contextIdentifier,
        const AZStd::string& actionIdentifier,
        const ActionProperties& properties,
        AZStd::function<void()> handler) = 0;

    // 可勾选（状态型，如"显示网格"）
    virtual ActionManagerOperationResult RegisterCheckableAction(
        const AZStd::string& contextIdentifier,
        const AZStd::string& actionIdentifier,
        const ActionProperties& properties,
        AZStd::function<void()> handler,
        AZStd::function<bool()> checkStateCallback) = 0;
};
```

- `MenuManagerInterface::AddActionToMenu(menuId, actionId, order)` — 放入菜单
- `ToolBarManagerInterface::AddActionToToolBar(toolBarId, actionId, order)` — 工具栏
- `HotKeyManagerInterface::SetActionHotKey(actionId, "Ctrl+Shift+R")` — 快捷键

### 完整注册例子

```cpp
void MyEditorSystemComponent::Activate()
{
    auto* am = AZ::Interface<ActionManagerInterface>::Get();
    auto* mm = AZ::Interface<MenuManagerInterface>::Get();
    auto* hkm = AZ::Interface<HotKeyManagerInterface>::Get();
    if (!am || !mm) return;

    AzToolsFramework::ActionProperties props;
    props.m_name        = "Reload Shaders";
    props.m_description = "Reload all shader assets";
    props.m_category    = "Atom";
    am->RegisterAction("o3de.context.editor", "mygem.action.reloadShaders", props,
        [](){ ShaderReloadBus::Broadcast(&ShaderReloadRequests::ReloadAll); });

    hkm->SetActionHotKey("mygem.action.reloadShaders", "Ctrl+Shift+R");
    mm->AddActionToMenu("o3de.menu.tools", "mygem.action.reloadShaders", 100);
}
```

Python 端可以触发同一 action（见下 Python 节）。

### Modes（动态可见性）

一个 Context 里可以有多个 Mode（例：ViewportContext 下有 "Translation" / "Rotation" / "Scale" 三 Mode），Action 属性里用 `m_modes` 指定在哪些 mode 下可见。模式切换时自动刷新菜单/工具栏。

---

## Undo/Redo 命令系统

### 基础类 [Undo/UndoSystem.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Undo/UndoSystem.h)

```cpp
class URSequencePoint   // 单个可撤销步骤
{
public:
    URSequencePoint(const AZStd::string& friendlyName, URCommandID id = 0);

    virtual void Undo() = 0;
    virtual void Redo() = 0;
    virtual bool Changed() const = 0;   // false → 框架会丢弃这一步

    void SetParent(URSequencePoint* parent);   // 树形命令
    const ChildVec& GetChildren() const;
};

class UndoStack   // 持 URSequencePoint 栈
{
public:
    UndoStack(int limit, IUndoNotify* notifier);
    void Post(URSequencePoint*);
    void Undo();
    void Redo();
};
```

### `ScopedUndoBatch`（日常用法）

```cpp
{
    AzToolsFramework::ScopedUndoBatch undo("Move Box");
    // 改状态
    AZ::TransformBus::Event(id, &AZ::TransformBus::Events::SetWorldTM, newTm);
    // 标记哪些 Entity 的哪些字段变了
    undo.MarkEntityDirty(id);
}
// 离开作用域时自动把这一个 "Move Box" 批次推到 UndoStack
```

### 内置具体命令

- `SelectionCommand` — 选中改动（`Ctrl+Z` 回到上次选中集合）
- `EntityStateCommand` — 反射状态快照 before/after 型 undo
- `EntityManipulatorCommand` — 操纵器交互
- `SliceDetachEntityCommand` 等（Slice 系统，已废）

**让自己的操作 undo-able**：继承 `URSequencePoint` 或用 `ScopedUndoBatch` + `AddDirtyEntity`。后者足够 99% 场景。

---

## AssetBrowser

[AssetBrowser/Entries/AssetBrowserEntry.h](../Code/Framework/AzToolsFramework/AzToolsFramework/AssetBrowser/Entries/AssetBrowserEntry.h)：

```cpp
enum class AssetEntryType { Root, Folder, Source, Product };

class AssetBrowserEntry : public QObject
{
public:
    virtual AssetEntryType GetEntryType() const = 0;
    const AZStd::string& GetName() const;
    const QString&       GetDisplayName() const;
    const AZStd::string& GetFullPath() const;
    const AZStd::string& GetRelativePath() const;
    void VisitUp(const AZStd::function<bool(const AssetBrowserEntry*)>&);
    void VisitDown(const AZStd::function<bool(const AssetBrowserEntry*)>&);
};
```

### 结构

```
Root
  Folder (e.g., "textures/")
    Source (e.g., "wall.tif")
      Product (e.g., "wall.dds")
      Product (e.g., "wall.texpng")
```

**过滤**：通过 `AssetBrowserFilterModel`。可以自定义过滤器类 `AssetBrowserEntryFilter` → `Match(entry)` 返回 bool。

**拖拽到 Viewport**：`AssetBrowserEntry` 被序列化为 QMime data → Viewport 接收 drop → 调对应资产类型的 "拖入处理器"（如 mesh asset → spawn entity with MeshComponent）。

---

## EditorEntityContext — Editor 侧实体管理

[Entity/EditorEntityContextComponent.h](../Code/Framework/AzToolsFramework/AzToolsFramework/Entity/EditorEntityContextComponent.h)。和运行时 `EntityContext` 的区别：

| 维度 | Editor | Runtime |
|---|---|---|
| 持有的组件 | `EditorXxxComponent` | `XxxComponent` |
| Undo 支持 | ✓ | ✗ |
| 选中 / 锁 / 可见性 | ✓ | ✗ |
| Prefab 关联 | ✓ | ✗（运行时已烘到 Spawnable） |

### 主要 API

```cpp
// EditorEntityContextRequestBus
AZ::EntityId CreateNewEditorEntity(const char* name);
AZ::EntityId CreateNewEditorEntityWithId(const char* name, const AZ::EntityId&);
void AddEditorEntity(AZ::Entity* entity);
bool CloneEditorEntities(
    const EntityIdList& src,
    EntityList& outCloned,
    AZ::SliceComponent::EntityIdToEntityIdMap& srcToCloneMap);
bool DestroyEditorEntity(AZ::EntityId);
```

### EditorEntityAPI（删除 / 复制的顶层入口）

[API/EditorEntityAPI.h](../Code/Framework/AzToolsFramework/AzToolsFramework/API/EditorEntityAPI.h)：

```cpp
class EditorEntityAPI
{
public:
    virtual void DeleteSelected() = 0;
    virtual void DeleteEntityById(AZ::EntityId) = 0;
    virtual void DeleteEntities(const EntityIdList&) = 0;
    virtual void DeleteEntityAndAllDescendants(AZ::EntityId) = 0;
    virtual void DuplicateSelected() = 0;
    virtual void DuplicateEntities(const EntityIdList&) = 0;
};

auto* api = AZ::Interface<AzToolsFramework::EditorEntityAPI>::Get();
api->DeleteSelected();
```

### EditorEntityInfoRequestBus（查询层级）

```cpp
AZStd::string name;
EditorEntityInfoRequestBus::EventResult(name, id, &EditorEntityInfoRequests::GetName);
AZ::EntityId parent;
EditorEntityInfoRequestBus::EventResult(parent, id, &EditorEntityInfoRequests::GetParent);
EntityIdList children;
EditorEntityInfoRequestBus::EventResult(children, id, &EditorEntityInfoRequests::GetChildren);
```

---

## Python 桥（EditorPythonBindings）

Gem [EditorPythonBindings](../Gems/EditorPythonBindings/) 自动把 `BehaviorContext` 反射的 C++ API 包成 `azlmbr.*`。Editor 启动时扫一遍，生成 Python 代理对象。

### 命名空间映射

BehaviorContext 里的 `Module` attribute 决定 Python 路径：

```cpp
bc->Class<MyType>("MyType")
  ->Attribute(AZ::Script::Attributes::Module, "editor.entity");
// → Python: azlmbr.editor.entity.MyType
```

### 三种 bus 调用

```python
import azlmbr.bus as bus
import azlmbr.editor as editor
import azlmbr.entity as entity

# 1) Broadcast（无 ID bus）
editor.ToolsApplicationRequestBus(bus.Broadcast, 'SaveEntitiesToStream', outStream)

# 2) Event（有 ID bus），第三参为 bus id
pos = azlmbr.components.TransformBus(bus.Event, 'GetWorldTranslation', entity_id)

# 3) BroadcastResult 没有专门语法：Broadcast/Event 直接 return 结果
ver = editor.EditorSettingsAPIBus(bus.Broadcast, 'GetVersion')
```

### 完整 Editor 自动化片段

```python
import azlmbr
import azlmbr.bus as bus
import azlmbr.editor as editor
import azlmbr.entity as entity
import azlmbr.prefab as prefab

# 创建 Entity
new_id = editor.ToolsApplicationRequestBus(
    bus.Broadcast, 'CreateNewEntity', entity.EntityId())

# 改名
editor.EditorEntityAPIBus(bus.Event, new_id, 'SetName', 'HeroSpawn')

# 加组件（按类型名字串查 ID 再加）
type_ids = editor.EditorComponentAPIBus(
    bus.Broadcast, 'FindComponentTypeIdsByEntityType',
    ['Transform', 'Mesh Component'], entity.EntityType_Game)
editor.EditorComponentAPIBus(
    bus.Broadcast, 'AddComponentsOfType', new_id, type_ids)

# 存为 prefab
prefab.PrefabPublicRequestBus(
    bus.Broadcast, 'CreatePrefabInMemory', [new_id], '/my/prefab.prefab')
```

### QtForPython（直接用 PySide2）

[Gems/QtForPython](../Gems/QtForPython/)：把 PySide2 装进 Editor Python 环境：

```python
from PySide2 import QtWidgets
dlg = QtWidgets.QDialog()
dlg.setWindowTitle("My Tool")
dlg.show()
```

和 Editor 主窗口共享事件循环。用于"用脚本快速做个工具窗口"。

### Bootstrap 位置

```
<Project>/Editor/Scripts/bootstrap.py     # 项目启动脚本
<Gem>/Editor/Scripts/bootstrap.py         # Gem 提供
<Gem>/Editor/Scripts/*.py                 # 常规脚本
```

`Editor → Tools → Python Console` 有交互式 REPL，`Python Scripts` 面板可跑文件。

---

## 常见坑（Editor 层）

1. **Editor 组件和 runtime 组件的 UUID 相同** → SerializeContext 混乱，Prefab 反序列化出错。
2. **Editor 组件 `GetProvidedServices` 不对齐 runtime** → BuildGameEntity 烘焙后 Entity 激活失败（Required 服务缺失）。
3. **Editor 组件 include runtime 细节（渲染/物理 头）跨 Gem** → Editor 模块被迫链接 runtime 的 3rdParty，构建图乱。
4. **`BuildGameEntity` 返回 runtime 组件时 include 了 Qt 头** → 不会报错但把 Qt 泄漏到 runtime 抽象面；monolithic 出包时炸。
5. **忘 `SetDirty()`** → 改了数据但 Editor 不知道要保存，下次打开丢。改完加：
   ```cpp
   SetDirty();
   AzToolsFramework::ToolsApplicationRequestBus::Broadcast(
       &ToolsApplicationRequests::AddDirtyEntity, GetEntityId());
   ```
6. **Manipulator 没 `Register` 或重复注册** → 点不到 / crash。`MakeShared` 返回后立即 `Register`，析构前 `Unregister`。
7. **ActionManager 的 contextId / actionId 全局唯一** → 重名 silent 失败。用 `o3de.<gem>.<category>.<name>` 反 DNS 命名。
8. **PropertyHandler 的 `WriteGUIValuesIntoProperty` 改了值没调 `RequestWrite`** → Undo 不感知。
9. **Python 脚本做慢操作阻塞 UI** → `bus.Broadcast` 在主线程执行；长耗时的操作考虑 QThread 或 Python `threading`（但回调必须 marshal 回主线程）。
10. **自定义 dock widget 不走 ViewPane** → Editor 关闭再开后位置不保存。应注册 ViewPane：
    ```cpp
    EditorRequestBus::Broadcast(&EditorRequests::RegisterCustomViewPane, "MyTool", "MyGem", viewOptions);
    ```

---

继续：[05_gems_and_modules.md](05_gems_and_modules.md) / [12_cookbook_recipes.md](12_cookbook_recipes.md)
