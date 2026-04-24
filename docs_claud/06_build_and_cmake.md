# 06 · 构建系统与 CMake 约定（深入版）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## 前置事实

- **驱动**：CMake（≥ 3.23，部分环节要求 3.24 / 3.28）
- **语言**：C++17（部分 C++20 feature-test），Python 3（工具 / 脚本）
- **生成器**：Windows 用 `Visual Studio 17 2022` 或 `Ninja Multi-Config`；Linux 用 `Ninja` / `Unix Makefiles`；Mac 用 `Xcode` / `Ninja`
- **预设**：[CMakePresets.json](../CMakePresets.json) —— `cmake --preset windows-default` 就能用
- **封装宏**：[cmake/LYWrappers.cmake](../cmake/LYWrappers.cmake)（这是 O3DE 构建系统的核心文件）

---

## 顶层 cmake 目录地图

```
cmake/
├── LYWrappers.cmake              ★ ly_add_target / ly_create_alias / ly_add_dependencies
├── Configurations.cmake          ★ debug / profile / release 配置与 flags
├── ConfigurationTypes.cmake
├── Monolithic.cmake              ★ LY_MONOLITHIC_GAME → GEM_STATIC 转换
├── 3rdParty.cmake                第三方依赖总入口
├── 3rdPartyPackages.cmake        按需下载包
├── 3rdParty/                     每个包的 Find 脚本
│   └── Platform/<OS>/BuiltInPackages_<os>.cmake  平台内置包清单
├── Platform/
│   ├── Common/                   通用 PAL
│   ├── Windows/
│   │   ├── PAL_windows.cmake     Windows trait 定义
│   │   ├── PALDetection_windows.cmake
│   │   └── CMakePresets.json     Windows preset 继承链
│   ├── Linux/ / Mac/ / Android/ / iOS/
├── PAL.cmake                     ★ Platform Abstraction（o3de_pal_dir 等）
├── Subdirectories.cmake          扫 engine.json / project.json 拉子目录
├── Gems.cmake                    Gem 解析
├── Projects.cmake                Project 注册与解析
├── Install.cmake                 install 阶段
├── RuntimeDependencies.cmake     runtime DLL 拷贝
├── SettingsRegistry.cmake        把 Gem 映射写入 *.setreg（launcher 用）
├── LYTestWrappers.cmake          ly_add_googletest / TIAF 集成
├── CommandExecution.cmake        configure-time 执行 Python
├── AzAutoGen.py                  ★ 代码生成器入口
├── LyAutoGen.cmake               ly_add_target 里 AUTOGEN_RULES 用
├── O3DEJson.cmake                读 engine.json / project.json / gem.json
├── FileUtil.cmake                辅助
└── Deployment.cmake              部署到设备（Android / iOS）
```

---

## `ly_add_target` 完整参数

[LYWrappers.cmake](../cmake/LYWrappers.cmake) 第 91-438 行。

### 目标类型（互斥）

```cmake
ly_add_target(
    NAME MyLib <TYPE>   # 必须选一个：
    # STATIC            静态库
    # SHARED            动态库
    # MODULE            平台模块（Windows 上的 .dll，Linux .so，无 lib 前缀）
    # GEM_MODULE        Gem 运行时动态库（等价 MODULE + GEM_MODULE 属性）
    # GEM_STATIC        Gem 静态库（monolithic 模式）
    # GEM_SHARED        Gem 动态库（少用）
    # EXECUTABLE        可执行
    # APPLICATION       可执行（带平台特化 WIN32 等）
    # OBJECT            object library（不链接，只编译 .o）
    # INTERFACE / HEADERONLY  仅头文件库
    # IMPORTED          外部导入（3rdParty）
)
```

`${PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE}` 根据 `LY_MONOLITHIC_GAME` 选 `GEM_MODULE` 或 `GEM_STATIC` — **Gem 的主 target 基本都这么写**。

### 全部参数

```cmake
ly_add_target(
    NAME mylib
    NAMESPACE MyNamespace           # 别人依赖时写 MyNamespace::mylib

    STATIC                          # 类型（见上）

    # 源文件组织（解耦 CMake 与文件列表）
    FILES_CMAKE
        mylib_files.cmake
        ${pal_dir}/platform_${PAL_PLATFORM_NAME_LOWERCASE}_files.cmake

    # 自动生成源文件（由 AutoGen / 其它工具产出）
    GENERATED_FILES
        ${CMAKE_BINARY_DIR}/generated/foo.cpp

    # include 路径，分 PUBLIC / PRIVATE / INTERFACE
    INCLUDE_DIRECTORIES
        PUBLIC  Include
        PRIVATE Source ${pal_dir}

    # 编译期依赖
    BUILD_DEPENDENCIES
        PUBLIC
            AZ::AzCore
            AZ::AzFramework
        PRIVATE
            Gem::Atom_RPI.Public
            3rdParty::OpenSSL

    # 运行时依赖（动态库拷贝 / runtime asset）
    RUNTIME_DEPENDENCIES
        Gem::LmbrCentral

    # 编译定义
    COMPILE_DEFINITIONS
        PUBLIC  LY_LOGGING_ENABLED
        PRIVATE MYLIB_EXPORTS

    # 平台特定 cmake 片段（注入变量: LY_FILES_CMAKE, LY_INCLUDE_DIRECTORIES, LY_BUILD_DEPENDENCIES, LY_COMPILE_OPTIONS, LY_LINK_OPTIONS, ...）
    PLATFORM_INCLUDE_FILES
        ${pal_dir}/platform_${PAL_PLATFORM_NAME_LOWERCASE}.cmake

    # CMake target 属性（直接 set_target_properties）
    TARGET_PROPERTIES
        FOLDER "MyCompany/Gem/MyGem"
        O3DE_PRIVATE_TARGET TRUE

    # AutoGen（见下）
    AUTOGEN_RULES
        *.AutoComponent.xml,AutoComponent_Header.jinja,$path/$fileprefix.AutoComponent.h
        ...

    # Qt MOC / RCC / UIC
    AUTOMOC
    AUTORCC
    AUTOUIC

    # Unity Build 控制
    NO_UNITY

    # 输出文件名 / 子目录
    OUTPUT_NAME "Gem.MyGem"
    OUTPUT_SUBDIRECTORY "plugins"
)
```

### 辅助函数

| 函数 | 作用 |
|---|---|
| `ly_create_alias(NAME x.Clients NAMESPACE Gem TARGETS Gem::MyGem)` | 给目标起别名（用于 `.Clients` / `.Servers` / `.Tools` / `.Builders`） |
| `ly_add_dependencies(<target> <dep>...)` | 追加 runtime 依赖（动态库拷贝） |
| `ly_associate_package(PACKAGE_NAME foo-1.0-windows TARGETS Foo PACKAGE_HASH <sha>)` | 登记第三方包 |
| `ly_add_external_target(NAME Foo VERSION 1.0 ...)` | 在 `Find<Foo>.cmake` 里定义 `3rdParty::Foo` |
| `ly_add_source_properties(SOURCES a.cpp PROPERTY COMPILE_DEFINITIONS VALUES X=1)` | 给单个源文件加定义 |
| `ly_add_googletest(NAME Gem::MyGem.Tests ...)` | 注册 gtest target |
| `ly_install_directory(DIRECTORIES ... DESTINATION ...)` | 装到 install 目录 |
| `o3de_pal_dir(out_var in_dir ...)` | PAL 目录解析 |
| `o3de_gem_setup()` | 在 Gem 根 CMakeLists 首行调，解析 gem.json |

---

## `*_files.cmake` 规范

### 内容格式

```cmake
# mygem_private_files.cmake
set(FILES
    Source/MyGemSystemComponent.cpp
    Source/MyGemSystemComponent.h
    Source/BlinkerComponent.cpp
    Source/BlinkerComponent.h
    Source/Audio/AudioHelper.cpp
    Source/Audio/AudioHelper.h
)
```

- 路径相对该 `*_files.cmake` 所在目录。
- `.h/.cpp` 都列（否则 install / IDE / Xcode 看不到）。
- **每个源文件只在一个 `*_files.cmake` 里**，否则 UBT 风险 / 重复编译。

### PAL 文件合并机制

典型 Gem CMake 里：

```cmake
o3de_pal_dir(pal_dir
    ${CMAKE_CURRENT_LIST_DIR}/Source/Platform/${PAL_PLATFORM_NAME}
    "${gem_restricted_path}" "${gem_path}" "${gem_parent_relative_path}")

ly_add_target(
    NAME ${gem_name}.Static STATIC
    PLATFORM_INCLUDE_FILES
        ${pal_dir}/platform_${PAL_PLATFORM_NAME_LOWERCASE}.cmake      # 平台 trait / flags
    FILES_CMAKE
        mygem_files.cmake                                              # 跨平台源
        ${pal_dir}/platform_${PAL_PLATFORM_NAME_LOWERCASE}_files.cmake  # 平台专属源
    ...
)
```

`o3de_pal_dir` 解析优先级（[PAL.cmake](../cmake/PAL.cmake) 第 340-404 行）：

1. 先看 `Gem/.../Source/Platform/<PlatformName>/` 是否存在。
2. 若平台是 restricted（如 Consoles）且 Gem 在 restricted 路径下，去 `<restricted>/<Platform>/...` 查。
3. 都不存在则返回空；`PLATFORM_INCLUDE_FILES` 会 `optional include`。

**restricted platforms**：平台专属目录（例如主机厂商独家，不在公开 repo）。见 [cmake/Platform/](../cmake/Platform/) 的 `PAL_restrictedplatformname.cmake`。

---

## PAL（Platform Abstraction Layer）

### 核心变量

**`PAL_PLATFORM_NAME`** / **`PAL_PLATFORM_NAME_LOWERCASE`**

```cmake
# PAL.cmake 第 268 行
file(GLOB detection_files "cmake/Platform/*/PALDetection_*.cmake")
foreach(detection_file ${detection_files})
    include(${detection_file})  # 定义 LY_PLATFORM_DETECTION_<CMAKE_SYSTEM_NAME> 映射
endforeach()

ly_set(PAL_PLATFORM_NAME ${LY_PLATFORM_DETECTION_${CMAKE_SYSTEM_NAME}})
string(TOLOWER ${PAL_PLATFORM_NAME} PAL_PLATFORM_NAME_LOWERCASE)
```

**`PAL_TRAIT_*` 变量**：在每个平台的 `PAL_<os>.cmake` 里设：

```cmake
# cmake/Platform/Windows/PAL_windows.cmake
ly_set(PAL_EXECUTABLE_APPLICATION_FLAG WIN32)
ly_set(PAL_LINKOPTION_MODULE MODULE)

ly_set(PAL_TRAIT_BUILD_HOST_TOOLS TRUE)        # 能构建 Editor
ly_set(PAL_TRAIT_BUILD_HOST_GUI_TOOLS TRUE)    # 能带 Qt
ly_set(PAL_TRAIT_BUILD_TESTS_SUPPORTED TRUE)
ly_set(PAL_TRAIT_TEST_GOOGLE_TEST_SUPPORTED TRUE)
ly_set(PAL_TRAIT_TEST_GOOGLE_BENCHMARK_SUPPORTED TRUE)
ly_set(PAL_TRAIT_TEST_PYTEST_SUPPORTED TRUE)
ly_set(PAL_TRAIT_COMPILER_ID MSVC)

# Monolithic 由 Monolithic.cmake 另外设：
# PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE / LIBRARY_TYPE
```

**Gem 用 PAL trait 守卫**：

```cmake
if(NOT PAL_TRAIT_MYGEM_SUPPORTED)
    return()   # 某些平台不支持时直接退出
endif()
```

在 `Gem/Code/Platform/<OS>/PAL_<os>.cmake` 里定义 `PAL_TRAIT_MYGEM_SUPPORTED=TRUE/FALSE`。

### `o3de_pal_dir` 真实使用模式

```cmake
# Gem CMakeLists.txt 标准开头
o3de_gem_setup()  # 识别 gem.json，设 ${gem_name} ${gem_version} ${gem_path}

o3de_pal_dir(pal_source_dir
    ${CMAKE_CURRENT_LIST_DIR}/Source/Platform/${PAL_PLATFORM_NAME}
    "${gem_restricted_path}" "${gem_path}" "${gem_parent_relative_path}")

include(${pal_source_dir}/PAL_${PAL_PLATFORM_NAME_LOWERCASE}.cmake)
```

---

## 四种 Configuration

[Configurations.cmake](../cmake/Configurations.cmake)：

```cmake
set(LY_CONFIGURATION_TYPES "debug;profile;release" CACHE STRING "" FORCE)
```

| 配置 | 优化 | 断言 | 调试符号 | 用途 |
|---|---|---|---|---|
| `debug` | `-O0`  | 开 | 全 | 日常开发 / 断点 |
| `profile` | `-O2` | 开 | 有 | 发版前 QA / profiler / 客户端默认 |
| `release` | `-O3` | **关** | 无 / 分离 | 真正出货 |

测试套件用额外叠加：`profile_test`, `debug_test` — 启用 `TESTS` 并链接 gtest / AzTest。

### 写 flags 的正确姿势

```cmake
ly_append_configurations_options(
    DEFINES
        ALWAYS_DEFINED=1
    DEFINES_DEBUG
        MY_DEBUG_FLAG=1
    DEFINES_PROFILE
        MY_PROFILE_FLAG=1
    COMPILATION           # 所有语言
        -Wall -Wextra
    COMPILATION_CXX       # 仅 CXX
        -std=c++17
    COMPILATION_C
        -std=c11
    LINK                  # 所有链接
        -Wl,--as-needed
    LINK_EXE              # 仅可执行
        -Wl,--subsystem,windows
    LINK_NON_STATIC_RELEASE
        -s                # strip
)
```

### 警告踢成错误？

`cmake/CompilerSettings.cmake` 和平台 PAL 里开 `-Werror` / `/WX`。**不要**在单个 Gem 的 CMake 里关 `-Werror` 绕过；修代码。

### AZ_Assert 被剔除的前提

`release` 默认 `AZ_Assert(cond, ...)` 会被剔除，**副作用一起丢**。因此：

```cpp
AZ_Assert(DoInit(), "init failed");  // ❌ release 下 DoInit 不执行
// 应改为：
bool ok = DoInit();
AZ_Assert(ok, "init failed");
if (!ok) { /* handle */ }
```

---

## Monolithic 构建

[cmake/Monolithic.cmake](../cmake/Monolithic.cmake) 全文就很短：

```cmake
set(LY_MONOLITHIC_GAME FALSE CACHE BOOL "Indicates if the game will be built monolithically")

if(LY_MONOLITHIC_GAME)
    add_compile_definitions(AZ_MONOLITHIC_BUILD)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_LIBRARY_TYPE STATIC)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE GEM_STATIC)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_GEM_SHARED_TYPE GEM_STATIC)
    ly_set(PAL_TRAIT_BUILD_HOST_TOOLS FALSE)      # 禁 Editor
    ly_set(PAL_TRAIT_BUILD_TESTS_SUPPORTED FALSE)
else()
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_LIBRARY_TYPE SHARED)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_MODULE_TYPE GEM_MODULE)
    ly_set(PAL_TRAIT_MONOLITHIC_DRIVEN_GEM_SHARED_TYPE GEM_SHARED)
endif()
```

### `AZ_MONOLITHIC_BUILD` 宏传播

1. 编译时注入。
2. 影响运行时代码两条关键路径：
   - `AZ_DECLARE_MODULE_CLASS(Gem_Foo, FooModule)` 展开的形式变：
     ```cpp
     #if defined(AZ_MONOLITHIC_BUILD)
         // 全局 static 注册 map 里 register（launcher 启动时遍历）
     #else
         extern "C" AZ_DLL_EXPORT AZ::Module* CreateModuleClass_Gem_Foo() {
             return aznew FooModule();
         }
     #endif
     ```
   - 一些"主线程 environment 单例"的注册机制不同（因为动态库跨模块需要 Environment 共享内存）。

### 触发 monolithic 构建

```bash
cmake -B build/mono -S . \
    -G "Ninja Multi-Config" \
    -DLY_MONOLITHIC_GAME=ON \
    -DLY_3RDPARTY_PATH=...

cmake --build build/mono --config release --target AutomatedTesting.GameLauncher
```

**CI 必须覆盖一次 monolithic 构建**，否则出货发现问题才晚了。

---

## 第三方依赖

### 包格式与目录

```
<LY_3RDPARTY_PATH>/
  zlib/
    1.2.11/
      windows/      # 解压自 zlib-1.2.11-windows.tar.gz
        include/
        lib/
        bin/
```

包命名约定：`<name>-<version>-<platform>.tar.gz`；下载地址由 `cmake/3rdParty/Platform/<OS>/BuiltInPackages_<os>.cmake` 中 `ly_associate_package` 定义。

### LY_3RDPARTY_PATH 解析顺序

[cmake/3rdParty.cmake](../cmake/3rdParty.cmake) 第 25-70 行：

```
1. CMake -DLY_3RDPARTY_PATH=<...> 命令行覆盖
2. 环境变量 LY_3RDPARTY_PATH
3. o3de_manifest.json 的 default_third_party_folder
4. ${HOME}/.o3de/3rdParty （默认）
```

### `ly_associate_package` 完整签名

```cmake
ly_associate_package(
    PACKAGE_NAME openssl-1.1.1b-rev2-windows
    TARGETS      OpenSSL                        # 创建 3rdParty::OpenSSL target
    PACKAGE_HASH ef7b72...                       # SHA256 校验
)
```

通常集中在 `cmake/3rdParty/Platform/<OS>/BuiltInPackages_<os>.cmake`：

```cmake
# BuiltInPackages_windows.cmake（片段）
ly_associate_package(PACKAGE_NAME zlib-1.2.11-rev5-windows
                     TARGETS zlib
                     PACKAGE_HASH 4d28f...)

ly_associate_package(PACKAGE_NAME openssl-1.1.1b-rev2-windows
                     TARGETS OpenSSL
                     PACKAGE_HASH ef7b72...)

ly_associate_package(PACKAGE_NAME Python-3.10.13-rev1-windows
                     TARGETS Python
                     PACKAGE_HASH 6f0c...)
```

### `Find<Pkg>.cmake` 写法（给自己的库）

```cmake
# cmake/3rdParty/FindMyLib.cmake
include_guard()

if(NOT TARGET 3rdParty::MyLib)
    ly_add_external_target(
        NAME MyLib
        VERSION 2.3.1
        3RDPARTY_DIRECTORY mylib      # <LY_3RDPARTY_PATH>/mylib/2.3.1/<platform>/
        INCLUDE_DIRECTORIES include
        BUILD_DEPENDENCIES
            INTERFACE Threads::Threads
        RUNTIME_DEPENDENCIES
            bin/mylib.dll             # 自动拷到 bin/
        COMPILE_DEFINITIONS
            PRIVATE -DMYLIB_USE_DLL
    )
endif()
```

之后使用：`BUILD_DEPENDENCIES PRIVATE 3rdParty::MyLib`。

---

## Install / 打包目录

`cmake --install build --config profile --prefix install/` 会：

1. 拷贝每个 `EXECUTABLE` / `SHARED` / `GEM_MODULE` 到 `bin/<config>/`。
2. 跟着 `RUNTIME_DEPENDENCIES`（含 3rdParty runtime lib）拷。
3. 拷配置 `*.setreg`、`*.pak`（如 AssetBundler 产出）。
4. 拷 SDK 头（若开 `LY_INSTALL_EXTERNAL_BUILD_DIRS`）。

```
install/
├── bin/
│   ├── profile/
│   │   ├── Editor.exe
│   │   ├── AutomatedTesting.GameLauncher.exe
│   │   ├── Gem.MyGem.dll
│   │   ├── *.pdb
│   │   └── Qt5Widgets.dll（3rdParty runtime）
│   └── debug/ ...
├── include/            头文件（供 SDK 消费者）
├── cmake/              export set
└── assets/...
```

---

## Gems.cmake / Projects.cmake / Subdirectories.cmake 协同

### 问题：怎么让 CMake 知道要编哪些 Gem

O3DE 的 Gem 不在固定目录，由 manifest 机制定位。

[Subdirectories.cmake](../cmake/Subdirectories.cmake) 流程：

```
1. 读 engine.json 的 external_subdirectories    → O3DE_EXTERNAL_SUBDIRS_ENGINE
2. 读 每个 project.json 的 external_subdirectories + gem_names
3. 递归解析 gem.json 的 dependencies + external_subdirectories
4. 把每个 Gem 的路径记进全局 property  @GEMROOT:<gem_name>@
5. 为每个路径 add_subdirectory()
6. 每个 Gem 的 CMakeLists.txt 顶头调 o3de_gem_setup() 解析 gem.json
7. ly_add_target / ly_create_alias 建 target + .Clients/.Servers/.Tools/.Builders 别名
```

**结论**：
- 项目要启 Gem：`scripts/o3de.bat enable-gem -gn MyGem -pp <proj>`（修改 `project.json`）。
- 想让某 Gem 被整个引擎"发现"：`engine.json` 的 `external_subdirectories` 加。
- 手动覆盖：`cmake -DO3DE_EXTERNAL_SUBDIRS=<path1>;<path2>`。

---

## Settings Registry 注入构建

[cmake/SettingsRegistry.cmake](../cmake/SettingsRegistry.cmake)：为每个 launcher target 生成一个 `cmake_dependencies.<proj>.<flavor>.setreg` 文件，记录"这 launcher 该加载哪些 Gem 模块"。

输出例（运行时真实加载时查这个）：

```json
{
  "O3DE": {
    "Gems": {
      "MyGem": {
        "Targets": {
          "MyGem": {
            "Modules": ["Gem.MyGem.dll"]
          }
        }
      },
      "LmbrCentral": { ... }
    }
  }
}
```

**改动**：你在 `ly_add_target` 加的 Gem 别名 + `o3de_add_variant_dependencies_for_gem_dependencies` 会自动影响这文件。

---

## CMakePresets.json

[CMakePresets.json](../CMakePresets.json) 是顶层，按平台 include 子 preset：

```json
{
    "version": 4,
    "cmakeMinimumRequired": {"major": 3, "minor": 23, "patch": 0},
    "include": [
        "cmake/Platform/Android/CMakePresets.json",
        "cmake/Platform/iOS/CMakePresets.json",
        "cmake/Platform/Linux/CMakePresets.json",
        "cmake/Platform/Mac/CMakePresets.json",
        "cmake/Platform/Windows/CMakePresets.json"
    ],
    "configurePresets": [],
    "buildPresets": [],
    "testPresets": []
}
```

### Windows 继承链

```
host-windows (base，设 generator / toolchain / 变量)
  └─ windows-default      (最常见：VS 2022)
  └─ windows-unity        (继承 default + 启 unity build)
  └─ windows-ninja        (Ninja Multi-Config)
  └─ windows-mono-default (单体构建：LY_MONOLITHIC_GAME=ON + BUILD_HOST_TOOLS=OFF)
  └─ windows-vs-unity     (VS 2022 + unity)
```

### 常用命令

```bash
# 配置
cmake --preset windows-default -DLY_3RDPARTY_PATH=C:/o3de-packages

# 构建
cmake --build --preset windows-default --config profile --target Editor

# 测试
ctest --preset windows-default -C profile
```

直接 preset 形式比 `-G "Visual Studio …"` 短得多；CI 建议都用 preset。

---

## Test Impact Framework (TIAF)

### `ly_add_googletest` 完整签名

[LYTestWrappers.cmake](../cmake/LYTestWrappers.cmake) 第 364-436 行：

```cmake
ly_add_googletest(
    NAME Gem::MyGem.Tests                       # 指向已经定义的 target
    TARGET Gem::MyGem.Tests                      # 可选（默认=NAME）
    TEST_SUITE "main"                            # smoke / main / periodic / benchmark / sandbox / awsi
    TEST_COMMAND ${custom_test_command}          # 可选（默认走 AzTestRunner）
    TEST_REQUIRES gpu                            # 资源标签
    TEST_SERIAL                                   # 不允许并行
    COMPONENT "Physics"                           # 特性域分组（给 TIAF）
    TIMEOUT 300                                   # 秒（默认 1500）
    LABELS                                        # 附加 label
        extralabel
    RUNTIME_DEPENDENCIES
        Gem::LmbrCentral                          # 跑测试需要的 Gem
    EXCLUDE_TEST_RUN_TARGET_FROM_IDE              # IDE 里隐藏
)
```

### 测试套件含义

| Suite | 意图 | 典型运行频率 |
|---|---|---|
| `smoke` | 最快、最基本冒烟 | 每次 PR |
| `main` | 标准回归测试 | 每次 PR |
| `periodic` | 慢测试 | 夜间 |
| `benchmark` | 性能基线 | 夜间 / 周 |
| `sandbox` | 已知不稳定，不阻塞 | 监控 |
| `awsi` | AWS 集成类 | 专项 CI |

### ctest 使用

```bash
# 所有
ctest -C profile

# 按套件
ctest -C profile -L "SUITE_smoke"
ctest -C profile -L "SUITE_main"

# 按 Gem 名
ctest -C profile -R "MyGem"

# 并行 + 失败时输出
ctest -C profile -j 8 --output-on-failure

# 输出 JUnit XML
ctest -C profile --output-junit results.xml

# 排除慢
ctest -C profile -E "Slow|Heavy"
```

### TIAF 工作原理

[TestImpactFramework/](../Code/Tools/TestImpactFramework/) 工具在 CI 上：

1. 解析某 PR 的 diff → 得变更的源码文件列表。
2. 从预生成的 "file → test" 关系图里查"哪些 test 覆盖这些文件"。
3. 只跑相关 test。
4. 未覆盖的文件 → 跑全量（fallback）。

关系图靠插桩构建出 coverage profile（首次运行慢，后续快）。

---

## Android / iOS 特殊性

### Android（[Docker/Android](../Docker/Android/) / cmake/Platform/Android）

关键变量：

```bash
cmake -B build_android -S . \
    -G "Ninja Multi-Config" \
    -DCMAKE_SYSTEM_NAME=Android \
    -DCMAKE_ANDROID_NDK=$ANDROID_NDK_ROOT \
    -DCMAKE_ANDROID_PLATFORM=android-29 \
    -DCMAKE_ANDROID_ABI=arm64-v8a \
    -DLY_3RDPARTY_PATH=~/o3de-packages
```

产出 `<Project>.GameLauncher.APK` target，内部用 Gradle 包装。

### iOS

```bash
cmake -B build_ios -S . \
    -G Xcode \
    -DCMAKE_SYSTEM_NAME=iOS \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=14.0 \
    -DLY_3RDPARTY_PATH=~/o3de-packages
```

出 `.IPA`。必须 macOS + Xcode。

**两个平台共同要求**：
- Monolithic 构建一般必须（`LY_MONOLITHIC_GAME=ON`）。
- 不开 HOST_TOOLS（没 Editor）。

---

## 常用命令速查

### 首次配置

```bash
# Windows VS 2022
cmake -B build/vs2022 -S . \
    -G "Visual Studio 17 2022" \
    -DLY_3RDPARTY_PATH=C:/o3de-packages

# Windows Ninja Multi-Config
cmake -B build/ninja -S . \
    -G "Ninja Multi-Config" \
    -DLY_3RDPARTY_PATH=C:/o3de-packages

# Linux（Ubuntu 24.04 noble / 22.04 jammy）
export CC=clang-17 CXX=clang++-17    # 24.04 默认；22.04 用 clang-14
cmake -B build/linux -S . -G Ninja \
    -DCMAKE_BUILD_TYPE=profile \
    -DLY_3RDPARTY_PATH=$HOME/o3de-packages

# macOS（Xcode）
cmake -B build/mac -S . -G Xcode \
    -DLY_3RDPARTY_PATH=~/o3de-packages

# 用 preset（推荐）
cmake --preset windows-default
```

### 常用 build 命令

Windows：
```bat
# 构建全部
cmake --build build/vs2022 --config profile -- /m:8

# 仅 Editor
cmake --build build/vs2022 --config profile --target Editor

# 仅某 Gem
cmake --build build/vs2022 --config profile --target Gem.MyGem Gem.MyGem.Editor

# GameLauncher 三件套
cmake --build build/vs2022 --config profile ^
    --target AutomatedTesting.GameLauncher AssetProcessor Editor

# 清理
cmake --build build/vs2022 --target clean

# 重新配置
rmdir /S /Q build\vs2022 && cmake --preset windows-default
```

Ubuntu 24.04：
```bash
# 构建全部
cmake --build build/linux --config profile -j$(nproc)

# 仅 Editor
cmake --build build/linux --config profile --target Editor -j$(nproc)

# 仅某 Gem
cmake --build build/linux --config profile --target Gem.MyGem Gem.MyGem.Editor

# GameLauncher 三件套
cmake --build build/linux --config profile \
    --target AutomatedTesting.GameLauncher AssetProcessor Editor -j$(nproc)

# 清理
cmake --build build/linux --target clean

# 重新配置
rm -rf build/linux && cmake --preset linux-default
```

### 运行测试

```bash
ctest --test-dir build/vs2022 -C profile              # 全部
ctest --test-dir build/vs2022 -C profile -L SUITE_smoke
ctest --test-dir build/vs2022 -C profile -R MyGem
ctest --test-dir build/vs2022 -C profile -j 8 --output-on-failure
```

### Install

```bash
cmake --install build/vs2022 --config profile --prefix install
```

---

## 改了什么，要做什么

| 改动 | `cmake -S` (reconfig) | `cmake --build` | 重启 Editor |
|---|:-:|:-:|:-:|
| `.cpp` / `.h` 内容 |  | ✓ | ✓ |
| 新加/删除源文件 + 改 `*_files.cmake` | ✓ | ✓ | ✓ |
| 改 `CMakeLists.txt` | ✓ | ✓ | ✓ |
| 改 `gem.json` (dependencies) | ✓ | ✓ | ✓ |
| 改 `project.json` (gem_names) | ✓ | ✓ | ✓ |
| 改 `engine.json` | ✓ | ✓ | ✓ |
| 改 shader / `.azsl` | — | ✓（AP 编） | — / 可 `r_ReloadShader` |
| 改 lua | — | ✓（AP 编） | — |
| 涨 SerializeContext Version | — | ✓ | ✓ + 资产 reprocess |
| 新增 `.AutoComponent.xml` | ✓ | ✓ | ✓ |

---

## 常见坑

### 跨平台通用

1. **忘改 `*_files.cmake`**：IDE 能编（因为 scan 路径），CI / 同事重配后缺 symbol / 链接错。
2. **Gem alias 漏配（`.Clients` / `.Servers` / `.Tools` / `.Builders`）**：GameLauncher 能启动但发现 Gem 的 system component 不存在；Editor 里 Asset Builder 不跑 —— 都没报错，查半天。
3. **include path 用 PUBLIC 太过**：静态库头 PUBLIC 后下游全染，引入不必要依赖。默认 PRIVATE，只把 `Include/` PUBLIC。
4. **`3rdParty::X` 找不到**：99% 是 `LY_3RDPARTY_PATH` 没设或包没下载；看 `build/**/CMakeError.log`。
5. **monolithic 没 CI 覆盖**：出货才发现 monolithic 下某 Gem 没注册。**每次 PR 都应至少过一次 monolithic 构建**。
6. **第三方包 hash 对不上**：`ly_associate_package` 的 `PACKAGE_HASH` 改了，但本地缓存还在，报 "hash mismatch"。`rm -rf <LY_3RDPARTY_PATH>/<pkg>/<ver>` 重新下载。
7. **PAL_TRAIT 用错**：直接 `if(WIN32)` 在 Gem 里，容易把平台检测分散。统一走 `PAL_TRAIT_MYGEM_SUPPORTED` 等自定义 trait。
8. **`set_property(TARGET ... APPEND)` 覆盖 `ly_add_target` 设置**：不要手动 set，用 `ly_add_target` 的参数；否则调试很困难。
9. **改了 CMake 没重跑 generate**：`cmake --build` 会自动触发，除非关了 `CMAKE_AUTOGEN_VERBOSE`。有时手动 `cmake --preset <name>` 一次干净重配。

### Windows 专有

10. **Windows 长路径**：O3DE 构建路径深，`build\profile\<gem>\<file>.cpp.obj` 容易超 260 字符。用 registry 打开长路径或把项目放 `C:\o\` 之类短路径。
11. **Windows Defender 实时扫描拖慢编译**：扫描每个 `.obj` / `.pdb`。把 `build\` 和 `o3de-packages\` 加入 AV 排除清单。

### Ubuntu 24.04 专有

12. **clang-14 硬编码**：某些旧 CMake 脚本 `find_program(CLANG clang-14)` 写死版本。24.04 默认 `clang-17`，find 不到。对策：`sudo apt install clang-14`（仍可从 universe 装）或改 preset 设 `-DCMAKE_C_COMPILER=clang-17`。
13. **大小写敏感导致 include 失败**：`.cpp` 里 `#include "Azcore/..."` 在 Windows 能过，Linux 必炸。grep 整个仓库对齐。
14. **`libc.so.6 version GLIBC_2.38 not found`**：3rdParty 包可能基于更新 Ubuntu 构建。24.04 的 glibc 2.39 是 OK 的；22.04 的 glibc 2.35 可能跑不动 2310+ 3rdParty。升系统或用官方 docker image 统一环境。
15. **`.sh` 没执行位**：Windows 同伴提交 `.sh` 默认不带 x 位 → Linux 上 `bash: permission denied`。`git update-index --chmod=+x path/to/file.sh` 修。
16. **Wayland 原因 Editor 花屏 / 输入奇怪**：`export QT_QPA_PLATFORM=xcb` 强制 X11；或 `xdg-session-type` 切到 X11 登录。
17. **缺 GPU 驱动 / Vulkan 支持**：`vulkaninfo` 报错 → `sudo apt install mesa-vulkan-drivers vulkan-tools` + NVIDIA 卡还要 `nvidia-driver-535+`。

继续：[07_asset_pipeline.md](07_asset_pipeline.md) / [05_gems_and_modules.md](05_gems_and_modules.md)
