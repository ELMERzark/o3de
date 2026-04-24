## 脚本与游戏逻辑层 (ScriptCanvas / Lua / Python)

概述:

- 支持 ScriptCanvas 可视脚本、Lua 与 Python 绑定，脚本层通过绑定或桥接模块访问底层 C++ 服务。

示例路径:

- [Gems/ScriptCanvas](Gems/ScriptCanvas)
- [Code/LuaScripts](Code/LuaScripts)

结构化占位:

- **Bindings**: 列出 C++ -> 脚本 API 的绑定点（函数/类）。
- **ScriptRuntime**: 脚本执行入口、生命周期与沙箱约束。
- **ExtractionTasks**:
  1. 自动识别并列出对外暴露给脚本的 API（类名 + 方法签名 + 文件）。

关键组件与代表文件：
- ScriptCanvas (可视脚本) 资源与示例：`Gems/ScriptCanvas`，AutomatedTesting 中有大量 `.scriptcanvas` 用例用于测试与示例。
- Lua 支持与工具：`Code/Tools/LuaIDE`，以及 `Code/LuaScripts` 下运行时脚本资源。
- Python 绑定（Tools/ProjectManager 使用 pybind11）：参考 [Code/Tools/ProjectManager/Source/Application.h](Code/Tools/ProjectManager/Source/Application.h#L1) 和 Python bindings 实现点。

自动化提取任务（建议）：
1. 查找 `AZ::BehaviorContext`、`pybind11` 或自定义绑定/Reflect(...) 的位置并提取被暴露的 API 列表（类/方法/签名与行号）。
2. 枚举 ScriptCanvas 的 asset handlers 与编译后运行时入口（查找 `.scriptcanvas` 编译/加载点）。
3. 列出 Lua 脚本运行时调用点（例如 spawnable 脚本加载与调用链）。

### Representative scripting entry points & bindings

- **ProjectManager::Application** (Python integration):
  - `bool Init(bool interactive = true, AZStd::unique_ptr<PythonBindings> pythonBindings = nullptr);`
  - `bool Run();`
  - `void TearDown();`
  - Notes: Implements `AzToolsFramework::EmbeddedPython::PythonLoader` and holds `AZStd::unique_ptr<PythonBindings>` to initialize Python embedding/pybind hooks.

- **Extraction guidance:**
  - Find `AZ::BehaviorContext` `Reflect(...)` functions and `pybind11::module` usage across `Gems/**` and `Code/**` to enumerate bindings exposed to ScriptCanvas, Lua, and Python.

### Next extraction step

- Scan `Gems/ScriptCanvas` and `Code/*` for `Reflect(AZ::ReflectContext*)`, `BehaviorContext->EBus`, and `pybind11` bindings and append line-numbered API lists into this doc.

### Line-numbered references (verified)

- From `Code/Tools/ProjectManager/Source/Application.h`:
  - [Code/Tools/ProjectManager/Source/Application.h](Code/Tools/ProjectManager/Source/Application.h#L35) — `bool Init(bool interactive = true, AZStd::unique_ptr<PythonBindings> pythonBindings = nullptr);`
  - [Code/Tools/ProjectManager/Source/Application.h](Code/Tools/ProjectManager/Source/Application.h#L36) — `bool Run();`
  - [Code/Tools/ProjectManager/Source/Application.h](Code/Tools/ProjectManager/Source/Application.h#L37) — `void TearDown();`
