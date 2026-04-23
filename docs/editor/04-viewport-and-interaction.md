# Viewport And Interaction

## Why This File Matters

The editor viewport is one of the most cross-cutting parts of `Code/Editor`.
It touches:

- camera state
- Qt widget behavior
- editor buses
- asset notifications
- prefab notifications
- undo listeners
- play-in-editor state

If an AI needs to explain viewport behavior, it should start here before searching the whole repo.

## Main Class

### `EditorViewportWidget`

Read first:

- `Code/Editor/EditorViewportWidget.h`
- `Code/Editor/EditorViewportWidget.cpp`

This is the main editor viewport widget. It derives from `QtViewport` and connects to a large number of systems, including:

- viewport border requests
- editor notifications
- undo manager listener
- editor camera request bus
- camera notification bus
- input system cursor constraint requests
- main editor viewport interaction requests
- editor entity viewport interaction requests
- asset catalog events
- Atom scene notifications
- prefab public notifications

That list alone explains why viewport behavior is often spread across several systems.

## What This Widget Owns Or Coordinates

From the header, the important responsibilities include:

- FOV and view transform control
- world-to-view and view-to-world conversion
- hit testing and bounds visibility
- active camera state queries
- context menu population
- viewport sizing and rendering updates
- fullscreen preview handling
- cursor hide and show behavior
- visible entity gathering
- reacting to play-in-editor transitions
- reacting to root prefab load

## Supporting Types

### `EditorViewportSettings`

Source:

- `Code/Editor/EditorViewportWidget.h`
- `Code/Editor/EditorViewportSettings.h`
- `Code/Editor/EditorViewportSettings.cpp`

This settings helper exposes editor viewport settings over the viewport settings request bus, such as:

- grid snapping
- grid size
- angle snapping
- helper visibility
- icon visibility
- default editor camera position and orientation

### `EditorModularViewportCameraComposer`

Source:

- `Code/Editor/EditorModularViewportCameraComposer.h`
- `Code/Editor/EditorModularViewportCameraComposer.cpp`
- `Code/Editor/EditorModularViewportCameraComposerBus.h`

Use this area when the question is about modular camera input composition rather than only widget rendering.

## Core Mental Model

### 1. The viewport is a bus hub

A lot of viewport behavior is not implemented as one local algorithm.
Instead, `EditorViewportWidget` is where multiple editor and framework buses meet.

### 2. Play-in-editor changes viewport behavior

The viewport explicitly has callbacks such as:

- `OnStartPlayInEditorBegin`
- `OnStartPlayInEditor`
- `OnStopPlayInEditor`

So if the viewport behaves differently during PIE, that is expected and visible in the editor code.

### 3. Viewport logic crosses runtime and editor layers

The widget uses:

- `AzFramework` viewport and camera concepts
- `AzToolsFramework` editor interaction buses
- editor-local UI and legacy interfaces

This is not a purely local `Code/Editor` subsystem.

## Read These Files First

- `Code/Editor/EditorViewportWidget.h`
- `Code/Editor/EditorViewportWidget.cpp`
- `Code/Editor/EditorViewportSettings.h`
- `Code/Editor/EditorViewportSettings.cpp`
- `Code/Editor/EditorModularViewportCameraComposer.h`
- `Code/Editor/Viewport.h`

## AI Search Hints

Use these terms first:

- `EditorViewportWidget`
- `BuildMouseInteraction`
- `ViewToWorld`
- `FindVisibleEntities`
- `OnStartPlayInEditor`
- `GetActiveCameraState`
- `EditorViewportSettings`
- `EditorModifierKeyRequestBus`

## Common Misreads

- The viewport widget is not only about drawing.
- Camera behavior may be split across buses and helper classes.
- Some viewport problems originate from editor state transitions, not from render code itself.

## What To Read Next

If the question is more about actions, commands, or undo behavior around viewport interaction, continue with:

- [05-commands-and-undo.md](05-commands-and-undo.md)
