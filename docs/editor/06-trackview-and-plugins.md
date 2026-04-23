# TrackView And Plugins

## Why This File Matters

Two editor areas still strongly reflect the hybrid nature of `Code/Editor`:

- TrackView
- plugin loading and plugin event routing

Both are highly relevant when an AI is tracing older editor behaviors that still remain important.

## TrackView

### `CTrackViewDialog`

Read first:

- `Code/Editor/TrackView/TrackViewDialog.h`
- `Code/Editor/TrackView/TrackViewDialog.cpp`

`CTrackViewDialog` is a major editor pane with many responsibilities:

- sequence selection and reload
- dope sheet and curve editor coordination
- key editing commands
- playback and recording controls
- snap mode behavior
- track color customization
- batch render entry points
- entity selection reaction
- undo manager listener behavior
- editor notification reaction

Its inheritance list is a strong signal that TrackView is deeply integrated with editor state:

- animation context listener
- editor notify listener
- sequence listeners
- entity system bus
- tools application notification bus
- undo manager listener

If a question is about cinematic sequence editing or TrackView UI state, this is the first file to inspect.

## Plugin Layer

### `CPluginManager`

Read first:

- `Code/Editor/PluginManager.h`
- `Code/Editor/PluginManager.cpp`

The plugin manager handles:

- loading plugin DLLs from the editor plugin folder
- releasing plugins
- unloading plugin DLLs
- routing editor notify events to plugins
- mapping UI ids and handlers back to plugin instances

This is important because the editor still supports significant plugin-driven behavior.

### Plugin load path from the editor core

Read first:

- `Code/Editor/IEditorImpl.cpp`

`CEditorImpl::LoadPlugins()` computes the editor plugin path and delegates loading to `CPluginManager`.

This is the best path to follow when answering:

- where editor plugins are discovered
- when plugin DLLs are loaded
- how shutdown unload is sequenced

## Useful Related Files

### `IEditor.h`

Read first:

- `Code/Editor/IEditor.h`

This file remains useful because it exposes a large number of legacy editor-wide concepts:

- notify events
- plugin access
- command manager access
- undo access
- view access
- status text and console access
- game mode and simulation mode state

Even when the implementation lives elsewhere, this file is often the fastest way to discover the public editor service surface.

### `Controls/ConsoleSCB`

Read first:

- `Code/Editor/Controls/ConsoleSCB.h`
- `Code/Editor/Controls/ConsoleSCB.cpp`

This is useful when the problem is about:

- editor console widget behavior
- console history
- console output buffering
- console variable editor pane registration

## Core Mental Model

### 1. TrackView is still a deep editor subsystem

It is not a tiny isolated tool. It connects to:

- animation context
- entity state
- undo
- editor notifications
- pane registration

### 2. Plugins still matter in editor behavior

Even in a more modernized editor stack, plugins remain part of the runtime behavior of the editor product.

### 3. `IEditor` is still a discovery map

Even when the implementation is scattered, `IEditor.h` is still one of the best top-down discovery files in `Code/Editor`.

## Read These Files First

- `Code/Editor/TrackView/TrackViewDialog.h`
- `Code/Editor/PluginManager.h`
- `Code/Editor/IEditor.h`
- `Code/Editor/IEditorImpl.cpp`
- `Code/Editor/Controls/ConsoleSCB.h`

## AI Search Hints

Use these terms first:

- `CTrackViewDialog`
- `RegisterViewClass`
- `OnSequenceChanged`
- `CPluginManager`
- `LoadPlugins`
- `NotifyPlugins`
- `IEditorNotifyListener`
- `ConsoleSCB`

## Common Misreads

- TrackView is not just a simple dock widget. It is tied to many editor systems.
- Plugin behavior is not always visible from one call site. UI ids and event maps are part of the routing.
- `IEditor.h` may look old, but it is still a high-value navigation file.
