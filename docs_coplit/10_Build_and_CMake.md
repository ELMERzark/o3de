## 构建系统与 CMake 约定

概述:

- 使用 CMake 进行多平台构建。顶层 `CMakeLists.txt`、`CMakePresets.json` 与子目录 `*_files.cmake` 管理模块编译与目标分离（editor vs runtime）。

关键文件示例:

- [CMakeLists.txt](CMakeLists.txt)
- [CMakePresets.json](CMakePresets.json)

结构化占位:

- **TargetGraph**: 为每个 CMake target 列出依赖的 sources 与依赖 targets。
- **PlatformMacros**: 汇总常见用于区分平台/配置的 CMake 宏与变量。
- **ExtractionTasks**:
  1. 解析 `CMakePresets.json` 与 top-level CMake，生成 target -> source 列表（可导出为 JSON 供 AI 使用）。

自动化提取任务（建议）：
1. 解析 workspace 中的 `CMakeLists.txt` 层级，构建 target dependency graph（将每个 `add_library`/`add_executable` 与其 `target_link_libraries` 解析出来）。
2. 列出每个 target 的源文件目录并映射到引擎模块（便于建立代码 -> build target 的索引）。
3. 提取 platform-specific cmake fragments（例如 `Platform/*_files.cmake`）以标明平台差异化源码与编译选项。

### Representative CMake patterns (from top-level `CMakeLists.txt`)

- Project initialization: `cmake_minimum_required(VERSION 3.24)` and `project(O3DE LANGUAGES C CXX VERSION ${O3DE_INSTALL_VERSION_STRING})`.
- Modular includes: `include(cmake/Gems.cmake)`, `include(cmake/Projects.cmake)` and `add_subdirectory(Code)` to register engine modules.
- Post-processing hooks: `ly_enable_gems_delayed()`, `ly_delayed_generate_static_modules_inl()`, `ly_delayed_generate_runtime_dependencies()` are called after all targets are known to finalize module registration and runtime dependency injection.

### Next extraction step

- Run an AST-lite parser across `**/CMakeLists.txt` to enumerate `add_library` / `add_executable` / `target_link_libraries` occurrences and emit a `targets.json` mapping targets -> sources -> linked targets for downstream AI processing.

### Line-numbered references (verified)

- Top-level `CMakeLists.txt`:
  - [CMakeLists.txt](CMakeLists.txt#L10) — `cmake_minimum_required(VERSION 3.24)`
  - [CMakeLists.txt](CMakeLists.txt#L33) — `project(O3DE` (project initialization)
  - [CMakeLists.txt](CMakeLists.txt#L169) — `ly_delayed_generate_static_modules_inl()` (post-processing hook used to finalize static module generation)
