# Scripting, Graph, And Pipeline Gems

## Why This Family Matters

This family contains the graph-based and scripting-centric tooling layer of O3DE, plus several build and automation gems that support authoring workflows.

It is the first place to look for:

- Script Canvas
- graph frameworks
- editor scripting helpers
- builder and pipeline-oriented gems

## Highest-Value Entry Points

Read these first:

- `Gems/ScriptCanvas/gem.json`
- `Gems/ScriptCanvas/Code/Source/ScriptCanvasGem.cpp`
- `Gems/ScriptEvents/gem.json`
- `Gems/GraphCanvas/gem.json`
- `Gems/GraphModel/gem.json`
- `Gems/SceneProcessing/gem.json`

## Family Anatomy

### Script Canvas family

The Script Canvas area is split into several manifests:

- `ScriptCanvas`
- `ScriptCanvasDeveloper`
- `ScriptCanvasPhysics`
- `ScriptCanvasTesting`

The top-level Script Canvas gem is a tool gem and depends on:

- `ScriptEvents`
- `ExpressionEvaluation`
- `GraphCanvas`

This means visual scripting analysis should usually read the graph and event gems together.

### Graph support

`GraphCanvas` and `GraphModel` are shared graph infrastructure gems.

If the question is about node editor behavior rather than Script Canvas semantics, start with these instead of Script Canvas proper.

### Pipeline and automation support

Gems such as `SceneProcessing`, `PythonAssetBuilder`, and `TestAssetBuilder` are not gameplay runtime gems.
They are pipeline and toolchain gems.

## Full Family Inventory

- `ScriptCanvas`
- `ScriptCanvasDeveloper`
- `ScriptCanvasPhysics`
- `ScriptCanvasTesting`
- `ScriptAutomation`
- `ScriptEvents`
- `GraphCanvas`
- `GraphModel`
- `ExpressionEvaluation`
- `EditorPythonBindings`
- `QtForPython`
- `PythonAssetBuilder`
- `TestAssetBuilder`
- `SceneProcessing`
- `TickBusOrderViewer`

## AI Search Hints

Use these names first:

- `ScriptCanvasModule`
- `SystemComponent`
- `GraphVariableManagerComponent`
- `ScriptEvents`
- `GraphCanvas`
- `GraphModel`
- `BuilderModule`
- `AssetBuilder`

## Common Misreads

- Script Canvas is not only runtime scripting logic; much of it is editor tooling
- graph framework gems are broader than one scripting product
- builder gems and pipeline gems often have very different entry points than gameplay code gems
