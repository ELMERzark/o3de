# Main Window And Panes

## Why This File Matters

A large amount of editor behavior becomes visible through:

- `MainWindow`
- pane registration
- dock widgets
- saved and restored layouts

If an AI needs to answer "where does this pane come from" or "who owns this docked widget," this is the right starting point.

## Main Classes

### 1. `MainWindow`

Read first:

- `Code/Editor/MainWindow.h`
- `Code/Editor/MainWindow.cpp`

`MainWindow` is the main Qt window for the editor product. Its responsibilities include:

- status bar ownership
- active view tracking
- pane opening helpers
- toolbar and layout setup
- auto-save timers
- Asset Importer integration
- source control notifications
- engine and Asset Processor connection status UI
- drag-and-drop entry points

It also owns an `EditorActionsHandler`, which is important for menus and toolbars.

### 2. `QtViewPaneManager`

Read first:

- `Code/Editor/QtViewPaneManager.h`
- `Code/Editor/QtViewPaneManager.cpp`

This is the central pane registry and docking manager. It handles:

- registering panes by name and category
- creating pane widgets through factory callbacks
- opening, closing, and toggling panes
- managing multi-instance panes
- saving and restoring layouts
- serializing pane layout state

Important data model:

- `QtViewPane`
- `DockWidget`

This layer is what turns a view factory into an actual docked pane in the editor.

### 3. `EditorActionsHandler`

Read first:

- `Code/Editor/Core/EditorActionsHandler.h`
- `Code/Editor/Core/EditorActionsHandler.cpp`

This class is a key bridge between:

- editor events
- action manager registration hooks
- menu and toolbar binding
- viewport settings state
- selection and undo notifications

If a question is about why an action appears in the menu or toolbar, or how pane actions are refreshed, check this class.

## How Panes Get Added

The usual pattern is:

1. a pane class exposes a static `RegisterViewClass()`
2. that function eventually calls into `QtViewPaneManager::RegisterPane(...)`
3. the pane is created through a widget factory
4. `MainWindow` or action handlers open it by name

This is a much better search strategy than looking only for direct constructor calls.

## High-Value Registration Sites

`MainWindow::Initialize()` is one of the best places to inspect because it registers several common panes, including:

- TrackView
- error report dialog
- Python scripts dialog
- console panes
- settings manager
- Asset Browser
- Asset Editor

That makes it a very useful hub for editor UI discovery.

## Layout System Notes

`QtViewPaneManager` stores and restores layout state. Important concepts include:

- named layouts
- default vs saved layout state
- main window state restoration
- per-pane dock widget state
- multi-instance pane behavior

When a pane appears in the wrong place or disappears after restore, this is one of the first files to inspect.

## Read These Files First

- `Code/Editor/MainWindow.h`
- `Code/Editor/MainWindow.cpp`
- `Code/Editor/QtViewPaneManager.h`
- `Code/Editor/QtViewPaneManager.cpp`
- `Code/Editor/Core/EditorActionsHandler.h`
- `Code/Editor/LyViewPaneNames.h`

## AI Search Hints

Use these names first:

- `MainWindow::Initialize`
- `QtViewPaneManager::RegisterPane`
- `RegisterViewClass`
- `OpenPane`
- `RestoreLayout`
- `EditorActionsHandler`
- `OnViewPaneOpened`

## Common Misreads

- A pane class is often not created where it is registered.
- A pane can exist as a registered concept before any widget instance is open.
- Layout restore bugs are often in pane management code, not in the pane widget itself.

## What To Read Next

If the pane is asset-related, continue with:

- [03-asset-workflows.md](03-asset-workflows.md)
