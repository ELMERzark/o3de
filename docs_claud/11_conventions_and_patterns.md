# 11 · 代码约定与常用模式

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

> 这是一份"给其他 AI 的风格守则"。希望输出代码时 AI 照这个来，而不是沿用它默认的 STL 习惯。

## 命名

| 规则 | 例 |
|---|---|
| 类 / 结构 / 枚举 | `PascalCase` — `PlayerController`, `HealthState` |
| 函数 / 方法 | `PascalCase` — `GetHealth()`, `Activate()` |
| 变量 | `camelCase` — `localIndex`, `worldTm` |
| 成员变量 | `m_` 前缀 — `m_health`, `m_entity` |
| static 成员 | `s_` 前缀 |
| 全局 / TU-local | `g_` 前缀 |
| 常量 | `PascalCase` — `DefaultSpeed`（constexpr / static const） |
| 宏 | `UPPER_SNAKE_CASE` — `AZ_ASSERT` |
| 命名空间 | `PascalCase` — `namespace AzFramework` |
| 接口类 | 前缀 `I` — `ISaveSystem` |
| EBus 类 | 行为总线以 `Request` / `Notification` 结尾 — `TransformRequests` |

**不要**：匈牙利前缀、`_foo`（下划线开头留给实现/编译器）、`snake_case` 函数（除非是绑定到 Python 后的自动转换）。

## 头文件

```cpp
#pragma once   // 一律用 pragma once，不用传统 include guard

#include <AzCore/Component/Component.h>
#include <AzCore/std/string/string.h>

namespace MyGem
{
    class Foo final
    {
        ...
    };
}
```

- 顶层 namespace 统一按 Gem / 子系统（`AzCore`, `AzFramework`, `MyGem`）。
- **不要** `using namespace` 在头文件里。
- 内部辅助类放匿名命名空间（cpp 里）。
- `.inl` 用于模板实现 / inline 重要函数（然后在 `.h` 末尾 include）。

## 智能指针 / 所有权

| 用途 | 选 |
|---|---|
| 独占所有权 | `AZStd::unique_ptr<T>` |
| 共享所有权 | `AZStd::shared_ptr<T>` |
| 非所有 raw | `T*` （生存期由上下文保证） |
| 资产引用 | `AZ::Data::Asset<T>` |
| Entity 引用 | `AZ::EntityId`（**永远不要持有 `AZ::Entity*` 跨越 Activate 边界**） |

> 持有 `Entity*` 几乎总是 bug；Entity 可能被销毁、重载、移动场景。**持 `EntityId`，用时查**。

## 容器

| 需求 | 用 |
|---|---|
| 动态数组 | `AZStd::vector<T>` |
| 固定小数组 | `AZStd::array<T, N>` |
| 哈希表 | `AZStd::unordered_map<K,V>` / `unordered_set<T>` |
| 按序表 | `AZStd::map<K,V>` |
| 链表 | `AZStd::list<T>` / `intrusive_list<T>` |
| 字符串 | `AZStd::string` (owned) / `AZStd::string_view` (non-owning) |
| 驻留字符串 | `AZ::Name` |
| 可选值 | `AZStd::optional<T>` |

**不要**混用 `std::vector` / `std::string` / `std::map`；它们走系统默认 allocator，和 AZStd 的 `SystemAllocator` 互不兼容。

## 错误处理

O3DE **不抛 C++ 异常**（构建开了 `/EHsc` 但业务代码禁用）。三种办法：

1. **`AZ::Outcome<Success, Error>`**（推荐，显式）：
   ```cpp
   AZ::Outcome<Handle, AZStd::string> OpenFile(AZStd::string_view p)
   {
       if (!Exists(p)) return AZ::Failure(AZStd::string::format("no such file: %.*s", AZ_STRING_ARG(p)));
       return AZ::Success(HandleFor(p));
   }

   auto r = OpenFile(path);
   if (!r.IsSuccess()) { AZ_Error("IO", false, "%s", r.GetError().c_str()); return; }
   auto h = r.TakeValue();
   ```
2. **bool + out 参数**（遗留代码常见）：
   ```cpp
   bool TryGetThing(int id, Thing& out);
   ```
3. **`AZ_Error` / `AZ_Warning`** 当"可容忍的失败"。

## 断言 vs 错误

| 场景 | 用 |
|---|---|
| 不变式（正常情况下绝对不会发生） | `AZ_Assert(cond, "...")` |
| 用户可触发的错误 | `AZ_Error("Window", cond, "...")` |
| 可疑但可继续 | `AZ_Warning("Window", cond, "...")` |
| 诊断信息 | `AZ_TracePrintf("Window", "...")` |

**`AZ_Assert` 的条件表达式 Release 构建下会被剔除** —— 不要依赖副作用（见 [06](06_build_and_cmake.md)）。

## 日志 "Window"

第一个字符串参数是 "window"，用作过滤标签。约定：

- Gem 自己：`"MyGem"` 或 `"MyGem::Foo"`（按子系统细分）
- 框架系统：参考对应模块（`"AssetProcessor"`, `"Script"`, `"Physics"`）

Editor/Launcher 日志文件里可以按 window 过滤。

## `AZ_RTTI` / `AZ_TYPE_INFO` / `AZ_CLASS_ALLOCATOR`

写一个可反射 / 有生命周期的类基本都是这套：

```cpp
class Foo
    : public Base
{
public:
    AZ_RTTI(Foo, "{uuid}", Base);
    AZ_CLASS_ALLOCATOR(Foo, AZ::SystemAllocator);
    // ...
};
```

组件则是：

```cpp
class MyComponent : public AZ::Component
{
public:
    AZ_COMPONENT(MyComponent, "{uuid}");  // 已经包含 RTTI + Allocator
};
```

用 Editor 菜单 **Edit → Generate UUID** 或 `python/python.bat -c "import uuid; print(uuid.uuid4())"` 生成 Uuid。

## 常见反射 attribute

```cpp
->DataElement(AZ::Edit::UIHandlers::Slider, &Foo::m_health, "Health", "")
    ->Attribute(AZ::Edit::Attributes::Min, 0.f)
    ->Attribute(AZ::Edit::Attributes::Max, 100.f)
    ->Attribute(AZ::Edit::Attributes::Step, 1.f)
    ->Attribute(AZ::Edit::Attributes::ChangeNotify, &Foo::OnHealthChanged)
    ->Attribute(AZ::Edit::Attributes::Visibility, &Foo::IsHealthVisible)
    ->Attribute(AZ::Edit::Attributes::ReadOnly, true)
    ->Attribute(AZ::Edit::Attributes::SoftMin, 10.f)
;
```

枚举显示为下拉框：

```cpp
->DataElement(AZ::Edit::UIHandlers::ComboBox, &Foo::m_mode, "Mode", "")
    ->EnumAttribute(Foo::Mode::Idle,    "Idle")
    ->EnumAttribute(Foo::Mode::Running, "Running")
```

## EBus 使用惯例

- **Notification Bus** 是 `Multiple`/`ById`，名以 `Notifications` 结尾。
- **Request Bus** 是 `Single`/`ById` 或 `Single`/`Single`，名以 `Requests` 结尾。
- 命名成对：`TransformRequests` / `TransformNotifications`（两个 bus）。
- 把 bus trait + handler 派生放同一个 `*Bus.h`。
- **不要**在 handler 的 `On*()` 回调里断开自己再广播 —— 迭代中修改容器 → 崩溃风险。

## 单例 / 服务

不推荐 Singleton。推荐：

1. **SystemComponent + EBus**（传统）
2. **`AZ::Interface<ISomething>`**（推荐，上 `Register/Unregister`）
3. **`AZ::Module` 构造时 insert descriptor**（注册机制，不是单例）

## 线程模型

- **主线程**跑 tick、Editor UI、反射系统；
- **AssetManager** 和 Jobs / Task 系统用工作线程；
- **渲染线程**由 Atom 管（通常 RPI 派发）。

规则：

- 反射 (`SerializeContext`) 是 MT-safe 读，但**构造时单线程注册**。
- `AZ::Data::AssetBus::Handler::OnAssetReady` 在主线程派发（AssetManager 会 marshal）。
- EBus 的线程政策看 `EBusTraits::LocklessDispatch` / `MutexType` —— 默认无锁，广播方**得**在同线程用。
- 写跨线程代码用 `AZStd::mutex` / `AZStd::atomic`（等同 std）或 `AzCore/Task/`。

## 字符串与 CRC

`AZ_CRC_CE("SomeString")` = 编译期 32-bit CRC。大量"服务名"/"tag"用这个做轻量标识：

```cpp
services.push_back(AZ_CRC_CE("TransformService"));
```

不要使用旧的 `AZ_CRC("Str", 0xdeadbeef)`（已弃用，后一个参数是运行时对拍用的）。

## 文件 IO

```cpp
auto* fileIo = AZ::IO::FileIOBase::GetInstance();
AZ::IO::HandleType f;
if (fileIo->Open("@user@/savegame.bin", AZ::IO::OpenMode::ModeRead | AZ::IO::OpenMode::ModeBinary, f))
{
    // ...
    fileIo->Close(f);
}
```

- 路径**一律用别名**：`@engroot@`（引擎根）、`@projectroot@`（项目根）、`@products@`（Cache）、`@user@`（用户写入）、`@log@`。
- **不要**直接 `std::ifstream` —— 无法跨平台、在 Android / iOS 上会坏。

## Prefab / Spawnable 使用

组件对 Entity 的引用持 `AZ::EntityId`；对 spawnable 持 `AZ::Data::Asset<AzFramework::Spawnable>`。运行时实例化见 [03_azframework.md](03_azframework.md) 的 Spawnable 节。

## 注释与文档

- 公共 API 的头上放 `//! ...` Doxygen 摘要（一行）；复杂函数加 `/*! ... */`。
- 实现细节**不要**在 cpp 顶部搞一大段"历史与动机"。commit message / PR 更合适。
- TODO 形式：`// TODO(name): ...` 或 `// TODO(github-issue-id): ...`。

## 格式

- 缩进 4 空格；无 tab。
- 大括号**另起一行**（Allman），包括函数、命名空间、类、语句块。
- 行宽建议 120。
- `if (cond)` 后面即便单句也要花括号。

仓库有 `.clang-format` —— 在提交前可 `clang-format -i <file>` 跑一下；贴近现有风格。

## 最常见的"AI 会犯的"错误

1. 使用 `std::*` 容器而不是 `AZStd::*`。
2. 忘 `AZ_CLASS_ALLOCATOR` → 类能编过但跨模块分配崩。
3. 在 `.h` 里写 `using namespace AZ;`。
4. 在 Editor 组件里 include 运行时 `.cpp` 或反之。
5. 对 Uuid 复制粘贴。
6. `ClientOnly` 代码加进 `*.Private`（运行时模块）而不是 `*.Editor.Private`。
7. `GetRequiredServices` 声明依赖但 Gem 里没启用相应组件，运行时 Activate 失败没看 log 就蒙了。
8. 把 `EntityId` 当做 bool 判断（`if (id)` —— `EntityId` 可能不是 0 但不 valid；要 `id.IsValid()`）。

继续：[12_cookbook_recipes.md](12_cookbook_recipes.md)。
