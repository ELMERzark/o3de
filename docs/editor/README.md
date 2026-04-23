# O3DE Editor C++ AI Guide

This document set maps the legacy-plus-modern editor code under `Code/Editor`.

The goal is to help an AI answer questions such as:

- where the editor process really starts
- which layer owns the main window and dock panes
- where Asset Browser, Asset Editor, and Asset Importer connect
- where viewport behavior is implemented
- where commands, undo, plugins, and TrackView live

## Scope

This batch focuses only on `Code/Editor`.

It does not try to fully document:

- `Code/Framework/*`
- editor behavior implemented in gems
- asset builders, Asset Processor internals, or `Code/Tools/*`

Those areas are often reached through `Code/Editor`, but they are not the main target here.

## Important Mental Model

`Code/Editor` is not a clean-room UI layer. It is a product layer that mixes:

- the newer `AzToolsFramework` editor stack
- Qt application and dock window hosting
- older CryEdit-era service patterns and interfaces

This means many workflows cross several styles of code at once:

- `main.cpp` and dynamic module bootstrap
- `EditorToolsApplication` and `ToolsApplication`
- `EditorQtApplication`
- `CEditorImpl` and `IEditor`
- `MainWindow` and `QtViewPaneManager`

An AI should expect hybrid architecture here.

## Reading Order

1. [01-startup-architecture.md](01-startup-architecture.md)
2. [02-main-window-and-panes.md](02-main-window-and-panes.md)
3. [03-asset-workflows.md](03-asset-workflows.md)
4. [04-viewport-and-interaction.md](04-viewport-and-interaction.md)
5. [05-commands-and-undo.md](05-commands-and-undo.md)
6. [06-trackview-and-plugins.md](06-trackview-and-plugins.md)

## Fast Routing Table

| If the question is about | Read first |
| --- | --- |
| startup, process bootstrap, app lifetime, editor system entity, legacy editor core | [01-startup-architecture.md](01-startup-architecture.md) |
| main window, dock panes, pane registration, layouts, view widgets | [02-main-window-and-panes.md](02-main-window-and-panes.md) |
| Asset Browser, Asset Editor, Asset Importer, asset database hookup | [03-asset-workflows.md](03-asset-workflows.md) |
| editor viewport widget, camera, viewport buses, PIE-related viewport behavior | [04-viewport-and-interaction.md](04-viewport-and-interaction.md) |
| command registration, command execution, undo and redo flow | [05-commands-and-undo.md](05-commands-and-undo.md) |
| TrackView, plugin loading, editor-wide legacy service interfaces | [06-trackview-and-plugins.md](06-trackview-and-plugins.md) |

## High-Value Directories

| Directory | Why it matters |
| --- | --- |
| `Code/Editor/Core` | Qt app shell and editor action registration helpers |
| `Code/Editor` root | process entry glue, `MainWindow`, `EditorToolsApplication`, `IEditorImpl` |
| `Code/Editor/AzAssetBrowser` | editor-facing Asset Browser pane and request handler |
| `Code/Editor/AssetEditor` | asset editor pane wrapper and request routing |
| `Code/Editor/AssetImporter` | import UI and drag-and-drop import flow |
| `Code/Editor/Commands` | command manager and auto-registration |
| `Code/Editor/Undo` | legacy editor undo stack |
| `Code/Editor/TrackView` | cinematic sequence editor |
| `Code/Editor/Plugins` | editor plugin integration points |

## Suggested Next Batch After This

If the editor docs are expanded further, good next targets are:

1. `Code/Editor/Plugins/ComponentEntityEditorPlugin`
2. `Code/Editor/TrackView/*`
3. `Code/Editor/Controls/ReflectedPropertyControl/*`
4. specific editor-facing gems used by your project
