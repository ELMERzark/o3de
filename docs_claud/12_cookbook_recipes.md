# 12 · 常见任务菜谱（Cookbook）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

每条都是"从零到能跑起来"的最小可行步骤。复杂场景叠加多条即可。

---

## R1. 新建一个 Gem（含运行时 + Editor + 测试）

```bash
scripts/o3de.bat create-gem -gn MyGem \
    -gp G:/AXX/O3DE/o3de/Gems/MyGem \
    --template-name DefaultGem
scripts/o3de.bat register --gem-path G:/AXX/O3DE/o3de/Gems/MyGem
scripts/o3de.bat enable-gem -gn MyGem -pp G:/AXX/O3DE/o3de/AutomatedTesting
cmake --build build/vs2022 --config profile \
      --target AutomatedTesting.GameLauncher Editor Gem.MyGem Gem.MyGem.Editor
```

**验证**：Editor 里 "Add Component" 菜单下能看到模板自带的组件。

---

## R2. 加一个运行时组件

1. **文件**：
   - `Code/Include/MyGem/MyCoolComponentBus.h`（EBus 接口）
   - `Code/Source/MyCoolComponent.h`
   - `Code/Source/MyCoolComponent.cpp`

2. **骨架**（见 [02_azcore.md](02_azcore.md) 的完整示例）：
   ```cpp
   class MyCoolComponent
       : public AZ::Component
       , public AZ::TickBus::Handler
   {
   public:
       AZ_COMPONENT(MyCoolComponent, "{<generate-uuid>}");
       static void Reflect(AZ::ReflectContext*);
       static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType&);
       static void GetRequiredServices(AZ::ComponentDescriptor::DependencyArrayType&);
   protected:
       void Activate() override;
       void Deactivate() override;
       void OnTick(float, AZ::ScriptTimePoint) override;
   };
   ```

3. **注册**到 `Source/MyGemModule.cpp` 的 `m_descriptors`：
   ```cpp
   m_descriptors.insert(m_descriptors.end(), {
       MyCoolComponent::CreateDescriptor(),
   });
   ```

4. **加到 `*_files.cmake`**：
   - `mygem_private_files.cmake` 加 `Source/MyCoolComponent.{h,cpp}`
   - `mygem_api_files.cmake` 加 `Include/MyGem/MyCoolComponentBus.h`

5. **Editor 侧（如果要在编辑器里加/调）** —— 见 R3。

---

## R3. 为一个运行时组件加 Editor 版本

1. **新增**：
   - `Code/Source/EditorMyCoolComponent.{h,cpp}` 派生 `AzToolsFramework::Components::EditorComponentBase`
   - 实现 `BuildGameEntity(AZ::Entity*)` 把 runtime 组件 `CreateComponent<MyCoolComponent>()`
   - Editor Uuid **要与 runtime 不同**

2. **注册**到 `Source/MyGemEditorModule.cpp` 的 `m_descriptors`。
3. **加入** `mygem_editor_private_files.cmake` / `mygem_editor_shared_files.cmake`。
4. **服务匹配**：Editor 组件的 `GetProvidedServices/Required/Incompatible` 必须和 runtime 组件一致，否则 prefab 保存后行为漂移。
5. **Reflect 的 EditContext** 只在 Editor 组件里写；runtime 组件只做 SerializeContext 和 BehaviorContext。

---

## R4. 新建一个 Notification / Request EBus

1. **文件**：`Code/Include/MyGem/MyServiceBus.h`
2. **接口**见 [02_azcore.md](02_azcore.md) EBus 节。
3. **订阅方**：组件派生 `MyNotificationBus::Handler` + 在 `Activate/Deactivate` 里 BusConnect/Disconnect。
4. **调用方**：`MyNotificationBus::Event(id, &MyNotifications::OnXxx, args...)`。
5. **反射给脚本**（可选）：`BehaviorContext::EBus<MyRequestBus>("MyRequestBus")->Event(...)` + `Handler<...>`。

---

## R5. 订阅每帧更新

```cpp
// .h
class Foo : public AZ::Component, public AZ::TickBus::Handler { ... };

// .cpp
void Foo::Activate()   { AZ::TickBus::Handler::BusConnect(); }
void Foo::Deactivate() { AZ::TickBus::Handler::BusDisconnect(); }
void Foo::OnTick(float dt, AZ::ScriptTimePoint) { /* ... */ }
int  Foo::GetTickOrder() const override { return AZ::TICK_GAME; }
```

要"系统级"tick（可能比帧快）→ 用 `AZ::SystemTickBus`。

---

## R6. 读取 Settings Registry 配置

```cpp
auto* sr = AZ::SettingsRegistry::Get();
AZ::s64 tickRate = 60;
sr->Get(tickRate, "/O3DE/MyGem/TickRate");
```

默认值放 `Gems/MyGem/Registry/mygem.setreg`：

```json
{ "O3DE": { "MyGem": { "TickRate": 60 } } }
```

---

## R7. 加控制台变量 / 命令

```cpp
#include <AzCore/Console/IConsole.h>

AZ_CVAR(float, mg_playerSpeed, 5.f, nullptr, AZ::ConsoleFunctorFlags::Null, "Player speed");

AZ_CONSOLEFREEFUNC(mg_kill, AZ::ConsoleFunctorFlags::Null, "Kill player", [](){
    PlayerRequestBus::Broadcast(&PlayerRequests::Kill);
});
```

同名前缀（`mg_`）方便在 Editor 控制台模糊匹配。

---

## R8. 暴露 C++ 给 Lua / ScriptCanvas

在组件的 `Reflect()` 里：

```cpp
if (auto* bc = azrtti_cast<AZ::BehaviorContext*>(context))
{
    bc->Class<MyCoolComponent>("MyCool")
        ->Attribute(AZ::Script::Attributes::Category, "MyGem")
        ->Method("SetSpeed", &MyCoolComponent::SetSpeed)
        ->Property("speed",
                   BehaviorValueProperty(&MyCoolComponent::m_speed));
}
```

验证：打开 ScriptCanvas 编辑器 → 节点面板 → Category "MyGem" → "MyCool" 下可见方法。

---

## R9. 加一种新的资产（源 → 产物）

1. **反射**你的资产类（派生 `AZ::Data::AssetData`，`AZ_RTTI` + `AZ_CLASS_ALLOCATOR`）。
2. **写 AssetHandler**（派生 `AZ::Data::AssetHandler` 或用 `GenericAssetHandler<T>`）—— 注册/注销在 SystemComponent。
3. **Builder**：新建 Editor 模块里的 SystemComponent，在 `Activate` 里 Broadcast `RegisterBuilderInformation`，`ProcessJob` 里读 source → 写 product（可用 `AZ::Utils::SaveObjectToFile`）。
4. **加到 `*.Builders` CMake 别名**。
5. **验证**：放源文件到项目 Assets/ 下 → AP GUI 应该跑一次 job → Cache 里出产物。

详见 [07_asset_pipeline.md](07_asset_pipeline.md)。

---

## R10. 运行时动态生成实体

用 Spawnable（优先）：

```cpp
#include <AzFramework/Spawnable/SpawnableEntitiesInterface.h>

auto* svc = AzFramework::SpawnableEntitiesInterface::Get();
AZ::Data::Asset<AzFramework::Spawnable> asset = /* 通过 AssetCatalog 拿到 */;
m_ticket = AzFramework::EntitySpawnTicket(asset);
svc->SpawnAllEntities(m_ticket);
```

销毁：`svc->DespawnAllEntities(m_ticket);`

---

## R11. 加 gtest

1. 新建 `Code/Tests/MyCoolComponentTests.cpp`：
   ```cpp
   #include <AzTest/AzTest.h>
   TEST(MyCool, Construct) { MyGem::MyCoolComponent c; EXPECT_FLOAT_EQ(c.GetSpeed(), 0.f); }
   AZ_UNIT_TEST_HOOK(DEFAULT_UNIT_TEST_ENV);   // 只在其中一个 TU 里
   ```
2. 加到 `mygem_tests_files.cmake`。
3. 确保 `MyGem.Tests` target 在 CMakeLists 里定义（见 [06_build_and_cmake.md](06_build_and_cmake.md)）。
4. 跑：`ctest --test-dir build/... -R MyGem`.

---

## R12. 加 Editor 菜单项

```cpp
// Editor SystemComponent 的 Activate 里
auto* am = AZ::Interface<AzToolsFramework::ActionManagerInterface>::Get();
auto* mm = AZ::Interface<AzToolsFramework::MenuManagerInterface>::Get();
if (!am || !mm) return;

AzToolsFramework::ActionProperties props;
props.m_name = "Hello From MyGem";
props.m_category = "MyGem";
am->RegisterAction("o3de.context.editor", "mygem.action.hello", props,
                   [](){ AZ_TracePrintf("MyGem", "hi"); });

mm->AddActionToMenu("o3de.menu.tools", "mygem.action.hello", 1000);
```

Python 版见 [09_scripting.md](09_scripting.md)。

---

## R13. 加第三方依赖

方案 A（官方已有包）：
```cmake
BUILD_DEPENDENCIES PRIVATE 3rdParty::OpenSSL
```

方案 B（新外部库）：
1. 把 `xyz-1.2.3-windows.tgz` 扔到 `LY_3RDPARTY_PATH`。
2. `cmake/3rdParty/Platform/Windows/BuiltInPackages_windows.cmake` 加：
   ```cmake
   ly_associate_package(PACKAGE_NAME xyz-1.2.3-windows TARGETS Xyz PACKAGE_HASH <sha>)
   ```
3. `Findxyz.cmake` 里 `ly_add_external_target(NAME Xyz ...)`.
4. 用 `3rdParty::Xyz`。

---

## R14. 把 Entity 持久化到存档

1. 反射要保存的数据（`SerializeContext::Class<T>()->Version(n)->Field(...)`）。
2. 用 `AZ::Utils::SaveObjectToFile("@user@/save0.dat", AZ::DataStream::ST_BINARY, &obj);`
3. 读：`AZ::Utils::LoadObjectFromFile<T>("@user@/save0.dat");`
4. **涨 Version** 和写 `VersionConverter` 是必须的，一旦字段变就必须做。

---

## R15. 日常"引擎启动看不到我的组件" 诊断

按顺序检查：

1. `mygem.setreg` / `project.json` 里 Gem 是不是被 enable？
2. `Gem_MyGem.dll` / `.so` / `.dylib` 是否在 `bin/profile/` 里？
3. 模块的 `m_descriptors` 有没有 push 这个组件？
4. `GetRequiredServices()` 依赖的服务有没有被项目启用的其它 Gem 提供？
5. Editor log / Launcher log 里搜 Gem 名 → 看加载失败原因。
6. `Reflect` 分支有没有漏写 `EditContext`？没写的话 Editor UI 显示不了它。

---

## R16. Prefab 反向：源 `.prefab` 里看谁加了哪个组件

`.prefab` 是 JSON：用文本编辑器搜组件 Uuid（就是 `AZ_COMPONENT` 第二参数），能立刻找到组件实例。

## R17. 热重载 / 快速迭代

- Lua / ScriptCanvas / Material / Shader：改完存，AP 编译，Editor viewport 秒级生效。
- C++：没有热重载；需要编译 → Editor 重启（Editor 支持 `File → Reload Current Level` 避免重开）。
- 反射格式变化：需要 "AP 重跑相关源资产" + Editor 重启，否则 spawnable 会用旧结构。

---

继续：[13_ai_context_guide.md](13_ai_context_guide.md)。
