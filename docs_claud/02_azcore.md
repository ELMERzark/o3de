# 02 · AzCore — 引擎的地基（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

路径：[Code/Framework/AzCore/AzCore/](../Code/Framework/AzCore/AzCore/)

AzCore **不依赖任何上层**（没有 Qt，没有渲染，甚至不假设有主循环）。写运行时代码几乎每天都要碰它。本章按"写代码时真正需要记住的 API 边界"组织，含真实签名与常见坑。

## 子目录速查

| 子目录 | 干啥的 | 必看头文件 |
|---|---|---|
| `Component/` | `Entity` + `Component` + `ComponentBus` 规范 | [Component.h](../Code/Framework/AzCore/AzCore/Component/Component.h), [Entity.h](../Code/Framework/AzCore/AzCore/Component/Entity.h), `ComponentApplicationBus.h`, `TickBus.h` |
| `EBus/` | 事件总线（信号/通知 + 接口暴露） | [EBus.h](../Code/Framework/AzCore/AzCore/EBus/EBus.h) |
| `Interface/` | 轻量跨模块单例接口 | [Interface.h](../Code/Framework/AzCore/AzCore/Interface/Interface.h) |
| `RTTI/` | `AZ_RTTI` / `AZ_CLASS_ALLOCATOR` / `BehaviorContext` | `RTTI.h`, `TypeInfo.h`, `BehaviorContext.h` |
| `Serialization/` | 反射 + 序列化（XML / JSON / ObjectStream） | `SerializeContext.h`, `EditContext.h`, `EditContextConstants.inl`, `Json/*` |
| `Memory/` | 分配器、Smart pointers、AZStd 容器用的 allocator | `Memory.h`, `SystemAllocator.h`, `Memory_fwd.h` |
| `Module/` | `AZ::Module` / `ModuleManager` / 动态库加载 | `Module.h`, `ModuleManager.h` |
| `Math/` | `Vector3`, `Quaternion`, `Aabb`, `Transform`（SIMD） | `Vector3.h`, `Transform.h` |
| `std/` | 自家 STL-ish: `AZStd::vector/string/unordered_map` | `std/containers/*` |
| `Jobs/` | 经典 fork-join Job 系统 | `Jobs/Job.h`, `Jobs/JobFunction.h` |
| `Task/` | 新一代 TaskGraph/TaskExecutor | `Task/TaskExecutor.h`, `Task/TaskGraph.h` |
| `IO/` | 文件抽象 + `Streamer` 异步流 | `IO/FileIO.h`, `IO/Streamer/Streamer.h` |
| `Settings/` | Settings Registry | `Settings/SettingsRegistry.h` |
| `Console/` | CVar / console command | `Console/IConsole.h`, `Console/IConsoleTypes.h` |
| `Name/` | `AZ::Name` 驻留字符串 | `Name/Name.h` |
| `Debug/` | Trace/Assert/Profiler | `Debug/Trace.h`, `Debug/Profiler.h`, `Debug/Budget.h` |
| `Asset/` | `AssetManager` / `AssetData` / `Asset<T>` | `Asset/AssetManager.h`, `Asset/AssetCommon.h` |

---

## Component / Entity 深入

### 生命周期完整顺序

```
构造 → Init() → Activate() → [运行...] → Deactivate() → 析构
```

- `Init()` 只调一次，且**在反序列化之后、Activate 之前**。用于一次性设置（如分配缓冲区）。**不要**在 Init 里 BusConnect — 那时 Entity 还不 Active。
- `Activate()` 订阅 EBus、启动定时器、拿资源。可重入（Entity 可反复 Activate/Deactivate）。
- `Deactivate()` 必须把 `Activate` 做的一切反过来：BusDisconnect、释放资源、停止 tick。**顺序很重要**：晚连接的 bus 先断开。
- 析构**不一定按栈顺序**；资源释放别依赖析构。

### 组件骨架 + 服务依赖

```cpp
#include <AzCore/Component/Component.h>
#include <AzCore/Serialization/SerializeContext.h>
#include <AzCore/Serialization/EditContext.h>

namespace MyGem
{
    class MovementComponent
        : public AZ::Component
        , public AZ::TickBus::Handler
    {
    public:
        AZ_COMPONENT(MovementComponent, "{12345678-1234-1234-1234-1234567890AB}");

        static void Reflect(AZ::ReflectContext*);

        // 依赖声明 - 影响 Entity 激活顺序和 Editor "Add Component" 菜单
        static void GetProvidedServices  (AZ::ComponentDescriptor::DependencyArrayType& s);
        static void GetRequiredServices  (AZ::ComponentDescriptor::DependencyArrayType& s);  // 没它就不能激活
        static void GetIncompatibleServices(AZ::ComponentDescriptor::DependencyArrayType& s);  // 不能同存
        static void GetDependentServices (AZ::ComponentDescriptor::DependencyArrayType& s);  // 软依赖（有则我后激活）

    protected:
        void Init() override;
        void Activate() override;
        void Deactivate() override;

        // AZ::TickBus
        void OnTick(float dt, AZ::ScriptTimePoint) override;
        int  GetTickOrder() const override { return AZ::TICK_GAME; }

    private:
        float m_speed = 1.f;
    };
}
```

服务声明写法：

```cpp
void MovementComponent::GetProvidedServices(DependencyArrayType& s) {
    s.push_back(AZ_CRC_CE("MovementService"));
}
void MovementComponent::GetRequiredServices(DependencyArrayType& s) {
    s.push_back(AZ_CRC_CE("TransformService"));
}
void MovementComponent::GetIncompatibleServices(DependencyArrayType& s) {
    s.push_back(AZ_CRC_CE("MovementService"));  // 同实体最多一个移动组件
}
void MovementComponent::GetDependentServices(DependencyArrayType& s) {
    s.push_back(AZ_CRC_CE("MeshService"));  // 如果有 mesh，我在它之后激活
}
```

Entity 在 `Activate` 时做拓扑排序：`Required` 硬依赖必须先激活、`Dependent` 软依赖如果存在则先激活、`Incompatible` 冲突时直接拒绝激活（Entity 进入 error 状态）。

---

## EBus 进阶

### 基础四个政策（从简单到复杂）

```cpp
class MyBusTraits : public AZ::EBusTraits
{
public:
    // 1. Handler 数量
    static constexpr auto HandlerPolicy = AZ::EBusHandlerPolicy::Multiple;
        // Single - 每地址只能有一个 handler；通常用于 Request Bus
        // Multiple - 任意多个；用于 Notification Bus
        // MultipleAndOrdered - 多个并按 GetOrder() 有序调用

    // 2. 地址数量
    static constexpr auto AddressPolicy = AZ::EBusAddressPolicy::ById;
        // Single - 整条 bus 只一个地址；无 ID
        // ById - 多地址，需 BusIdType（如 EntityId）
        // ByIdAndOrdered - 多地址并按 BusIdType::operator< 有序枚举

    using BusIdType = AZ::EntityId;
};
```

### 同步/队列/线程模型

**EBus 的其他政策**（来自 `EBus.h`）：

| Trait | 类型/值 | 作用 |
|---|---|---|
| `MutexType` | 类型，默认 `AZ::NullMutex` | 事件执行和连接管理的锁；若要跨线程广播，至少 `AZStd::mutex`，支持嵌套事件用 `AZStd::recursive_mutex` |
| `EventQueueMutexType` | 类型，默认同 `MutexType` | 队列添加/取出用的锁（启用队列时才用） |
| `EnableEventQueue` | bool，默认 false | 允许 `QueueBroadcast/QueueEvent` + `ExecuteQueuedEvents` |
| `EventQueueingActiveByDefault` | bool，默认 true | 默认自动接受队列消息；false 则要显式 `AllowFunctionQueuing(true)` |
| `EnableQueuedReferences` | bool，默认 false | 队列中允许引用参数（调用方保障参数生命周期） |
| `LocklessDispatch` | bool，默认 false | true = 广播时不加锁，速度快但不可跨线程改连接 |
| `ConnectionPolicy` | 模板，默认无操作 | hook 连接/断连（例如连上就 immediate 发快照） |

**真实使用**：`AZ::TickBus` 启用了事件队列（`AzCore/Component/TickBus.h`）：

```cpp
class TickEvents : public AZ::EBusTraits {
    static const bool EnableEventQueue = true;
    typedef AZStd::recursive_mutex EventQueueMutexType;  // 允许 OnTick 里再 QueueEvent
};

// 使用：
AZ::TickBus::QueueBroadcast(&AZ::TickEvents::OnTick, dt, now);
// 稍后在主线程某一点：
AZ::TickBus::ExecuteQueuedEvents();
```

### 三种调用语法

```cpp
// Bus 广播（所有地址，所有 handler）
MyBus::Broadcast(&MyInterface::Foo, arg);

// Bus 对某地址的所有 handler
MyBus::Event(entityId, &MyInterface::Foo, arg);

// 带返回值 — Request 常用
float result = 0.f;
MyBus::BroadcastResult(result, &MyInterface::GetValue);
MyBus::EventResult  (result, entityId, &MyInterface::GetValue);

// 遍历 handler（需要自定义聚合）
MyBus::EnumerateHandlers([](MyInterface* h) { /* ... */ return true; });
```

### ConnectionPolicy 小样

自定义 policy 让 handler 一连上就收到历史快照（某些"状态"型 notification 用）：

```cpp
struct MyConnectionPolicy : AZ::EBusConnectionPolicy<MyBus>
{
    static void Connect(typename MyBus::BusPtr& busPtr,
                        typename MyBus::Context& ctx,
                        typename MyBus::HandlerNode& handler,
                        typename MyBus::Context::ConnectLockGuard& lock,
                        const typename MyBus::BusIdType& id = 0)
    {
        EBusConnectionPolicy::Connect(busPtr, ctx, handler, lock, id);
        // 额外：立即推当前状态给新 handler
        handler->OnStateChanged(GetCurrentState());
    }
};
// 在 Traits 里：using ConnectionPolicy = MyConnectionPolicy;
```

### 常见 EBus 死法

1. **忘了 BusDisconnect → 组件析构后再广播 → crash**。习惯 `Activate/Deactivate` 配对写，别等 destructor。
2. **默认 `NullMutex` 下跨线程广播** → 数据竞争。做多线程 bus 明确指定 `MutexType = AZStd::mutex`。
3. **`LocklessDispatch=true` 时在 handler 里 BusDisconnect 自己** → 迭代中破坏链表。不要这样写，用 `QueueFunction`。
4. **handler 的 `On*` 里再发同一个 bus 消息 → 可能无限递归**。`LocklessDispatch` 下更容易崩。

---

## `AZ::Interface<T>` —— 现代单例

用于"进程内只有一个实现者"的系统接口，相比 Single-Handler Request Bus 代码量小、调用开销小、链接干净。

```cpp
// ISaveSystem.h
class ISaveSystem
{
public:
    AZ_RTTI(ISaveSystem, "{<uuid>}");
    virtual ~ISaveSystem() = default;
    virtual bool Save(AZStd::string_view slot) = 0;
};

// 方式 A：手动 Register/Unregister
class SaveSystem : public ISaveSystem
{
    void Activate()   { AZ::Interface<ISaveSystem>::Register(this); }
    void Deactivate() { AZ::Interface<ISaveSystem>::Unregister(this); }
};

// 方式 B：继承 Registrar，构造即注册、析构即注销
class SaveSystem
    : public AZ::Component
    , public AZ::Interface<ISaveSystem>::Registrar
{
    // 自动调用 Register(this)；析构自动 Unregister
};

// 调用
if (auto* svc = AZ::Interface<ISaveSystem>::Get())
    svc->Save("slot0");
```

和 EBus::Single 的区别：

| 维度 | `AZ::Interface<T>` | EBus (Single/Single) |
|---|---|---|
| 调用开销 | 一次 atomic load + 虚函数 | 查 handler 表 + 虚函数 |
| 可广播 / 排序 | ✗ | ✓ |
| 可队列 / 跨线程分发 | ✗ | ✓（启用 event queue） |
| 代码模板样板 | 极少 | 中等 |
| 适用 | 一个进程一个实现 | 可能多订阅者 / 要排序 / 跨线程异步 |

**引擎核心的 Interface 注册点**（阅读学习）：
- `AZ::Interface<AZ::IConsole>` — 在 `ComponentApplication.cpp`
- `AZ::Interface<AZ::NameDictionary>`
- `AZ::Interface<AZ::SettingsRegistryInterface>`
- `AzFramework::SpawnableEntitiesInterface`

---

## Reflection 三件套（深入）

同一个 `Reflect(ReflectContext*)` 会被多个 context 分别调用：

| Context | 作用 | 什么时候检测 |
|---|---|---|
| `SerializeContext` | 磁盘序列化、Prefab/Spawnable 持久化、跨进程传输 | 总是 |
| `EditContext` | Editor 属性面板 UI | 仅 Editor 进程 |
| `BehaviorContext` | 暴露给 Lua/Python/ScriptCanvas | 仅启用脚本系统的进程 |
| `JsonRegistrationContext` | JSON 自定义 serializer | 需 JSON 读写时 |

### SerializeContext + 版本化

```cpp
void Foo::Reflect(AZ::ReflectContext* ctx)
{
    if (auto* sc = azrtti_cast<AZ::SerializeContext*>(ctx))
    {
        sc->Class<Foo, BaseFoo>()
            ->Version(3, &Foo::VersionConverter)   // 🔑 改字段就涨版本
            ->Field("health", &Foo::m_health)
            ->Field("maxHealth", &Foo::m_maxHealth)
            ->Field("team", &Foo::m_team)
            ;
    }
}
```

**VersionConverter 真实签名**：

```cpp
// 接收一个 DataElementNode（旧数据树），返回成功/失败
bool Foo::VersionConverter(
    AZ::SerializeContext& sc,
    AZ::SerializeContext::DataElementNode& node)
{
    // node.GetVersion() 是旧数据的版本号
    if (node.GetVersion() < 2)
    {
        // v1→v2：重命名 "hp" → "health"
        const int idx = node.FindElement(AZ_CRC_CE("hp"));
        if (idx >= 0)
        {
            float value = 0.f;
            node.GetSubElement(idx).GetData<float>(value);
            node.RemoveElement(idx);
            const int newIdx = node.AddElement<float>(sc, "health");
            node.GetSubElement(newIdx).SetData<float>(sc, value);
        }
    }
    if (node.GetVersion() < 3)
    {
        // v2→v3：添加默认 team
        node.AddElementWithData<AZ::u32>(sc, "team", 0);
    }
    return true;
}
```

**`DataElementNode` 常用 API**：
- `GetVersion()` / `SetVersion(n)`
- `GetName()` / `GetNameCrc()`
- `GetNumSubElements()` / `GetSubElement(idx)`
- `FindElement(nameCrc)` — 返回 index 或 -1
- `GetData<T>(outValue)` / `SetData<T>(sc, value)`
- `AddElement<T>(sc, name)` / `AddElementWithData<T>(sc, name, value)`
- `RemoveElement(idx)` / `ReplaceElement(...)`

**关键事实**：**改了字段就必须涨 `Version(n)` 并写 VersionConverter**，不然老 prefab/save 加载会 silently drop data 或 crash。

### EditContext — Editor UI 属性表

核心 Attribute（`AzCore/Serialization/EditContextConstants.inl`）：

| Attribute | 值类型 | 用途 |
|---|---|---|
| `AZ::Edit::Attributes::Category` | string | Editor 分类显示 |
| `AZ::Edit::Attributes::AppearsInAddComponentMenu` | Crc32 | 哪些菜单能 Add 这个组件（`"Game"`, `"Level"`, `"UI"`） |
| `ChangeNotify` | 方法指针 或 Crc32 refresh | 值改变时回调 / 或刷新整个 tree |
| `Visibility` | 方法指针 → bool 或 `ShowChildrenOnly`/`Hide`/`Show` | 动态显隐 |
| `ReadOnly` | bool 或方法 | 只读 |
| `Min` / `Max` / `Step` / `SoftMin` / `SoftMax` | 数值 | 输入限制 |
| `Slider` | UIHandler | 滑块控件 |
| `EnumValue` | `{value, label}` | 下拉框选项（每个值一行） |
| `AutoExpand` | bool | Group 默认展开 |
| `ValueText` / `SuffixText` | string | 显示附加文字 |

UI Handler（控件类型）：

```cpp
->DataElement(AZ::Edit::UIHandlers::Default, &Foo::m_x, "X", "")   // 自动选控件
->DataElement(AZ::Edit::UIHandlers::Slider,  &Foo::m_volume, ...)
->DataElement(AZ::Edit::UIHandlers::ComboBox, &Foo::m_mode, ...)
    ->EnumAttribute(Mode::Idle, "Idle")
    ->EnumAttribute(Mode::Run,  "Run")
->DataElement(AZ::Edit::UIHandlers::MultiLineEdit, &Foo::m_text, ...)
->DataElement(AZ::Edit::UIHandlers::Color,    &Foo::m_color, ...)
->DataElement(AZ::Edit::UIHandlers::Button,   &Foo::m_button, "", "")
```

**Group / 折叠**：

```cpp
ec->Class<Foo>("Foo", "")
  ->ClassElement(AZ::Edit::ClassElements::Group, "Movement")
      ->Attribute(AZ::Edit::Attributes::AutoExpand, true)
  ->DataElement(0, &Foo::m_speed, "Speed", "")
  ->DataElement(0, &Foo::m_accel, "Accel", "")
  ->ClassElement(AZ::Edit::ClassElements::Group, "Health")
  ->DataElement(0, &Foo::m_hp,  "HP",  "")
  ;
```

### BehaviorContext — 暴露到脚本

```cpp
if (auto* bc = azrtti_cast<AZ::BehaviorContext*>(ctx))
{
    bc->Class<Foo>("Foo")
        ->Attribute(AZ::Script::Attributes::Category, "MyGem")
        ->Attribute(AZ::Script::Attributes::Module, "gameplay.foo")   // 决定 Python 路径 azlmbr.gameplay.foo.Foo
        ->Method("Heal",  &Foo::Heal)
        ->Method("Damage", &Foo::Damage, { {"amount", "dmg to apply"} })
        ->Property("health", BehaviorValueProperty(&Foo::m_health))   // getter+setter
        ->Property("maxHealth",
                   [](Foo* f){ return f->m_maxHealth; },              // 自定义 getter
                   [](Foo* f, float v){ f->m_maxHealth = v; })         // 自定义 setter
        ->Constant("MaxTeams", BehaviorConstant(8))
        ->Enum<(int)Mode::Idle>("Mode_Idle")
        ->Enum<(int)Mode::Run>("Mode_Run")
        ;

    bc->EBus<FooNotificationBus>("FooNotificationBus")
        ->Handler<BehaviorFooNotificationBusHandler>()  // 让脚本能"订阅"
        ->Event("OnDied",    &FooNotifications::OnDied)
        ->Event("OnDamaged", &FooNotifications::OnDamaged)
        ;
}
```

关键 `AZ::Script::Attributes`（`AzCore/Script/ScriptContextAttributes.h`）：

| 属性 | 值 | 作用 |
|---|---|---|
| `Category` | string | UI 分类 |
| `Module` | string "a.b.c" | Python 下 `azlmbr.a.b.c.Foo` |
| `Ignore` | bool | 跳过这个成员 |
| `ExcludeFrom` | `ExcludeFlags::List` / `Documentation` / `All` | 从节点面板/文档隐藏 |
| `Deprecated` | bool | 标废弃，调用有警告 |
| `Storage` | `ScriptOwn` / `RuntimeOwn` / `Value` | 对象所有权 |
| `Alias` | string | PEP8 风格的 Python 名字 |
| `Scope` | `Launcher` / `Automation` / `Common` | 在 Editor 还是 Runtime 可见 |
| `Operator` | `Add/Sub/.../ToString/IndexRead/...` | Lua operator overload |

**值类型属性 shortcut**：`BehaviorValueProperty(&Class::member)` 自动创建 getter+setter。

---

## 内存与分配器

两个固定习惯：

```cpp
// 类必须声明自己的 allocator（否则跨模块分配会崩）
class MyThing { public: AZ_CLASS_ALLOCATOR(MyThing, AZ::SystemAllocator); };

// 堆分配一律 aznew，不要裸 new
auto* t = aznew MyThing();
delete t;   // 或者用 AZStd::unique_ptr<MyThing>
```

常用 Allocator：

- `AZ::SystemAllocator` — 通用，默认选它
- `AZ::OSAllocator` — 极底层（用于 Allocator 自身的 bootstrap、不走反射）
- 自定义 Pool Allocator — 性能热路径才考虑

**绝不** `std::vector<T>` / `std::string` 进入引擎存储数据 —— 它们用 system malloc，崩溃和反射都会出问题。一律 `AZStd::`。

---

## Jobs vs Task — 两代并发系统

| 特性 | Jobs (`AzCore/Jobs/`) | Task (`AzCore/Task/`) |
|---|---|---|
| 粒度 | 细粒度，显式 `SetDependent` 链 | 粗粒度 DAG / 立即提交 |
| 调度器 | `JobManager` + work-stealing | `TaskExecutor` + 线程池 |
| 优先级 | s8 [-128, 127] | 枚举 `CRITICAL/HIGH/MEDIUM/LOW` |
| 何时用 | 引擎热路径、固定频 fork-join | 资产加载、Editor 后台作业、一次性异步 |
| 新代码推荐 | 多见于老模块 | 新模块首选 |

### Task 最简用法

```cpp
#include <AzCore/Task/TaskExecutor.h>
#include <AzCore/Task/TaskDescriptor.h>

AZ::TaskDescriptor desc{ "LoadChunk", "assets", AZ::TaskPriority::MEDIUM };
AZ::TaskExecutor::Instance().Submit(desc, []{
    // 在工作线程执行
});
```

### TaskGraph（有依赖）

```cpp
#include <AzCore/Task/TaskGraph.h>
AZ::TaskGraph g{"LevelLoad"};
auto t1 = g.AddTask({"Decompress"},  [&]{ /* ... */ });
auto t2 = g.AddTask({"Deserialize"}, [&]{ /* ... */ });
t1.Precedes(t2);
g.Submit();
```

### Jobs 示例（老风格，仍有效）

```cpp
AZ::JobContext* ctx = AZ::JobContext::GetGlobalContext();
AZ::Job* parent = aznew AZ::JobEmpty(false, ctx);
for (auto& item : items)
{
    AZ::Job* child = AZ::CreateJobFunction([&item]{ process(item); }, true, ctx);
    child->SetDependent(parent);
    child->Start();
}
parent->StartAndWaitForCompletion();
```

---

## Trace / 日志 / Profiler

### 日志宏速查

| 宏 | 等级 | 用途 |
|---|---|---|
| `AZ_TracePrintf("Window", "fmt %d", x)` | Trace (5) | 详细调试信息 |
| `AZ_Printf("Window", "fmt")` | Info (3) | 普通信息 |
| `AZ_Warning("Window", cond, "fmt")` | Warning (2) | 条件假则警告 |
| `AZ_Error("Window", cond, "fmt")` | Error (1) | 条件假则错误（Editor 弹窗） |
| `AZ_Assert(cond, "fmt")` | — | Debug 中断，Release 通常剔除 |
| `AZ_Fatal("fmt")` | — | 不可恢复 |

`"Window"` 是过滤标签。Editor 的日志窗口可按它筛。常用：用 Gem 名 + 子系统，如 `"Multiplayer::Replication"`。

### Profiler

```cpp
#include <AzCore/Debug/Profiler.h>

void MyFunc()
{
    AZ_PROFILE_FUNCTION(Gameplay);     // 自动按函数名作 scope
    // 或者
    {
        AZ_PROFILE_SCOPE(Gameplay, "ExpensiveLoop");
        for (...) { /* ... */ }
    }
    AZ_PROFILE_INTERVAL_START(Gameplay, "Flush", 0);
    DoFlush();
    AZ_PROFILE_INTERVAL_END(Gameplay, "Flush", 0);

    AZ_PROFILE_DATAPOINT(Gameplay, m_entityCount, "Entities");
}
```

`Gameplay` 等是在 `AzCore/Debug/Budget.h` 里注册的 budget 标签。项目可加自己的：

```cpp
AZ_DEFINE_BUDGET(MyGem);   // 放在 cpp 某个 TU 的 namespace scope
```

Profiler 后端可绑 Tracy / Superluminal（编译时宏选），无后端时开销低到可忽略。

---

## Settings Registry（现代版 ini）

`AzCore/Settings/SettingsRegistry.h` 提供 JSON-Pointer 风格访问。

### 合并顺序（越后越高）

```
引擎默认 Registry/*.setreg
  < Gem 的 Registry/*.setreg（按加载顺序）
  < 项目 Registry/*.setreg
  < 项目 Registry/Platform/<os>/*.setreg
  < user/Registry/*.setreg
  < 命令行 --regset "/path/to/key=value"
  < 命令行 --regset-file <path>
```

命名约定：`basename.<specialization1>.<specialization2>.setreg` — 只在 specializations 集合匹配时加载。如 `streamer.editor.windows.setreg` 只在 Editor 进程 + Windows 平台加载。

### 读/写

```cpp
auto* sr = AZ::SettingsRegistry::Get();
AZ::s64 tickRate = 60;
sr->Get(tickRate, "/O3DE/MyGem/TickRate");    // 拿整数
AZStd::string name;
sr->Get(name, "/O3DE/MyGem/Name");            // 拿字符串

sr->Set("/O3DE/MyGem/LastSave", "slot0");      // 写（进程内）

// 复杂结构：反射后直接 GetObject / SetObject
MyConfig cfg;
sr->GetObject(cfg, "/O3DE/MyGem/Config");
```

### 注册 Notifier（值变了就回调）

```cpp
AZ::SettingsRegistryInterface::NotifyEventHandler h;
sr->RegisterNotifier([](const auto& args){
    if (args.m_jsonKeyPath == "/O3DE/MyGem/TickRate") {
        // 重新读取
    }
});
```

### 命令行语法

```
Editor.exe --regset "/O3DE/Debug/Enable=true" --regset-file=override.setreg
```

---

## `AZ::IO::FileIO` vs `AZ::IO::Streamer`

- **FileIOBase**：同步 API，`Open/Read/Close`。轻量，适合小的关键路径文件（CVars、setreg、快速读配置）。
- **Streamer**：异步、带优先级和 deadline、可去重请求、支持流式大资源。资产管线走它。

### FileIO 用法（始终用 alias）

```cpp
auto* io = AZ::IO::FileIOBase::GetInstance();
AZ::IO::HandleType h;
if (io->Open("@user@/save0.bin",
             AZ::IO::OpenMode::ModeRead | AZ::IO::OpenMode::ModeBinary, h))
{
    AZ::u64 size = 0; io->Size(h, size);
    AZStd::vector<char> buf(size);
    io->Read(h, buf.data(), size);
    io->Close(h);
}
```

**别名一览**（由 `AzFramework::Application::SetFileIOAliases` 建立）：

| 别名 | 解析到 |
|---|---|
| `@engroot@` | 引擎根目录 |
| `@projectroot@` | 当前项目根 |
| `@products@` | `Cache/<platform>` — 产物资产 |
| `@user@` | 项目用户数据（存档、profile） |
| `@log@` | `@user@/log` 默认 |
| `@exefolder@` | 当前可执行所在目录 |
| `@gemroot:<gem>@` | 指定 Gem 的根目录 |

### Streamer（异步读大文件）

```cpp
#include <AzCore/IO/Streamer/Streamer.h>

auto* streamer = AZ::Interface<AZ::IO::IStreamer>::Get();
auto req = streamer->Read(
    "@products@/levels/L1.pak",  // 路径
    targetBuffer, targetSize,     // 目标
    fileSize,                     // 期望字节数
    AZStd::chrono::milliseconds(16),  // deadline
    AZ::IO::IStreamerTypes::s_priorityHigh);
streamer->SetRequestCompleteCallback(req,
    [](AZ::IO::FileRequestHandle r){ /* ... */ });
streamer->QueueRequest(req);
```

---

## `AZ::Name` 与 Uuid

### AZ::Name — 驻留字符串

```cpp
AZ::Name tag("Enemy");              // 运行时构造（查字典）
AZ::Name weapon = AZ::Name::FromStringLiteral("Sword", nullptr);  // 静态优先

// O(1) 比较
if (tag == weapon) { ... }

// 取 hash
auto h = tag.GetHash();
auto sv = tag.GetStringView();
```

所有 `AZ::Name` 共享一个 `NameDictionary`（全局单例）。线程安全：构造/复制/比较都安全。

### Uuid

用于 RTTI / 反射 / 资产 ID 的唯一标识。

```cpp
AZ::Uuid u = AZ::Uuid::CreateRandom();
AZ::Uuid v = AZ::Uuid::CreateString("{12345678-1234-1234-1234-1234567890AB}");
AZ::Uuid t = azrtti_typeid<MyClass>();
```

**重要**：`AZ_COMPONENT(MyComp, "{uuid}")` / `AZ_RTTI(..., "{uuid}", ...)` 里的 Uuid 必须独一无二。重复会让 SerializeContext 注册 "silently" 覆盖前面的，出现加载错乱。

---

## 常见陷阱（AzCore 层）

1. **字段加减改类型不涨 `Version(n)`** → 已有 prefab/save 反序列化 silent 丢字段或崩。
2. **`AZ_Assert(DoX(), "…")`** → `DoX()` 在 Release 构建被整个表达式剔除，别靠副作用。
3. **Reflect 里 `azrtti_cast` 为 nullptr 仍访问成员** → 某些 context 没构造（如 GameLauncher 不开 EditContext），分支必判 null。
4. **跨 Gem include 具体组件头** → 构建图上 Gem 变"硬依赖"；改用 `*RequestBus` 或 `AZ::Interface<ISomething>`。
5. **`EntityId` 当 bool 判 `if (id)`** → EntityId 内部是 u64，可能不是 0 但无效。用 `id.IsValid()`。
6. **EBus handler 在回调里 `BusDisconnect(self)`** → 迭代中改容器，`LocklessDispatch` 下立刻崩。
7. **`AZStd::string` 按值塞 EBus 方法** → 频繁拷贝；改 `AZStd::string_view` 或 `const AZ::Name&`。
8. **多 `Reflect` 函数分布在多个 TU** → 只有第一个执行的会生效（同类型注册不可覆盖）。反射集中到一处。
9. **`Activate` 里 `BusConnect` 顺序反了** → 某些 bus 连接时会立即回 sync 快照，此时依赖的其它 bus 还没连；确认"回调里只用已初始化的数据"。

继续：[03_azframework.md](03_azframework.md) / [11_conventions_and_patterns.md](11_conventions_and_patterns.md)
