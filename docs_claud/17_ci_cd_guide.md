# 17 · CI / CD 集成指南

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

本章讲如何把 O3DE 项目上到 CI。覆盖：本地自动化、GitHub Actions / Jenkins、TIAF 增量测试、打包发布、常见陷阱。

---

## O3DE 仓库自己怎么做 CI（参考实现）

O3DE 主仓库的 CI 在 [.github/workflows/](../.github/workflows/)：

| 工作流 | 作用 |
|---|---|
| `windows-build.yml` | Windows 构建 |
| `linux-build.yml` | Linux 构建 |
| `mac-build.yml` | macOS |
| `android-build.yml` | Android |
| `ios-build.yml` | iOS |
| `ar.yml` | Auto-Review：PR 触发的聚合 workflow |
| `validation.yaml` | commit 格式 / 许可证头检查 |
| `stabilization-pr-checklist.yaml` | PR check |

### CI 驱动脚本

[scripts/build/ci_build.py](../scripts/build/ci_build.py) 是核心入口。流程：

```
CI 触发
  → 调 ci_build.py -p windows -t profile_test
    → 读 scripts/build/Platform/<platform>/build_config.json
    → 找 "profile_test" 条目
    → 里面列出 cmake_configure / cmake_build / test 命令
    → 逐步执行
```

看 `scripts/build/Platform/Windows/` 下的真实 cmd/ps1 脚本知道每步在跑什么：

- `env_windows.cmd` — 设 VS 环境 + 第三方路径
- `build_windows.cmd` — cmake configure + build
- `build_test_windows.cmd` — 加 TESTS 选项
- `test_windows.cmd` — ctest
- `build_installer_windows.cmd` — 出 MSI
- `clean_windows.cmd` — 清理

其它平台（Linux / Mac / Android / iOS）在 `scripts/build/Platform/<OS>/` 下有类似命令。

### 本地模拟 CI 一跑

```bash
# 例：跟 CI 一样的 windows profile_test build
python scripts/build/ci_build.py -p Windows -t profile_test
```

这比直接跑 `cmake --build` 好，因为它走配置文件（保证和 CI 结果一致）。

---

## 建 CI 的最小组合

### 必做的检查

1. **Configure**：`cmake -B build -S . --preset <platform>-default` —— 捕获 CMake 错误
2. **Build**：至少 Editor + GameLauncher（profile 配置）
3. **Smoke Tests**：`ctest -L SUITE_smoke` —— 1-2 分钟跑完的最基本测试
4. **Main Tests**：`ctest -L SUITE_main` —— PR 合入前必过
5. **资产编译**：`AssetProcessorBatch` 跑一次确保所有源资产能编译

### 典型流程

```
Git push / PR
  ↓
CI trigger
  ↓
Checkout + fetch LFS
  ↓
Restore 3rdParty cache
  ↓
cmake configure
  ↓
cmake build profile
  ↓
AssetProcessorBatch --platforms=pc
  ↓
ctest -L SUITE_smoke
  ↓
(optional) ctest -L SUITE_main
  ↓
Upload artifacts + results
```

---

## GitHub Actions 范例（3rd-party 项目用）

```yaml
# .github/workflows/ci.yml
name: O3DE Project CI

on:
  pull_request:
    branches: [main, development]
  push:
    branches: [main]

env:
  O3DE_REPO: <your org>/<your project>
  LY_3RDPARTY_PATH: D:/o3de-packages

jobs:
  windows-build:
    runs-on: windows-2022
    steps:
      - name: Checkout project
        uses: actions/checkout@v4
        with:
          path: project
          lfs: true

      - name: Checkout engine
        uses: actions/checkout@v4
        with:
          repository: o3de/o3de
          path: engine
          lfs: true

      - name: Cache 3rdParty
        uses: actions/cache@v3
        with:
          path: ${{ env.LY_3RDPARTY_PATH }}
          key: o3de-3rdparty-windows-${{ hashFiles('engine/cmake/3rdParty/Platform/Windows/BuiltInPackages_windows.cmake') }}

      - name: Register engine
        shell: pwsh
        run: |
          cd engine
          ./scripts/o3de.bat register --this-engine

      - name: Register project
        shell: pwsh
        run: |
          cd engine
          ./scripts/o3de.bat register --project-path ../project

      - name: Configure
        shell: cmd
        run: |
          cmake -B build -S project -G "Visual Studio 17 2022" ^
                -DLY_3RDPARTY_PATH=%LY_3RDPARTY_PATH%

      - name: Build Editor + Launcher
        shell: cmd
        run: |
          cmake --build build --config profile --target Editor MyProject.GameLauncher -- /m:4

      - name: Process assets
        shell: cmd
        run: |
          build\bin\profile\AssetProcessorBatch.exe --platforms=pc

      - name: Run smoke tests
        shell: cmd
        run: |
          ctest --test-dir build -C profile -L SUITE_smoke --output-on-failure

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-windows
          path: build/Testing/**/*.xml

      - name: Upload Editor log on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: editor-log
          path: project/user/log/
```

---

## 关键要点

### 1) 3rdParty 缓存

`LY_3RDPARTY_PATH` 里的包 ~GB 级，**一定要 cache**。key 用 `BuiltInPackages_<os>.cmake` 的 hash（改包版本自动失效）。

没缓存 → 每次 CI 重下几 GB → 构建从 15min 变 45min+。

### 2) Git LFS

O3DE 用 LFS 存大二进制（美术资产、3rdParty 压缩包）。`actions/checkout@v4` 要 `lfs: true`。忘了 → 大文件是文本指针，编译肯定挂。

### 3) Compiler Cache

[.github/workflows/windows-build.yml](../.github/workflows/windows-build.yml) 用 `ccache`：

```yaml
env:
  CMAKE_C_COMPILER_LAUNCHER: ccache
  CMAKE_CXX_COMPILER_LAUNCHER: ccache
```

同样 cache `~/.ccache` 目录。增量构建能从 20min 降到 5min。

### 4) 固定工具链版本

别依赖 "latest"。`BuildTools` / `Windows SDK` 版本锁住，避免 "今天跑着明天突然红"。

```yaml
- uses: ilammy/msvc-dev-cmd@v1
  with:
    toolset: 14.38   # 具体版本
```

### 5) 构建类型矩阵

典型 O3DE 项目至少跑这几个 job：

| Platform | Config | 目的 |
|---|---|---|
| Windows | profile | PR 验证 |
| Windows | profile_test | 单元测试 |
| Windows | release + monolithic | 出货验证 |
| Linux | profile | 跨平台兼容 |
| Linux | profile_test | 单元测试 |
| (periodic) Mac / Android / iOS | profile | 移动端 |

---

## TIAF（Test Impact Framework）— 增量测试

### 为什么用

跑全量测试在大项目 = 1+ 小时。TIAF 根据 PR 的 diff 选"只可能被影响的 test"，常规 PR 降到几分钟。

### 怎么接入

[Code/Tools/TestImpactFramework/](../Code/Tools/TestImpactFramework/)：

```bash
# 1) 首次在 main 分支离线生成覆盖图（很慢，只需一次 / 定期重建）
tiaf.py generate-coverage --build-dir build --output coverage.json

# 2) PR 上跑影响分析
tiaf.py analyze \
    --build-dir build \
    --coverage coverage.json \
    --changed-files <(git diff --name-only origin/main)

# 输出受影响 test 列表，传给 ctest -R 过滤
```

大多数项目**不一定要上 TIAF**（配置复杂）。策略：

- 小项目：跑全量 smoke + main suite。
- 中项目：smoke 每 PR + main 每小时 batch + full 夜间。
- 大项目：TIAF。

### 用 ctest label 直接分层

这是最简单的"穷人版 TIAF"：

```bash
# PR 触发（2 min 内完成）
ctest -L "SUITE_smoke" -j 8

# Merge 触发（主分支 push）
ctest -L "SUITE_smoke|SUITE_main" -j 8

# 夜间
ctest -j 8   # 全部
```

---

## Asset CI

资产问题常见：开发机上能跑但 CI 挂。典型原因：

1. **资产路径大小写**：Windows 不敏感、Linux 敏感。大小写错了 Windows 本地跑着、Linux CI 炸。
2. **资产缺失**（没 commit 或没 LFS push）。
3. **fingerprint 不稳定** → 每次 CI 重编所有产物。
4. **Builder 版本漂移** → AP 报 "Builder does not match"。

### CI 里的 AP 运行

```bash
# 干净跑
bin/profile/AssetProcessorBatch.exe --platforms=pc --regset="/Amazon/AssetProcessor/Settings/enableBuilderDebugFlag=1"
echo %ERRORLEVEL%   # 非 0 = 失败

# 检查产物
if not exist Cache\pc\assetcatalog.xml exit /b 1
```

### AP 失败 fail-fast

在 CI 开 `"EnableBuilderDebugFlag"=true` → 任何 builder error 立即非 0 退出，不 retry。

---

## 打包 / Release CI

### 构建 monolithic

CI 必须覆盖一次：

```bash
cmake -B build/release -S . \
    -G "Ninja Multi-Config" \
    -DLY_MONOLITHIC_GAME=ON \
    -DLY_3RDPARTY_PATH=%LY_3RDPARTY_PATH%

cmake --build build/release --config release --target MyProject.GameLauncher
```

不测 monolithic → 出货第一天必翻车。

### Bundle 资产

```bash
# 1) 生成 seed → assetList
bin/profile/AssetBundlerBatch.exe assetLists \
    --addSeed AutomatedTesting.GameLauncher.Seeds \
    --output out.assetlist

# 2) asstlist → .pak
bin/profile/AssetBundlerBatch.exe bundles \
    --assetListFile out.assetlist \
    --outputBundlePath Bundles/Game.pak \
    --maxSize 2048
```

### 包文件夹结构

```
dist/
├── MyProject.GameLauncher.exe
├── *.dll
├── Bundles/
│   ├── Game.pak
│   └── Game.pak.manifest.xml
├── Registry/
│   └── *.setreg
└── Assets/                # 如果没 bundle，保留松散资产
```

CI 最后一步 zip / tar 上传到 release artifacts。

---

## Jenkins（O3DE 主仓库用）

[scripts/build/Jenkins/Jenkinsfile](../scripts/build/Jenkins/Jenkinsfile) + [scripts/build/Jenkins/o3de.json](../scripts/build/Jenkins/o3de.json) 是参照。

主要思路：

- `o3de.json` 是构建矩阵配置（哪些平台 / 哪些类型 / 哪些 label 跑哪个）。
- `Jenkinsfile` 读它，for 循环生成 parallel jobs。

自有项目用 Jenkins，可以抄这套。要点：

- agent label 要匹配平台（`windows-vs2022`, `ubuntu-2404` 或 `ubuntu-2204`）。
- 每 agent 预装好 3rdParty 缓存。
- 失败通知到 Slack / 邮件。

---

## 代码质量 / 静态检查

主仓库的 [.github/workflows/validation.yaml](../.github/workflows/validation.yaml) 有：

- 许可证头检查（每个新文件要有 Apache-2.0 or MIT header）
- 行尾空白 / CRLF 检查
- Python 代码 `pylint`

自有项目可加：

- `clang-format --dry-run -Werror` 格式检查
- `clang-tidy` 静态分析
- 自定义脚本扫 `AZ_Assert(DoThing())` 之类副作用模式

---

## Docker 构建（Linux / Android）

[Docker/](../Docker/) 目录：

```
Docker/
├── Dockerfile         # Linux 构建镜像
├── build.sh
└── entrypoint.sh
```

用法：

```bash
# Ubuntu 24.04（noble）为 base — 推荐
docker build -f Dockerfile \
    --build-arg INPUT_IMAGE=ubuntu \
    --build-arg INPUT_TAG=noble \
    -t o3de:ubuntu-noble .

# Ubuntu 22.04（jammy）为 base — 老项目兼容
docker build -f Dockerfile \
    --build-arg INPUT_IMAGE=ubuntu \
    --build-arg INPUT_TAG=jammy \
    -t o3de:ubuntu-jammy .

# ROS2 Jazzy（基于 Ubuntu 24.04）
docker build -f Dockerfile \
    --build-arg INPUT_IMAGE=ros \
    --build-arg INPUT_TAG=jazzy \
    -t o3de:ros-jazzy .

# 在容器里跑构建
docker run --rm \
    -v $PWD:/workspace \
    -v $HOME/o3de-packages:/packages \
    -e LY_3RDPARTY_PATH=/packages \
    o3de:ubuntu-noble ./Docker/build.sh
```

好处：构建环境锁死（Ubuntu 版本 / compiler 版本 / Python 版本）。CI 镜像基于这个起。

**INPUT_TAG 支持的值**（见 [Docker/README.md](../Docker/README.md)）：
- `jammy` — Ubuntu 22.04
- `noble` — Ubuntu 24.04（推荐）
- `humble` — ROS2 Humble（Ubuntu 22.04 base）
- `jazzy` — ROS2 Jazzy（Ubuntu 24.04 base）

---

## 常见 CI 陷阱

1. **3rdParty 缓存 miss**：key 不稳定（带时间戳 / CI 运行 ID）→ 每次重下。key 用配置文件 hash。
2. **LFS 没 fetch**：默认 checkout 不拉 LFS。`lfs: true`。
3. **Runner 磁盘空间不够**：O3DE 编译产物 + Cache + 3rdParty ~50GB。用 `actions/cache` 清老 key。
4. **编译器版本漂移**：`ubuntu-latest` 某天升级 → ABI 不兼容。锁具体版本：`ubuntu-24.04`（推荐 / 对应 O3DE 官方 Docker noble tag）或 `ubuntu-22.04`（老项目）。
5. **AP 在 CI 跑挂在 "waiting for connection"**：`bootstrap.setreg` 里 `wait_for_connect=false`。
6. **Tests require GPU but runner headless**：tests 加 `TEST_REQUIRES gpu` 标签，CI 用 `ctest -LE REQUIRES_gpu` 排除。
7. **monolithic 构建和 shared 构建产物共用 build 目录** → symbol 冲突。分开 `build/shared` / `build/mono`。
8. **Windows 长路径超 260 字符**：`build\profile\<deep>\<long>.obj.pdb`。用 `C:\o\` 根目录 + 注册表开长路径支持。
9. **Git checkout 全量历史**：clone 慢。`fetch-depth: 1`（如果你不需要 git log 分析）。
10. **没跑 monolithic**：出货前必翻车。**每个 PR 至少冒烟一次 monolithic build**（可以只编 launcher 不 run test）。

---

## 最小 CI yaml（给小项目当起点）

粘贴即用（改几个名字）：

```yaml
name: CI

on: [pull_request]

env:
  LY_3RDPARTY_PATH: ${{ github.workspace }}/3rdparty

jobs:
  build-windows:
    runs-on: windows-2022
    steps:
      - uses: actions/checkout@v4
        with: { lfs: true }

      - uses: actions/cache@v3
        with:
          path: ${{ env.LY_3RDPARTY_PATH }}
          key: 3p-win-${{ hashFiles('cmake/3rdParty/Platform/Windows/BuiltInPackages_windows.cmake') }}

      - name: Configure
        run: cmake -B build -G "Visual Studio 17 2022" -DLY_3RDPARTY_PATH=${{ env.LY_3RDPARTY_PATH }}

      - name: Build
        run: cmake --build build --config profile --target Editor MyProject.GameLauncher

      - name: Process Assets
        run: build\bin\profile\AssetProcessorBatch.exe --platforms=pc

      - name: Test
        run: ctest --test-dir build -C profile -L SUITE_smoke --output-on-failure

      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: logs-windows
          path: |
            user/log/
            build/Testing/**/*.xml

  build-linux:
    runs-on: ubuntu-24.04    # O3DE 官方 Docker noble tag 同系列
    steps:
      - uses: actions/checkout@v4
        with: { lfs: true }

      - name: Install deps
        run: |
          sudo apt update
          sudo apt install -y build-essential cmake ninja-build clang-17 lld-17 \
            libglu1-mesa-dev libxcb-xinerama0 libfontconfig1-dev \
            libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
            libxcb-randr0 libxcb-render-util0 libxcb-xkb-dev \
            libxkbcommon-x11-dev libssl-dev zlib1g-dev \
            libxcb-cursor-dev

      - uses: actions/cache@v3
        with:
          path: ${{ env.LY_3RDPARTY_PATH }}
          key: 3p-linux-${{ hashFiles('cmake/3rdParty/Platform/Linux/BuiltInPackages_linux.cmake') }}

      - name: Configure
        env:
          CC: clang-17
          CXX: clang++-17
        run: cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=profile -DLY_3RDPARTY_PATH=${{ env.LY_3RDPARTY_PATH }}

      - name: Build
        run: cmake --build build --config profile --target Editor MyProject.GameLauncher -j$(nproc)

      - name: Process Assets
        run: ./build/bin/profile/AssetProcessorBatch --platforms=pc

      - name: Test
        run: ctest --test-dir build -C profile -L SUITE_smoke --output-on-failure

      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: logs-linux
          path: |
            user/log/
            build/Testing/**/*.xml
```

两个 job 并行跑，Linux 作用：**早期发现 Windows 上不会暴露的问题**（大小写、编译器差异、动态库依赖）。

---

## 发布流程 checklist

出 alpha / beta / release 时过一遍：

- [ ] monolithic 构建过
- [ ] 跑 `SUITE_main` 全绿
- [ ] AP 无 warning（`--strict-mode`）
- [ ] Bundler 跑完，无 missing dependency
- [ ] `release` config + 优化开（`LY_PROFILE_DISABLE=ON` 如果有）
- [ ] 平台签名（Windows Authenticode / macOS codesign / iOS provisioning）
- [ ] PDB 另存 symbol server（崩溃分析用）
- [ ] Changelog 生成
- [ ] Smoke test 装好的包（在全新机器上 clean install）

---

## 相关 O3DE 仓库文件参考

| 文件 / 目录 | 作用 |
|---|---|
| [.github/workflows/](../.github/workflows/) | GitHub Actions 全套 |
| [scripts/build/ci_build.py](../scripts/build/ci_build.py) | CI 入口 |
| [scripts/build/Platform/](../scripts/build/Platform/) | 各平台 build_config.json + 命令 |
| [scripts/build/Jenkins/](../scripts/build/Jenkins/) | Jenkinsfile 参考 |
| [scripts/build/TestImpactAnalysis/](../scripts/build/TestImpactAnalysis/) | TIAF 脚本 |
| [Docker/](../Docker/) | Linux / Android 容器构建 |
| [cmake/LYTestWrappers.cmake](../cmake/LYTestWrappers.cmake) | `ly_add_googletest` 定义 |
| [CMakePresets.json](../CMakePresets.json) | CI 用 preset |

继续：[06_build_and_cmake.md](06_build_and_cmake.md) 讲构建系统；[15_debugging_toolkit.md](15_debugging_toolkit.md) 调试；[16_performance_checklist.md](16_performance_checklist.md) 性能。
