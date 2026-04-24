# 16 · 性能优化 Checklist

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

本章是"做 O3DE 项目性能优化时按顺序查什么"。每节都有**具体工具 + 具体动作**。

---

## 总原则

1. **测量先于优化**：没数据别改代码。
2. **按帧预算拆分**：60 FPS = 16.6 ms/帧。CPU 主线程 / 渲染线程 / GPU 三条预算单独看。
3. **最贵的事情做一次就够了**：每帧分配 / 每帧反射查找 / 每帧跨线程锁 —— 挑出来缓存。
4. **从最大开销开始**：10% 优化 Top5 函数 > 100% 优化尾部长条函数。

典型目标（3D 动作游戏 60fps）：

| 预算 | 典型分配 |
|---|---|
| CPU 主线程 | ≤ 8 ms（gameplay + Tick + Input） |
| 渲染线程 | ≤ 4 ms（DrawPacket 构建 + Pass build） |
| GPU | ≤ 14 ms（留一点给 swap/present） |
| Asset 流 | 后台线程，不阻塞帧 |

---

## 测量工具

### AZ::Debug::Profiler 宏族

[Code/Framework/AzCore/AzCore/Debug/Profiler.h](../Code/Framework/AzCore/AzCore/Debug/Profiler.h)：

```cpp
// 函数级
void Foo() {
    AZ_PROFILE_FUNCTION(MyGem);
    // ...
}

// 作用域级
{
    AZ_PROFILE_SCOPE(Rendering, "UpdateMesh");
    // ...
}

// 间隔事件（跨多帧）
AZ_PROFILE_INTERVAL_START(Gameplay, "LevelLoad", 0);
LoadLevel();
AZ_PROFILE_INTERVAL_END(Gameplay, "LevelLoad", 0);

// 数据点（绘制曲线）
AZ_PROFILE_DATAPOINT(Entity, m_entityCount, "Entities");
```

### Budget —— profiler 的分组标签

[Code/Framework/AzCore/AzCore/Debug/Budget.h](../Code/Framework/AzCore/AzCore/Debug/Budget.h) + [Budget.cpp](../Code/Framework/AzCore/AzCore/Debug/Budget.cpp)：

引擎内置 budget：`Animation`, `Audio`, `AzCore`, `Editor`, `Entity`, `Game`, `System`, `Physics`。

自己 Gem 加：

```cpp
// 在 Gem 的某个 .cpp 顶层 namespace scope：
AZ_DEFINE_BUDGET(MyGem);

// 其它 .cpp 用到前先声明：
AZ_DECLARE_BUDGET(MyGem);
```

用：`AZ_PROFILE_FUNCTION(MyGem)`。profiler GUI 按 budget 分组显示。

### Profiler 后端

启 [Gems/Profiler](../Gems/Profiler/)。后端编译期选：

- **Tracy** — 开源轻量，默认启。exe 旁起 `Tracy.exe`，本地网络连。实时 + 历史帧。
- **Superluminal** — 商业 profiler。CPU flame graph 强。
- **ImGui Profiler** — 启 `Gems/Profiler` 后 `F1` 弹 ImGui overlay 有。

CPU 主线程 / 工作线程都会被抓到。

### Tracy 接入要点

```cpp
// CMake 里启
-DLY_PROFILER_TRACY=ON
```

运行时：Launcher 自动监听 8086 端口；Tracy.exe 连上即可。

### GPU Profiler

- **RenderDoc**：开源；DX11/DX12/Vulkan。attach launcher → F12 capture → 完整帧分析（每 draw、每 resource）。
- **PIX**（Windows DX12）：NVIDIA Nsight 替代。GPU frame timing 更细。
- **NVIDIA Nsight Graphics**：跨 API。
- Atom 内置 `r_ProfileGpu 1` 打印 pass-level GPU 时间到 log；`r_ShowGpuMemory` 看显存。

---

## CPU 主线程诊断

### Tick 频率检查

```cpp
// 加到某系统组件的 OnTick：
AZ_PROFILE_FUNCTION(MyGem);
// 看 Tracy 里该 scope 每帧多久
```

典型罪魁：

1. **每帧 Reflect 查找 / `azrtti_cast`**：缓存到成员。
2. **每帧 `AZ::Interface<T>::Get()`**：`Get()` 是 atomic load，成本小但 hot loop 要避免。缓存指针。
3. **每帧 `EBus::Broadcast` 大量广播**：batch；或用 Event Queue。
4. **每帧 `AZ::Name("foo")` 构造**：查字典有锁。用 `static AZ::Name` / `AZ_NAME_LITERAL`。
5. **每帧 allocator 分配**：`AZStd::vector` 每帧 push_back/clear → 用 `reserve` 或 object pool。

### Entity 数量爆炸

几百个 Entity 没问题；几万起，EntityContext / TransformBus 广播扩散显著。对策：

- 用 **instanced mesh**（`MeshFeatureProcessor` 支持）而不是每个实例一个 Entity。
- 静态物体加 `StaticMeshComponent`（不订阅 TransformNotification）。
- 批量 spawn 用 `SpawnAllEntities`（一次激活），不要 for 循环创建。
- 合并可以合并的"一堆 tag 组件" → 一个组件 + 位图。

### EBus 热路径

`EBus::Broadcast(func)` 对每个 handler 一次虚调用。10k handler × 广播 → 10k 虚调用。

- 若要批量：提前 `EnumerateHandlers` 拿指针列表，自己循环调（省 dispatch）。
- `LocklessDispatch = true` 可省 mutex（确保不跨线程改连接）。
- **Single** 政策的 bus 比 Multiple 快得多 —— 只有一个 handler 时就别用 Multiple。

### 字符串 / Name

- 热路径不用 `AZStd::string` + `::format` — 分配 + 格式化双倍慢。
- 用 `AZ::Name` 做标识符比较（O(1) hash）。
- CRC32 常量 `AZ_CRC_CE("Key")` 编译期计算，比 `AZ::Name` 更省（但没字符串，debug 看不到）。

### Unity build

CMake 有 `ly_add_target(... NO_UNITY)`；Unity build 编译快（合并 TU），但会掩盖 include 依赖问题。**不影响运行时性能**；只影响编译。

---

## 内存优化

### 监控

```cpp
AZ::Debug::MemoryStatistics stats;
AZ::AllocatorInstance<AZ::SystemAllocator>::Get().GetAllocationInfo(stats);
AZ_Printf("Mem", "Bytes: %llu, Allocs: %llu", stats.m_bytesAllocated, stats.m_numAllocations);
```

运行时 log 打内存快照：`--allocator_record_memory 1`。

### 常见省法

| 做法 | 收益 |
|---|---|
| 用 `AZStd::fixed_vector<T, N>` 代替 `AZStd::vector<T>` 当数量有上限 | 省堆分配 |
| `AZStd::string_view` 传参，不传 `AZStd::string` 按值 | 省 copy |
| `AZ::Name` 驻留标识 | 几个 byte vs 几十 byte |
| `AZStd::unique_ptr` 代 `shared_ptr` 当所有权单一 | 省原子计数 + 内存 |
| Entity / 组件重用 pool 而非销毁重建 | 省 Reflect / allocator overhead |
| 显式 `reserve` 容器 | 避免 growth reallocation |

### 资产流式加载

大资产（纹理、模型）**不要 PreLoad** 所有。用 `QueueLoad` / `NoLoad`。

- Streaming Image：贴图按 mip 流式加载，距离远只加载低 mip。
- [Gems/Streamer](../Gems/Streamer/) 启用后，大文件异步读。`StreamerProfiler` 查流水。

---

## 渲染 / GPU 优化

### 通用 pipeline-level 调整

| 开关 | 效果 |
|---|---|
| 关 `SsaoPass` | 省 1-2 ms |
| 关 `BloomPass` | 省 0.5 ms |
| 关 `DepthOfFieldPass` | 省 1 ms |
| MSAA 4x → 2x → Off | 显存 + 带宽 大降 |
| Shadow cascade 4 → 3 | 阴影 pass 省 20% |
| `DiffuseProbeGrid` 密度减半 | 省 GI 采样 |

运行时切 pass：`r_EnablePass "SsaoPass" 0`；持久改 pipeline asset。

### Draw call 数量

- 合并 material（StandardPBR + instancing）。
- 静态物体用 `ForwardSubpassMaterialPipeline` 而非 Deferred（如果 Feature 支持）。
- 频繁变 entity 用 `DynamicDrawSystem` 而不是 per-frame 建 DrawPacket。

### Shader 变体爆炸

**变体**按 ShaderOption 组合 = 2^N。运行时首次遇到某变体会触发**在线编译**，掉帧明显。

对策：
- 用 **Shader Management Console** 工具离线编译 supervariant。
- 把 `.shadervariantlist` 文件列出已知会用的变体，AP 离线编。
- 代码里监听 `ShaderReloadNotificationBus`，在关卡加载时 warmup 常用变体。

### 纹理带宽

- DX12/Vulkan 下用 BC7 / ASTC；避免 RGBA8 全尺寸贴图。
- 预烘焙 mip；别运行时生成。
- Streaming Image + streaming budget。

### 材质属性变化 per-frame

```cpp
material->SetPropertyValue(idx, value);
material->Compile();   // 每帧调 = 每帧上传 SRG
```

热路径别这么干。用不同 material 实例 / 用实例化常数。

---

## 物理优化

### CVar

| CVar | 作用 |
|---|---|
| `ph_ShowColliders 1` | 看 collider 形状 |
| `ph_ShowSceneQueries 1` | raycast 可视化 |
| `ph_MaxTimeStep 0.033` | 子步上限 |
| `physx_SimulationTimeStep` | 模拟步长 |

### 常见省法

- 静态物体用 `PhysXStaticRigidBodyComponent`（不参加 dynamic 模拟）。
- **Sleep**：静止刚体自动 sleep，不占 CPU。别频繁 `Activate` 它们。
- **Simplify collider**：Mesh Collider 慢，用 Primitive（Box/Sphere/Capsule）替代。
- CollisionLayer / Group 过滤：减少 collision 对儿。
- Tick 频率：物理默认 60Hz；若游戏 30fps 可调到 30Hz。

### Raycast 优化

- 每帧不要发多于几百条 raycast。
- 按 CollisionGroup 过滤到目标层。
- 批量用 `AzPhysics::SceneInterface::QueryScene` 多条一次提交。

---

## 网络优化

### 带宽

- `NetworkProperty` 加 `FloatCompression`：`Attribute="FloatCompression(0, 100, 0.1)"`。
- `IsRewindable=false`（不需回滚的属性不保历史，省内存）。
- 降同步频率：ReplicationWindow 实现过滤 / 降采样。
- RPC：非关键用 `IsReliable="false"`。

### CPU

- 每连接的 `EntityReplicationManager` 处理 O(entity × connection)：减少 netbind entity 数（LOD）。
- Authority 端 tick 里别做 client 逻辑（`if (IsNetEntityRoleAuthority())` 守卫）。

### 压缩

启 [Gems/MultiplayerCompression](../Gems/MultiplayerCompression/)；设 `net_UdpCompressor "MultiplayerCompressor"`。

### 监控

- `net_debug 1` → 屏幕 overlay
- `MultiplayerStatSystemComponent` 的数据可以导 CSV

---

## 资产流 / 启动

### 启动时间

1. 启动后首帧前 log 打 `AZ_PROFILE_INTERVAL_START(System, "BootTime", 0)` ～ `...END`。
2. 找最慢的 SystemComponent::Activate。
3. 热点通常：
   - 反射所有类型（Serialize/Behavior Context 注册）—— 数秒
   - 加载 asset catalog —— 随项目规模
   - Gem module 加载 —— 一次加载上百 DLL 可达秒级
   - Bootstrap 初始化 Atom —— 1-2 秒

### 对策

- 延迟初始化：用 `AZ::Interface` 懒注册，首次 Get 时才构造。
- 把重 init 挪到 `OnSystemTick` 首次 tick，让 splash screen 先显示。
- 禁用不用的 Gem（每个都要 reflect 所有类）。

### 关卡加载

Profile 点：

- `.spawnable` 解析
- 所有 PreLoad asset 加载
- Entity `Activate` 激活链

对策：

- 分段 spawn（`SpawnEntities` 指定 index）。
- `AssetLoadBehavior` 按需调：不是关键的降 `QueueLoad` / `NoLoad`。
- 异步 spawn + 等待 barrier。

---

## Editor 性能

Editor 自身性能问题（属性面板卡顿、视口卡顿）不少见：

| 症状 | 对策 |
|---|---|
| 拖动 transform 卡 | EditContext 属性里 `ChangeNotify` 函数别做重活；标成 `AZ::Edit::PropertyRefreshLevels::AttributesAndValues` 而不是整棵重建 |
| 大 Prefab 保存慢 | 检查是不是触发了 "propagate all instances"；能分层就分层 |
| 视口 FPS 低 | Editor pipeline 关不需要的 pass；`ed_PostEffects 0` 临时省 |
| AP 占 CPU | 限制并行 job 数 `/Amazon/AssetProcessor/Settings/Jobs/maxJobs` |
| 选中上万 Entity 后响应慢 | Focus Mode 把范围限制到单个 Prefab |

---

## 频率感知 — 把东西放到最低频率

按"最少 vs 最多"排序，每个操作思考"能放到更低频率吗"：

```
Scene 创建（1 次）
  < Level 加载（< 1/min）
    < 关卡切换（1/min）
      < Entity 激活（偶发）
        < 重要状态变化（秒级）
          < 输入事件（帧级）
            < Tick（60Hz）
              < 渲染每 draw / 每像素
```

**常见误把高频操作放低频**（反了方向）不多；**把低频操作放高频**（Tick 里做只需做一次的）是最常见性能坑。

---

## SRG 频率（渲染）

这里是渲染性能最重要的一个心智模型。按每帧更新次数排序（从便宜到贵）：

| SRG 频率 | 更新次数/帧 | 放什么 |
|---|---|---|
| PerScene | 1 | 全局常数、天空盒 |
| PerView | ~视图数（1-5） | view/proj 矩阵 |
| PerPass | ~pass 数（10-30） | pass 资源 |
| PerMaterial | 材质数 | 材质参数 |
| PerObject | 绘制数（100-10k） | world matrix |
| PerDraw | 每 DrawItem | 实例参数 |
| PerInstance | 硬件实例数 | 骨骼 |

**原则**：**把每个值放到它最低能接受的频率**。误把"不怎么变的值"放 PerObject → 每帧 10k 次 SRG Compile。

---

## Quick Performance Audit（20 分钟自查）

顺序跑：

1. Tracy 接入 + capture 一帧 → 看 CPU flame graph。Top10 函数做了什么？
2. `r_ShowPasses 1` → GPU pass 里哪个最贵？关它看总帧时降多少。
3. `r_ProfileGpu 1` → log 里每 pass ms。
4. 内存快照（启动后 + 关卡加载后 + 玩 5min 后）→ 看 heap 增长。
5. AP 空闲时 `assetdb.sqlite` 大小、Job 失败率。
6. 启用 Gem 数量 —— 真用得到吗？
7. Draw call / triangle 数（RenderDoc Properties）。
8. Shader variant 数 / 编译时间（Shader Management Console）。

---

## 常见 10 个性能陷阱 AI 最容易犯

1. **Reflect 里做 IO / 分配大资源** → 启动期每类型调一次，累加几秒。
2. **每帧 `AZStd::string::format`** → 堆分配风暴。
3. **TickBus handler 里 `BusConnect` / `BusDisconnect`** → 修改迭代中的容器风险 + 性能。
4. **`AZ::Data::Asset<T>` 按值作参数** → 原子计数 + 可能触发 handler 订阅链。用 `const Asset<T>&`。
5. **所有物体都是 `PhysXRigidBody`（动态）** → 实际只是静态几何。用 `StaticRigidBody`。
6. **材质运行时修改 + `Compile()` 每帧** → 每帧上传 SRG。用 Material instance 或 mesh-level override。
7. **Feature 的 `Render()` 里做 CPU 重计算** → Simulate 做计算，Render 只填 GPU。
8. **每个 NPC 一个 Entity + 完整组件栈** → 百个 NPC 就满帧；考虑 LOD / culled update。
9. **所有 asset PreLoad** → 首帧前所有资产加载，启动极慢。
10. **TickOrder 全默认** → 可能 Tick → Transform → Render 链不对，一帧延迟。

继续：[17_ci_cd_guide.md](17_ci_cd_guide.md)、[15_debugging_toolkit.md](15_debugging_toolkit.md)。
