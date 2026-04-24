# 05 · Gem 与模块系统（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## 为什么特别重要

O3DE 里**一切功能都是 Gem**。渲染、物理、脚本、UI、联网 … 都是 Gem。哪怕 `LmbrCentral` 这种"看上去像核心"的东西也是 Gem。理解 Gem 结构是开发的核心技能。

本章目标：**读完后能从零开始新建一个 Gem，含 Runtime 模块 + Editor 模块 + AutoGen + 单元测试**，并理解 Gem 如何被发现、加载、链接。

---

## Gem 物理结构 — 以真实 Gem 为参照

以 [Gems/LmbrCentral/](../Gems/LmbrCentral/)（O3DE 最基础的 Gem 之一）为例：

```
Gems/LmbrCentral/
├── gem.json                         元数据（名字、版本、依赖、tags）
├── preview.png                      Editor 显示用图标
├── CMakeLists.txt                   外层入口：add_subdirectory(Code)
├── Assets/                          源资产
│   ├── Editor/Icons/Components/       组件图标
│   └── Test/                          测试资产
├── Registry/                        默认 setreg
└── Code/
    ├── CMakeLists.txt               ★ 定义所有 CMake target（核心！）
    ├── include/LmbrCentral/          对外公开头（.API 模块用）
    │   ├── Animation/
    │   ├── Audio/
    │   ├── Component/
    │   ├── Shape/                      
    │   └── ... (按子系统分)
    ├── Source/                       运行时实现（.Private）
    │   ├── LmbrCentral.cpp              Runtime Module 入口
    │   ├── LmbrCentral.h                Module 类定义
    │   ├── LmbrCentralEditor.cpp        Editor Module 入口（仅 host tools）
    │   ├── Audio/ / Shape/ / ...         各子系统 .cpp
    │   ├── Editor/                      editor-only 代码（与 Source/ 并列）
    │   └── Builders/                    AssetBuilder 实现
    │       ├── SliceBuilder/
    │       └── CopyDependencyBuilder/
    ├── Mocks/LmbrCentral/            单元测试 Mock
    ├── Platform/                     PAL：平台特化
    │   ├── Windows/
    │   │   ├── PAL_windows.cmake        TRAIT 定义
    │   │   ├── lmbrcentral_*_files.cmake  平台特有源文件
    │   │   └── *.cpp
    │   ├── Linux/ / Mac/ / Android/ / iOS/
    │   └── Common/
    ├── Tests/                        gtest 源
    └── *_files.cmake                 源文件清单（解耦 CMake）
```

### `*_files.cmake` 规范（重要约定）

典型 Gem 有多份（与 CMake target 一一对应）：

| 文件 | 被谁 include | 内容 |
|---|---|---|
| `lmbrcentral_api_files.cmake` | `.API` target | 公开头（`include/<Name>/*.h`） |
| `lmbrcentral_private_files.cmake` | `.Static` target | runtime `.cpp/.h` |
| `lmbrcentral_shared_files.cmake` | 主 GEM_MODULE target | 只 `LmbrCentral.cpp`（Module 入口） |
| `lmbrcentral_editor_files.cmake` | `.Editor.Static` | editor-only 实现 |
| `lmbrcentral_editor_shared_files.cmake` | `.Editor` GEM_MODULE | editor Module 入口 |
| `lmbrcentral_tests_files.cmake` | `.Tests` | gtest 源 |
| `Platform/<os>/platform_<os>_files.cmake` | 对应 target | 平台特有源 |

内容规范：

```cmake
# lmbrcentral_private_files.cmake
set(FILES
    Source/LmbrCentralSystemComponent.cpp
    Source/LmbrCentralSystemComponent.h
    Source/Audio/AudioEnvironmentComponent.cpp
    Source/Audio/AudioEnvironmentComponent.h
    ...
)
```

**关键约定**：
- 每个源文件**只在一个 `*_files.cmake` 里出现**。
- 头文件也要列入（否则 Install / symbol dump / IDE 显示会丢失）。
- 路径相对 `Code/` 目录。
- 新增/删除 `.cpp/.h` 必须同步改对应的 `*_files.cmake` —— **这是 AI 最常忘的地方**。

---

## CMakeLists 真实结构（可直接套用）

这是一个完整 Gem 的 `Code/CMakeLists.txt` 骨架（混合 LmbrCentral + Atom/RPI + DefaultGem 的核心模式）：

```cmake
# 平台子目录
o3de_pal_dir(pal_dir
    ${CMAKE_CURRENT_LIST_DIR}/Platform/${PAL_PLATFORM_NAME}
    "${gem_restricted_path}" "${gem_path}" "${gem_parent_relative_path}")
include(${pal_dir}/PAL_${PAL_PLATFORM_NAME_LOWERCASE}.cmake)

# 有些 Gem 某平台不支持直接早退
if(NOT PAL_TRAIT_MYGEM_SUPPORTED)
    return()
endif()

# =====================================================
# 1) API target ─ 只有公开头
# =====================================================
ly_add_target(
    NAME ${gem_name}.API INTERFACE
    NAMESPACE Gem
    FILES_CMAKE mygem_api_files.cmake
    INCLUDE_DIRECTORIES INTERFACE Include
    BUILD_DEPENDENCIES INTERFACE AZ::AzCore
)

# =====================================================
# 2) Private static lib ─ runtime 实现（内部）
# =====================================================
ly_add_target(
    NAME ${gem_name}.Private.Object STATIC
    NAMESPACE Gem
    FILES_CMAKE
        mygem_private_files.cmake
        ${pal_dir}/mygem_private_files.cmake    # 平台补充
    TARGET_PROPERTIES O3DE_PRIVATE_TARGET TRUE   # 不对外暴露
    INCLUDE_DIRECTORIES
        PRIVATE Source Include
    BUILD_DEPENDENCIES
        PUBLIC
            AZ::AzCore
            AZ::AzFramework
            Gem::${gem_name}.API
)

# =====================================================
# 3) 主 Module（GEM_MODULE 或 GEM_STATIC 取决于 monolithic）
# =====================================================
ly_add_target(
    NAME ${gem_name} ${PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE}
    NAMESPACE Gem
    OUTPUT_NAME Gem.${gem_name}
    FILES_CMAKE mygem_shared_files.cmake     # 只含 Module 入口 .cpp
    INCLUDE_DIRECTORIES PRIVATE Source
    BUILD_DEPENDENCIES
        PRIVATE Gem::${gem_name}.Private.Object
)

# 注入 Gem 名字宏（给 AZ_DECLARE_MODULE_CLASS 用）
ly_add_source_properties(
    SOURCES Source/Clients/MyGemModule.cpp
    PROPERTY COMPILE_DEFINITIONS
    VALUES
        O3DE_GEM_NAME=${gem_name}
        O3DE_GEM_VERSION=${gem_version}
)

# 告诉 launcher 在 Clients/Servers/Unified 下加载
ly_create_alias(NAME ${gem_name}.Clients NAMESPACE Gem TARGETS Gem::${gem_name})
ly_create_alias(NAME ${gem_name}.Servers NAMESPACE Gem TARGETS Gem::${gem_name})
ly_create_alias(NAME ${gem_name}.Unified NAMESPACE Gem TARGETS Gem::${gem_name})

# 把 gem.json dependencies 链接到三种 variant
o3de_add_variant_dependencies_for_gem_dependencies(
    GEM_NAME ${gem_name} VARIANTS Clients Servers Unified)

# =====================================================
# 4) Editor targets（仅 host tools）
# =====================================================
if(PAL_TRAIT_BUILD_HOST_TOOLS)
    ly_add_target(
        NAME ${gem_name}.Editor.API INTERFACE
        NAMESPACE Gem
        FILES_CMAKE mygem_editor_api_files.cmake
        INCLUDE_DIRECTORIES INTERFACE Include
        BUILD_DEPENDENCIES INTERFACE
            Gem::${gem_name}.API
            AZ::AzToolsFramework
    )

    ly_add_target(
        NAME ${gem_name}.Editor.Private.Object STATIC
        NAMESPACE Gem
        AUTOMOC  AUTORCC                    # Qt MOC / 资源
        FILES_CMAKE mygem_editor_private_files.cmake
        INCLUDE_DIRECTORIES PRIVATE Source
        BUILD_DEPENDENCIES
            PUBLIC
                Gem::${gem_name}.Editor.API
                Gem::${gem_name}.Private.Object
                3rdParty::Qt::Widgets
                AZ::AzToolsFramework
        COMPILE_DEFINITIONS PUBLIC MYGEM_EDITOR
    )

    ly_add_target(
        NAME ${gem_name}.Editor GEM_MODULE
        NAMESPACE Gem
        OUTPUT_NAME Gem.${gem_name}.Editor
        FILES_CMAKE mygem_editor_shared_files.cmake
        INCLUDE_DIRECTORIES PRIVATE Source
        BUILD_DEPENDENCIES
            PRIVATE Gem::${gem_name}.Editor.Private.Object
    )

    ly_add_source_properties(
        SOURCES Source/Tools/MyGemEditorModule.cpp
        PROPERTY COMPILE_DEFINITIONS
        VALUES
            O3DE_GEM_NAME=${gem_name}
            O3DE_GEM_VERSION=${gem_version}
    )

    ly_create_alias(NAME ${gem_name}.Tools    NAMESPACE Gem TARGETS Gem::${gem_name}.Editor)
    ly_create_alias(NAME ${gem_name}.Builders NAMESPACE Gem TARGETS Gem::${gem_name}.Editor)

    o3de_add_variant_dependencies_for_gem_dependencies(
        GEM_NAME ${gem_name} VARIANTS Tools Builders)
endif()

# =====================================================
# 5) Tests
# =====================================================
if(PAL_TRAIT_BUILD_TESTS_SUPPORTED)
    ly_add_target(
        NAME ${gem_name}.Tests ${PAL_TRAIT_TEST_TARGET_TYPE}
        NAMESPACE Gem
        FILES_CMAKE mygem_tests_files.cmake
        INCLUDE_DIRECTORIES PRIVATE Tests Source
        BUILD_DEPENDENCIES
            PRIVATE
                AZ::AzTest
                Gem::${gem_name}.Private.Object
    )
    ly_add_googletest(
        NAME Gem::${gem_name}.Tests
        LABELS REQUIRES_tiaf
    )
endif()
```

### 多 Target 到 Alias 的映射（核心心智模型）

| 编译产物 | 别名 | 被谁加载 |
|---|---|---|
| `Gem::MyGem`（动态库 `Gem.MyGem.dll`） | `.Clients`, `.Servers`, `.Unified` | GameLauncher / ServerLauncher |
| `Gem::MyGem.Editor` | `.Tools`, `.Builders` | Editor, AssetProcessor |
| `Gem::MyGem.API`, `.Editor.API` | — | 其它 Gem 直接链接（编译期依赖） |
| `Gem::MyGem.Private.Object` | — | 同一 Gem 内部用 |
| `Gem::MyGem.Tests` | — | CTest 跑 |

一个 Gem 可以为不同 flavor 配不同 module（比如 `.Servers` 指向 dedicated-server 专用 module），更细粒度见 Multiplayer Gem。

---

## `AZ::Module` 类真实实现

参考 [Gems/LmbrCentral/Code/Source/LmbrCentral.cpp](../Gems/LmbrCentral/Code/Source/LmbrCentral.cpp)（简化版）：

```cpp
#include <AzCore/Module/Module.h>
#include "LmbrCentralSystemComponent.h"
// ... 其他组件头

namespace LmbrCentral
{
    class LmbrCentralModule : public AZ::Module
    {
    public:
        AZ_RTTI(LmbrCentralModule, "{7969B004-21A2-4D3D-AC8B-90A4FABCFF1E}", AZ::Module);
        AZ_CLASS_ALLOCATOR(LmbrCentralModule, AZ::SystemAllocator);

        LmbrCentralModule()
        {
            // 把所有组件描述器注册进来
            m_descriptors.insert(m_descriptors.end(), {
                LmbrCentralSystemComponent::CreateDescriptor(),
                AudioListenerComponent::CreateDescriptor(),
                BoxShapeComponent::CreateDescriptor(),
                SphereShapeComponent::CreateDescriptor(),
                TagComponent::CreateDescriptor(),
                GeometrySystemComponent::CreateDescriptor(),
                // ... 30+ 个
            });
        }

        // 返回的 SystemComponent 会在 SystemEntity 上自动挂接 + 激活
        AZ::ComponentTypeList GetRequiredSystemComponents() const override
        {
            return AZ::ComponentTypeList{
                azrtti_typeid<LmbrCentralSystemComponent>(),
                azrtti_typeid<GeometrySystemComponent>(),
                azrtti_typeid<AudioSystemComponent>(),
            };
        }
    };
}

// 宏展开后声明导出函数 CreateModuleClass_Gem_LmbrCentral()
// Launcher 用这个名字 dlsym 拿到工厂
#if defined(O3DE_GEM_NAME)
AZ_DECLARE_MODULE_CLASS(AZ_JOIN(Gem_, O3DE_GEM_NAME), LmbrCentral::LmbrCentralModule)
#else
AZ_DECLARE_MODULE_CLASS(Gem_LmbrCentral, LmbrCentral::LmbrCentralModule)
#endif
```

### Editor Module 对比

**Editor module 只放 editor-only 的描述器**，不重复 runtime 的：

```cpp
class LmbrCentralEditorModule : public AZ::Module
{
public:
    AZ_RTTI(LmbrCentralEditorModule, "{another-uuid}", AZ::Module);

    LmbrCentralEditorModule()
    {
        m_descriptors.insert(m_descriptors.end(), {
            EditorAudioEnvironmentComponent::CreateDescriptor(),
            EditorBoxShapeComponent::CreateDescriptor(),
            // ... 只有 EditorXxxComponent
        });
    }

    AZ::ComponentTypeList GetRequiredSystemComponents() const override
    {
        return { azrtti_typeid<LmbrCentralEditorSystemComponent>() };
    }
};

AZ_DECLARE_MODULE_CLASS(Gem_LmbrCentral_Editor, LmbrCentral::LmbrCentralEditorModule)
```

**关键事实**：Editor 进程启动时**同时加载 runtime module 和 editor module**。所以 Editor 里两份描述器都在，`EditorXxxComponent` 负责 UI，runtime `XxxComponent` 负责（有时 Editor 里也跑）业务数据。

### `AZ_DECLARE_MODULE_CLASS` 展开后

```cpp
// 非 monolithic（GEM_MODULE）
extern "C" AZ_DLL_EXPORT AZ::Module* CreateModuleClass_Gem_LmbrCentral() {
    return aznew LmbrCentral::LmbrCentralModule();
}

// Monolithic（GEM_STATIC）—— 用全局注册
static AZ::Module* (*g_moduleFactory_Gem_LmbrCentral)() = &CreateModuleClass_Gem_LmbrCentral;
namespace { struct AutoRegister { AutoRegister() {
    AZ::Environment::FindVariable<ModuleFactoryRegistry>(/*...*/)
        .Register("Gem_LmbrCentral", &CreateModuleClass_Gem_LmbrCentral);
}} s_autoReg; }
```

AI 不需要自己写这些展开，但理解它有助于 debug "为什么 Gem 加载不到" 类问题。

---

## `gem.json` 字段完整语义

```json
{
    "gem_name": "MyGem",                             // 唯一 ID；也是 CMake ${gem_name}
    "version": "1.2.0",
    "display_name": "My Awesome Gem",                // UI 显示名
    "type": "Code",                                   // Code / Asset / Tool
    "summary": "One-line description.",
    "canonical_tags": ["Gem"],                       // 引擎分类，不要自改
    "user_tags": ["Gameplay", "Network"],            // 你的自定义标签
    "platforms": ["Windows", "Linux", "Mac"],        // 支持平台
    "icon_path": "preview.png",
    "requirements": "",                               // 遗留字段
    "license": "Apache-2.0 Or MIT",
    "license_url": "https://…",
    "origin": "Your Company - example.com",
    "origin_url": "https://github.com/…",
    "documentation_url": "https://…",
    "repo_uri": "https://canonical.o3de.org",        // 指向远程 Gem 仓库
    "compatible_engines": [                           // SemVer 范围
        "o3de>=0.1.0.0",
        "o3de<1.0.0.0"
    ],
    "engine_api_dependencies": [                      // 依赖的引擎 API 版本
        "framework>=1.2.0"
    ],
    "dependencies": [                                 // 其它 Gem 依赖（启用时自动拉）
        "Atom_RPI",
        "LmbrCentral"
    ],
    "external_subdirectories": [                      // 子 Gem 目录（各有自己的 gem.json）
        "Multiplayer_ScriptCanvas"
    ],
    "restricted": "MyGem"                             // 受限 Gem 的独立分支
}
```

**关键要点**：
- `dependencies` 是**启用层**的依赖：用 `o3de enable-gem MyGem` 时会递归自动启用。
- CMake 层的 `BUILD_DEPENDENCIES` 是编译期依赖，**两者必须对齐**：CMake 依赖的 Gem，gem.json 也要列。
- `compatible_engines` 决定能不能在某引擎版本上启用；不匹配时 `enable-gem` 报错。

---

## 真实 Gem 依赖图（示例）

### Atom 内部

```
Atom_RHI                      ──┐
Atom_RPI   ─→  Atom_RHI         │
Atom_Feature_Common ─→ RPI, RHI, ImGui
Atom_Bootstrap ─→ RPI
AtomLyIntegration/CommonFeatures ─→ Feature_Common, RPI
AtomLyIntegration/AtomImGuiTools ─→ Feature_Common, ImGui
AtomToolsFramework (editor) ─→ RPI, Qt
MaterialEditor (editor tool) ─→ AtomToolsFramework
```

### Multiplayer Gem 依赖

```
Multiplayer
 ├─ AzNetworking                (build dep)
 ├─ AzFramework                 (build dep)
 ├─ CertificateManager          (gem.json dep)
 ├─ Atom_Feature_Common         (gem.json dep, for debug draw)
 └─ ImGui                       (gem.json dep, for debug UI)
MultiplayerCompression
 └─ Multiplayer
```

### LmbrCentral（特殊：几乎无依赖）

```
LmbrCentral
 └─ (gem.json dependencies: [])
 └─ build: AzFramework + Legacy::CryCommon + AudioSystem.API
```

因此几乎所有项目都要启用 `LmbrCentral`，它是其它 Gem 的隐式基底。

---

## Gem 启用/禁用机制（实际发生了什么）

```bash
scripts/o3de.bat enable-gem -gn MyGem -pp G:/path/to/Proj
```

此命令：
1. 在引擎注册表（`~/.o3de/o3de_manifest.json` 或 `engine.json`）找到 MyGem。
2. 读 `MyGem/gem.json`，检查 `compatible_engines`。
3. 递归读取 `dependencies`，把 MyGem + 依赖链一起加入项目的 `project.json` 的 `gem_names`。

运行时 Launcher 的加载流程（简化）：

```cpp
// 伪代码
for (const auto& gemName : projectJson["gem_names"]) {
    // 按构建模式选 alias：Clients → 客户端, Servers → 服务器, Tools → Editor
    std::string moduleName = LookupAliasedModule(gemName, currentFlavor);
    // 动态加载 Gem.MyGem.dll / libGem.MyGem.so / Gem.MyGem.dylib
    auto* module = LoadDynamicModule(moduleName);
    // dlsym("CreateModuleClass_Gem_MyGem") → 工厂
    AZ::Module* instance = module->CreateFactory();
    ModuleManager::Instance().AddModule(instance);
    // 把 instance->m_descriptors 注册到 ComponentApplication
    // 把 instance->GetRequiredSystemComponents() 自动挂到 SystemEntity
}
```

**debug "Gem 没加载"的 checklist**：
1. `project.json` 的 `gem_names` 有它吗？
2. 对应的 `.dll/.so/.dylib` 在 `bin/<config>/` 里吗？（`ls bin/profile/Gem.*`）
3. 动态库的依赖 DLL 齐吗？（Windows 上 Dependency Walker / `dumpbin /dependents`）
4. Launcher 的 log 里有 "Failed to load dynamic module" 行吗？通常带原因。
5. monolithic 构建下别名配齐了吗？（`.Clients` / `.Servers` / `.Tools` / `.Builders`）

---

## AutoGen 集成（代码生成，重点）

Multiplayer / ScriptCanvas / AzAutoGen 的 AzNetworking 协议 packet 等**大量使用 XML → C++ 代码生成**，减少样板。

### CMake 入口

见 [cmake/LyAutoGen.cmake](../cmake/LyAutoGen.cmake)。`ly_add_target` 支持 `AUTOGEN_RULES` 参数：

```cmake
ly_add_target(
    NAME MyGem.Static STATIC
    FILES_CMAKE mygem_files.cmake
    AUTOGEN_RULES
        # 格式：<glob>,<jinja 模板>,<输出路径>
        *.AutoComponent.xml,AutoComponent_Header.jinja,$path/$fileprefix.AutoComponent.h
        *.AutoComponent.xml,AutoComponent_Source.jinja,$path/$fileprefix.AutoComponent.cpp
        *.AutoComponent.xml,AutoComponentTypes_Header.jinja,$path/AutoComponentTypes.h
        *.AutoComponent.xml,AutoComponentTypes_Source.jinja,$path/AutoComponentTypes.cpp
        *.AutoPackets.xml,AutoPackets_Header.jinja,$path/$fileprefix.AutoPackets.h
    ...
)
```

`$path` = 输入文件相对目录；`$fileprefix` = 文件名去掉 `.AutoComponent.xml` 后剩下的基础名。

### 工作流（cmake 配置阶段）

1. CMake 调 `cmake/AzAutoGen.py`。
2. 脚本扫 `*_files.cmake` 里的 `*.xml` 列表。
3. 为每个 xml + 模板组合渲染出 `.h` / `.cpp`（存到 `<build>/Azcg/Generated/<target>/...`）。
4. 生成的文件自动加入 target source + include 路径。
5. 编译阶段 `add_custom_command` 追踪 xml 变化，必要时重跑。

### 模板位置

- Multiplayer 的模板：[Gems/Multiplayer/Code/Include/Multiplayer/AutoGen/](../Gems/Multiplayer/Code/Include/Multiplayer/AutoGen/)（`.jinja` 文件）
- AzNetworking 的模板：`Code/Framework/AzNetworking/.../AutoGen/`

### 用 AutoGen 的 Gem 的典型源码结构

```
Code/Source/Components/MyNetComp.AutoComponent.xml   ← 作者手写（见下）
Code/Source/Components/MyNetComp.cpp                 ← 作者写，派生自动生成的 Base
Code/Source/Components/MyNetComp.h                   ← 同上
<build>/.../Generated/MyGem.Client.Static/Components/
  MyNetComp.AutoComponent.h                          ← 自动生成：MyNetCompBase
  MyNetComp.AutoComponent.cpp                        ← 自动生成
  AutoComponentTypes.h                               ← 所有 AutoComponent 的 forward decl
  AutoComponentTypes.cpp
```

AI 扩展 Multiplayer 组件的模式：
1. 写 `.AutoComponent.xml`（见 [10_networking_physics.md](10_networking_physics.md)）。
2. 在 `*_files.cmake` 里加它。
3. 写 `MyNetComp.h/cpp` 派生 `MyNetCompBase` 实现 hook（OnInit/OnActivate/OnRpc*）。
4. 在 Module 的 `m_descriptors` 加 `CreateDescriptor()`。

---

## Editor / Runtime 代码分离最佳实践

### 目标

- **Runtime 模块不链 Qt** —— 发布包里不要 QtCore.dll / QtWidgets.dll。
- **Editor 组件持有 editor 友好类型**（路径、AssetId 包装），`BuildGameEntity` 时转成 runtime 类型。
- **两边共享 data-only 结构**（反射体）——放 API 模块。

### 模式：BuildGameEntity 完整例子

```cpp
// Editor 组件（.Editor 模块）
class EditorMovementComponent
    : public AzToolsFramework::Components::EditorComponentBase
{
public:
    AZ_EDITOR_COMPONENT(EditorMovementComponent, "{editor-uuid}", AzToolsFramework::Components::EditorComponentBase);
    static void Reflect(AZ::ReflectContext*);

    // 把自己烘焙成 runtime 组件（保存 Prefab 时框架调）
    void BuildGameEntity(AZ::Entity* gameEntity) override
    {
        // 从 editor 类型转 runtime 类型
        auto* runtime = gameEntity->CreateComponent<MovementComponent>();
        runtime->m_speed = m_editorSpeed;
        runtime->m_curve = m_speedCurveAsset.GetId();   // editor 持 asset 引用，runtime 持 ID
    }

    // Editor 组件的服务声明必须与 runtime 对齐
    static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& s) {
        MovementComponent::GetProvidedServices(s);
    }
    // GetRequiredServices / Incompatible 同样对齐

private:
    float m_editorSpeed = 1.f;
    AZ::Data::Asset<CurveAsset> m_speedCurveAsset;  // Editor 侧能预览
};
```

### 关键守则

1. **Runtime / Editor 组件 UUID 必须不同**。否则 Serialize 混乱。
2. **Provided/Required/Incompatible 服务必须对齐**。Prefab 在 Editor 先挂 Editor 组件，BuildGameEntity 换成 runtime，服务拓扑必须一致。
3. **EditorComponent 的 `SetDirty()` 要在改动后调一次**：
   ```cpp
   SetDirty();
   AzToolsFramework::ToolsApplicationRequestBus::Broadcast(
       &AzToolsFramework::ToolsApplicationRequests::AddDirtyEntity, GetEntityId());
   ```
4. **Runtime 组件 include Qt**：编译会过（如果没开 WEAK linker），**链接时 runtime launcher 找不到 Qt DLL → 加载 Gem 失败**。
5. **BuildGameEntity 不能 include editor-only 头**：它被 Runtime 组件和 Editor 组件共同依赖的链路上使用。

---

## Static Gem（Monolithic）vs Shared Gem

从 [cmake/Monolithic.cmake](../cmake/Monolithic.cmake)：

```cmake
set(LY_MONOLITHIC_GAME FALSE CACHE BOOL "Build game monolithically")

if(LY_MONOLITHIC_GAME)
    add_compile_definitions(AZ_MONOLITHIC_BUILD)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE GEM_STATIC)
    ly_set(PAL_TRAIT_BUILD_HOST_TOOLS FALSE)       # monolithic 一般出货，不带 editor
    ly_set(PAL_TRAIT_BUILD_TESTS_SUPPORTED FALSE)
else()
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE GEM_MODULE)
endif()
```

所以 `ly_add_target(NAME ${gem_name} ${PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE} ...)` 自动根据模式选：

- Dev 模式：`GEM_MODULE` → 动态库
- Monolithic 出货：`GEM_STATIC` → 静态库

**业务代码无需改**，但有几个要点：
- `AZ_DECLARE_MODULE_CLASS` 宏在两种模式下展开不同代码（一种 dlsym，一种全局 static 注册）。
- **不要依赖 dlsym 跨 Gem 找符号**；monolithic 下行不通。用反射系统或 EBus/Interface 通信。
- Monolithic 出货前**跑一次 monolithic 构建**确保链接通过（CI 应该有这个 job）。

---

## 新 Gem 模板与 CLI

### 从模板创建

```bash
# 方式 A：使用默认模板
scripts/o3de.bat create-gem \
    -gn MyGem \
    -gp G:/AXX/O3DE/o3de/Gems/MyGem

# 方式 B：指定模板（Templates/ 下的其它选项）
scripts/o3de.bat create-gem \
    -gn MyGem \
    -gp G:/AXX/O3DE/o3de/Gems/MyGem \
    --template-name CppToolGem          # 有 Qt 工具窗口骨架
```

模板在 [Templates/](../Templates/) 下。含：

| 模板 | 用途 |
|---|---|
| `DefaultGem` | 通用：runtime + editor + tests + 平台支持 |
| `CppToolGem` | Editor 专属工具窗口 Gem |
| `PythonToolGem` | Editor 内 Python 工具 |
| `AssetGem` | 只含资产（无 C++） |
| `GraphicsGem` | 渲染特性骨架（含 RPI/Feature 整合） |
| `PrebuiltGem` | 预编译交付（二进制 Gem） |
| `UnifiedMultiplayerGem` | Multiplayer AutoComponent 骨架 |

### Placeholder 替换

- `${Name}` → `MyGem`（PascalCase）
- `${NameLower}` → `mygem`
- `${NameUpper}` → `MYGEM`
- UUID 随机生成

### 注册与启用

```bash
# 1. 注册到引擎
scripts/o3de.bat register --gem-path G:/AXX/O3DE/o3de/Gems/MyGem

# 2. 在项目里启用
scripts/o3de.bat enable-gem -gn MyGem \
    -pp G:/AXX/O3DE/o3de/AutomatedTesting

# 3. 构建
cmake --build build/vs2022 --config profile \
    --target AutomatedTesting.GameLauncher Editor Gem.MyGem Gem.MyGem.Editor
```

---

## 常见坑（Gem 层）

1. **`*_files.cmake` 漏文件** → IDE 能 include 但 cmake reconfig 后找不到。改完必须检查每份 `*_files.cmake`。
2. **runtime 组件描述器同时注册到 editor module** → SerializeContext 重复注册，引擎启动 `AZ_Assert`。
3. **Editor UUID 复用 runtime UUID** → 同上，更隐蔽。
4. **`.Clients` / `.Servers` / `.Tools` / `.Builders` alias 漏配** → GameLauncher 能启动（没报错），但运行时发现该 Gem 的系统组件不在。
5. **gem.json 写了 dependency，CMake 没写 BUILD_DEPENDENCIES** → 自己仓库能跑，发给别人的项目立刻炸（别人项目没启用那个 Gem）。
6. **PAL 配置缺某平台** → Linux CI 红，本地 Windows 看不出。
7. **Module 构造函数抛异常或做重 IO** → Module 加载在引擎早期，SystemAllocator 可能都没完全就绪；**只做 `m_descriptors.insert`，别的放 SystemComponent::Activate**。
8. **Qt 泄漏到 Runtime 模块** → 开 monolithic 出包时 OS 找不到 Qt dll，Gem 加载失败。
9. **AutoGen xml 放错地方** → 必须在该 target 的 `*_files.cmake` 里；否则 AzAutoGen.py 扫不到。

继续：[06_build_and_cmake.md](06_build_and_cmake.md)、[09_scripting.md](09_scripting.md)、[10_networking_physics.md](10_networking_physics.md)。
