# 15 · 调试工具与技巧集合

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

写 O3DE 代码时**遇到问题基本是这几类**：编译通过但组件不激活、引擎启动崩溃、渲染黑屏、资产加载卡住、联机对不上。本章按症状给出诊断路径。

---

## 日志 / Trace

### 日志宏回顾

| 宏 | 等级 | 场景 |
|---|---|---|
| `AZ_TracePrintf("W", fmt, ...)` | Trace(5) | 详细 |
| `AZ_Printf("W", fmt, ...)` | Info(3) | 普通信息 |
| `AZ_Warning("W", cond, fmt, ...)` | Warning(2) | 条件假警告 |
| `AZ_Error("W", cond, fmt, ...)` | Error(1) | 条件假错误（Editor 弹窗） |
| `AZ_Assert(cond, fmt, ...)` | — | Debug 断点；Release 剔除 |
| `AZ_Fatal(fmt, ...)` | — | 不可恢复 |

第一参 `"Window"` 是过滤 tag。日志面板按它筛。约定用 `"MyGem"` / `"MyGem::Subsystem"`。

### 调整日志等级

在 `.setreg`：

```json
{
    "Amazon": {
        "AzCore": {
            "Runtime": {
                "LogLevel": 5
            }
        }
    }
}
```

或运行时命令行：`--regset "/Amazon/AzCore/Runtime/LogLevel=5"`。

### Editor 日志窗口

**Editor → Tools → Log** 打开。顶上可按 Window 名过滤。右键"Copy" / "Save" 存文本。

### 日志文件位置

| 进程 | 位置 |
|---|---|
| Editor | `@log@/Editor.log`（= `<project>/user/log/Editor.log`） |
| GameLauncher | `@log@/Game.log` |
| AssetProcessor | `<project>/Cache/logs/AssetProcessor/` — 每个 session + 每个 Builder 单独 log |

### 让某 Window 永远开 Debug 级别

```cpp
// 代码里
AZ::Debug::Trace::Instance().SetLogLevel("MyGem", AZ::Debug::LogLevel::Debug);
```

### Remote Console 抓 log

```
Launcher.exe --remote_console --remote_console_port=4600
```

另一端：Editor 菜单 **Tools → Remote Console** 连上 → 可以实时看 log + 打 CVar。无头服务器调试特别有用。

---

## 启动崩 / 组件看不到：诊断顺序

### 1) 读真实 log

启动失败时 Editor 会弹对话框，但**真相在 log 文件**。搜索这几串：

- `"Failed to load dynamic module"` — Gem 动态库加载失败（DLL 依赖缺 / 路径不对 / 架构不对）
- `"Failed to activate entity"` — 服务依赖没满足
- `"Duplicate"` / `"already registered"` — 类型 UUID 冲突
- `"Descriptor not found"` — 组件反射没注册

### 2) Gem 加载失败

**Windows**：
```bat
dumpbin /dependents build\vs2022\bin\profile\Gem.MyGem.dll
```
看依赖哪些 DLL 没在旁边 / 缺失。

**Ubuntu 24.04**：
```bash
ldd build/linux/bin/profile/libGem.MyGem.so            # 看依赖动态库
readelf -d build/linux/bin/profile/libGem.MyGem.so     # 看 rpath / NEEDED
nm -D --undefined-only build/linux/bin/profile/libGem.MyGem.so | head  # 看未解析符号
```

Linux 常见：
- `libQt6*.so not found` → 3rdParty Qt 没拉全 / rpath 没指对；重新 cmake configure
- `libGLIBCXX_3.4.32 not found` → 系统 libstdc++ 过老；`sudo apt install libstdc++6`
- `libasound.so.2 not found` → `sudo apt install libasound2`

**通用**：检查 `<project>/project.json` 的 `gem_names` 有没有它；`build/<dir>/runtime_dependencies/profile/<launcher>.cmake` 里该 Gem 的 DLL/so 有没有被拷贝。

### 3) 组件没出现在 Editor "Add Component" 菜单

按顺序查：

1. `CreateDescriptor()` 有没有被 push 进 Module 的 `m_descriptors`？
2. `Reflect()` 有没有写 `EditContext` 分支？
3. 有没有 `->Attribute(AZ::Edit::Attributes::AppearsInAddComponentMenu, AZ_CRC_CE("Game"))`？
4. Editor 重启了吗？（Reflect 只在启动时注册）
5. Gem 的 `.Tools` alias 有没有 → Editor 加载的是 editor module？

### 4) 组件激活失败（Entity 进入 error state）

日志找 `"Entity '<name>' failed to activate, missing requirement"`。通常是：

- `GetRequiredServices` 声明了 X，但 X 没人提供（没启相应 Gem）
- `GetIncompatibleServices` 冲突
- 依赖的 Entity / Asset 没 ready

运行时在 SystemComponent::Activate 加：

```cpp
AZ::ComponentApplicationBus::Broadcast(
    &AZ::ComponentApplicationRequests::EnumerateEntities,
    [](AZ::Entity* e) {
        if (e->GetState() == AZ::Entity::State::Init) {
            AZ_Warning("Debug", false, "Entity %s stuck in Init",
                        e->GetName().c_str());
        }
    });
```

### 5) 初步测试某 Gem 是否真加载

```cpp
// 某启动期代码
AZ::ModuleManagerRequests::LoadedModuleInfoList modules;
AZ::ModuleManagerRequestBus::BroadcastResult(
    modules, &AZ::ModuleManagerRequests::GetLoadedModules);
for (auto& m : modules) AZ_Printf("Debug", "Loaded: %s\n", m.m_name.c_str());
```

或者：Editor → **Help → About → Installed Gems**（如果该 Editor 版本有这个面板）。

---

## EBus 不工作 / 收不到事件

**典型症状**：发了 `Event(id, &...)` 但 handler 没被调。按顺序查：

1. **Handler `BusConnect` 了吗**：在 `Activate` 里 `BusConnect()` / `BusConnect(id)`，`Deactivate` 里 `BusDisconnect()`。
2. **ID 对吗**：`Event(id, ...)` 的 id 和 `BusConnect(id)` 的 id 必须完全相等。`AZ::EntityId` 对比 debug：`AZ_Printf("D", "id=%llu", (AZ::u64)id);`
3. **地址政策匹配吗**：`AddressPolicy::Single` 的 bus 用 `Broadcast`，不是 `Event(id,...)`。用错 silently 无效。
4. **handler 已析构却没 disconnect**：bus 还持悬垂指针，下次广播 crash。检查 `Activate/Deactivate` 配对。
5. **线程问题**：`LocklessDispatch` 的 bus 跨线程广播 → 数据竞争。改 `MutexType = AZStd::mutex`。
6. **BroadcastResult / EventResult 的 result 没初始化**：

```cpp
float hp = -1.f;  // 🔑 初值，若没 handler 会保持 -1
HealthBus::EventResult(hp, id, &HealthRequests::GetHealth);
if (hp < 0) { /* 没 handler 响应 */ }
```

### 检查谁在订阅

```cpp
size_t count = 0;
MyBus::EnumerateHandlersId(entityId, [&count](MyBus::InterfaceType*){ ++count; return true; });
AZ_Printf("Debug", "Handlers at %llu: %zu", (AZ::u64)entityId, count);
```

### TickBus 顺序问题

装 **TickBusOrderViewer** Gem（[Gems/TickBusOrderViewer](../Gems/TickBusOrderViewer/)），在 Editor 跑：可视化所有 TickBus 订阅者的 `GetTickOrder()` 顺序。

---

## 断言 / 崩溃排查

### 断点不命中？

- Release 构建下 `AZ_Assert` 被剔除：用 `AZ_Error` + `if` 代替。
- 符号没加载：检查 `.pdb` 在 exe 同目录。
- Module 动态加载，用 "Modules" 窗口（VS）确认 DLL 加载时间。

### 调用栈很短？

多线程崩溃常被工作线程吃掉栈。方法：

- VS 启用 **Debug → Windows → Parallel Stacks**。
- 跑 Windows 开 `Dr. Memory` / AppVerifier。
- 用 crash dump（`Windows + R → drwtsn32` 或启用 Windows Error Reporting）抓 minidump，事后用 `windbg -z` 分析。

### 引擎自带的 CrashReporting Gem

启用 [Gems/CrashReporting](../Gems/CrashReporting/) 后，launcher 崩溃时自动生成 minidump。配合 [scripts/build/build_failure_rca](../scripts/build/build_failure_rca/) 可批量分析。

---

## 渲染问题

### 全屏黑 / 花屏

按顺序：

1. **Bootstrap 有没有启**：`Atom_Bootstrap` Gem + log 里 `BootstrapSystemComponent::Activate`。
2. **RenderPipeline 加载了吗**：搜 log `"Loaded RenderPipeline: MainPipeline"`。
3. **有 MainCamera View 吗**：没相机 = 没 view = 什么都不画。
4. **CVars**：
   - `r_enableAtom 1`
   - `r_ShowPasses 1` 看 pass tree
5. **开 RenderDoc / PIX 抓帧**：对着 exe 附加，capture 一帧 → 看 draw call 有没有 / 输出是不是全黑（可能是 shader 编译失败）。

### 某材质显示错 / 紫色

紫色 fallback = 引擎的"找不到 material/shader"标志。

- AP GUI 查这个 `.material` 或它引用的 `.azmaterialtype` / `.azshader` 有没有跑成功。
- `r_ReloadShader 1` / `r_ReloadMaterial` 强刷。
- Editor 选中资产 → **Browse → Reprocess source asset**。

### Shader 编译失败

AP GUI → Jobs 标签 → 找 `MyShader.shader` → 看 error 列。azslc 错误通常直白；常见：

- `.azsli` include 路径错
- SRG 里用了未定义的结构体
- Option 声明在 SRG 外部

### GPU 调试命令

| CVar | 作用 |
|---|---|
| `r_ShowPasses 1` | Pass tree UI |
| `r_EnablePass "SsaoPass" 0` | 关某 pass |
| `r_ReloadShader 1` | 全部重编 |
| `r_ProfileGpu 1` | GPU timing 到 log |
| `r_ShowGpuMemory 1` | 显存统计 |
| `r_DrawListDebug 1` | DrawList 详情 |

---

## 资产 / AP 问题

### 症状：Editor 打开资产转圈 / "Waiting for asset"

1. **AP GUI 启动了吗**：Editor 右下角看到"AP connected"标志？没连 → 启 AssetProcessor.exe。
2. **Queue 里在排队吗**：AP GUI → Jobs 标签。
3. **Job 失败了吗**：Failed 栏里有 → 双击看日志。

### 症状：改源文件后产物不变

- Builder 的 `m_version` 忘涨：加 `m_version++` 重编。
- 源文件 fingerprint 没变（纯打了空格）：AP 优化跳过。**Reprocess** 强制。
- AP 没看到该路径（不在 scan folder 里）。

### 数据库直查

```bash
# 用 SQLite CLI 或 DB Browser 打开
sqlite3 <project>/Cache/assetdb.sqlite

-- 查某文件的 job 状态
SELECT J.JobKey, J.Status, J.Fingerprint, J.ErrorCount
FROM Jobs J JOIN Sources S ON J.SourcePK = S.SourceID
WHERE S.SourceName LIKE '%hero%';

-- 查某 source 产了什么
SELECT P.ProductName, P.SubID
FROM Products P JOIN Jobs J ON P.JobPK = J.JobID
JOIN Sources S ON J.SourcePK = S.SourceID
WHERE S.SourceName = 'levels/main.prefab';

-- 查失败的 job
SELECT S.SourceName, J.JobKey, J.ErrorCount
FROM Jobs J JOIN Sources S ON J.SourcePK = S.SourceID
WHERE J.Status != 3 OR J.ErrorCount > 0;
```

### 命令行批量重跑

```bash
# 只跑 PC 平台某 Gem 的资产
bin/profile/AssetProcessorBatch \
    --regset "/Amazon/AssetProcessor/Settings/Platforms/pc/tags=+tools" \
    --project-path <path> \
    --platforms=pc

# 指定重跑某源文件（把 Cache 里的产物先删也行）
```

### SerializeContextTools dry run

```bash
bin/profile/SerializeContextTools dumpfiles \
    --file <somedata.prefab>  # 打印结构

bin/profile/SerializeContextTools convert \
    --source <old.prefab> --format binary  # 强制跑一次版本转换
```

---

## 联机 / Multiplayer

### 症状：客户端连不上 server

1. 防火墙 / 端口（默认 UDP 33450）。
2. Server 先起还是 client 先起顺序：server 先 listen。
3. server 用的是 `.ServerLauncher` 吗？（`.GameLauncher` 跑 server 模式也行但 CVar 不同）
4. log 搜 `"Failed to connect"` / `"Disconnect reason"`。

### CVar 调试

| CVar | 作用 |
|---|---|
| `net_debug 1` | 网络统计输出到 log + 屏幕 |
| `net_DumpStats` | 一次打印 |
| `sv_port 33450` | server 监听端口 |
| `cl_serveraddr 127.0.0.1` | client 连向 |
| `cl_serverport 33450` | |
| `net_LatencyMs 100` | 本地模拟延迟 |
| `net_PacketLossPct 5` | 本地模拟丢包 |
| `net_UdpUseEncryption 1` | 启 DTLS |

### 组件没同步？

- `NetBindComponent` 加到 Entity 了吗？
- `MultiplayerComponent` / AutoComponent 生成的基类 `m_descriptors` 注册了吗？
- 角色判断错：客户端不该执行 Authority 逻辑。用 `IsNetEntityRoleAuthority()` 守卫。

### AutomatedTesting 的 test 场景

运行 `AutomatedTesting/Gem/Code/Source/AutoGen/NetworkTestPlayerComponent.AutoComponent.xml` 对应的场景做 sanity check — 如果这个也不同步，说明本地网络环境问题。

---

## Python / ScriptCanvas / Lua 调试

### Lua

- 装 **LuaIDE**（[Code/Tools/LuaIDE](../Code/Tools/LuaIDE/)），`lua_enableDebug 1` 后从 IDE 连进程。
- 基本打印：`Debug.Log("msg")`（反射进 Lua 的 C++ API）。
- 脚本没生效：AP 没编到 `.luac`；Entity 没重激活。

### ScriptCanvas

- Editor **View → Script Canvas** 打开画布；在节点右键 "Break on execute" 下断点。
- Translation 模式（SC → Lua）时可以用 LuaIDE。
- 节点不出现：BehaviorContext 里 `Category` 没设 / `ExcludeFrom=List`。

### Python

- **Editor → Tools → Python Console** 交互 REPL。
- `import traceback; traceback.print_exc()` 在脚本里捕异常。
- `sys.path` 加自己脚本目录。
- **QtForPython** 可以直接 `from PySide2 import QtWidgets` 做工具窗口。

---

## 内存问题

### 引擎自带

```
# 启动参数
--allocator_trace 1    # 追踪分配源
--allocator_record_memory 1
```

运行时：

```cpp
AZ::AllocatorInstance<AZ::SystemAllocator>::Get().GetRecords()->PrintSnapshot();
```

### 泄漏 / 越界

- **Windows**：Application Verifier 开 AppVerif，heap checks。
- **Ubuntu 24.04**：
  ```bash
  # 临时加 ASan（clang-17 默认就带）
  cmake -B build/linux-asan -S . -G Ninja \
        -DCMAKE_BUILD_TYPE=debug \
        -DCMAKE_C_COMPILER=clang-17 -DCMAKE_CXX_COMPILER=clang++-17 \
        -DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer" \
        -DCMAKE_LINKER_FLAGS="-fsanitize=address" \
        -DLY_3RDPARTY_PATH=$HOME/o3de-packages
  # 注意 ASan 会和某些 3rdParty (Mimalloc) 冲突；可能要禁用自定义 allocator
  ```
- **其它 Linux 工具**：
  - Valgrind memcheck（慢但仔细）：`valgrind --leak-check=full ./Editor ...`
  - `strace -f -e trace=openat,read,write ./Editor ...`（文件系统调用）
- CMake 里找 `LY_ENABLE_ASAN` 之类选项（如果有该开关，以当前仓库为准）。

### 常见 leak 源

- 裸 `new` 没对应 `delete`（用 `aznew` + `AZStd::unique_ptr`）。
- `AZ_CLASS_ALLOCATOR` 和实际分配的 allocator 不一致。
- Asset 循环引用（A 引用 B，B 引用 A）。
- EBus Handler 析构没 Disconnect → 广播时 crash。

---

## Editor / UI 问题

### 视口拾取不响应

- `EditorComponentSelectionRequestsBus` 有 handler 吗？
- `EditorEntityVisibilityNotificationBus` 订阅了吗？
- Focus Mode 可能锁定了别的 prefab：**Escape** 退 Focus。

### Undo 不工作

- 改数据时裹 `AzToolsFramework::ScopedUndoBatch`：
  ```cpp
  AzToolsFramework::ScopedUndoBatch undo("My Change");
  // ... 改数据
  undo.MarkEntityDirty(id);
  ```
- 没 `SetDirty()` 也会让 Editor 不知道要 save。

### Qt 控件不更新

- `PropertyEditorGUIMessages::Bus::Broadcast(&...::RequestWrite, widget)` 通知写回。
- `RequestRefresh` 强制刷新属性树。

---

## 常用 CVar 速查

| 前缀 | 领域 |
|---|---|
| `r_` | 渲染（`r_ReloadShader`, `r_ShowPasses`, `r_ProfileGpu`, `r_EnablePass`） |
| `net_` / `cl_` / `sv_` | 网络（`net_debug`, `sv_port`, `cl_serveraddr`） |
| `ph_` | 物理（`ph_ShowColliders`, `ph_Debug`, `ph_ShowSceneQueries`） |
| `ed_` | Editor（`ed_ShowFPS`, `ed_LogLevel`） |
| `ai_` | AI / Nav |
| `audio_` | 音频 |
| `sys_` | 系统（`sys_MaxFps`） |
| `bg_` / `imgui_` | debug UI |

**列举所有 CVar**：console 里输入 `cvarlist` 或 `help`。

---

## 诊断命令模板

把这套"一句话诊断"记熟，90% 的 debug 能在几分钟内找到路径：

```
# Gem 加载问题
dumpbin /dependents bin\profile\Gem.MyGem.dll
grep "Failed to load" <project>/user/log/Editor.log

# 组件问题
grep "MyComponent" <project>/user/log/Editor.log
grep "<GEM-UUID>" <project>/user/log/Editor.log

# AP 问题
sqlite3 <project>/Cache/assetdb.sqlite "SELECT * FROM Jobs WHERE Status != 3 LIMIT 20"
ls <project>/Cache/logs/AssetProcessor/

# 渲染问题
RenderDoc → attach to launcher → F11 capture

# 网络问题
remoteconsole → net_debug 1

# 内存问题
--allocator_trace 1 --allocator_record_memory 1
```

---

## 常用 "为什么" → "去看这"

| 症状 | 第一反应查 |
|---|---|
| 编译过但 Editor 启动崩 | log 中 `Failed to load dynamic module` + `dumpbin` |
| 组件菜单没出现 | Editor module 的 `m_descriptors` + `Reflect` 的 EditContext |
| Entity 激活失败 | `GetRequiredServices` + log 中 "missing requirement" |
| EBus 收不到 | `BusConnect` 配对 + id 正确 + AddressPolicy 匹配 |
| 渲染黑屏 | RenderDoc capture + `r_ShowPasses` |
| 材质紫色 | AP 重跑 + `r_ReloadMaterial` |
| AP 卡住 | AP GUI Jobs 标签 + assetdb.sqlite |
| Version converter 报错 | SerializeContext `Version(n+1)` + 写 `VersionConverter` |
| Prefab 加载丢字段 | 同上 |
| 联机不同步 | `net_debug 1` + `NetBindComponent` |
| 脚本改了没生效 | AP 编译 `.luac` / `.scriptcanvas` + Entity 重激活 |
| CVar 不生效 | 看 `ConsoleFunctorFlags::ReadOnly` + 发起源（CLI / setreg / PerformCommand） |
| gtest 跑不起来 | PAL_TRAIT_BUILD_TESTS_SUPPORTED + `ly_add_googletest` |

继续：[16_performance_checklist.md](16_performance_checklist.md)、[17_ci_cd_guide.md](17_ci_cd_guide.md)。
