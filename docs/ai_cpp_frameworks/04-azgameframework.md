# AzGameFramework

## Module Role

`AzGameFramework` is thin but important. It mainly wraps `AzFramework::Application` into a game or launcher-oriented application entry point.

Do not treat it as the main gameplay framework. In the current `Code/Framework/AzGameFramework/AzGameFramework` tree it is mostly about:

- game application startup
- pak mounting
- headless and console mode handling
- game-specific Settings Registry merging

If the question is "how does the game process start," "when are paks mounted," or "how does console mode get selected," this is the first place to read.

## Key Entry Points

### 1. `AzGameFramework::GameApplication`

Source:

- `Code/Framework/AzGameFramework/AzGameFramework/Application/GameApplication.h`
- `Code/Framework/AzGameFramework/AzGameFramework/Application/GameApplication.cpp`

It extends `AzFramework::Application` and adds behavior such as:

- allowing `SettingsRegistry` to use `FileIO`
- attempting to mount `engine.pak`
- opening all `@products@/*.pak` archives by default
- deciding whether console-only mode should be enabled based on settings or command line
- merging game and launcher-specific settings data

### 2. `AzGameFrameworkModule`

Source:

- `Code/Framework/AzGameFramework/AzGameFramework/AzGameFrameworkModule.cpp`

The module itself is minimal. `GetRequiredSystemComponents()` returns an empty list, which is a useful signal that this layer is more about application wrapping than a heavy collection of systems.

## Directory Map

| Path | Purpose |
| --- | --- |
| `Application/` | `GameApplication` implementation |
| `API/` | game application event interface |
| `AzGameFrameworkModule.*` | module shell |

## Core Mental Model

### 1. This layer turns the runtime application into a launcher or game process

The clearest evidence is in `GameApplication.cpp`:

- the constructor checks the cache root or executable directory for `engine.pak`
- it then opens `@products@/*.pak` archives by default

That means this layer directly affects early startup resource visibility.

### 2. Console mode can come from either config or command line

`StartCommon(...)` checks several places:

- `/O3DE/Launcher/Bootstrap/ConsoleMode`
- `/O3DE/Atom/RPI/Initialization/NullRenderer`
- command-line `-console-mode`
- command-line `-NullRenderer`
- command-line `-rhi=null`

If an AI is trying to explain why no window appears or why a null renderer path was selected, this file matters.

### 3. Settings Registry merging is specialized for game startup

`MergeSettingsToRegistry(...)` does the following:

- builds specializations and appends `game`
- merges shared settings
- reads `/O3DE/Runtime/LauncherType`
- loads `bootstrap.<launcher-type>.<config>.setreg` when applicable
- merges user settings last

So many launcher or game startup settings are not hard-coded in C++. They are composed from setreg files.

## Read These Files First

- `Code/Framework/AzGameFramework/AzGameFramework/Application/GameApplication.h`
- `Code/Framework/AzGameFramework/AzGameFramework/Application/GameApplication.cpp`
- `Code/Framework/AzGameFramework/AzGameFramework/API/GameApplicationAPI.h`
- `Code/Framework/AzGameFramework/AzGameFramework/AzGameFrameworkModule.cpp`

## AI Search Hints

Use these names first:

- `GameApplication`
- `StartCommon`
- `MergeSettingsToRegistry`
- `engine.pak`
- `console-mode`
- `LauncherType`

## Common Misreads

- Gameplay rules, character systems, and level-specific logic are usually not in `AzGameFramework`.
- `AzGameFramework` is not the renderer, not the multiplayer layer, and not the project gameplay gem.
- Once the problem moves into real game features, continue into gems or project code.

## Relationship To Other Modules

- It reuses the runtime application shell from `AzFramework`.
- It is a direct C++ bootstrap layer for launcher and game processes.
- Higher-level game functionality is usually distributed across gems and project modules.
