# Editor Startup Architecture

## Why This File Matters

The editor startup path is not a single class. It is a chain that moves across:

- a tiny executable entry point
- a dynamically loaded editor library
- a Qt application shell
- an `AzToolsFramework`-based tools application
- a legacy `IEditor` service object

If an AI does not understand this chain, it will misread almost every editor subsystem.

## Startup Chain

### 1. `Code/Editor/main.cpp`

This file is the process entry point.

Its job is intentionally small:

- check whether a project path is available
- launch the project manager when needed
- dynamically load `EditorLib`
- look up `CryEditMain`
- invoke that function

This means the executable itself is only a bootstrap shell.

## 2. `CryEditMain`

The symbol is exported from the editor library and is implemented in:

- `Code/Editor/CryEdit.cpp`

This is one of the core orchestration points of the editor product.

From the file-level call sites and startup sequence, the important phases are:

- create the Qt-side editor application
- create the legacy editor core object
- initialize the editor core
- initialize the main window
- register auto commands
- load plugins

Use `CryEditMain` when you need the top-level lifecycle path.

## 3. `Editor::EditorQtApplication`

Read first:

- `Code/Editor/Core/QtEditorApplication.h`
- `Code/Editor/Core/QtEditorApplication.cpp`

This is the editor's `QApplication`-derived shell. It handles:

- Qt setup and event filters
- editor settings load and save
- native event filtering
- key and mouse button state tracking
- stylesheet refresh
- translator installation
- editor idle-related behavior

This class is about the Qt process shell, not the editor system entity.

## 4. `EditorInternal::EditorToolsApplication`

Read first:

- `Code/Editor/EditorToolsApplication.h`
- `Code/Editor/EditorToolsApplication.cpp`

This class extends `AzToolsFramework::ToolsApplication` for the editor product. It is responsible for:

- registering editor-specific reflected components and Python bindings
- adding required editor system components
- marking the application as `Editor | Tool`
- creating the edit context
- exposing editor automation APIs on a behavior bus
- level open, level create, and exit helpers

Important detail:

- this is the modern system-entity-facing editor app layer
- it is not the same thing as the Qt app shell

## 5. `CEditorImpl`

Read first:

- `Code/Editor/IEditorImpl.h`
- `Code/Editor/IEditorImpl.cpp`
- `Code/Editor/IEditor.h`

`CEditorImpl` is the legacy editor service hub behind the `IEditor` interface.

It owns or coordinates many major services:

- command manager
- plugin manager
- undo manager
- view manager
- animation context
- TrackView sequence manager
- display settings
- asset browser request handler
- asset editor request handler
- asset database location listener

This is one of the most important bridge objects in `Code/Editor`.

## Core Mental Model

### 1. There are two application shells, not one

You need to distinguish:

- `EditorQtApplication`: Qt process and UI app shell
- `EditorToolsApplication`: `AzToolsFramework` tools application and editor system components

Many bugs come from mixing these two roles together.

### 2. `CEditorImpl` is still central

Even though the editor uses `AzToolsFramework`, the product still routes a lot of behavior through:

- `GetIEditor()`
- `IEditor`
- `CEditorImpl`

So if a workflow feels modern in one layer and legacy in another, that is expected.

### 3. Startup is hybrid on purpose

The editor does not go directly from `main()` to `MainWindow`.
It goes through a hybrid bootstrap:

1. executable bootstrap
2. dynamic editor library
3. Qt app shell
4. tools application
5. legacy editor core
6. main window and panes

## Read These Files First

- `Code/Editor/main.cpp`
- `Code/Editor/CryEdit.cpp`
- `Code/Editor/Core/QtEditorApplication.h`
- `Code/Editor/EditorToolsApplication.h`
- `Code/Editor/IEditorImpl.h`
- `Code/Editor/IEditor.h`

## AI Search Hints

Use these terms first:

- `CryEditMain`
- `EditorQtApplication`
- `EditorToolsApplication`
- `CEditorImpl`
- `GetIEditor`
- `Initialize`
- `LoadPlugins`

## Common Misreads

- `main.cpp` is not where most editor logic lives.
- `EditorToolsApplication` is not the same thing as `MainWindow`.
- `CEditorImpl` is not obsolete just because `AzToolsFramework` exists.

## What To Read Next

After this file, continue with:

- [02-main-window-and-panes.md](02-main-window-and-panes.md)
