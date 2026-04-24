# 09 · 脚本系统（ScriptCanvas / Lua / Python）深入

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## 为什么专门有这一章

**脚本是 O3DE 最大的"生产力杠杆"**。三条路线都有各自的应用：

| 脚本 | 用途 | 不重编 C++ 就能改 | 适用进程 |
|---|---|---|---|
| **Lua** | 运行时游戏逻辑（组件脚本、关卡脚本） | ✓（改 `.lua` → AP 编译 `.luac` → 秒生效） | Runtime + Editor |
| **ScriptCanvas (SC)** | 可视化节点编程；美术/策划友好 | ✓（改图保存即生效） | Runtime + Editor |
| **Python** | Editor 自动化、AP 管线、测试脚本 | ✓（重新 `import` 即可） | **仅 Editor / tools** |

三者**共享 `AZ::BehaviorContext`** 作为 "C++ → 脚本" 的唯一出口：反射一次 → 三种语言都能用。

**性能级心智模型**：C++ 原语做热路径 → 脚本拼接调用 → 快速迭代 → 稳定后考虑固化到 C++。

---

## BehaviorContext — 三路脚本的总源

路径：[Code/Framework/AzCore/AzCore/RTTI/BehaviorContext.h](../Code/Framework/AzCore/AzCore/RTTI/BehaviorContext.h)

### Class<T>() 完整链式方法

```cpp
if (auto* bc = azrtti_cast<AZ::BehaviorContext*>(ctx))
{
    bc->Class<Foo>("Foo")                          // name 显示名（留空用 C++ 类名）
      ->Attribute(AZ::Script::Attributes::Category, "Gameplay")

      // 构造
      ->Constructor()                               // 无参
      ->Constructor<int, float>()                  // (int,float) 版本

      // 普通方法
      ->Method("Heal", &Foo::Heal)
      ->Method("Damage", &Foo::Damage,
               { { {"amount", "Damage amount"} } })  // 参数名+描述

      // 属性（自动 getter/setter）
      ->Property("health", BehaviorValueProperty(&Foo::m_health))

      // 属性（自定义 getter/setter 或只读）
      ->Property("maxHealth",
                 [](Foo* f){ return f->m_maxHealth; },      // getter
                 [](Foo* f, float v){ f->m_maxHealth = v; }) // setter；nullptr 则只读

      // 常量（运行时不可改）
      ->Constant("MaxTeams", BehaviorConstant(8))

      // 枚举（按值分别注册）
      ->Enum<(int)Mode::Idle>("Mode_Idle")
      ->Enum<(int)Mode::Run >("Mode_Run")

      // Operator overload（Lua 用）
      ->Method("Add", &Foo::operator+)
          ->Attribute(AZ::Script::Attributes::Operator,
                      AZ::Script::Attributes::OperatorType::Add)
      ;
}
```

### EBus<T>() 注册（让脚本调/订阅 EBus）

```cpp
// Request Bus：脚本调（发消息）
bc->EBus<FooRequestBus>("FooRequestBus")
    ->Attribute(AZ::Script::Attributes::Category, "Gameplay")
    ->Event("GetHealth", &FooRequests::GetHealth)
    ->Event("SetHealth", &FooRequests::SetHealth)
    ;

// Notification Bus：脚本订阅（收消息）
bc->EBus<FooNotificationBus>("FooNotificationBus")
    ->Handler<BehaviorFooNotificationBusHandler>()   // 见下，handler adapter
    ->Event("OnDied",    &FooNotifications::OnDied)
    ->Event("OnDamaged", &FooNotifications::OnDamaged)
    ;
```

### Handler Adapter — 让脚本实现 EBus

C++ 端要写一个 adapter 类桥接脚本 handler 和 C++ EBus：

```cpp
class BehaviorFooNotificationBusHandler
    : public FooNotificationBus::Handler
    , public AZ::BehaviorEBusHandler
{
public:
    // 声明绑定 + Uuid + Allocator + 所有事件名
    AZ_EBUS_BEHAVIOR_BINDER(
        BehaviorFooNotificationBusHandler,
        "{handler-uuid}",
        AZ::SystemAllocator,
        OnDied, OnDamaged);

    void OnDied() override { Call(FN_OnDied); }
    void OnDamaged(float dmg) override { Call(FN_OnDamaged, dmg); }
};
```

`FN_OnDied` 等是宏自动生成的索引常量。`Call(FN_..., args...)` 会跨到脚本侧执行。

### AZ::Script::Attributes 完整清单

来自 [Code/Framework/AzCore/AzCore/Script/ScriptContextAttributes.h](../Code/Framework/AzCore/AzCore/Script/ScriptContextAttributes.h)：

| 属性 | 值类型 | 作用 |
|---|---|---|
| `Category` | string | Editor 节点面板分类；Python `__doc__` 分组 |
| `Module` | string "a.b" | Python 下成为 `azlmbr.a.b.Foo` |
| `ToolTip` | string | 鼠标悬浮说明 |
| `Ignore` | bool | 完全跳过此成员 |
| `Deprecated` | bool | 调用时 warn |
| `ExcludeFrom` | `List(1) / Documentation(2) / All(3)` | 从 SC 节点面板/文档隐藏 |
| `Alias` | string | 提供 PEP8 风格的 Python 名字 |
| `ClassNameOverride` | string | 覆盖脚本里显示的类名 |
| `Storage` | `ScriptOwn / RuntimeOwn / Value` | 对象所有权决定是否 GC |
| `Scope` | `Launcher(1<<0) / Automation(1<<1) / Common(3)` | Editor 运行 / 自动化脚本 / 两者 |
| `Operator` | `OperatorType::*` | 让 Lua 的 `+`/`*`/`[]`/`#` 等 overload |
| `AzEventDescription` | struct | 为 AZ::Event 生成脚本可见属性 |
| `ConstructorOverride` | Method | 自定义脚本端构造（如需要 factory） |

---

## Lua 脚本

### 运行时路径

```
<Name>.lua (源)
  → AP 触发 LuaBuilder（Gems/LmbrCentral/Code/Source/Builders/LuaBuilder/）
  → <Name>.luac (字节码) + fingerprint
  → 运行时 ScriptComponent 加载 .luac
  → ScriptContext::Load → lua_pcall → 脚本表入栈
  → 每 tick 调 OnTick 之类
```

### `ScriptComponent` 与约定

游戏里用法：给 Entity 加 **"Script" 组件** → 指定 `.lua` 资产 → Editor 读取脚本的 `Properties` 表生成属性面板。

Lua 模板：

```lua
local Mover = {
    -- 这些字段会出现在 Editor 属性面板（反射到 SerializeContext）
    Properties = {
        Speed = { default = 5.0, description = "Units per second" },
        Target = { default = EntityId() },
        DebugDraw = { default = false },
    }
}

function Mover:OnActivate()
    -- self.entityId 是当前 Entity 的 ID（自动注入）
    -- self.Properties 是上面的属性表（已被 Editor 填值）

    -- 订阅 TickBus
    self.tickHandler = TickBus.Connect(self, self.entityId)
end

function Mover:OnDeactivate()
    if self.tickHandler then self.tickHandler:Disconnect() end
end

function Mover:OnTick(deltaTime, timePoint)
    -- 调 C++ 反射方法
    local pos = TransformBus.Event.GetWorldTranslation(self.entityId)
    pos.x = pos.x + self.Properties.Speed * deltaTime
    TransformBus.Event.SetWorldTranslation(self.entityId, pos)
end

return Mover
```

**关键约定**：
- 模块必须 `return` 一张表。
- 方法用冒号定义（`function Mover:Foo()` 等价 `function Mover.Foo(self, ...)`）。
- `self.entityId` 和 `self.Properties` 是引擎自动注入的。
- `OnActivate/OnDeactivate` 对应 C++ `Component::Activate/Deactivate`。

### 调用 C++

所有反射过的类 / EBus 直接可见：

```lua
-- 类：静态方法
local v = Vector3(1, 2, 3)
v:Normalize()                           -- 冒号调非 static，点调 static
local dot = Vector3.Dot(a, b)           -- static

-- 常量 / 枚举
if mode == Mode.Run then ... end

-- EBus 调用
TransformBus.Event.SetWorldTranslation(entityId, v)       -- Event：带 ID
HealthRequestBus.Broadcast.ApplyDamage(10)                -- Broadcast：不带 ID
local hp = HealthRequestBus.Event.GetHealth(entityId)     -- 有返回值

-- EBus 订阅（需要反射了 Handler<> 的 Notification Bus）
function MyScript:OnActivate()
    self.healthListener = HealthNotificationBus.Connect(self, self.entityId)
end
function MyScript:OnHealthChanged(newHp)  -- 方法名 = Event 名
    ...
end
```

### `.lua` → `.luac` Builder

实现在 [Gems/LmbrCentral/Code/Source/Builders/LuaBuilder/](../Gems/LmbrCentral/Code/Source/Builders/LuaBuilder/)。关键：
- Fingerprint 追踪源文件 + 用到的 BehaviorContext 版本，反射改了 builder 自动重跑。
- 产物 `.luac` 是平台无关字节码，跨平台包装。

### LuaIDE 调试器

独立工具：[Code/Tools/LuaIDE/](../Code/Tools/LuaIDE/)。
- 连上 Editor / Launcher（`lua_enableDebug 1`）。
- 断点、单步、变量查看、调用栈。
- 运行时内建 `AZ::ScriptContextDebug` 支持（`Code/Framework/AzCore/AzCore/Script/ScriptContextDebug.h`）。

---

## ScriptCanvas（核心重点）

可视化编程：节点图保存 `.scriptcanvas` 资产，AP 编译到运行时可执行形式。

### 分层

```
┌────────────────────────────────────────────────────────┐
│ ScriptCanvas (Gems/ScriptCanvas/)                      │
│   运行时 Node / Graph / Slot / Datum / Execution        │
└────────────────────────────────────────────────────────┘
                      ▲
                      │ 基于
┌────────────────────────────────────────────────────────┐
│ GraphModel (Gems/GraphModel/)                          │
│   图的数据模型（SlotDefinition, ConnectionDefinition）    │
└────────────────────────────────────────────────────────┘
                      ▲
                      │ UI 渲染
┌────────────────────────────────────────────────────────┐
│ GraphCanvas (Gems/GraphCanvas/)                        │
│   通用节点画布控件（Qt widget）— 供 SC / Landscape / …    │
└────────────────────────────────────────────────────────┘
```

### 资产与编译

```
*.scriptcanvas (xml - 作者在 Editor 里编辑)
  → ScriptCanvasBuilder
  → 两条路径：
       a) 解释执行（旧）— 直接序列化图，运行时 interpreter
       b) 翻译到 Lua （新，"Translation"）— 图转 Lua 源 → LuaBuilder → .luac
```

Translation 路径带来：性能接近 Lua、堆栈可读、调试用 LuaIDE 即可。细节见 Gems/ScriptCanvas/Code/Include/ScriptCanvas/Grammar/。

### 节点的三种来源

1. **手写 C++ Node** — 派生 `ScriptCanvas::Node`。用于复杂控制流、高性能。
   ```cpp
   class MyCustomNode : public ScriptCanvas::Node {
       SCRIPTCANVAS_NODE(MyCustomNode);      // 宏：反射 + 注册
       void OnInputSignal(const SlotId&) override;
       void OnInit() override;
   };
   ```
2. **自动反射 Node** — `ScriptCanvas::Nodeable` 基础设施从 BehaviorContext 自动生成节点（`ReflectionNodeFactory`）。零样板，跟着 C++ 自动更新。**大部分 API 调用走这条**。
3. **Function Node / Subgraph** — 作者把一段图封装成可复用 "函数"，跨图调用。

### Slot / Connection 模型

- **Execution Slot**（红色）：`In` / `Out`，决定执行流程。
- **Data Slot**（蓝/绿等色）：带 `Datum`（类型化值），连接后数据自动拷贝。

一次执行流程：节点 A 的 `Out` → 节点 B 的 `In` → B::OnInputSignal → B 读 data slot 算结果 → B 的 `Out` 发出。

### Script Events — 最强跨语言通讯

`.scriptevents` 是**独立的"契约资产"**：定义一组命名事件 + 参数。生成后：

- **C++** 可订阅/发送（反射成 EBus）
- **Lua** 同上（`MyEventBus.Broadcast.Fire(x)`）
- **ScriptCanvas** 自动有 Sender / Receiver 节点

示例 `PlayerEvents.scriptevents`（XML 简化）：

```xml
<ScriptEvent>
    <name>PlayerEvents</name>
    <method>
        <name>OnPlayerDamaged</name>
        <returnType>void</returnType>
        <parameters>
            <parameter name="amount" type="float"/>
        </parameters>
    </method>
    <method>
        <name>OnPlayerDied</name>
        <returnType>void</returnType>
    </method>
</ScriptEvent>
```

保存后 AP 生成桥接代码，**无需重启 Editor**。三种语言任意混用订阅/发送。

### ScriptCanvas 热重载

改图 → Ctrl+S → AP 编译 → AssetBus::OnAssetReloaded → 挂 `.scriptcanvas` 的 Entity 自动换新图。**不用重启 Editor / 游戏**。

---

## Python (Editor 内)

### 运行架构

Gem [EditorPythonBindings](../Gems/EditorPythonBindings/) 在 Editor 启动时：

1. 初始化 Python 3 解释器（嵌入）。
2. 扫 `AZ::BehaviorContext`，把所有反射类自动包装成 Python 对象 → 放入 `azlmbr.<module>.<Class>`。
3. 运行 `bootstrap.py`（项目 / Gem 提供）。

命名空间映射：

```cpp
->Attribute(AZ::Script::Attributes::Module, "editor.entity")
// → Python:  azlmbr.editor.entity.YourClass
```

没有 `Module` 属性的类落到 `azlmbr.globals` 或默认命名空间。

### bus 调用语法（关键）

```python
import azlmbr.bus as bus
import azlmbr.editor as editor
import azlmbr.entity as entity

# 1) Broadcast（无 ID）
editor.ToolsApplicationRequestBus(bus.Broadcast, 'SaveEntitiesToStream', outStream)

# 2) Event（有 ID）— 第三参为 bus id
pos = azlmbr.bus.TransformBus(bus.Event, 'GetWorldTranslation', entity_id)

# 3) 带返回值：函数直接 return；Python 侧做成 tuple 如果多返回

# 4) Broadcast 结果：同 Event，没 id
version = editor.EditorSettingsAPIBus(bus.Broadcast, 'GetVersion')
```

API 调用约定：**第一参 bus 名、第二参方向常量、第三参方法名**，后面是方法参数（`Event` 模式第一个额外参数是 bus id）。

### 常见 Editor 自动化片段

```python
import azlmbr
import azlmbr.editor as editor
import azlmbr.entity as entity
import azlmbr.bus as bus

# 创建空 Entity
new_id = editor.ToolsApplicationRequestBus(bus.Broadcast, 'CreateNewEntity', entity.EntityId())

# 改名
editor.EditorEntityAPIBus(bus.Event, new_id, 'SetName', 'HeroSpawn')

# 加组件
type_ids = editor.EditorComponentAPIBus(
    bus.Broadcast, 'FindComponentTypeIdsByEntityType',
    ['Transform', 'Mesh Component'],
    entity.EntityType_Game)
editor.EditorComponentAPIBus(bus.Broadcast, 'AddComponentsOfType', new_id, type_ids)

# 保存 Prefab
pref = azlmbr.prefab.PrefabPublicRequestBus(
    bus.Broadcast, 'CreatePrefabInMemory', [new_id], '/my/prefab.prefab')
```

### QtForPython — 直接写 PySide2 GUI

Gem [QtForPython](../Gems/QtForPython/) 把 PySide2 装进 Editor Python 环境，脚本可直接：

```python
from PySide2 import QtWidgets, QtCore

class MyTool(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        ...

dlg = MyTool(); dlg.show()
```

和 Editor 主窗口共享事件循环。

### PythonAssetBuilder — 用 Python 写 AssetBuilder

Gem [PythonAssetBuilder](../Gems/PythonAssetBuilder/) 允许写 `.py` 文件作为 Asset Builder，而不用整 C++ 编译：

```python
# my_builder.py
def create_jobs(job_data):
    return [{'platform': 'pc', 'job_key': 'Convert', 'fingerprint': '1'}]

def process_job(job_data):
    src = job_data['source_file']
    dst = job_data['output_path'] + '/converted.json'
    # 用 Python 库处理，调 azlmbr API，写产物
    ...
    return {'status': 'ok', 'products': [dst]}
```

对原型阶段的 asset 流水非常快。稳定后可固化到 C++。

### Python 脚本入口

```
<Project>/Editor/Scripts/bootstrap.py     # Editor 启动时自动跑
<Gem>/Editor/Scripts/*.py                 # Gem 提供的脚本
Editor → Tools → Python Console           # 交互式 REPL
Editor → Tools → Python Scripts           # 文件浏览器
```

### Action Manager 注册（Python 版）

```python
import azlmbr.action as action

action.ActionManagerInterface.register_action(
    context_id='o3de.context.editor',
    action_id='mygem.action.export',
    name='Export All',
    description='Export all levels to JSON',
    category='MyGem',
    callback=lambda: my_export_func()
)
action.MenuManagerInterface.add_action_to_menu(
    'o3de.menu.tools', 'mygem.action.export', 1000)
```

---

## 为什么脚本"加速开发"（具体机制）

### 热重载路径

```
Lua  /  ScriptCanvas  /  ScriptEvents
    ↓ 改
  Ctrl+S
    ↓ AP 检测变化
  Builder 重新编译（毫秒级）
    ↓ 产物写入 Cache/
  AssetBus::OnAssetReloaded
    ↓ 自动通知
  运行时 ScriptComponent / ScriptCanvasComponent 换内容
    ↓
  Editor 场景里立即生效，不需要重启
```

### C++ 开发 vs 脚本开发的迭代时间

| 改动类型 | C++ | Lua | ScriptCanvas | Python (Editor) |
|---|---|---|---|---|
| 修改一个算法常数 | 重编 (~30s-数分钟) + Editor 重启 | 秒级 | 秒级 | 按 F5 重 import |
| 加一个方法 | 重编 + 反射变动 + 可能资产 reproc | 秒级 | 秒级（如果调已有 C++ 方法） | 秒级 |
| 改组件新字段 | 重编 + Version 升 + 资产迁移 | N/A | N/A | N/A |
| 大改架构 | 小时级 | 不适合 | 不适合 | 不适合 |

### 推荐工作流

1. **C++ 暴露系统原语 + 稳定数据结构**（反射到 BehaviorContext）。
2. **Lua / ScriptCanvas 组合 + 快速 tweak**。
3. **Python 做 Editor 工具和 batch 操作**（生成资产、校验、批量修改）。
4. **ScriptEvents 做跨组件/跨语言的通讯契约**（比写 EBus 接口快）。
5. 稳定后再决定：继续脚本化 or 固化到 C++。

---

## AI 写脚本反射代码时的关键 checklist

1. **两个 cast 分支不可少**：
   ```cpp
   if (auto* sc = azrtti_cast<AZ::SerializeContext*>(ctx)) { /* 序列化 */ }
   if (auto* bc = azrtti_cast<AZ::BehaviorContext*>(ctx)) { /* 脚本 */ }
   ```
2. **Method 可能有重载歧义**：用 `static_cast<RetType(Class::*)(Args...)>(&Class::Foo)` 消歧。
3. **`->Attribute(AZ::Script::Attributes::Module, "x.y")` 决定 Python 模块路径**，别忘加。
4. **`BehaviorValueProperty` 适合公共字段**，私有字段用 lambda getter/setter。
5. **EBus 反射后 Handler adapter 要用 `AZ_EBUS_BEHAVIOR_BINDER` 宏**声明所有事件名。
6. **写 Lua 调 C++ method 时注意 `.Event` vs `.Broadcast` vs 静态调用**。
7. **Python `bus.Event/Broadcast` 的参数顺序**：bus 名、方向、方法名、[bus id]、args...。
8. **别在 Reflect 函数里做 IO 或分配资源** — 它只执行一次，是"声明"。

---

## 常见坑

1. **BehaviorContext 忘反射** → 脚本侧 `nil` / `AttributeError`。`Reflect` 里加上 `azrtti_cast<BehaviorContext*>` 分支。
2. **Lua 方法名大小写错** → Lua 端严格匹配 C++ 反射名；用 `PascalCase`。
3. **ScriptCanvas 节点找不到** → 没反射 `Category`，或 `ExcludeFrom=List` 被隐藏，或 Gem 没 rebuild。
4. **Python `ImportError: No module named azlmbr`** → 脚本跑在外部 python 解释器里了；`azlmbr` 只在 Editor 嵌入的 python 内存在。
5. **Lua 改动没生效** → AP 没编译（看 AP 状态），或场景 Entity 没重激活。
6. **ScriptCanvas 图保存后行为错** → Translation 模式下可能要 "File → Compile Graph"，或重跑 AP。
7. **Python 回调触发时主线程安全性** → 默认在主线程执行，但如果你用 `threading.Thread` 起后台，**不要直接碰 Editor Entity API**，要 post 回主线程。
8. **ScriptEvents 改签名**（加/删参数）→ 现有调用者和订阅者都要重新编译；老 Prefab 里的 ScriptCanvas 节点可能 invalidate。

继续：[10_networking_physics.md](10_networking_physics.md) / [12_cookbook_recipes.md](12_cookbook_recipes.md)
