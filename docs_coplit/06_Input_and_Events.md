## 输入系统与事件总线 (Input / EBus)

概述:

- 处理平台输入、Action 映射，并借助 `EBus`/通知向订阅端分发事件。

示例文件:

- [Gems/BarrierInput/Code/Source/BarrierInputMouse.cpp](Gems/BarrierInput/Code/Source/BarrierInputMouse.cpp)

结构化占位:

- **DeviceAbstraction**: 平台原始输入 -> 引擎抽象层的映射文件。
- **EventFlows**: EBus 定义、发送与订阅实例。
- **ExtractionTasks**:
  1. 提取 Action 映射表及其配置文件（若有）。
  2. 生成 EBus 使用统计（哪些模块发起/订阅某个 EBus）。

关键组件与代表文件：
- 核心 Input System: `InputSystemComponent`（实现示例：[Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp](Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp#L1)），包含设备创建/配置与 BehaviorContext 绑定。
- 设备适配器: `AzFramework/Input/Devices/*`（Keyboard/Mouse/Gamepad/Touch 等）。
- 鼠标/光标管理与游标请求总线：参见 Editor 的使用点（例如 [Code/Editor/MainWindow.cpp](Code/Editor/MainWindow.cpp#L493) 中的 `InputSystemCursorRequestBus` 调用）。

自动化提取任务（建议）：
1. 提取 `InputSystemComponent::Reflect` 中暴露的 BehaviorContext 事件与方法签名。
2. 列举 `AzFramework::InputDevice*` 的 channel id 列表并记录在案（可用于生成映射表）。
3. 在 `Code/Editor/**` 中查找 `InputSystemCursorRequestBus`、`InputChannelRequestBus` 的调用并记录常见用法示例与行号。

### Extracted signatures & behaviors (representative)

- From `Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp`:
  - `void InputSystemComponent::Reflect(AZ::ReflectContext* context)` — registers `InputSystemNotificationBus` and `InputSystemRequestBus` to BehaviorContext and reflects input device types (`InputDeviceMouse`, `InputDeviceKeyboard`, etc.).
  - `void InputSystemComponent::Activate()` — reads settings from `AZ::SettingsRegistry`, calls `CreateEnabledInputDevices()`, and connects request/tick buses.
  - `void InputSystemComponent::TickInput()` — broadcasts `InputSystemNotificationBus` pre/post events and dispatches input device ticks via `InputDeviceRequestBus::TickInputDevice`.
  - `void InputSystemComponent::CreateEnabledInputDevices()` — instantiates `InputDeviceGamepad`, `InputDeviceKeyboard`, `InputDeviceMouse`, `InputDeviceMotion`, `InputDeviceTouch`, `InputDeviceVirtualKeyboard` based on settings.

These show the common lifecycle: `Reflect()` exposes APIs to scripting, `Activate()` configures devices, `TickInput()` dispatches per-frame input updates.

### Next extraction step

- Enumerate all `InputDevice*::Reflect` methods and record channel id lists and their names for use in automated mapping generation.

### Line-numbered references (verified)

- From `Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp`:
  - [Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp](Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp#L82) — `void InputSystemComponent::Reflect(AZ::ReflectContext* context)`
  - [Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp](Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp#L205) — `void InputSystemComponent::Activate()`
  - [Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp](Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp#L267) — `void InputSystemComponent::TickInput()`
  - [Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp](Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.cpp#L300) — `void InputSystemComponent::CreateEnabledInputDevices()`
