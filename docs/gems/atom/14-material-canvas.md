# Material Canvas

## Role

Path:

- `Gems/Atom/Tools/MaterialCanvas`

Gem name:

- `MaterialCanvas`

This tool gem provides a graph-based editor for material-related authoring workflows.

## Key Entry Points

- `Code/Source/main.cpp`
- `Code/Source/MaterialCanvasApplication.h`
- `Code/Source/MaterialCanvasApplication.cpp`

## What To Expect

The application class derives from `AtomToolsFramework::AtomToolsDocumentApplication` and initializes:

- dynamic node management
- graph context and graph view settings
- document types for material graph and shader source data
- preview viewport settings
- the main window

## Read First

- `Gems/Atom/Tools/MaterialCanvas/gem.json`
- `Gems/Atom/Tools/MaterialCanvas/Code/Source/MaterialCanvasApplication.h`

## AI Search Hints

- `MaterialCanvasApplication`
- `DynamicNodeManager`
- `GraphContext`
- `InitMaterialGraphDocumentType`
- `AtomToolsDocumentApplication`

## Common Misreads

- This is a standalone tool application, not a runtime rendering gem.
- It depends on AtomToolsFramework heavily and should be read together with it.
