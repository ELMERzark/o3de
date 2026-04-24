# 03 · AzFramework — 运行时骨架（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

路径：[Code/Framework/AzFramework/AzFramework/](../Code/Framework/AzFramework/AzFramework/)

AzFramework 在 AzCore 之上，给"一个会跑的进程"加必要的东西：主循环、应用生命周期、输入、场景、控制台、网络基础。**仍然没有 Qt**。所有 Launcher 都派生它，Editor 间接派生它。

## 子目录速查

| 子目录 | 职责 | 代表头文件 |
|---|---|---|
| `Application/` | `Application` 生命周期总管 | [Application.h](../Code/Framework/AzFramework/AzFramework/Application/Application.h) |
| `Entity/` | `EntityContext` / `GameEntityContext` | `EntityContext.h` |
| `Scene/` | 多场景（一个进程同时跑多个逻辑世界） | `Scene/Scene.h`, `Scene/SceneSystemInterface.h` |
| `Spawnable/` | `.spawnable` 资产的运行时实例化 | `Spawnable/SpawnableEntitiesInterface.h` |
| `Components/` | 通用运行时组件（Transform、Console、NonUniformScale） | `TransformComponent.h` |
| `Input/` | 跨平台输入：Devices/Channels/Events | `Input/Devices/*`, `Input/Channels/*`, `Input/Events/*` |
| `Archive/` | `.pak` 访问 | `Archive/IArchive.h` |
| `Asset/` | 运行时资产层 (AssetCatalog / AssetBuilder SDK / GenericAssetHandler) | `Asset/GenericAssetHandler.h` |
| `IO/` | `LocalFileIO` + 别名解析 | `IO/LocalFileIO.h` |
| `Physics/` | 运行时物理公共 API（实现在 PhysX Gem） | `Physics/PhysicsSystem.h` |
| `Render/` | 渲染抽象接口（实现在 Atom） | `Render/GeometryIntersectionBus.h` |
| `Script/` | 通用脚本辅助 | `Script/ScriptComponent.h` |
| `Network/` | 早期网络辅助 | `Network/IRemoteTools.h` |

---

## 应用生命周期（详细调用链）

所有 O3DE 可执行都走这条路径。理解它能省 80% 启动 bug 的调试时间。

```
WinMain / main()
 └── 构造 AzFramework::Application app(argc, argv)
 └── AzFramework::Application::Descriptor desc;
 └── app.Start(desc, startupParameters)
      ├── ComponentApplication::Create(desc, startupParameters)
      │    ├── MergeSettingsToRegistry()  // 合并配置（顺序见下）
      │    ├── CreateStaticModules()      // 虚函数，派生类可 override
      │    ├── LoadDynamicModules()       // 扫 engine.json/project.json 列的 Gem，dlopen/LoadLibrary
      │    │    └── 每个 Gem Module 构造时把 descriptors.insert 进去
      │    ├── CreateSystemEntity()       // 空 Entity，System Components 挂这里
      │    └── Module::GetRequiredSystemComponents() → 自动 AddComponent
      ├── SetFileIOAliases()              // 别名：@engroot@ / @projectroot@ / @products@ / @user@ / @log@ / @exefolder@ / @gemroot:<gem>@
      └── StartCommon(systemEntity)
           ├── systemEntity->Init();
           ├── systemEntity->Activate();  // 触发所有 SystemComponent::Activate
           └── [可选] 加载 AssetCatalog (@products@/assetcatalog.xml)

[运行]
每帧：
  app.Tick()    → AZ::TickBus::ExecuteQueuedEvents() → 广播 OnTick
  app.TickSystem() → AZ::SystemTickBus::ExecuteQueuedEvents()

退出：
  app.Stop()
   ├── systemEntity.Deactivate()  // 反向激活顺序
   ├── ModuleManager.UnloadModules()
   └── Destroy allocators
```

### 关键派生层次

```
AZ::ComponentApplication          (AzCore)   — 模块/组件管理，无主循环概念
  └── AzFramework::Application              — 加运行时通用：FileIO、Input、Archive、AssetCatalog
        ├── AzGameFramework::GameApplication  — GameLauncher / ServerLauncher：关闭 editor-only 模块
        └── AzToolsFramework::ToolsApplication — Editor：启用 editor 模块 + Qt 事件桥
```

**改启动行为一般不改这些类，而是写一个 SystemComponent 在 `Activate` 里做**。想访问 app：`AZ::ComponentApplicationBus::Broadcast` 或 `AZ::Interface<AZ::ComponentApplicationRequests>::Get()`。

### Settings 合并顺序

从 `AzCore/Settings/SettingsRegistryMergeUtils.cpp` 可看到实际顺序（自底向上，后者覆盖前者）：

1. 引擎默认 `<engroot>/Registry/*.setreg`
2. 每个启用 Gem 的 `Gems/<gem>/Registry/*.setreg`
3. 项目 `<projectroot>/Registry/*.setreg`
4. 平台特化 `Registry/Platform/<os>/*.setreg`
5. 构建模式特化 `Registry/*.<build>.setreg`（development/profile/release）
6. 用户 `<projectroot>/user/Registry/*.setreg`
7. 命令行 `--regset "/path=value"` / `--regset-file file.setreg`

**specialization** 是一组标签（editor / client / server / game / tools / windows / linux / …），文件名里带这些标签才会加载。例如 `bootstrap.editor.setreg` 只在 Editor 进程加载。

### GameApplication vs ToolsApplication 差异

| 维度 | GameApplication | ToolsApplication |
|---|---|---|
| specialization | `game`, `client` 或 `server` | `editor`, `tools` |
| 启用的模块 | 仅 `.Clients` / `.Servers` alias 下的 Gem | 额外加 `.Tools` / `.Builders` |
| 启用 Qt? | ✗ | ✓ |
| 启用 Python? | ✗ | ✓ (如果 EditorPythonBindings 启用) |
| 是否加载 Editor-only 组件描述器 | ✗ | ✓ |

---

## TickBus / SystemTickBus（帧心跳）

两个最常用的帧事件：

| Bus | 频率 | 典型用途 |
|---|---|---|
| `AZ::TickBus` | 每游戏帧 | 组件业务逻辑；有 delta time 和 ScriptTimePoint |
| `AZ::SystemTickBus` | 每次系统 tick（通常 ≥ 帧率，甚至 app 未启动主循环时也跑） | 资产流水、OS 事件、等待初始化 |

Tick 执行顺序（`AzCore/Component/TickBus.h`）：

```
TICK_FIRST / TICK_PLACEMENT / TICK_INPUT / TICK_GAME / TICK_ANIMATION
  / TICK_PHYSICS / TICK_ATTACHMENT / TICK_PRE_RENDER / TICK_DEFAULT
  / TICK_UI / TICK_LAST
```

```cpp
int GetTickOrder() const override { return AZ::TICK_GAME; }
```

想让多个组件内部有序，自己定 tick order 常量（避免都挤在 `TICK_DEFAULT`）。

---

## Scene + Spawnable（旧 Slice 系统的替代）

### Scene —— 独立模拟世界

`AzFramework::Scene` 不是 3D 场景概念，而是**一组 subsystem + 一个 EntityContext**的容器。一个 App 可跑多个 Scene（运行时场景 + UI 场景 + 工具场景…）。

关键 API（`Scene.h` / `SceneSystemInterface.h`）：

```cpp
// 全局服务
auto* sceneSys = AZ::Interface<AzFramework::ISceneSystem>::Get();

// 创建
auto outcome = sceneSys->CreateScene("GameScene");
AZStd::shared_ptr<AzFramework::Scene> scene = outcome.GetValue();

// 往 Scene 挂 subsystem（Atom 渲染、物理、UI 都是这样挂的）
scene->SetSubsystem(aznew MyRenderSystem);
// 查找
auto* rs = scene->FindSubsystem<MyRenderSystem>();     // 当前 + 父 Scene 递归
auto* rsLocal = scene->FindSubsystemInScene<MyRenderSystem>();

// 常量场景名
constexpr AZStd::string_view MainSceneName = "Main";          // 游戏主
constexpr AZStd::string_view EditorMainSceneName = "Editor";  // Editor 视口
```

**Parent Scene**：子 Scene 没找到 subsystem 会回退查 parent。用于"Editor 窗口共享主场景的渲染服务"一类场景。

### Spawnable 运行时 API

编辑器的 `.prefab` 经 PrefabBuilder 烘焙为 `.spawnable` 产物资产；运行时通过 `SpawnableEntitiesInterface` 实例化。

```cpp
#include <AzFramework/Spawnable/SpawnableEntitiesInterface.h>

auto* svc = AzFramework::SpawnableEntitiesInterface::Get();

AZ::Data::Asset<AzFramework::Spawnable> asset = /* 从 AssetCatalog / 引用拿到 */;
AzFramework::EntitySpawnTicket ticket(asset);

// 选项
AzFramework::SpawnAllEntitiesOptionalArgs opts;
opts.m_preInsertionCallback = [](auto id, auto begin, auto end){
    // 注入数据：在实体加入世界之前改组件参数
};
opts.m_completionCallback = [](auto id, auto view){
    // 全部激活完成（注意：可能在工作线程！）
};
opts.m_priority = AzFramework::SpawnablePriority_Default;  // 0 最高 / 255 最低
svc->SpawnAllEntities(ticket, AZStd::move(opts));

// 销毁
svc->DespawnAllEntities(ticket);

// 更多
svc->SpawnEntities(ticket, {0, 2, 5}, {});   // 只生成索引 0/2/5 对应的实体
svc->ReloadSpawnable(ticket, newAsset, {});  // 热替换 Spawnable 资产
svc->Barrier(ticket, callback, {});          // 同步点：等前面所有操作完成再回调
svc->ListEntities(ticket, cb);               // 枚举票内所有实体
```

**`EntitySpawnTicket` 生命周期语义**：票**析构即销毁所有该票生成的实体**。所以通常把 ticket 存成组件成员。

**陷阱**：
- `completionCallback` **可能在任意线程**被调用 —— 别在里面做主线程专用操作（Entity 相关 API 绝大多数只能主线程）。要 marshal 回主线程，`AZ::TickBus::QueueFunction` 是安全做法。
- 同一 ticket 的请求**按提交顺序执行**（队列），多线程并发提交不同请求则顺序不保证。
- `m_referencePreviouslySpawnedEntities = false` 会重置 ID 映射 → 下一次 `SpawnEntities` 不能引用前一次的 entity；默认 true 更直觉。

---

## Input 系统（完整视图）

分三层：`InputDevice` → `InputChannel` → 事件（`InputChannelNotificationBus` / `InputChannelEventListener`）。

### 设备与通道

| Device | 实现 | 典型 Channel |
|---|---|---|
| Keyboard | `InputDeviceKeyboard` | `Key::AlphanumericA`, `Key::EditSpace`, `Key::ModifierCtrlL` … |
| Mouse | `InputDeviceMouse` | `Button::Left/Right/Middle`, `Movement::X/Y/Z`（z=滚轮） |
| Gamepad | `InputDeviceGamepad` (多个 index) | `Button::A/B/X/Y`, `Trigger::L2/R2`, `ThumbStickAxis1D::LX` 等 |
| Touch | `InputDeviceTouch` | `Touch::Index0..9`（多点） |
| VirtualKeyboard | `InputDeviceVirtualKeyboard` | 软键盘字符 |

Channel 子类（`Input/Channels/`）：

- `InputChannelDigital` — 开关（按键按下/抬起）
- `InputChannelAnalog` — 单 float 值（触发板深度）
- `InputChannelAxis1D/2D/3D` — 方向向量（摇杆、motion）
- `InputChannelDelta` — 帧间增量（鼠标移动）

Channel 的 `State`：`Idle / Began / Updated / Ended`。

### 低层监听（直接拿原始事件）

```cpp
#include <AzFramework/Input/Events/InputChannelEventListener.h>

class MyInput : public AzFramework::InputChannelEventListener
{
public:
    MyInput() : InputChannelEventListener(
        AzFramework::InputChannelEventListener::GetPriorityGameplay()) {
        Connect();
    }

    bool OnInputChannelEventFiltered(const AzFramework::InputChannel& ch) override
    {
        using Keyboard = AzFramework::InputDeviceKeyboard;
        if (ch.GetInputChannelId() == Keyboard::Key::AlphanumericA && ch.IsStateBegan())
        {
            // 按下 A
            return true;  // true = 消费，后续 listener 收不到
        }
        // 2D 位置（touch/mouse）
        if (const auto* pos2d = ch.GetCustomData<AzFramework::InputChannel::PositionData2D>()) {
            // pos2d->m_normalizedPosition  (0..1)
        }
        return false;
    }
};
```

优先级常量：

```
GetPriorityFirst()  = INT_MAX
GetPriorityDebug()  ≈ INT_MAX * 3/4
GetPriorityUI()     = INT_MAX / 2
GetPriorityGameplay() = 0 (Default)
GetPriorityLast()   = INT_MIN
```

**同一事件按优先级传递，任一 listener `return true` 即消费**，后续不再收到。UI 框架利用这个实现"点击穿透阻止"。

### 高层：StartingPointInput（推荐做游戏逻辑）

[Gems/StartingPointInput](../Gems/StartingPointInput/) 提供"输入映射"资产：把原始按键映射为语义事件 (`"Jump"`, `"Fire"`)：

```cpp
using namespace StartingPointInput;
InputEventNotificationId eventId(localUser, AZ_CRC_CE("Jump"));

class MyGame : public InputEventNotificationBus::Handler {
    void OnActivate() { InputEventNotificationBus::Handler::BusConnect(eventId); }
    void OnPressed(float value) override { /* jump 按下 */ }
    void OnHeld(float value)    override { /* jump 持续 */ }
    void OnReleased(float value)override { /* jump 抬起 */ }
};
```

**建议**：Gem 内核用低层 InputChannel；游戏逻辑一律走 StartingPointInput。换映射方案时不用改 C++。

---

## TransformComponent 与空间

### TransformBus 完整 API（`AzCore/Component/TransformBus.h`）

```cpp
// 读
AZ::Transform world;  AZ::TransformBus::EventResult(world, id, &AZ::TransformBus::Events::GetWorldTM);
AZ::Transform local;  AZ::TransformBus::EventResult(local, id, &AZ::TransformBus::Events::GetLocalTM);
AZ::Vector3 pos;      AZ::TransformBus::EventResult(pos, id, &AZ::TransformBus::Events::GetWorldTranslation);
AZ::Vector3 scale;    AZ::TransformBus::EventResult(scale, id, &AZ::TransformBus::Events::GetLocalScale);

// 写
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::SetWorldTM, tm);
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::SetLocalTranslation, pos);
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::MoveEntity, offset);        // 增量
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::RotateAroundLocalZ, 0.1f);

// 层次
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::SetParent,          parentId); // 保留 world
AZ::TransformBus::Event(id, &AZ::TransformBus::Events::SetParentRelative,  parentId); // 保留 local
AZStd::vector<AZ::EntityId> kids;
AZ::TransformBus::EventResult(kids, id, &AZ::TransformBus::Events::GetChildren);
```

### 通知：TransformNotificationBus

```cpp
class MyFollower : public AZ::TransformNotificationBus::Handler {
    void Activate() { BusConnect(m_targetId); }
    void OnTransformChanged(const AZ::Transform& local, const AZ::Transform& world) override { }
    void OnParentChanged(AZ::EntityId oldParent, AZ::EntityId newParent) override {}
    void OnChildAdded(AZ::EntityId child) override {}
};
```

### `SetParent` vs `SetParentRelative` 的区别

```
SetParent(P):          world 保留，local 重算为 world * parent^-1
SetParentRelative(P):  local 保留，world 重算为 parent * local（实体"跳到"父相对位置）
```

UI 拖挂时默认 `SetParent`（不让物体跳）；脚本里生成一个预制作"口袋内物品"时用 `SetParentRelative`。

### NonUniformScale

`AZ::Transform` 只支持**统一缩放**。需要非统一缩放时加 `NonUniformScaleComponent`：

```cpp
AZ::Vector3 s(2.f, 1.f, 1.f);
AZ::NonUniformScaleRequestBus::Event(id, &AZ::NonUniformScaleRequests::SetScale, s);
```

注意：**许多组件不支持非统一 scale**（collider、mesh LOD 等），加了会有警告。

---

## Console (CVar / Command) 深入

### 定义 CVar

```cpp
#include <AzCore/Console/IConsole.h>

// 基本
AZ_CVAR(float, gm_playerSpeed, 5.f, nullptr, AZ::ConsoleFunctorFlags::Null, "Player speed");

// 带变更回调
void OnSpeedChanged(const float& newValue) { /* ... */ }
AZ_CVAR(float, gm_playerSpeed, 5.f, &OnSpeedChanged, AZ::ConsoleFunctorFlags::Null, "Player speed");
```

### 定义命令

```cpp
// 自由函数
AZ_CONSOLEFREEFUNC(gm_kill, AZ::ConsoleFunctorFlags::Null, "Kill the player", [](){
    PlayerRequestBus::Broadcast(&PlayerRequests::Kill);
});

// 类成员
class PlayerController {
    void Teleport(const AZ::ConsoleCommandContainer& args);
    AZ_CONSOLEFUNC(PlayerController, Teleport, AZ::ConsoleFunctorFlags::Null, "Teleport");
};
```

`Teleport` 会注册成 `PlayerController.Teleport x y z`。

### `ConsoleFunctorFlags` 关键值

| 值 | 意义 |
|---|---|
| `Null` | 无特殊 |
| `DontReplicate` | 不跨网络同步（多数 cvar 应该选这个或默认） |
| `ServerOnly` | 仅 server 执行；client 尝试则拒绝 |
| `ReadOnly` | 运行时不可改（`PerformCommand` 默认拒绝 ReadOnly） |
| `IsCheat` | 作弊类，可能被"作弊保护"屏蔽 |
| `IsInvisible` | 自动补全不显示 |
| `IsDeprecated` | 调用时警告 |
| `AllowClientSet` | Multiplayer 场景下允许客户端修改（警告：安全隐患） |
| `DontDuplicate` | 重复注册静默丢弃（不覆盖） |

### 执行

```cpp
auto* console = AZ::Interface<AZ::IConsole>::Get();
console->PerformCommand("gm_playerSpeed 10");
console->PerformCommand("gm_kill");
console->ExecuteCommandLine(cmdLine);       // 从命令行参数
console->ExecuteConfigFile("autoexec.cfg"); // 从文件批量执行

// 查找 / 自动完成
auto* func = console->FindCommand("gm_playerSpeed");
AZStd::vector<AZStd::string> matches;
console->AutoCompleteCommand("gm_", &matches);
```

### CVar 默认值来源

```
代码 AZ_CVAR 初值
  < Registry/*.setreg 里的 "/Amazon/AzCore/Runtime/ConsoleCommands/<name>" = "<value>"
  < 命令行 --<name>=<value> 或 --regset ...
```

所以要给 cvar 换默认值，**不要改 .cpp，改 setreg**。

### Remote Console

运行时进程可以开端口让外部 console 连上：

```
Launcher.exe --remote_console --remote_console_port=4600
# 另一端用 Code/Tools/RemoteConsole/ 或 Editor 内"Remote Console" 面板
```

用于调试服务器或已锁屏的无头实例。

---

## Asset 运行时 API（深入）

### Asset<T> 引用类型

`AZ::Data::Asset<T>` 不是裸指针，是"**ID + 可选已解析数据**"的智能引用。四种状态：

```
NotLoaded → Queued → Loading → Ready（可读）
                                ↓
                              Error（加载失败）
```

### `GetAsset` vs `FindAsset`

```cpp
// GetAsset：一定返回非空；未在内存就触发加载
auto tex = AZ::Data::AssetManager::Instance().GetAsset<TextureAsset>(
    assetId, AZ::Data::AssetLoadBehavior::PreLoad);
tex.BlockUntilLoadComplete();  // 同步阻塞（不推荐在主帧使用）

// FindAsset：只查缓存，返回可能空
auto cached = AZ::Data::AssetManager::Instance().FindAsset<TextureAsset>(
    assetId, AZ::Data::AssetLoadBehavior::Default);
if (!cached) { /* 还没加载 */ }
```

### `AssetLoadBehavior`

| 值 | 效果 |
|---|---|
| `Default` | 按类型默认 |
| `PreLoad` | 发现即加载；**父资产** Ready 状态要等它先 Ready（递归） |
| `QueueLoad` | 异步队列；父资产可独立 Ready |
| `NoLoad` | 只持 ID 不加载（按需 `QueueLoad`） |

关键：**材质的贴图引用**通常是 `PreLoad`，因为材质未加完成就显示会黑屏；**音效资产**可以 `QueueLoad`。

### 订阅加载完成

```cpp
class UsesAsset : public AZ::Data::AssetBus::Handler
{
public:
    void Activate() {
        AZ::Data::AssetBus::Handler::BusConnect(assetId);
        m_asset = AZ::Data::AssetManager::Instance()
            .GetAsset<MyAsset>(assetId, AZ::Data::AssetLoadBehavior::PreLoad);
    }
    void Deactivate() { AZ::Data::AssetBus::Handler::BusDisconnect(); }

    void OnAssetReady(AZ::Data::Asset<AZ::Data::AssetData> a) override { /* 用 */ }
    void OnAssetReloaded(AZ::Data::Asset<AZ::Data::AssetData> a) override { /* 热更新 */ }
    void OnAssetError(AZ::Data::Asset<AZ::Data::AssetData> a) override { /* 错 */ }
    void OnAssetUnloaded(const AZ::Data::AssetId, const AZ::Data::AssetType) override {}

    AZ::Data::Asset<MyAsset> m_asset;
};
```

**`OnAssetReady`** 在 bus connect 时如果资产已 Ready 会立刻同步回调一次 — 不用担心错过。

### GenericAssetHandler — 最快加个新资产类型

```cpp
// MyAsset.h
class MyAsset : public AZ::Data::AssetData {
public:
    AZ_CLASS_ALLOCATOR(MyAsset, AZ::SystemAllocator);
    AZ_RTTI(MyAsset, "{uuid-A}", AZ::Data::AssetData);

    static void Reflect(AZ::ReflectContext* c) {
        if (auto* sc = azrtti_cast<AZ::SerializeContext*>(c)) {
            sc->Class<MyAsset, AZ::Data::AssetData>()
                ->Version(1)
                ->Field("data", &MyAsset::m_data);
        }
    }
    AZStd::vector<AZ::u32> m_data;
};

// MySystemComponent.cpp
using MyAssetHandler = AzFramework::GenericAssetHandler<MyAsset>;

void MySystemComponent::Activate()
{
    m_handler = AZStd::make_unique<MyAssetHandler>(
        "My Asset",            // display name
        "MyGem",               // group
        "myasset",             // extension (no dot)
        AZ::Uuid::CreateNull() // associated component type（若可拖到实体）
    );
    m_handler->Register();
}

void MySystemComponent::Deactivate() { m_handler->Unregister(); }
```

注册后运行时就能 `GetAsset<MyAsset>(id, ...)`。还需搭配一个 Builder（见 [07_asset_pipeline.md](07_asset_pipeline.md)）把源文件转成产物。

---

## File IO Alias 完整解析

所有 alias 在 `AzFramework::Application::SetFileIOAliases()`（`Application.cpp` 约 681 行）建立，SettingsRegistry 提供源头：

| 别名 | Registry 键 | 默认回退 |
|---|---|---|
| `@engroot@` | `FilePathKey_EngineRootFolder` | 必须有 |
| `@projectroot@` | `FilePathKey_ProjectPath` | `@engroot@` |
| `@exefolder@` | `FilePathKey_BinaryFolder` | 可执行路径 |
| `@products@` | `FilePathKey_CacheRootFolder` | `@projectroot@/Cache/<platform>` |
| `@user@` | `FilePathKey_ProjectUserPath` | `@projectroot@/user` |
| `@log@` | `FilePathKey_ProjectLogPath` | `@user@/log` |
| `@gemroot:<name>@` | 每个活跃 Gem 的根路径 | 各 Gem 自报 |
| 自定义 | `/O3DE/Filesystem/Aliases` 下任意 key | 无 |

### 解析层次（LocalFileIO）

```
path ("@products@/textures/wall.texpng")
 → LocalFileIO::ResolvePath
 → ReplaceAlias 替换 "@products@" 为实际路径
 → ArchiveFileIO 检查 .pak 内有没有（若游戏打包模式）
 → SystemFile 平台调用 (Win32 / POSIX)
```

**要点**：
- **Alias 在路径的任意位置都能识别**（不仅开头），比如 `@gemroot:Atom@/Assets/default.png`。
- **大小写**：alias 本身敏感，但 Windows 上磁盘路径大小写不敏感。
- **自定义 alias**：在 `.setreg` 写 `"/O3DE/Filesystem/Aliases/mod_root": "<path>"`，启动后 `@mod_root@` 可用。

---

## 常见陷阱 / AzFramework 层

1. **在非主线程碰 Entity API** → 主线程才能安全操作 Entity/Component；想后台做事用 Task，完成再 `QueueFunction` 回主线程。
2. **`SpawnEntitiesInterface` 回调里主线程假设** → 可能在工作线程；`AZ::TickBus::QueueFunction(...)` 切回。
3. **多 Scene 场景下 EntityId 冲突** → 同一 EntityId 在不同 Scene 都能"有效"，但 TransformBus 之类全局 bus 会混；跨 scene 访问必须走 scene system。
4. **InputChannelEventListener 忘 Connect** → 继承了默认 disconnected，别以为构造就订阅。
5. **CVar 回调假设主线程** → Remote Console / 命令行提交的命令可能任意线程；回调要线程安全（或 QueueFunction）。
6. **Asset 依赖没写 PreLoad** → 游戏逻辑看到 `Asset ready` 但其引用的子资产还没 ready，显示出错。
7. **`@user@` 目录未创建就写**：SetFileIOAliases 调过 `CreatePath`，但自定义 alias 要自己建。
8. **Spawnable 票没留** → `EntitySpawnTicket` 作为 local var 出作用域就析构，实体被 despawn。存成 member。

继续：[04_aztoolsframework.md](04_aztoolsframework.md) / [05_gems_and_modules.md](05_gems_and_modules.md)
