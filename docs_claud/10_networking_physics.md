# 10 · 网络与物理（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

本章的网络部分是**写 O3DE 联机游戏的主菜**。物理部分在最后。

---

# 第一部分 · 网络

## 层次结构

```
┌─────────────────────────────────────────────────────────────┐
│ 游戏组件 (派生自 MultiplayerComponent)                        │
│   NetworkTransformComponent / NetworkMovementComponent 等     │
└─────────────────────────────────────────────────────────────┘
                            ▲
┌─────────────────────────────────────────────────────────────┐
│ Multiplayer Gem (Gems/Multiplayer/)                         │
│   NetBindComponent, MultiplayerComponent 基类, NetworkEntity │
│   EntityReplicationManager, ReplicationWindow, NetworkInput  │
│   AutoComponent XML → AutoGen → C++ 胶水代码                  │
└─────────────────────────────────────────────────────────────┘
                            ▲
┌─────────────────────────────────────────────────────────────┐
│ AzNetworking (Code/Framework/AzNetworking/)                 │
│   UDP/TCP 传输、连接、数据包、加密 (DTLS)、压缩、序列化         │
│   INetworkInterface, IConnection, IPacket, ISerializer       │
└─────────────────────────────────────────────────────────────┘
                            ▲
                   OS Socket (Winsock / POSIX)
```

分工很清晰：**AzNetworking 不知道 Entity / 游戏的存在**，只管字节流和包。**Multiplayer Gem 只关心游戏数据同步**，不关心 UDP 细节。

---

## AzNetworking：传输层

### 传输选择

通过 `INetworking::CreateNetworkInterface` 选 UDP 还是 TCP：

```cpp
// INetworking 接口
INetworkInterface* CreateNetworkInterface(
    const AZ::Name& name,
    ProtocolType protocolType,     // Udp / Tcp
    TrustZone trustZone,           // ExternalClientToServer / InternalServerToServer
    IConnectionListener& listener
);
```

**选型**：
- UDP + DTLS → 低延迟、可靠性自己管（游戏主要选这条）。
- TCP + TLS → 需要严格顺序和大消息（登录、聊天、管理接口）。

### UDP 加密 / 压缩 CVars

[Code/Framework/AzNetworking/AzNetworking/UdpTransport/UdpNetworkInterface.cpp](../Code/Framework/AzNetworking/AzNetworking/UdpTransport/UdpNetworkInterface.cpp):

```cpp
AZ_CVAR(bool, net_UdpUseEncryption, false, nullptr,
        AZ::ConsoleFunctorFlags::DontReplicate,
        "Enable encryption (DTLS) on UDP connections");
AZ_CVAR(uint32_t, net_SslInflationOverhead, 32, nullptr,
        AZ::ConsoleFunctorFlags::DontReplicate,
        "SSL inflation margin for fragment sizing");
AZ_CVAR(AZ::TimeMs, net_UdpPacketTimeSliceMs, AZ::TimeMs{ 8 }, nullptr,
        AZ::ConsoleFunctorFlags::DontReplicate,
        "Per-frame budget for UDP packet processing");
AZ_CVAR(AZ::CVarFixedString, net_UdpCompressor, "MultiplayerCompressor", nullptr,
        AZ::ConsoleFunctorFlags::DontReplicate,
        "UDP compressor to use");
```

启用加密时构造的是 `DtlsSocket` 而非 `UdpSocket`：

```cpp
m_socket(net_UdpUseEncryption ? new DtlsSocket() : new UdpSocket())
```

### `INetworkInterface` 核心 API

```cpp
class INetworkInterface
{
public:
    virtual AZ::Name GetName() const = 0;
    virtual ProtocolType GetType() const = 0;
    virtual TrustZone GetTrustZone() const = 0;
    virtual uint16_t GetPort() const = 0;
    virtual bool IsEncrypted() const = 0;
    virtual bool IsOpen() const = 0;

    // 监听 / 连接
    virtual bool Listen(uint16_t port) = 0;
    virtual ConnectionId Connect(const IpAddress& remoteAddress, uint16_t localPort = 0) = 0;

    // 每帧由 NetworkingSystem 驱动
    virtual void Update() = 0;

    // 发包
    virtual bool SendReliablePacket(ConnectionId, const IPacket&) = 0;
    virtual PacketId SendUnreliablePacket(ConnectionId, const IPacket&) = 0;
    virtual bool WasPacketAcked(ConnectionId, PacketId) = 0;

    // 断开 / 超时
    virtual bool Disconnect(ConnectionId, DisconnectReason) = 0;
    virtual bool StopListening() = 0;
    virtual void SetTimeoutMs(AZ::TimeMs) = 0;

    virtual IConnectionSet& GetConnectionSet() = 0;
    virtual IConnectionListener& GetConnectionListener() = 0;
};
```

### 连接状态机

`Code/Framework/AzNetworking/AzNetworking/ConnectionLayer/ConnectionEnums.h`:

```cpp
enum class ConnectionState : uint8_t {
    Disconnected,
    Disconnecting,
    Connected,
    Connecting,
};
enum class ConnectionRole : uint8_t {
    Connector,  // 主动建立
    Acceptor    // 被动接受
};
```

生命周期：`Disconnected → Connecting → Connected → Disconnecting → Disconnected`。

### Packet 与 `IPacket`

```cpp
AZ_TYPE_SAFE_INTEGRAL(PacketType, uint16_t);

class IPacket {
public:
    virtual PacketType GetPacketType() const = 0;
    virtual AZStd::unique_ptr<IPacket> Clone() const = 0;
    virtual bool Serialize(ISerializer& serializer) = 0;
};
```

具体 Packet 类通过 `.AutoPackets.xml` 生成（AzNetworking 内用 AutoGen 产出子类）。**应用层一般不手写 Packet**，而是通过 Multiplayer 的 RPC / 属性同步系统。

### `ISerializer` 紧凑二进制序列化

核心方法（`ISerializer.h`）：

```cpp
// 所有方法返回 bool，false 表示包损坏 / 超界
virtual bool Serialize(bool& value, const char* name) = 0;
virtual bool Serialize(int8_t&  value, const char* name, int8_t  minVal, int8_t  maxVal) = 0;
virtual bool Serialize(uint32_t& value, const char* name, uint32_t minVal, uint32_t maxVal) = 0;
virtual bool Serialize(float&   value, const char* name, float minVal, float maxVal) = 0;
// 以及 Vector3 / Quaternion / 字符串 / 容器 / 嵌套对象
```

与 AzCore `SerializeContext` 的区别：

| 维度 | `ISerializer` | `SerializeContext` |
|---|---|---|
| 目标 | 最小二进制 bytes（网络） | 完整 XML / JSON 反射 |
| 范围 | 可指定 min/max → 位压缩 | 无概念 |
| 版本兼容 | 严格（包结构必须匹配） | 版本号 + VersionConverter |
| 用途 | 网络传输 / 回放录像 | 资产 / 存档 / Prefab |

---

## Multiplayer Gem：游戏层

### 模块布局

```
Gems/Multiplayer/Code/
├── Include/Multiplayer/
│   ├── Components/
│   │   ├── NetBindComponent.h               ← "让 Entity 可联网"
│   │   ├── MultiplayerComponent.h           ← 网络组件基类
│   │   ├── MultiplayerController.h          ← Authority/Autonomous 控制器基类
│   │   └── NetworkTransformComponent.h      ← 位置/旋转同步
│   ├── NetworkEntity/
│   │   ├── INetworkEntityManager.h
│   │   ├── NetworkEntityHandle.h
│   │   └── EntityReplication/
│   │       ├── EntityReplicationManager.h    ← 每连接一个
│   │       └── EntityReplicator.h            ← 每 entity × 连接
│   ├── NetworkInput/
│   │   ├── NetworkInput.h                    ← 客户端输入容器
│   │   └── IMultiplayerComponentInput.h
│   ├── ReplicationWindows/
│   │   └── IReplicationWindow.h              ← 可见性窗口
│   ├── MultiplayerTypes.h                    ← NetEntityRole / NetEntityId / HostFrameId
│   └── AutoGen/                              ← Jinja 模板
├── Source/
│   ├── AutoGen/                              ← XML（NetworkTransformComponent.AutoComponent.xml 等）
│   ├── Components/                           ← 组件实现
│   ├── NetworkEntity/EntityReplication/
│   └── MultiplayerStatSystemComponent.{h,cpp}
└── CMakeLists.txt
```

### NetEntityRole（角色）

```cpp
// Gems/Multiplayer/Code/Include/Multiplayer/MultiplayerTypes.h
enum class NetEntityRole : uint8_t {
    InvalidRole,
    Client,       // 客户端模拟代理 — 只读、无权修改状态
    Autonomous,   // 客户端自主代理 — 产生输入，预测本地
    Server,       // 跨服次要代理 — 只读（dedicated 多服拓扑）
    Authority     // 权威代理 — 唯一的真相来源（主服务器）
};

bool NetworkRoleHasController(NetEntityRole);  // Authority / Autonomous 有 controller
```

**同一个 Entity 在不同机器上角色不同**：
- 服务器上 PlayerA 的 Entity 是 Authority
- PlayerA 的客户端机器上同一个 Entity 是 Autonomous（输入源）
- PlayerB 看到的 PlayerA 的 Entity 是 Client（只观察）

### `NetBindComponent` — 联网能力的开关

**任何要参与同步的 Entity 必须加此组件**。真实 API 摘录（[NetBindComponent.h](../Gems/Multiplayer/Code/Include/Multiplayer/Components/NetBindComponent.h)）：

```cpp
class NetBindComponent final : public AZ::Component
{
public:
    // 角色查询
    NetEntityRole GetNetEntityRole() const;
    bool IsNetEntityRoleAuthority() const;
    bool IsNetEntityRoleAutonomous() const;
    bool IsNetEntityRoleServer() const;
    bool IsNetEntityRoleClient() const;

    // 身份
    NetEntityId GetNetEntityId() const;
    ConstNetworkEntityHandle GetEntityHandle() const;

    // 迁移控制（权威在不同服务器间移动）
    void SetAllowEntityMigration(EntityMigration);
    void SetOwningConnectionId(AzNetworking::ConnectionId);
    AzNetworking::ConnectionId GetOwningConnectionId() const;

    // 输入与预测（autonomous / authority 端都要实现）
    void CreateInput(NetworkInput&, float deltaTime);
    void ProcessInput(NetworkInput&, float deltaTime);
    void ReprocessInput(NetworkInput&, float deltaTime);
    bool IsProcessingInput() const;
    bool IsReprocessingInput() const;

    // 生命周期
    void NetworkActivated();
    void ConstructControllers();
    void ActivateControllers(EntityIsMigrating);
    void DeactivateControllers(EntityIsMigrating);

    // RPC / 属性
    RpcSendEvent& GetSendAuthorityToClientRpcEvent();
    RpcSendEvent& GetSendAuthorityToAutonomousRpcEvent();
    RpcSendEvent& GetSendServerToAuthorityRpcEvent();
    RpcSendEvent& GetSendAutonomousToAuthorityRpcEvent();
};
```

### `MultiplayerComponent` 基类

你不直接派生它 —— **AutoGen 从 XML 生成 `XxxBase` 派生它**，你再派生 `XxxBase`。关键接口（`MultiplayerComponent.h`）：

```cpp
class MultiplayerComponent : public AZ::Component
{
public:
    // hook 点
    virtual void OnNetworkActivated() {}

    // AutoGen 生成物实现的纯虚
    virtual void SetOwningConnectionId(AzNetworking::ConnectionId) = 0;
    virtual NetComponentId GetNetComponentId() const = 0;
    virtual bool HandleRpcMessage(AzNetworking::IConnection*, NetEntityRole, NetworkEntityRpcMessage&) = 0;
    virtual bool SerializeStateDeltaMessage(ReplicationRecord&, AzNetworking::ISerializer&) = 0;
    virtual void NotifyStateDeltaChanges(ReplicationRecord&) = 0;
    virtual void ConstructController()    = 0;
    virtual void DestructController()     = 0;
    virtual void ActivateController  (EntityIsMigrating) = 0;
    virtual void DeactivateController(EntityIsMigrating) = 0;
    virtual void NetworkAttach(NetBindComponent*, ReplicationRecord&, ReplicationRecord&) = 0;
};

#define AZ_MULTIPLAYER_COMPONENT(ComponentClass, Guid, Base)   \
    AZ_RTTI(ComponentClass, Guid, Base)                        \
    AZ_COMPONENT_INTRUSIVE_DESCRIPTOR_TYPE(ComponentClass)     \
    AZ_COMPONENT_BASE(ComponentClass)                          \
    AZ_CLASS_ALLOCATOR(ComponentClass, AZ::ComponentAllocator)
```

---

## AutoComponent XML（重点！）

真实样例：[NetworkTransformComponent.AutoComponent.xml](../Gems/Multiplayer/Code/Source/AutoGen/NetworkTransformComponent.AutoComponent.xml)

```xml
<?xml version="1.0"?>
<Component
    Name="NetworkTransformComponent"
    Namespace="Multiplayer"
    OverrideComponent="true"
    OverrideController="true"
    OverrideInclude="Multiplayer/Components/NetworkTransformComponent.h"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

    <ComponentRelation Constraint="Weak" HasController="false"
                       Name="TransformComponent" Namespace="AzFramework"
                       Include="AzFramework/Components/TransformComponent.h" />

    <Include File="Multiplayer/MultiplayerTypes.h"/>

    <NetworkProperty Type="AZ::Quaternion" Name="rotation"
                     Init="AZ::Quaternion::CreateIdentity()"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="true" IsPredictable="true" IsPublic="true"
                     Container="Object"
                     ExposeToEditor="false" ExposeToScript="false"
                     GenerateEventBindings="true" />

    <NetworkProperty Type="AZ::Vector3" Name="translation"
                     Init="AZ::Vector3::CreateZero()"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="true" IsPredictable="true" IsPublic="true"
                     Container="Object"
                     ExposeToEditor="false" ExposeToScript="false"
                     GenerateEventBindings="true" />

    <NetworkProperty Type="float" Name="scale" Init="1.0f"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="true" IsPredictable="true" IsPublic="true"
                     Container="Object"
                     ExposeToEditor="false" ExposeToScript="false"
                     GenerateEventBindings="true" />

    <NetworkProperty Type="uint8_t" Name="resetCount" Init="0"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="false" IsPredictable="true" IsPublic="true"
                     Container="Object"
                     ExposeToEditor="false" ExposeToScript="true"
                     GenerateEventBindings="true" />

    <NetworkProperty Type="NetEntityId" Name="parentEntityId"
                     Init="InvalidNetEntityId"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="true" IsPredictable="true" IsPublic="true"
                     Container="Object"
                     ExposeToEditor="false" ExposeToScript="false"
                     GenerateEventBindings="true" />

    <RemoteProcedure Name="MultiplayerTeleport"
                     InvokeFrom="Server" HandleOn="Authority"
                     IsPublic="true" IsReliable="true"
                     GenerateEventBindings="true"
                     Description="Teleports to a position while incrementing resetCount to avoid interpolation">
        <Param Type="AZ::Vector3" Name="TeleportToPosition" />
    </RemoteProcedure>
</Component>
```

### XML 字段逐一解释

#### `<Component>` 根元素

| 属性 | 说明 |
|---|---|
| `Name` | 生成的 C++ 类基础名 |
| `Namespace` | C++ 命名空间 |
| `OverrideComponent` | 若 `true`，作者自己的 `MyComp.h` 覆盖生成物 |
| `OverrideController` | 同上，对 Controller |
| `OverrideInclude` | 作者的头文件路径（供 AutoGen 代码 include） |

#### `<ComponentRelation>` — 依赖组件

声明"同一 Entity 上需要/最好有其它组件"。`Constraint` 可以是 `Required`（硬）或 `Weak`（软）。

#### `<NetworkProperty>` 属性

| 属性 | 取值 | 作用 |
|---|---|---|
| `Type` | C++ 类型 | 属性类型 |
| `Name` | 标识符 | 属性名 |
| `Init` | 初始化表达式 | 默认值 |
| `ReplicateFrom` | `Authority` / `Autonomous` | 数据源角色 |
| `ReplicateTo` | `Client` / `Autonomous` / `Server`（可组合用斜杠） | 目标角色 |
| `IsRewindable` | `true`/`false` | 是否保留历史，支持回滚 |
| `IsPredictable` | `true`/`false` | Autonomous 端可本地预测 |
| `IsPublic` | `true`/`false` | 生成 Get/Set 为 public |
| `Container` | `Object` / `Array` / `Vector` | 单值 or 数组 |
| `Count` | 整数 | 数组/向量长度（固定大小） |
| `ExposeToEditor` | `true`/`false` | EditContext 反射 |
| `ExposeToScript` | `true`/`false` | BehaviorContext 反射 |
| `GenerateEventBindings` | `true`/`false` | 生成 `XxxAddEvent(handler)` 订阅 API |

**ReplicateFrom / ReplicateTo 组合的意义**：

| From → To | 效果 |
|---|---|
| `Authority → Client` | 服务器推给所有客户端（典型 transform / health） |
| `Authority → Autonomous` | 服务器推给主控客户端（可预测属性） |
| `Autonomous → Authority` | 客户端输入回流服务器（通常走 RPC，不走属性） |
| `Server → Authority` | 多服拓扑（cross-server sharding） |

#### `<RemoteProcedure>` RPC

| 属性 | 取值 |
|---|---|
| `Name` | RPC 名 |
| `InvokeFrom` | 调用端角色（Authority / Autonomous / Server / Client） |
| `HandleOn` | 处理端角色 |
| `IsPublic` | 可否从外部调（C++） |
| `IsReliable` | 是否走可靠通道（重要操作设 true，频繁状态留 false） |
| `GenerateEventBindings` | 生成 `OnRpcXxx` 回调绑定 |
| `Description` | 说明（显示在生成的 doc） |
| `<Param Type="..." Name="...">` | 参数 |

典型组合：

| Invoke / Handle | 语义 |
|---|---|
| `Autonomous → Authority` | 客户端命令服务器（开火、捡物品） |
| `Authority → Autonomous` | 服务器回应单个客户端（"你中了 20 伤害"） |
| `Authority → Client` | 服务器广播给所有客户端（播放动画、特效） |
| `Server → Authority` | 多服跨服请求（不常用） |

---

## AutoGen 生成物与派生方式

每个 `Foo.AutoComponent.xml` 生成（输出在 `<build>/Azcg/Generated/<target>/...`）：

| 文件 | 内容 |
|---|---|
| `Foo.AutoComponent.h` | `class FooBase : public MultiplayerComponent`，所有 Get/Set/Event/RPC 生成 |
| `Foo.AutoComponent.cpp` | 上面类的实现，包括 `Reflect()`、序列化 |
| `Foo.AutoComponent.Common.h` / `.inl` | 共享 Controller Base、事件类型 |
| `AutoComponentTypes.h` / `.cpp` | 整个 Gem 里所有 AutoComponent 的 forward decl + `CreateDescriptor` 列表 |

### 派生与实现

```cpp
// Foo.h （作者写）
#include <Foo.AutoComponent.h>   // 用 OverrideInclude 指向的路径

class Foo : public FooBase
{
public:
    AZ_MULTIPLAYER_COMPONENT(Foo, "{uuid}", FooBase);

    static void Reflect(AZ::ReflectContext*);

    // 生命周期 hook
    void OnInit() override;
    void OnActivate(EntityIsMigrating) override;
    void OnDeactivate(EntityIsMigrating) override;

    // 网络激活（所有绑定就绪）
    void OnNetworkActivated() override;

    // 属性变化回调（GenerateEventBindings=true 的属性都有）
    void OnTranslationChanged(const AZ::Vector3& newValue);
    void OnRotationChanged(const AZ::Quaternion& newValue);

    // RPC 回调（HandleOn 是本端角色才触发）
    void OnRpcMultiplayerTeleport(const AZ::Vector3& pos);

private:
    AZ::Event<const AZ::Vector3&>::Handler m_translationChangedHandler;
};
```

### 在 OnActivate 里挂事件

```cpp
void Foo::OnActivate(EntityIsMigrating)
{
    m_translationChangedHandler = AZ::Event<const AZ::Vector3&>::Handler(
        [this](const AZ::Vector3& v){ OnTranslationChanged(v); });
    TranslationAddEvent(m_translationChangedHandler);   // 生成的 API
}
```

### Controller

`FooController`（或 `FooControllerBase`）是**只在 Authority/Autonomous 存在**的部分。用来：

- 采集输入：`CreateInput(NetworkInput&, float dt)` — Autonomous 端调
- 执行输入：`ProcessInput(NetworkInput&, float dt)` — 双端都调（客户端本地预测 + 服务器真实）
- 回放：`ReprocessInput(NetworkInput&, float dt)` — 服务器纠正后回放

---

## 客户端输入 + 预测 + 回滚

### NetworkInput 结构

```cpp
class NetworkInput {
    ClientInputId GetClientInputId() const;   // 客户端输入序号（递增）
    HostFrameId   GetHostFrameId() const;     // 服务器帧号
    AZ::TimeMs    GetHostTimeMs() const;
    float         GetHostBlendFactor() const; // 插值因子

    // 按组件存储：XML <NetworkInput> 标签生成存取方法
    // 如: float GetFwdBack() / void SetFwdBack(float)
};
```

### 流程图

```
[Autonomous 每帧]
    CreateInput(ni, dt)              ← 采集按键/摇杆到 NetworkInput
        └─ Server 同时：NetBindComponent::ProcessInput(ni, dt)
            和本地先跑一次 (预测)
    NetworkInput 发往 Authority
                     ↓
[Authority 收到]
    ProcessInput(ni, dt)              ← 真实运行
    与客户端预测状态对比
    若不一致 → 发 correction 回 Autonomous
                     ↓
[Autonomous 收到 correction]
    Reprocess 所有 未 ack 的输入
    ReprocessInput(ni[i], dt) 循环      ← 回滚重放
    最终状态 = 权威状态 + 本地新输入重放
```

### 为什么 ProcessInput 必须"幂等 / 直接赋值"

```cpp
// ❌ 错误：累加
void Foo::ProcessInput(NetworkInput& input, float dt) {
    m_position += input.GetVelocity() * dt;  // 回放时再加一遍 → 位置飞
}

// ✅ 正确：按权威状态重算
void Foo::ProcessInput(NetworkInput& input, float dt) {
    AZ::Vector3 pos = GetTranslation();      // 读当前网络同步状态
    pos += input.GetVelocity() * dt;
    SetTranslation(pos);                      // 设回（触发同步）
}
```

原则：**ProcessInput 的输入只依赖网络同步的状态 + 当前 NetworkInput**。不要依赖本地未同步的成员变量、随机数（除非加种子同步）、时间（除非用 `GetHostTimeMs`）。

### 其它要点

- `ClientInputId` 递增；Authority 用这个确认已处理到哪一帧，ack 回客户端。
- `HostFrameId` 来自服务器的逻辑帧号；回滚时用这个对齐。
- Rewindable 属性（`IsRewindable="true"`）才能参与回滚；不 rewindable 的属性回滚时不会回放。

---

## RPC 使用细节

### 生成的函数

对于 `<RemoteProcedure Name="Teleport" InvokeFrom="Server" HandleOn="Authority" ...>`，生成：

```cpp
// 在 "Server" 端调：
void Teleport(const AZ::Vector3& pos);    // 你调用这个

// 在 "Authority" 端：
virtual void OnRpcTeleport(const AZ::Vector3& pos);  // 你 override 这个
// 或通过 GenerateEventBindings 获得 AZ::Event，用 Handler 订阅
```

### 可靠性选择

| 场景 | `IsReliable` |
|---|---|
| 伤害/治疗 | `true` |
| 死亡 / 获得物品 | `true` |
| 动画播放 | `false`（丢了下一帧自然继续） |
| 射击（但服务器权威判定） | `false`（本帧走了就行） |
| 聊天消息 | `true` |

### Broadcast / Unicast 对应

没有显式 Broadcast 宏，通过 RPC 方向实现：

| 方向 | 效果 |
|---|---|
| `Authority → Client` | 所有观察该 Entity 的客户端（Broadcast 给 visible 的） |
| `Authority → Autonomous` | 仅主控那个客户端（Unicast） |
| `Autonomous → Authority` | 客户端给服务器（命令） |

---

## Replication Window + Replicator（节流/可见性）

### IReplicationWindow

每个连接一个 Window，决定"这个玩家能看到哪些 Entity + 每帧发多少个更新"：

```cpp
class IReplicationWindow
{
public:
    virtual const ReplicationSet& GetReplicationSet() const = 0;
    virtual bool IsInWindow(const ConstNetworkEntityHandle&, NetEntityRole& out) const = 0;
    virtual uint32_t GetMaxProxyEntityReplicatorSendCount() const = 0;
    virtual void UpdateWindow() = 0;

    virtual AzNetworking::PacketId SendEntityUpdateMessages(NetworkEntityUpdateVector&) = 0;
    virtual void SendEntityRpcs(NetworkEntityRpcVector&, bool reliable) = 0;
    virtual void SendEntityResets(const NetEntityIdSet&) = 0;
};
```

典型实现：空间分区（距离/视锥），离玩家越近优先级越高。默认 Multiplayer 给了一个 `NullReplicationWindow`（发所有）和 `ServerToClientReplicationWindow`（按 view）。

### EntityReplicator

单个 entity × 单连接的状态追踪：

- 记录上次发给该连接的属性值（做 delta）
- 追踪未 ack 的 packetId
- 接收端：处理属性变更包

应用层一般不碰它，但调 `net_debug` 时看到大量此类对象 log。

### 带宽压缩

XML 属性上可以加压缩：

```xml
<NetworkProperty Type="float" Name="velocity"
                 Attribute="FloatCompression(0.0f, 100.0f, 0.1f)"
                 ... />
```

效果：float 压缩到 `log2((max-min)/precision)` 位。`[0..100]` 精度 0.1 = 10 位。

全局 compressor 由 [MultiplayerCompression](../Gems/MultiplayerCompression/) Gem 提供（`net_UdpCompressor` CVar）。

---

## 最小可行联网组件：从零到跑起来

### 目标

做一个 `NetworkHealthComponent`：服务器持血量，广播给所有人；有 `TakeDamage` RPC（服务器调，减血）。

### 步骤

**1. 写 XML**  `Gems/MyGame/Code/Source/AutoGen/NetworkHealthComponent.AutoComponent.xml`:

```xml
<?xml version="1.0"?>
<Component Name="NetworkHealthComponent" Namespace="MyGame"
           OverrideComponent="false" OverrideController="false">

    <Include File="Multiplayer/MultiplayerTypes.h"/>

    <NetworkProperty Type="float" Name="health" Init="100.0f"
                     ReplicateFrom="Authority" ReplicateTo="Client"
                     IsRewindable="false" IsPredictable="false" IsPublic="true"
                     Container="Object" ExposeToEditor="true" ExposeToScript="true"
                     GenerateEventBindings="true" />

    <RemoteProcedure Name="TakeDamage"
                     InvokeFrom="Authority" HandleOn="Authority"
                     IsPublic="true" IsReliable="true" GenerateEventBindings="true">
        <Param Type="float" Name="damage" />
    </RemoteProcedure>
</Component>
```

**2. `*_files.cmake` 加这个 xml 到 `mygame_private_files.cmake`**：

```cmake
set(FILES
    ...
    Source/AutoGen/NetworkHealthComponent.AutoComponent.xml
    Source/Components/NetworkHealthComponent.h
    Source/Components/NetworkHealthComponent.cpp
)
```

**3. 确保 CMakeLists 里有 AUTOGEN_RULES**（通常父级 Multiplayer-based gem 模板已有）：

```cmake
AUTOGEN_RULES
    *.AutoComponent.xml,AutoComponent_Header.jinja,$path/$fileprefix.AutoComponent.h
    *.AutoComponent.xml,AutoComponent_Source.jinja,$path/$fileprefix.AutoComponent.cpp
    *.AutoComponent.xml,AutoComponentTypes_Header.jinja,$path/AutoComponentTypes.h
    *.AutoComponent.xml,AutoComponentTypes_Source.jinja,$path/AutoComponentTypes.cpp
```

**4. 写 C++**  `NetworkHealthComponent.h`：

```cpp
#pragma once
#include <Source/AutoGen/NetworkHealthComponent.AutoComponent.h>

namespace MyGame
{
    class NetworkHealthComponent
        : public NetworkHealthComponentBase
    {
    public:
        AZ_MULTIPLAYER_COMPONENT(NetworkHealthComponent,
            "{uuid-generate}", NetworkHealthComponentBase);

        static void Reflect(AZ::ReflectContext*);

        void OnInit() override {}
        void OnActivate(Multiplayer::EntityIsMigrating) override;
        void OnDeactivate(Multiplayer::EntityIsMigrating) override;

        // RPC 回调
        void OnRpcTakeDamage(const float& damage);

        // 属性变更回调（GenerateEventBindings → 有对应 AddEvent）
        void OnHealthChanged(float newHp);

    private:
        AZ::Event<float>::Handler m_healthHandler;
    };
}
```

`NetworkHealthComponent.cpp`：

```cpp
#include "NetworkHealthComponent.h"

namespace MyGame
{
    void NetworkHealthComponent::Reflect(AZ::ReflectContext* ctx)
    {
        if (auto* sc = azrtti_cast<AZ::SerializeContext*>(ctx))
        {
            sc->Class<NetworkHealthComponent, NetworkHealthComponentBase>()
                ->Version(1);
        }
    }

    void NetworkHealthComponent::OnActivate(Multiplayer::EntityIsMigrating)
    {
        m_healthHandler = AZ::Event<float>::Handler(
            [this](float hp){ OnHealthChanged(hp); });
        HealthAddEvent(m_healthHandler);   // ← AutoGen API
    }

    void NetworkHealthComponent::OnDeactivate(Multiplayer::EntityIsMigrating)
    {
        m_healthHandler.Disconnect();
    }

    void NetworkHealthComponent::OnRpcTakeDamage(const float& dmg)
    {
        // 此时角色是 Authority（XML 里 HandleOn="Authority"）
        float newHp = AZStd::max(0.f, GetHealth() - dmg);
        SetHealth(newHp);   // SetHealth 会触发复制和 OnHealthChanged 事件
    }

    void NetworkHealthComponent::OnHealthChanged(float newHp)
    {
        // 这里在 Client / Authority / Autonomous 都可能被调
        if (newHp <= 0.f) {
            // 触发死亡逻辑（各端可能有不同行为，用 GetNetEntityRole() 判断）
        }
    }
}
```

**5. 注册到 Module**：

```cpp
// MyGameModule.cpp
#include "Source/AutoGen/AutoComponentTypes.h"   // 包含 CreateDescriptor 列表
...
MyGameModule() {
    CreateComponentDescriptors(m_descriptors);   // AutoGen 生成的 helper
    m_descriptors.insert(m_descriptors.end(), {
        NetworkHealthComponent::CreateDescriptor(),
        // ... 手写非网络组件
    });
}
```

**6. 构建 + 在 Prefab 里用**：
- Prefab 上的 Entity 加 `NetBindComponent` + `NetworkHealthComponent`。
- 保存 → AP → spawnable。
- 起 `Launcher --server` + `Launcher --connect=127.0.0.1`。
- 服务器端调 `healthComp->TakeDamage(10.f)` → 客户端看到 `SetHealth` 变化。

---

## 调试

| 工具 | 用途 |
|---|---|
| `net_debug 1` | 网络统计输出到日志 + 屏幕 |
| `net_DumpStats` | 一次性打印统计 |
| `ImGui` Multiplayer 面板 | 实时连接 / RPC / 带宽监控（ImGui Gem 启用时） |
| `MultiplayerStatSystem` | 代码访问统计 |
| Wireshark + UDP 抓包 | 底层排查丢包，按 AzNetworking PacketHeader 二进制解析 |
| `net_LatencyMs N` / `net_PacketLossPct N` | 本地模拟网络状况 |

### AutomatedTesting 参考

[AutomatedTesting/Gem/Code/Source/AutoGen/](../AutomatedTesting/Gem/Code/Source/AutoGen/) 有完整真实的网络组件 XML，强烈建议对照学习：

- `NetworkTestPlayerComponent.AutoComponent.xml` — 玩家控制 + 输入 + 多种 RPC 方向
- `NetworkTestLevelEntityComponent.AutoComponent.xml` — 关卡 Entity 的同步
- `SimpleScriptPlayerComponent.AutoComponent.xml` — 脚本集成示例

---

## 常见坑（网络）

1. **`NetBindComponent` 忘加** → 整个 Entity 不参与网络，没任何报警。检查 Prefab。
2. **`.AutoComponent.xml` 没加入 `*_files.cmake`** → AutoGen 扫不到，生成物缺失，编译报 `NetworkXxxBase` 不存在。
3. **两端都执行本地副作用** → 用 `GetNetEntityRole()` 或 `IsNetEntityRoleAuthority()` 分支。
4. **ProcessInput 累加状态** → 回滚时重复计算，客户端看到位置抖动。
5. **大量 `Authority→Client` 高频属性** → 带宽爆炸。考虑 FloatCompression / 降频 / 只发关键状态。
6. **Reliable RPC 风暴** → 一帧发百个 reliable，TCP-like 阻塞。按需改 `IsReliable="false"`。
7. **修改 `.AutoComponent.xml` 属性类型** → 老 prefab 里保存的值反序列化失败。加 Version 或重 author。
8. **Multiplayer Gem 未启用但加了 NetBindComponent** → 启动时 `AZ_Error` 找不到系统服务。

---

# 第二部分 · 物理（PhysX Gem）

## 结构

[Gems/PhysX/](../Gems/PhysX/) 按 PhysX SDK 大版本拆目录：

```
Gems/PhysX/
├── Common/         跨版本代码（接口、组件公共实现）
├── Core/
│   ├── PhysX4/     绑 PhysX SDK 4
│   └── PhysX5/     绑 PhysX SDK 5 （新项目选这个）
├── Debug/
│   ├── PhysX4/     PVD 连接、debug draw（PhysX 4 版本）
│   └── PhysX5/     同上，5 版本
```

**关键事实**：AzFramework 有抽象物理 API（[AzFramework/Physics/](../Code/Framework/AzFramework/AzFramework/Physics/)），PhysX Gem 是实现。上层代码 include `AzFramework/Physics/*.h`，**不 include PhysX SDK 头**。这样未来换实现或多物理并存不会推倒业务代码。

## 运行时核心对象

| 概念 | 类 | 说明 |
|---|---|---|
| 物理场景 | `AzPhysics::Scene` | 每个逻辑世界一个；默认一个 `DefaultPhysicsSceneName` |
| 刚体 | `AzPhysics::RigidBody` (动态) / `AzPhysics::StaticRigidBody` | 具体在 `PhysXRigidBodyComponent` |
| 形状配置 | `Physics::ShapeConfiguration` (虚基) | Box/Sphere/Capsule/Mesh/Heightfield 派生 |
| 查询 | `AzPhysics::SceneQuery` | Raycast / Overlap / Sweep |
| 材质 | `Physics::MaterialAsset` | Friction / Restitution / Density |
| 角色控制器 | `Physics::CharacterConfiguration` | 对应 `PhysXCharacterControllerComponent` |

### 常用代码：Raycast

```cpp
#include <AzFramework/Physics/PhysicsScene.h>
#include <AzFramework/Physics/Common/PhysicsSceneQueries.h>

auto* scene = AZ::Interface<AzPhysics::SceneInterface>::Get();
AzPhysics::SceneHandle sceneHandle = scene->GetSceneHandle(
    AzPhysics::DefaultPhysicsSceneName);

AzPhysics::RayCastRequest req;
req.m_start = startWorld;
req.m_direction = dir.GetNormalized();
req.m_distance = 1000.f;
req.m_reportMultipleHits = false;
req.m_collisionGroup = AzPhysics::CollisionGroup::All;

AzPhysics::SceneQueryHits hits = scene->QueryScene(sceneHandle, &req);
if (!hits.m_hits.empty()) {
    const auto& h = hits.m_hits[0];
    // h.m_position / h.m_normal / h.m_entityId / h.m_distance / h.m_material
}
```

### Overlap / Sweep 类似

`AzPhysics::OverlapRequest` / `AzPhysics::ShapeCastRequest` 的 API 同步，接收填好的 request，返回 hits。

### Collision Layer / Group

- **Layer** — 一个 entity 的"身份"（玩家、敌人、道具、触发器）。
- **Group** — 一个 entity"能感知到"的 layer 集合。
- 配置在 `physxconfiguration.setreg` 或 Editor 的 Physics Configuration 窗口。

Raycast / 碰撞发生时，engine 查两边的 layer × group 交集决定是否响应。

## Editor 组件一览

常用（Editor 里 "Add Component → PhysX" 能看到）：

- `PhysXRigidBodyComponent` / `PhysXStaticRigidBodyComponent`
- `PhysXColliderComponent`（配合 Shape / Mesh 组件提供形状）
- `PhysXCharacterControllerComponent`（FPS 角色）
- `PhysXBallJointComponent` / `PhysXFixedJointComponent` / `PhysXHingeJointComponent` / `PhysXPrismaticJointComponent` / `PhysXD6JointComponent`
- `PhysXRagdollComponent`（与 EMotionFX 配合）
- `PhysXForceRegionComponent`（区域力场）
- `PhysXHeightfieldColliderComponent`（与 Terrain）
- `PhysXShapeColliderComponent`（组合 ShapeComponent 为碰撞）

## Cloth (NvCloth)

[Gems/NvCloth/](../Gems/NvCloth/)：基于 NVIDIA NvCloth 的独立布料系统（不走 PhysX Scene）。挂 `ClothComponent` 到 Mesh。

## 调试

- `ph_ShowColliders 1` / `ph_Debug 1` / `ph_ShowSceneQueries 1` 等 CVar
- PhysX Visual Debugger (PVD)：Editor Physics 设置里开 PVD 端口 → PC 上打开 NVIDIA PVD GUI 连接，看场景实时
- Editor Viewport → Display → Physics 开关

## 常见坑（物理）

1. **Collider 没 Shape** → `PhysXColliderComponent` 必须配 `BoxShapeComponent` / `SphereShapeComponent` / Mesh Collider。
2. **Raycast miss 全部** → CollisionGroup 设成 `None` 或过滤太紧；先 `CollisionGroup::All` 跑通再收紧。
3. **动态刚体 Sleep** → Trigger Enter 才有回调；需要 Stay 事件就要订 `OnTriggerEnter + OnTriggerExit` 自己维护。
4. **Character Controller 穿地** → 使用 capsule；Step Height / Slope Limit 根据几何调。
5. **PhysX 4 / 5 冲突** → 同一项目**不能同时启用** `PhysX4` 和 `PhysX5`；选一个。
6. **RigidBody 非统一 scale** → PhysX 不喜欢；加 `NonUniformScaleComponent` 时很多 collider 会警告并取统一 scale。
7. **跨 Physics Scene 查询** → `SceneInterface::QueryScene(sceneHandle, ...)` 必须传对 sceneHandle，默认场景之外的不会自动跨。

---

继续：[11_conventions_and_patterns.md](11_conventions_and_patterns.md) / [12_cookbook_recipes.md](12_cookbook_recipes.md)
