# Commands And Undo

## Why This File Matters

`Code/Editor` still has a strong command and undo layer of its own.
This matters for:

- console commands
- menu and toolbar command execution
- Python-accessible editor commands
- legacy editor undo stacks

If an AI needs to answer "where is this editor command registered" or "why does undo behave this way," start here.

## Command Layer

### `CEditorCommandManager`

Read first:

- `Code/Editor/Commands/CommandManager.h`
- `Code/Editor/Commands/CommandManager.cpp`
- `Code/Editor/Include/Command.h`
- `Code/Editor/Include/ICommandManager.h`

This manager handles:

- command registration and unregistration
- UI command registration
- command execution by command line, module and name, or command id
- auto-complete for console use
- scripting availability flags
- UI metadata attachment

One especially important pattern is auto-registration:

- `CAutoRegisterCommandHelper`
- `REGISTER_EDITOR_COMMAND(...)`

If a command seems to appear "by magic," it is often because it is auto-registered through this mechanism.

## Undo Layer

### `CUndoManager`

Read first:

- `Code/Editor/Undo/Undo.h`
- `Code/Editor/Undo/Undo.cpp`
- `Code/Editor/Undo/IUndoObject.h`
- `Code/Editor/Undo/IUndoManagerListener.h`

`CUndoManager` is the legacy editor undo stack. It still provides:

- `Begin`, `Accept`, `Cancel`
- `Undo`, `Redo`
- super-undo batching through `SuperBegin` and `SuperAccept`
- suspend and resume
- listener notifications
- stack inspection and flushing

The header itself includes an important comment:

- this class is considered superseded by `AzToolsFramework::UndoSystem`

That means an AI should expect coexistence between:

- legacy `CUndoManager`
- newer `AzToolsFramework` undo-related systems

## Where These Systems Surface

The command and undo layers connect to many visible parts of the editor:

- `MainWindow`
- `EditorActionsHandler`
- console panes
- TrackView
- viewport interactions
- scripting and Python handlers

`IEditor` and `CEditorImpl` still expose many of the legacy undo entry points directly.

## Core Mental Model

### 1. Command registration is distributed

Command registration may happen through:

- explicit registration
- auto-registration helpers
- UI command binding
- script exposure helpers

Do not assume all commands are registered from one central menu file.

### 2. Undo is partially legacy and partially modernized

Some editor workflows still route through `CUndoManager`.
Other workflows may rely on `AzToolsFramework` undo support.
The codebase is in a hybrid state here.

### 3. Listener interfaces matter

When undo affects UI state, look for listeners such as:

- `IUndoManagerListener`
- editor notifications
- tools application notifications

The visible update often happens outside the object that originally recorded undo.

## Read These Files First

- `Code/Editor/Commands/CommandManager.h`
- `Code/Editor/Commands/CommandManager.cpp`
- `Code/Editor/Include/Command.h`
- `Code/Editor/Undo/Undo.h`
- `Code/Editor/Undo/Undo.cpp`
- `Code/Editor/IEditorImpl.h`

## AI Search Hints

Use these names first:

- `CEditorCommandManager`
- `RegisterAutoCommands`
- `REGISTER_EDITOR_COMMAND`
- `Execute`
- `CUndoManager`
- `SuperBegin`
- `RecordUndo`
- `IUndoManagerListener`

## Common Misreads

- The editor command manager is not only for the console.
- Undo behavior may be split between old and new systems.
- A UI update after undo often happens through listeners, not inside the undo object itself.

## What To Read Next

If the question is more about TrackView or plugins, continue with:

- [06-trackview-and-plugins.md](06-trackview-and-plugins.md)
