# AGENTS.md — O3DE 项目给 AI 助手的工作指南

这是 **O3DE (Open 3D Engine)** 的仓库。写代码前请先读 `docs_claud/` 下的项目上下文文档。

---

## 工作前必读（每次新 session）

1. 打开 [`docs_claud/00_index.md`](docs_claud/00_index.md) —— 看文档清单 + 版本元数据。
2. 打开 [`docs_claud/13_ai_context_guide.md`](docs_claud/13_ai_context_guide.md) —— 这是给你的"使用说明"，讲陷阱和惯例。
3. 打开 [`docs_claud/11_conventions_and_patterns.md`](docs_claud/11_conventions_and_patterns.md) —— 代码风格守则。

---

## 按任务类型加读

| 任务 | 读这些 |
|---|---|
| 写 / 改 C++ 组件 | `docs_claud/02_azcore.md` + `03_azframework.md` |
| Editor 端 / Qt 工具 | `docs_claud/04_aztoolsframework.md` |
| 新建 Gem / 改 Gem 结构 | `docs_claud/05_gems_and_modules.md` + `06_build_and_cmake.md` |
| 选型用什么 Gem | `docs_claud/14_gems_catalog.md` |
| 资产 / Builder 相关 | `docs_claud/07_asset_pipeline.md` |
| 渲染 / 材质 / shader | `docs_claud/08_rendering_atom.md` |
| Lua / ScriptCanvas / Python | `docs_claud/09_scripting.md` |
| 联网 / 多人游戏 / 物理 | `docs_claud/10_networking_physics.md` |
| 构建 / CMake | `docs_claud/06_build_and_cmake.md` |
| CI / 发布 | `docs_claud/17_ci_cd_guide.md` |
| DCC / FBX / 美术流水 | `docs_claud/18_dcc_integration.md` |
| 从零起新项目 / 环境配置 | `docs_claud/19_new_project_checklist.md` |

**遇到 bug**：先查 [`docs_claud/15_debugging_toolkit.md`](docs_claud/15_debugging_toolkit.md)（按症状组织的诊断路径）。
**要做性能优化**：看 [`docs_claud/16_performance_checklist.md`](docs_claud/16_performance_checklist.md)。
**常见 "怎么做 X" 任务**：查 [`docs_claud/12_cookbook_recipes.md`](docs_claud/12_cookbook_recipes.md) 有没有现成菜谱。

**上下文窗口有限时**：不要一次塞全部 `docs_claud/*.md`（共 ~400 KB）。按任务只读 3-5 份相关的。

---

## 工作步骤（每个任务都按这个做）

### 第 1 步 · 理解任务

- 明确目标：要改什么？影响哪些文件？
- **不确定时反问用户**，不要猜。特别是：组件所属 Gem、UUID 如何生成、是否需要 Editor 侧对应物。

### 第 2 步 · 读相关 docs

- 按上面清单选 2-4 份相关文档读。
- **不要通读整棵代码树**，仓库太大（`3rdParty/` + `build/` + `Cache/` 可能几十 GB）。
- 需要具体实现细节时再 grep 代码。

### 第 3 步 · 给计划（**在动手前**）

非平凡任务（≥ 3 个文件改动）：**先给文件清单 + 关键决策，让我确认后再动手**。不要直接闷头写然后给一大坨 diff。

输出格式：

```
计划：
  目标：<一句话>
  改动：
    - path/A.h        新建：<类名> + 方法签名
    - path/A.cpp      同上实现
    - path/mygem_private_files.cmake    加入 A.{h,cpp}
    - path/MyGemModule.cpp               m_descriptors 加 A::CreateDescriptor()
  关键决策：
    - 选了 Multiple/ById EBus 政策因为 ...
    - Editor 组件分开因为 ...
  待用户决定：
    - Uuid 我用占位 {<uuid-A>}，需要你生成
```

### 第 4 步 · 验证文档与当前代码一致

`docs_claud/` 的戳记是：`aa2f89cb7e (2026-04-24)`。

如果当前仓库 HEAD commit 和这个不同，文档里引用的类名 / 路径 / API 签名**可能漂移**。这种情况：

- 先 `grep -r "ClassName" Code/` / `git log aa2f89cb7e..HEAD --stat -- Code/Framework/AzCore` 确认事实
- 不要基于过时文档直接生成代码
- 发现文档过时，在回复末尾指出具体哪条，让用户更新

### 第 5 步 · 写代码

必须遵守（摘自 `docs_claud/11_conventions_and_patterns.md`）：

- 用 `AZStd::*` 容器，**不要** `std::vector` / `std::string` 存引擎数据
- 类要 `AZ_CLASS_ALLOCATOR(Foo, AZ::SystemAllocator)`
- 组件用 `AZ_COMPONENT(Foo, "{uuid}")`，UUID 必须唯一
- 堆分配用 `aznew`，不要 `new`
- `EntityId` 判 valid 用 `.IsValid()`，不要 `if (id)`
- 反射过的类字段改了必须涨 `SerializeContext::Version(n)` 并写 VersionConverter
- Editor 组件和 runtime 组件 **UUID 必须不同**
- 新建文件必须在对应的 `*_files.cmake` 里登记（否则构建图丢失）
- 新组件 `CreateDescriptor()` 要 push 进对应 Gem Module 的 `m_descriptors`
- `Reflect` 里 `azrtti_cast<SerializeContext*>` / `<BehaviorContext*>` / `<EditContext*>` 必须判 nullptr
- 日志宏第一参 `Window` 用 Gem 名或 `"MyGem::Subsystem"` 格式

### 第 6 步 · 给 diff / 文件改动清单

一次给完所有改动，不要分段留悬空状态。典型组件改动至少 3-5 个文件：

1. `.h` / `.cpp`（头 + 实现）
2. 对应的 `*_files.cmake`
3. Module 的 `m_descriptors` 列表
4. （如有 Editor 侧）Editor 组件 + EditorModule 注册 + editor `*_files.cmake`
5. （如改反射）Version 涨 + VersionConverter

### 第 7 步 · 给验收步骤

写完代码告诉用户怎么验证：

- 要跑什么 cmake 命令
- Editor 里会看到什么（菜单项 / Add Component 下的新条目 / log 输出）
- 要手动测的行为

---

## 风格底线

1. 不要用 emoji（除非用户明确要求）
2. 回答用中文（用户主语言）
3. 代码块带语言 tag：` ```cpp ` / ` ```cmake ` / ` ```python ` / ` ```xml `
4. 路径用 POSIX 正斜杠（`Code/Framework/AzCore/...`），哪怕在 Windows 下
5. **不要编造 UUID** — 写 `"{<replace-with-fresh-uuid>}"` 占位，提醒用户生成
6. **不要编造 API** — 不确定就承认"未验证，建议 grep 确认"
7. 引用具体事实时带路径：`docs_claud/02_azcore.md#ebus-进阶` 或 `Code/Framework/AzCore/.../File.h:123`

---

## 绝对禁止

- 不要 `git commit` / `git push` 代码（用户自己来）
- 不要改 `engine.json` / `project.json` / `gem.json` 里的 `*id` / `*_id` 字段（稳定 UUID）
- 不要动 `3rdParty/` / `build/` / `Cache/` / `.git/` / `user/` 目录
- 不要 `git commit --no-verify` / `git push --force` / `git reset --hard`（除非用户明确说）
- 大范围重构（跨 Gem / 跨 Framework）前先征求同意，不要"顺手整理"
- 不要在 Runtime 组件 include Qt / AzToolsFramework 头
- 不要在 Editor 组件 UUID 和 Runtime 组件相同（即使类名一样）
- 不要跳过 `AZ_CLASS_ALLOCATOR` 声明（类能编过但跨模块分配崩）

---

## 仓库事实（快速参考）

### 开发平台

用户可能在 **Windows** 和 **Ubuntu 24.04**（noble）两套环境下开发，给建议 / 写命令时要分别适配。

| 维度 | Windows | Ubuntu 24.04 |
|---|---|---|
| **主要身份** | 主开发 / 日常工作流 | 备用 / Linux 客户端 / Docker / 服务器端测试 |
| **CMake 生成器** | `Visual Studio 17 2022`（或 `Ninja Multi-Config`） | `Ninja`（推荐） or `Unix Makefiles` |
| **Preset 推荐** | `cmake --preset windows-default` | `cmake --preset linux-default` |
| **构建路径** | `build/vs2022/` 或 `build/ninja/` | `build/linux/` |
| **编译器** | MSVC (VS 2022 v143, 17.6+) | Clang 17/18（24.04 默认）或 GCC 13 |
| **Bootstrap 路径** | `scripts/o3de.bat` | `scripts/o3de.sh` |
| **Shell** | PowerShell / cmd | bash / zsh |
| **可执行后缀** | `.exe` | 无 |
| **DLL 后缀** | `.dll` | `.so` |
| **路径分隔** | `\\` 原生，`/` 也接受 | `/` |
| **第三方缓存** | `C:/o3de-packages` 或 `D:/...` | `~/o3de-packages` |
| **图形后端** | DX12（首选） / Vulkan | Vulkan（唯一） |

**关键事实**：
- O3DE 的 [Docker/README.md](Docker/README.md) 官方支持 Ubuntu `jammy` (22.04) 和 `noble` (24.04)；24.04 用户直接用官方 docker 镜像流程完全 OK。
- Linux 下**没有 DX12 后端**；`Atom_RHI_Vulkan` 自动启用。
- Linux 下文件名**大小写敏感**；Windows 开发的资产路径错一个大小写，Linux 上必炸。

### Ubuntu 24.04 的 apt 前置

```bash
sudo apt update
sudo apt install -y \
    build-essential cmake ninja-build clang-17 \
    git git-lfs python3 python3-pip \
    libglu1-mesa-dev libxcb-xinerama0 libfontconfig1-dev \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-xkb-dev \
    libxkbcommon-x11-dev libssl-dev zlib1g-dev \
    libxcb-cursor-dev   # 24.04 比 22.04 多要这个
```

### Linux 侧的日常命令适配

| 操作 | Windows | Ubuntu 24.04 |
|---|---|---|
| Configure | `cmake --preset windows-default` | `cmake --preset linux-default -G Ninja` |
| Build Editor | `cmake --build build/vs2022 --config profile --target Editor -- /m:8` | `cmake --build build/linux --config profile --target Editor -j$(nproc)` |
| 启动 Editor | `build\vs2022\bin\profile\Editor.exe --project-path=...` | `build/linux/bin/profile/Editor --project-path=...` |
| 启动 AP | `AssetProcessor.exe` | `./AssetProcessor` |
| Remote Tools | `scripts/o3de.bat ...` | `scripts/o3de.sh ...` |

### 共同事实

- **资产缓存**：`<project>/Cache/`（不要提交）
- **用户目录**：`<project>/user/`（不要提交）
- **默认项目**：`AutomatedTesting/`（做参考最安全的样例）
- **Framework 层级**：`AzCore` → `AzFramework` → `AzToolsFramework`（严格向下依赖）
- **最近 commit（写本 AGENTS.md 时）**：`aa2f89cb7e` on `development`

### 跨平台代码守则（Linux 专属坑）

给两边都用的代码时要留神：

1. **路径大小写**：include `"AzCore/Component/Component.h"` 必须和磁盘路径完全一致。
2. **路径分隔**：代码里统一用 `/` 或 `AZ::IO::Path` 的 `/` operator；别硬编码 `\\`。
3. **行尾符**：.gitattributes 已设 LF；不要 Windows 下用 CRLF 提交 `.sh` / `.cmake`。
4. **可执行权限**：`.sh` / `.py` 入库时 `git update-index --chmod=+x`。
5. **平台分支**：宏 `AZ_TRAIT_OS_PLATFORM_LINUX` / `AZ_TRAIT_OS_PLATFORM_WINDOWS`；或 CMake 里 `PAL_TRAIT_*`。**不要**直接 `#ifdef _WIN32`（虽然也能用，但引擎风格是 TRAIT）。
6. **Qt 依赖**：Linux 下 Qt 通过 xcb 实现；apt 装不全会 silently fail，遇到 Editor 启动黑屏先查 `libxcb-*`。
7. **AssetProcessor 在 headless server**：Linux 服务器无 GUI 时用 `AssetProcessorBatch`，别用 `AssetProcessor`（前者无 Qt GUI）。

### Linux 特有命令速查

```bash
# 装 Git LFS（Ubuntu 24.04 仓库里有）
sudo apt install git-lfs
git lfs install

# Clone
git clone https://github.com/o3de/o3de.git
cd o3de
git lfs pull

# 注册引擎
scripts/o3de.sh register --this-engine

# 首次 configure
cmake -B build/linux -S . -G Ninja \
    -DLY_3RDPARTY_PATH=$HOME/o3de-packages

# 构建
cmake --build build/linux --config profile \
    --target Editor AssetProcessor AutomatedTesting.GameLauncher \
    -j$(nproc)

# 可执行不要加 .exe
./build/linux/bin/profile/AssetProcessor
./build/linux/bin/profile/Editor --project-path=$HOME/MyProject

# 测试
ctest --test-dir build/linux -C profile -L SUITE_smoke --output-on-failure
```

---

## 典型任务的计划模板（给你起草 "计划" 用）

### 新建一个组件

```
计划 — 新建 XxxComponent：
  Gem: Gems/MyGem/
  Runtime 文件:
    - Code/Source/XxxComponent.h       (AZ::Component 派生)
    - Code/Source/XxxComponent.cpp
    - Code/Include/MyGem/XxxBus.h      (如果需要 EBus)
  Editor 文件:
    - Code/Source/EditorXxxComponent.h
    - Code/Source/EditorXxxComponent.cpp
  CMake:
    - Code/mygem_private_files.cmake         + XxxComponent.{h,cpp}
    - Code/mygem_api_files.cmake             + XxxBus.h
    - Code/mygem_editor_private_files.cmake  + EditorXxxComponent.{h,cpp}
  Module 注册:
    - Code/Source/MyGemModule.cpp            m_descriptors += XxxComponent::CreateDescriptor()
    - Code/Source/MyGemEditorModule.cpp      m_descriptors += EditorXxxComponent::CreateDescriptor()
  Uuid 占位:
    - Runtime: {<uuid-runtime>}
    - Editor:  {<uuid-editor>}
  服务声明:
    - Provides: XxxService
    - Requires: TransformService
    - Incompatible: XxxService (同实体不允许两个)
  反射:
    - SerializeContext Version(1)
    - EditContext: Category = "MyGem", AppearsInAddComponentMenu = "Game"
    - BehaviorContext: <填 / 不需要>

等你确认这个清单后再写代码。
```

### 新建 Gem

```
计划 — 新建 CombatSystem Gem:
  命令:
    scripts/o3de.bat create-gem -gn CombatSystem \
        -gp <abs-path>/Gems/CombatSystem \
        --template-name DefaultGem
    scripts/o3de.bat register --gem-path <abs-path>/Gems/CombatSystem
    scripts/o3de.bat enable-gem -gn CombatSystem -pp <project>

  Gem 结构（template 生成后我改这些）:
    - Code/CMakeLists.txt              ly_add_target 五件套
    - Code/Include/CombatSystem/       对外头
    - Code/Source/                     内部实现 + Module
    - Code/Source/Tools/               Editor 部分
    - Code/Platform/                   PAL（默认空）
    - gem.json                         依赖: ["LmbrCentral"] (举例)

  示例组件: HealthComponent (见上一个模板的计划结构)

  预计文件数: ~15-20 个
  预计用时: 约 1 小时 review + 调整

等你确认。
```

### 性能诊断（不改代码）

```
计划 — <函数/系统> 性能诊断:
  诊断步骤:
    1. 读 docs_claud/16_performance_checklist.md
    2. 读该领域深入文档（渲染看 08，联网看 10…）
    3. grep 实际代码定位热点
    4. 列 top 5 可能原因
    5. 每条给验证方法（profiler / cvar / 测试 case）
    6. 给修复方向，不直接给代码
  产出: 诊断报告（markdown）
  不做: 修改代码

等你确认是否继续。
```

---

## 当用户给你不够明确的任务时

**不要猜，问**。典型要澄清的：

- "帮我加个移动" → 第三人称 FPS 还是 Top-down？玩家控制还是 AI？
- "加网络同步" → client 权威还是 server 权威？要回滚吗？
- "让它更快" → 哪个指标慢？具体帧时间 ms？CPU 还是 GPU？
- "修 bug" → 完整 log / stack / repro 步骤

问 1-3 个具体问题，不要列出 10 个让用户烦。

---

## 最后

这套文档是静态快照，**有可能和仓库最新状态不一致**。把它当"资深同事给的 onboarding 手册"—— 多数场景极有用，但不能取代读代码。疑虑时 grep 实际文件确认。
