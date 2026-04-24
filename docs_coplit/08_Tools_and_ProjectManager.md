## 工具与 Project Manager

概述:

- 包含 Project Manager、Asset Processor、Editor 相关工具的源代码，关注 UI 流程与工具链集成点。

示例文件:

- [Code/Tools/ProjectManager/Source/Application.cpp](Code/Tools/ProjectManager/Source/Application.cpp)

结构化占位:

- **UserFlows**: 列出工具的用户操作入口（新建/打开/导出项目）。
- **BackgroundWorkers**: 列出后台构建/导出/下载任务的实现文件。
- **ExtractionTasks**:
  1. 提取 ProjectManager 的 CLI/API 接口与 Qt GUI 入口点。

---

MainClasses (sample extracted):

- `Application` (Project Manager 主入口)
  - 文件: Code/Tools/ProjectManager/Source/Application.h
  - 关键方法: `bool Init(bool interactive = true, AZStd::unique_ptr<PythonBindings> pythonBindings = nullptr)`, `bool Run()`, `void TearDown()`。

- `PythonBindings` (Embedded Python 绑定接口)
  - 文件: Code/Tools/ProjectManager/Source/PythonBindings.h / PythonBindings.cpp
  - 说明: 提供与 Python 脚本层交互的桥接，示例实现会使用 `pybind11` 将 C++ 方法暴露给 Python。

- `ScreensCtrl` / `ScreenFactory` (UI 屏幕路由与构建)
  - 文件: Code/Tools/ProjectManager/Source/ScreensCtrl.h / ScreenFactory.cpp
  - 关键方法: `BuildScreens`, `ChangeToScreen`, `FindScreen`, `BuildScreen(...)`。

KeyFiles (quick pointers):

- Application: Code/Tools/ProjectManager/Source/Application.h / Application.cpp
- Python bindings: Code/Tools/ProjectManager/Source/PythonBindings.h / PythonBindings.cpp
- UI screen & widgets: Code/Tools/ProjectManager/Source/ScreenFactory.*, ScreensCtrl.*, ScreenWidget.*
- Project utilities: Code/Tools/ProjectManager/Source/ProjectUtils.*

Notes for AI fill-in:

- For each class, parse header to extract public methods and their signatures, then locate implementations in corresponding .cpp files to capture behavior comments and usage.
- For Python bindings, identify `pybind11::module` usage and list exposed functions to Python for external scripting use.

