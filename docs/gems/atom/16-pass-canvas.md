# Pass Canvas

## Role

Path:

- `Gems/Atom/Tools/PassCanvas`

Gem name:

- `PassCanvas`

This tool gem provides a graph-oriented pass authoring and inspection application.

## Key Entry Points

- `Code/Source/main.cpp`
- `Code/Source/PassCanvasApplication.h`
- `Code/Source/PassCanvasApplication.cpp`

## What To Expect

The application class derives from `AtomToolsFramework::AtomToolsDocumentApplication` and initializes:

- dynamic node management
- graph context
- pass graph document types
- preview viewport settings
- the main window

## Read First

- `Gems/Atom/Tools/PassCanvas/gem.json`
- `Gems/Atom/Tools/PassCanvas/Code/Source/PassCanvasApplication.h`

## AI Search Hints

- `PassCanvasApplication`
- `InitPassGraphDocumentType`
- `DynamicNodeManager`
- `GraphContext`

## Common Misreads

- Like Material Canvas, this is a standalone tool app, not a runtime pass execution gem.
