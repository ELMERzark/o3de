# 13 · 给其他 AI 的"使用说明书"

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

> 这份文档是给**其他 AI 模型**看的元指令。把它和挑出来的几个其它 md 一起塞进对方的 system prompt / context window。

## 你在帮一个什么项目

你正在协助修改 **O3DE (Open 3D Engine)** 的一个本地 checkout（仓库根路径由用户给）。这是一个 C++17 + Python 3 + CMake 的大型游戏引擎项目。代码风格、框架抽象、构建系统都**不是行业通用默认**，所以：

1. **不要套用 Unreal/Unity/godot 的假设**。O3DE 的"Component"不是 `UActorComponent`、不是 `MonoBehaviour`；EBus 不是 UE 的 `Delegate`；Gem 不是 UE 的 `Plugin`（形似但生命周期不同）。
2. **不要套用默认 C++/STL 习惯**。代码用 `AZStd::` / `AZ_CLASS_ALLOCATOR` / `AZ_RTTI` 等自家设施，混用 `std::vector` 会隐性跨堆分配导致崩溃。
3. **不要编造 Uuid / 类名 / 路径**。不知道就明说，或让用户生成 Uuid。

## 读文件的推荐顺序

接到任务后，按需读。**不要"读整棵树"**，仓库太大。

1. 先读 [01_overview.md](01_overview.md) —— 知道这东西长啥样。
2. 读 [11_conventions_and_patterns.md](11_conventions_and_patterns.md) —— 对齐代码风格。
3. 按任务类型读对应的那一份：
   - 改 C++ 组件 → [02_azcore.md](02_azcore.md) + [03_azframework.md](03_azframework.md)
   - 改 Editor 功能 → [04_aztoolsframework.md](04_aztoolsframework.md) + [05_gems_and_modules.md](05_gems_and_modules.md)
   - 改构建 → [06_build_and_cmake.md](06_build_and_cmake.md)
   - 改资产/管线 → [07_asset_pipeline.md](07_asset_pipeline.md)
   - 改渲染 → [08_rendering_atom.md](08_rendering_atom.md)
   - 改脚本 → [09_scripting.md](09_scripting.md)
   - 改网络/物理 → [10_networking_physics.md](10_networking_physics.md)
4. 找"怎么做"模板 → [12_cookbook_recipes.md](12_cookbook_recipes.md)

## 动手前先问 / 自答的 3 件事

### ① 这个东西该住在哪

- 运行时逻辑 → 某 Gem 的 `Code/Source/`
- Editor-only（Qt / Prefab / Python 桥）→ 同 Gem 的 `Code/Source/` 里 editor 子模块
- 底层公共能力（EBus / 接口 / 数学）→ `AzCore` 或 `AzFramework`（**需要非常谨慎**，改核心影响面大，除非用户明确要求）
- 资产类型 / 资产格式 → `AssetBuilder` + `GenericAssetHandler`

### ② 我需要动几个位置

典型添加一个组件，至少要同步改 **3 处**：

1. C++ 实现 (`.h`/`.cpp`)
2. 对应的 `*_files.cmake`
3. Gem Module 的 `m_descriptors` 列表

如果是 Editor 组件：另加 Editor 版的 3 处（headers, files.cmake, EditorModule）。

**遗漏这些的修改编译能过，但运行时"组件看不到/不生效"—— 这是 O3DE 常见 AI bug。**

### ③ 会影响序列化吗

修改任何用 `SerializeContext::Class<T>()->Field(...)` 注册的字段布局（加/删/重命名/改类型）：

- 必须 `->Version(n+1)`
- 通常需要 `->Version(n+1, &Foo::VersionConverter)`
- 否则老的 `.prefab` / `.spawnable` / save file 加载崩

这条**非常容易被 AI 忘记**。

## 回答用户问题时的好习惯

1. **给路径用仓库相对路径**（`Gems/MyGem/Code/...`），不要用绝对路径。
2. **UUID 留占位**：写 `"{<replace-with-fresh-uuid>}"`，并提醒用户替换 + 怎么生成。
3. **先最小可编译版本**，再叠装饰：用户常说"帮我写个组件"，先给一个 Activate/Deactivate/Reflect 空架子，跑得起来再谈功能。
4. **多文件修改一次给完**：把相关的 `.h` / `.cpp` / `*_files.cmake` / `Module.cpp` 改动一次列出；避免"改了 .cpp 但没改 cmake"的悬空状态。
5. **引用宏 / 接口时附一个"所在头"**：`AZ_COMPONENT (AzCore/Component/Component.h)`。用户不一定记得从哪 include。
6. **不确定时建议 Grep / 读已有实现**。O3DE 自带的 Gem（例如 `LmbrCentral`, `CommonFeatures`）是最准的范本。

## 警惕的 "看起来像但不是" 陷阱

| 你可能以为 | 实际 |
|---|---|
| `AZ::Component` 有 `Start()` / `Update()` 虚函数 | 没有。生命周期是 `Init`/`Activate`/`Deactivate`；更新要订阅 `TickBus` |
| `AZ::EBus` 类似 boost::signals | 更像"命名有状态总线"，带 Address/Handler 政策，订阅/广播有严格接口 |
| `AZStd::string` 等价 `std::string` | 接口很像但内部 allocator 不同，**不要**和 `std::string` 互换 |
| Gem 之间通过 include 互相调 | 应该通过 EBus / `AZ::Interface<T>` 通信，直接 include 跨 Gem 头会卡 CMake 依赖 |
| "Prefab 直接在运行时加载" | 不。`.prefab` 是源，运行时用 `.spawnable`（AP 编译产物） |
| 渲染改 pass 要重编 C++ | 管线是 JSON 资产驱动，常见修改不需要 C++ |
| 控制台用 `cout` 看 | 默认看不到；用 `AZ_TracePrintf` |

## 回答模板（给其他 AI 参考）

> 用户："帮我加一个会让 Entity 每帧移动的组件"
>
> 好的回答骨架：
>
> 1. **目标**：加一个 `AutoMoverComponent`（AZ::Component + TickBus::Handler），挂到 MyGem Gem。
> 2. **要改的文件**（列出 4~5 个文件路径 + 每个文件干啥）
> 3. **按文件给 diff / 完整内容**，`.h` 写 AZ_COMPONENT / Reflect / Activate；`.cpp` 实现；`*_files.cmake` 加两行；`MyGemModule.cpp` 的 descriptors 加一行。
> 4. **验证步骤**：`cmake --build ... --target Gem.MyGem` → 开 Editor → Add Component → MyGem → AutoMover。
> 5. **注意**：Uuid 占位、Version 涨号、依赖的服务（TransformService）说明。

## 如果用户让你"读仓库"

- 仓库大，不要一次性 `ls -R`。
- 先看 [engine.json](../engine.json) 拿到启用的 Gem 列表。
- 需要代码细节时，按关键词 grep；`Code/Framework/Az*` 和 `Gems/<相关 Gem>/Code` 是主要猎场。
- 平台相关的东西总在 `Platform/<OS>` 子目录 + `*_Platform.inl`。
- **跳过** `build/`, `3rdParty/` 下载缓存, `Cache/`, `python/runtime/`, `.gitignore` 列出的生成物。

## 如果编译错误

- **首发**：检查 `*_files.cmake` 是否加了新文件（找 `undefined reference` / `missing header`）。
- **LNK2019 / undefined symbol**：99% 是 Gem 依赖 / `BUILD_DEPENDENCIES` 没配对。
- **AZ_TRAIT_*** 之类编译报错：Platform 分支缺同步。
- **Gem load fail**：看 Launcher log 找 missing symbol / uuid collision。

## 最后

- 有不确定，**宁可问用户**，别猜。O3DE 的一个错误提交能带崩整个场景的反序列化。
- 用户要求"修复编译"时，**先读上下文**，别直接删报错行 —— 错的往往是依赖配置、不是代码逻辑。
- 引用这份文档里的某页可以直接说 "按 04_aztoolsframework.md 节的模式"。

完。
