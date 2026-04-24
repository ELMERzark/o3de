# 19 · 新项目第一天 Checklist

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

本章是"从零装 O3DE 到能在 Editor 里拖一个 Entity 跑起来"的最短路径。以及第一周应该做的前置工作（别拖到三个月后）。

---

## Part 0 · 前置（装机）

### Windows（最常用）

- [ ] **Visual Studio 2022**（任何 edition 含 Community）
  - Workload：**Game Development with C++**
  - 组件：**MSVC v143**、**Windows 11 SDK 最新**、**CMake tools**
  - 不要依赖 `Build Tools` 单装；全装 IDE 避免找不到组件
- [ ] **CMake ≥ 3.24**（建议 3.28+）从 [cmake.org](https://cmake.org/download/)
  - 装到 PATH
- [ ] **Git** + **Git LFS**（LFS 必须，O3DE 用它存大二进制）
  - `git lfs install` 在 clone 前跑一次
- [ ] **Python 3.10+**（可选；引擎自带 python，但用自己的一套也行）
- [ ] **磁盘**：≥ 200 GB 空闲
  - 引擎 + 3rdParty + build + cache 很吃空间
- [ ] **一个短路径根目录**：`C:\o\` 或 `D:\o3de\`
  - 别放 `C:\Users\xxx\Documents\Projects\...` 里。Windows 长路径限制会崩。

### Linux（Ubuntu 24.04 noble 主推 / 22.04 jammy 也支持）

> O3DE 官方 [Docker/README.md](../Docker/README.md) 确认同时支持 `jammy` (22.04) 和 `noble` (24.04)。以下以 **Ubuntu 24.04** 为主。

- [ ] 基础包：
  ```bash
  sudo apt update
  sudo apt install -y \
      build-essential cmake ninja-build clang-17 lld-17 \
      git git-lfs python3 python3-pip python3-venv \
      libglu1-mesa-dev libxcb-xinerama0 libfontconfig1-dev \
      libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
      libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
      libxcb-sync1 libxcb-xfixes0 libxcb-xkb-dev \
      libxkbcommon-x11-dev libssl-dev zlib1g-dev \
      libxcb-cursor-dev
      # ↑ libxcb-cursor-dev 是 Qt 6 在 24.04 下必需，22.04 不强求
  ```
- [ ] Git LFS：`sudo apt install git-lfs && git lfs install`
- [ ] Python 3.12 是 24.04 默认；O3DE 自带 runtime python 在 `python/` 下，**你自己的 python 可以不装**
- [ ] CMake：24.04 自带 3.28，已达 O3DE 最低要求 3.23；想更新：
  ```bash
  sudo apt install -y kitware-archive-keyring
  # 或从 cmake.org 下载二进制包到 /opt/
  ```
- [ ] 编译器选择：
  - **Clang 17/18** 是首选（24.04 默认 `clang-17`）
  - **GCC 13** 也可用（24.04 默认）
  - `export CC=clang-17 CXX=clang++-17` 后再 cmake（或在 preset 里指定）

#### 22.04 差异提醒

如果你同时维护 22.04 环境：

- clang 用 `clang-14`（22.04 默认）
- `libxcb-cursor-dev` 通常不用装
- 其他包名一致

### macOS

- [ ] Xcode 14+（全装，不是只 Command Line Tools）
- [ ] Homebrew：`brew install cmake ninja git-lfs python@3.10`

### 目录布局约定（跨平台）

下文示例默认写 Windows 路径 `C:/o/...`。**Linux 下等价替换**：

| Windows | Ubuntu 24.04 |
|---|---|
| `C:/o/o3de/` | `~/o3de/` 或 `/opt/o3de/` |
| `C:/o/o3de-packages/` | `~/o3de-packages/` |
| `C:/o/MyProject/` | `~/projects/MyProject/` |
| `scripts/o3de.bat` | `scripts/o3de.sh` |
| `Editor.exe` | `Editor`（无后缀） |
| `build/vs2022/` | `build/linux/` |

**Linux 特殊提醒**：

- 仓库**不要**放在 `~/Documents/` 或带空格的中文目录下（某些 cmake 脚本对空格/unicode 敏感）。
- 第三方缓存 `o3de-packages` 目录别放到 NFS / WSL mount（解压时会很慢 + 权限问题）。
- 路径大小写**敏感**：`Code/Framework/AzCore` ≠ `code/framework/azcore`；Windows 同伴提交错大小写你这边必炸。

---

## Part 1 · 拉代码 + 引擎注册

### 1.1 选目录布局

两种常见：

**单仓布局**（小团队 / 个人）：
```
C:/o/
├── o3de/              ← 引擎源码（clone 下来）
├── o3de-packages/     ← 3rdParty 缓存
└── MyProject/         ← 你的项目
```

**多引擎布局**（多项目复用一个 O3DE 版本）：
```
C:/o/
├── engines/
│   ├── o3de-2310/     ← 发布版本
│   └── o3de-dev/      ← 开发版本
├── o3de-packages/
└── projects/
    ├── ProjectA/
    └── ProjectB/
```

### 1.2 Clone 引擎

```bash
# 1. 先设 LFS（关键！）
git lfs install

# 2. clone
cd C:/o
git clone https://github.com/o3de/o3de.git
cd o3de
git lfs pull         # 强制把 LFS 文件拉下来（保险一步）

# 3. 如果你要某个稳定分支
git checkout stabilization/2310
```

**不用 LFS**会出现的症状：看上去 clone 成功，但 `Assets/` 下许多二进制文件是文本"指针"（几十字节），编译时必崩。

### 1.3 注册引擎

```bash
cd o3de
scripts/o3de.bat register --this-engine
```

这会在 `~/.o3de/o3de_manifest.json` 里加一条引擎登记。之后项目能找到它。

---

## Part 2 · 建项目

### 2.1 选模板

```bash
scripts/o3de.bat create-project \
    --project-path C:/o/MyProject \
    --project-name MyProject \
    --template-name DefaultProject
```

模板对比：

| 模板 | 启用 Gem | 用途 |
|---|---|---|
| `MinimalProject` | 仅 `Atom`, `CameraFramework`, `ImGui` + 项目 Gem | 最小可跑，适合学习 |
| `DefaultProject` | 上面 + LmbrCentral + 常用 Gem 一大票 | 一般项目起点 |
| `ScriptOnlyProject` | 无自定义 C++ Gem | 纯脚本项目 |

**AI 建议**：学习选 `MinimalProject`，生产选 `DefaultProject`。后续按需加 Gem（见 [14_gems_catalog.md](14_gems_catalog.md)）。

### 2.2 注册项目

```bash
scripts/o3de.bat register --project-path C:/o/MyProject
```

### 2.3 检查 `project.json`

打开 `C:/o/MyProject/project.json`，确认：

```json
{
  "project_name": "MyProject",
  "engine": "o3de",              ← 指向注册的引擎名
  "external_subdirectories": ["Gem"],
  "gem_names": [
    "MyProject",                  ← 项目自带的 Gem
    "Atom",
    "CameraFramework",
    "ImGui",
    "LmbrCentral",
    // ... 其它
  ]
}
```

---

## Part 3 · 首次构建

### 3.1 准备 3rdParty 包缓存

Windows：
```bat
mkdir C:\o\o3de-packages
setx LY_3RDPARTY_PATH "C:/o/o3de-packages"
```

Ubuntu 24.04：
```bash
mkdir -p ~/o3de-packages
echo 'export LY_3RDPARTY_PATH=$HOME/o3de-packages' >> ~/.bashrc
source ~/.bashrc
```

### 3.2 Configure

Windows（VS 2022）：
```bat
cd C:\o\MyProject
cmake -B build/vs2022 -S . -G "Visual Studio 17 2022" ^
      -DLY_3RDPARTY_PATH=C:/o/o3de-packages
```

或用 preset（推荐）：
```bat
cmake --preset windows-default -DLY_3RDPARTY_PATH=C:/o/o3de-packages
```

Ubuntu 24.04（Ninja + Clang 17）：
```bash
cd ~/projects/MyProject

# 指定 clang 17（24.04 默认的 clang 版本）
export CC=clang-17 CXX=clang++-17

cmake -B build/linux -S . -G Ninja \
      -DCMAKE_BUILD_TYPE=profile \
      -DLY_3RDPARTY_PATH=$HOME/o3de-packages
```

或用 preset：
```bash
cmake --preset linux-default -DLY_3RDPARTY_PATH=$HOME/o3de-packages
```

**首次会花几分钟**：下载并解压 3rdParty 包（~几 GB）。Linux 下会额外校验 glibc / libstdc++ 兼容性，24.04 用 glibc 2.39，和 3rdParty 包有可能的最低要求对齐。

如果报错：
- **"LY_3RDPARTY_PATH not found"** → 环境变量没设 / 路径不对
- **"Cannot find package xxx"** → 包下载失败，网络 / hash；删 `o3de-packages/xxx/` 重试
- **"No C++ compiler"** → VS 没装或 generator 错
- **"Python not found"** → 装 Python 或让 CMake 用引擎自带的

### 3.3 Build

至少把 **Editor + AssetProcessor + GameLauncher** 编出来：

Windows：
```bat
cmake --build build/vs2022 --config profile ^
      --target Editor AssetProcessor MyProject.GameLauncher -- /m:8
```

Ubuntu 24.04：
```bash
cmake --build build/linux --config profile \
      --target Editor AssetProcessor MyProject.GameLauncher \
      -j$(nproc)
```

**首次会花 20 分钟到 1 小时**（取决于 CPU 核数）。

能在 `build/<dir>/bin/profile/` 下看到对应可执行才算过关：
- Windows：`Editor.exe` / `AssetProcessor.exe` / `MyProject.GameLauncher.exe`
- Linux：`Editor` / `AssetProcessor` / `MyProject.GameLauncher`（**无 `.exe` 后缀**）

### 3.4 跑 AssetProcessor 一次

Windows：
```bat
build\vs2022\bin\profile\AssetProcessorBatch.exe --platforms=pc
```

Ubuntu 24.04：
```bash
./build/linux/bin/profile/AssetProcessorBatch --platforms=pc
```

（无头 / 服务器场景用 `AssetProcessorBatch` — Linux 若没 X server / Wayland，`AssetProcessor` GUI 启不来。）

等它跑完（几分钟到十几分钟，首次慢）。会：
- 编译所有 shader
- 处理默认 prefab
- 处理引擎自带资产

完成后 `MyProject/Cache/pc/` 下应有 `assetcatalog.xml` + 一堆产物。

### 3.5 打开 Editor

Windows：
```bat
build\vs2022\bin\profile\Editor.exe --project-path=C:/o/MyProject
```

Ubuntu 24.04：
```bash
./build/linux/bin/profile/Editor --project-path=$HOME/projects/MyProject
```

或直接从 VS / VSCode 里 F5 launch Editor target。

如果卡在"Connecting to Asset Processor"：
- AP GUI 是不是还在启动？Editor 会等它
- 防火墙弹窗点允许
- 重启 AP 和 Editor

**Linux Editor 启动常见问题**：
- **黑窗口 / 闪退**：`libxcb-*` 依赖没装全，照 Part 0 的 apt 清单再跑一遍
- **Wayland 下异常**：强制 X11：`QT_QPA_PLATFORM=xcb ./Editor ...`
- **`libQt6Core.so.6 not found`**：3rdParty Qt 包没拉全；`rm -rf ~/o3de-packages/qt/` 重配
- **远程 SSH 显示黑屏**：X11 forwarding 性能差，建议直接在桌面 / VNC

**成功标志**：能看到 Editor 主界面，Viewport 里有个默认场景（或空）。

---

## Part 4 · 第一个场景 / 第一个 Entity

### 4.1 新建 Level

Editor → **File → New Level** → 给个名字 → 保存。

默认 level 应该已带：
- Global Sky Component
- Default Camera
- Directional Light

能运行 **Game → Play** 看到 3D 空间。

### 4.2 摆个方块

1. 视口空地右键 → **Create Entity**
2. 右下 Entity Inspector → **Add Component → Mesh**
3. Mesh 组件 → Model asset → 选 `PrimitiveAssets/Cube.azmodel`
4. 看到视口里出现一个立方体

如果看不到：
- Entity 位置是不是远离相机
- Cube asset 编译完了吗（AP 里查）
- `r_ShowPasses 1` 看渲染管线跑了没

### 4.3 保存为 Prefab

右键 Entity → **Create Prefab** → 存成 `Prefabs/MyCube.prefab`。

**Prefab = 可复用模板**。AP 会自动把 `.prefab` → `.spawnable`；运行时能动态实例化。

### 4.4 挂脚本

```
右键 Cube → Add Component → Script → Lua Script
→ 指定 .lua 文件（若无则新建）
```

或用 ScriptCanvas（更友好）：
```
Add Component → Script Canvas
→ 指定 .scriptcanvas 资产
```

见 [09_scripting.md](09_scripting.md) 的 Lua 骨架模板。

---

## Part 5 · 版本控制（尽早做）

### 5.1 Git 设置

```bash
cd C:/o/MyProject
git init
git lfs install    # 项目层也要
```

### 5.2 `.gitattributes`（LFS 规则）

新建 `C:/o/MyProject/.gitattributes`：

```gitattributes
# 二进制走 LFS
*.fbx           filter=lfs diff=lfs merge=lfs -text
*.png           filter=lfs diff=lfs merge=lfs -text
*.tif           filter=lfs diff=lfs merge=lfs -text
*.tiff          filter=lfs diff=lfs merge=lfs -text
*.tga           filter=lfs diff=lfs merge=lfs -text
*.psd           filter=lfs diff=lfs merge=lfs -text
*.exr           filter=lfs diff=lfs merge=lfs -text
*.dds           filter=lfs diff=lfs merge=lfs -text
*.wav           filter=lfs diff=lfs merge=lfs -text
*.mp3           filter=lfs diff=lfs merge=lfs -text
*.ogg           filter=lfs diff=lfs merge=lfs -text
*.mp4           filter=lfs diff=lfs merge=lfs -text
*.ttf           filter=lfs diff=lfs merge=lfs -text
*.otf           filter=lfs diff=lfs merge=lfs -text

# 文本保持 LF
*.cpp           text eol=lf
*.h             text eol=lf
*.py            text eol=lf
*.cmake         text eol=lf
*.json          text eol=lf
*.setreg        text eol=lf
```

### 5.3 `.gitignore`

```gitignore
# 构建产物
build/
out/
bin/
*.obj
*.exp
*.ilk
*.pdb

# 资产缓存（每个人本地生成）
Cache/
user/

# Editor 临时
*.Crashlog.txt
*.log

# 3rdParty（已有独立 cache 目录）
3rdParty/

# 编辑器 / IDE
.vs/
.vscode/
*.user
*.suo
*.swp
*.swo
.idea/

# Python
__pycache__/
*.pyc
.venv/

# OS
.DS_Store
Thumbs.db

# 项目特定
AssetProcessorTemp/
RemoteAssetProcessor/
```

### 5.4 初次 commit

```bash
git add .gitattributes .gitignore
git commit -m "chore: git + lfs setup"

git add project.json CMakeLists.txt Gem/ Assets/ Levels/ Prefabs/ ...
git commit -m "initial project scaffold"
```

**要点**：
- 不要把 `build/` `Cache/` `user/` 进 git
- 不要把第三方 `.fbx` 直接存（走 LFS）
- 资产命名规范立项时就定（见 [18_dcc_integration.md](18_dcc_integration.md)）

---

## Part 6 · 开发环境（VS / IDE）

### 6.1 打开解决方案

```
build/vs2022/MyProject.sln
```

第一次打开会 cold 加载所有 target（1-2 分钟）。

### 6.2 设置启动项目

Solution Explorer → 右键 `Editor` 项目 → **Set as Startup Project**。

F5 启动：自动附调试器，Editor 崩溃时断点命中。

### 6.3 常用调试配置

- VS：**Debug → Windows → Parallel Stacks**（多线程栈）
- VS：**Debug → Windows → Modules**（看加载了哪些 Gem DLL）
- VS Natvis 文件：`Code/Framework/*/.natvis` 自动加载 → Variable watcher 显示 `AZStd::vector` / `AZ::Transform` 友好

### 6.4 VSCode（跨平台）

推荐扩展：

- **C/C++**（microsoft）
- **CMake Tools**
- **Python**
- **CodeLLDB**（Linux/Mac 调试）
- **GitLens**

配合 `cmake --preset` 做 configure，VSCode 的 CMake Tools 自动识别。

---

## Part 7 · 建 CI / 建流程（第一周做）

见 [17_ci_cd_guide.md](17_ci_cd_guide.md) 最小 CI yaml 模板，粘贴到 `.github/workflows/ci.yml`：

- [ ] GitHub Actions（或 Jenkins / GitLab CI）基础 workflow
- [ ] 3rdParty 缓存策略（建 cache key）
- [ ] 冒烟测试：`ctest -L SUITE_smoke`
- [ ] 自动构建触发（PR / 每日）

**关键**：别拖到项目后期才建 CI。第一周上 CI，后续"绿灯才合"，比"PR 堆积一周一次大合"省数十倍调试成本。

---

## Part 8 · 常见第一天坑

### 跨平台通用

| 症状 | 原因 | 解法 |
|---|---|---|
| `git clone` 后 Assets/ 里文件只有几十字节 | LFS 没 install 或没 pull | `git lfs install && git lfs pull` |
| CMake 报 "LY_3RDPARTY_PATH is empty" | 环境变量没设 | `-DLY_3RDPARTY_PATH=<path>` |
| Editor 启动 crash `Failed to load Gem.X.{dll,so}` | 动态库依赖缺 / 路径不对 | 看 log；Platform 对不对 |
| AP 连不上 | 防火墙阻止 45643 端口 | 放行或改端口 |
| 编译警告被当错误 | `-Werror` | 修代码，别关 warning |
| 跑 Editor 直接打开 "default" 项目不是我的 | 没传 `--project-path` | 带 `--project-path=<abs>` |
| 修改 `.cpp` 重建后 Editor 没变化 | Editor 还没关 / Gem 动态库没重新加载 | 重启 Editor |
| 改了 `.prefab` 但 Launcher 里没变 | AP 没编完 / 没连上 | 看 AP Jobs 队列 |

### Windows 专有

| 症状 | 原因 | 解法 |
|---|---|---|
| 编译报 "constexpr too long"（MSVC） | VS 版本太老 | 升到 VS 2022 17.6+ |
| 首次 build 几小时（不正常） | Unity build 关了 / 并行度不够 | `cmake --preset windows-unity` + `-- /m:16` |
| 编译报 `cannot open PDB 'vc143.pdb'` | 磁盘空间 / 并行编译冲突 | 降 `/m:8` → `/m:4`；清磁盘 |
| 路径超过 260 字符错 | Windows 长路径限制 | `C:\o\` 短根 + regedit 开长路径：`HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1` |
| Windows Defender 扫过每个 .obj 导致慢 | AV 扫描 | 把 `build\` 和 `o3de-packages\` 加入 AV 排除列表 |

### Ubuntu 24.04 专有

| 症状 | 原因 | 解法 |
|---|---|---|
| Editor 启动黑屏 / 即闪退 | `libxcb-*` 或 `libxcb-cursor-dev` 没装（Qt 6 新增依赖） | 按 Part 0 apt 清单重装；缺的是 `libxcb-cursor-dev` / `libxcb-shape0` / `libxcb-sync1` |
| `QT_QPA_PLATFORM` 报错 | Wayland 下某些 xcb 插件异常 | `export QT_QPA_PLATFORM=xcb` 强制 X11 |
| `clang-14: command not found` | O3DE 旧脚本期望 clang-14，24.04 默认 clang-17 | `export CC=clang-17 CXX=clang++-17` 或软链 `sudo ln -s /usr/bin/clang-17 /usr/local/bin/clang-14`（不推荐） |
| `libstdc++ GLIBCXX_3.4.30 not found` | 3rdParty 包用了新 glibcxx 但系统 libstdc6 版本旧 | `sudo apt install libstdc++6` 升级；或检查 LD_LIBRARY_PATH |
| 构建报 "relocation R_X86_64_PC32 against ..." | 第三方静态库和项目 `-fPIC` 不匹配 | 确认 cmake 用了 `-DCMAKE_POSITION_INDEPENDENT_CODE=ON`（preset 已带） |
| `.sh` 没执行权限 | Windows 提交时没设 chmod | `chmod +x scripts/*.sh` |
| 文件名大小写问题 | 项目里某文件 include 大小写错，Windows 过、Linux 炸 | 统一命名；大小写对齐 磁盘文件 |
| `ulimit: open files too low` | 编译时打开太多文件 | `ulimit -n 65536` 临时提升 |
| ccache 不生效 | 没装或没指定 | `sudo apt install ccache && export CMAKE_CXX_COMPILER_LAUNCHER=ccache` |
| GPU driver / Vulkan validation 报错 | 驱动版本太老 | `sudo apt install mesa-vulkan-drivers vulkan-tools` + `vulkaninfo` 验证 |
| 磁盘空间爆炸（100+ GB） | build/ + Cache + 3rdParty 累加 | `du -sh build/* Cache/* ~/o3de-packages/*` 看哪块；定期清 build |

---

## Part 9 · 第一周要做的其它事

- [ ] **团队约定**：坐标系 / 单位 / 命名规范（参照 [18_dcc_integration.md](18_dcc_integration.md)）
- [ ] **Gem 启用清单定稿**：写死 "项目用哪些 Gem"（见 [14_gems_catalog.md](14_gems_catalog.md) 推荐组合）
- [ ] **CMakePresets.json 扩展**：项目专属 preset（Debug/Profile/Release + monolithic）
- [ ] **autoexec.cfg**：项目启动时自动跑的 cvar / 命令，存在项目根
- [ ] **project.json 的 `engine`**：锁到具体引擎版本 / 分支，避免队友 clone 不同 engine branch
- [ ] **README.md**：写清本地环境怎么装（把本文档缩减版放进去）
- [ ] **pre-commit hook**（可选）：`clang-format --dry-run --Werror`、TODO 扫描
- [ ] **任务跟踪 / issue tracker**：GitHub Issues / Jira / Linear
- [ ] **符号服务器**：出 release 前准备，崩溃分析救命
- [ ] **内部 demo 场景**：一个能证明"引擎 + 项目健康"的最小 level，每次 commit 跑通

---

## Part 10 · 快速参考命令

```bash
# ===== 引擎相关 =====
scripts/o3de.bat register --this-engine
scripts/o3de.bat register --project-path <path>
scripts/o3de.bat register --gem-path <path>
scripts/o3de.bat create-project --project-path <path> --project-name <name>
scripts/o3de.bat create-gem --gem-path <path> --gem-name <name>
scripts/o3de.bat enable-gem -gn <GemName> -pp <project_path>
scripts/o3de.bat disable-gem -gn <GemName> -pp <project_path>
scripts/o3de.bat get-registered --gems
scripts/o3de.bat get-registered --projects

# ===== 构建（Windows）=====
cmake --preset windows-default -DLY_3RDPARTY_PATH=<path>
cmake --build build/vs2022 --config profile --target Editor -- /m:8
cmake --build build/vs2022 --config profile --target <Proj>.GameLauncher

# ===== 构建（Ubuntu 24.04）=====
cmake --preset linux-default -DLY_3RDPARTY_PATH=$HOME/o3de-packages
cmake --build build/linux --config profile --target Editor -j$(nproc)
cmake --build build/linux --config profile --target <Proj>.GameLauncher -j$(nproc)

# ===== 资产（Windows）=====
build/vs2022/bin/profile/AssetProcessorBatch.exe --platforms=pc
build/vs2022/bin/profile/AssetProcessor.exe        # GUI
build/vs2022/bin/profile/AssetBundlerBatch.exe <cmd>

# ===== 资产（Ubuntu 24.04）=====
./build/linux/bin/profile/AssetProcessorBatch --platforms=pc
./build/linux/bin/profile/AssetProcessor                    # GUI（需 X server）
./build/linux/bin/profile/AssetBundlerBatch <cmd>

# ===== 运行（Windows）=====
build/vs2022/bin/profile/Editor.exe --project-path=<path>
build/vs2022/bin/profile/<Proj>.GameLauncher.exe --project-path=<path>
build/vs2022/bin/profile/<Proj>.GameLauncher.exe --connect=127.0.0.1   # client
build/vs2022/bin/profile/<Proj>.ServerLauncher.exe --port=33450         # server

# ===== 运行（Ubuntu 24.04）=====
./build/linux/bin/profile/Editor --project-path=<path>
./build/linux/bin/profile/<Proj>.GameLauncher --project-path=<path>
./build/linux/bin/profile/<Proj>.GameLauncher --connect=127.0.0.1
./build/linux/bin/profile/<Proj>.ServerLauncher --port=33450

# ===== 测试 =====
ctest --test-dir build/vs2022 -C profile -L SUITE_smoke --output-on-failure   # Windows
ctest --test-dir build/linux  -C profile -L SUITE_smoke --output-on-failure   # Linux

# ===== 工具 =====
build/vs2022/bin/profile/SerializeContextTools.exe dumpfiles --file <xxx>   # Windows
./build/linux/bin/profile/SerializeContextTools dumpfiles --file <xxx>      # Linux
build/vs2022/bin/profile/MaterialEditor.exe
./build/linux/bin/profile/MaterialEditor
```

---

## Part 11 · 项目健康度 smoke 测试（每日跑）

### Windows · `scripts/smoke.bat`

```batch
@echo off
echo === Configure ===
cmake --preset windows-default -DLY_3RDPARTY_PATH=%LY_3RDPARTY_PATH% || exit /b 1

echo === Build Editor + Launcher ===
cmake --build build/vs2022 --config profile --target Editor MyProject.GameLauncher -- /m:8 || exit /b 1

echo === Process Assets ===
build/vs2022/bin/profile/AssetProcessorBatch.exe --platforms=pc || exit /b 1

echo === Smoke Tests ===
ctest --test-dir build/vs2022 -C profile -L SUITE_smoke --output-on-failure || exit /b 1

echo === ALL GOOD ===
```

### Ubuntu 24.04 · `scripts/smoke.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

export CC=clang-17
export CXX=clang++-17
export LY_3RDPARTY_PATH="${LY_3RDPARTY_PATH:-$HOME/o3de-packages}"

echo "=== Configure ==="
cmake --preset linux-default -DLY_3RDPARTY_PATH="$LY_3RDPARTY_PATH"

echo "=== Build Editor + Launcher ==="
cmake --build build/linux --config profile \
    --target Editor MyProject.GameLauncher -j$(nproc)

echo "=== Process Assets ==="
./build/linux/bin/profile/AssetProcessorBatch --platforms=pc

echo "=== Smoke Tests ==="
ctest --test-dir build/linux -C profile -L SUITE_smoke --output-on-failure

echo "=== ALL GOOD ==="
```

加可执行：`chmod +x scripts/smoke.sh`。

队友每天早上第一件事跑一次。任何步骤挂了立刻查 — 比"周五发现整周构建是红的"好十倍。

---

## Part 12 · 学习路径（第一个月）

按顺序读：

1. [01_overview.md](01_overview.md) — 架构全景
2. [11_conventions_and_patterns.md](11_conventions_and_patterns.md) — 代码风格
3. [02_azcore.md](02_azcore.md) — Entity/Component/EBus 基础
4. [12_cookbook_recipes.md](12_cookbook_recipes.md) — R1/R2 "新建 Gem + 组件"跑一遍
5. [14_gems_catalog.md](14_gems_catalog.md) — 熟悉可选 Gem
6. 按项目方向挑 03/04/05/08/09/10 深入
7. 遇问题查 [15_debugging_toolkit.md](15_debugging_toolkit.md)

---

**第一天结束时你应该有**：
- ✅ Editor 能打开
- ✅ 自己创建了一个 Prefab 并能在 Play 模式看到
- ✅ 项目已经在 git + LFS 下
- ✅ 至少跑过一次 smoke test
- ✅ 知道接下来要读 docs_claud/ 的哪几份

完。
