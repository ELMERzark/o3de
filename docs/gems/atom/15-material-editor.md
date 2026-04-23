# Material Editor

## Role

Path:

- `Gems/Atom/Tools/MaterialEditor`

Gem name:

- `MaterialEditor`

This tool gem provides the desktop Material Editor application.

## Key Entry Points

- `Code/Source/main.cpp`
- `Code/Source/MaterialEditorApplication.h`
- `Code/Source/MaterialEditorApplication.cpp`

## What To Expect

The application class derives from `AtomToolsFramework::AtomToolsDocumentApplication` and owns:

- `MaterialEditorMainWindow`
- entity preview viewport settings support

It also overrides startup, reflection, destroy, and critical asset filter setup.

## Read First

- `Gems/Atom/Tools/MaterialEditor/gem.json`
- `Gems/Atom/Tools/MaterialEditor/Code/Source/MaterialEditorApplication.h`

## AI Search Hints

- `MaterialEditorApplication`
- `MaterialEditorMainWindow`
- `GetCriticalAssetFilters`
- `StartCommon`

## Common Misreads

- This gem is an end-user Atom desktop tool, not a shared runtime renderer layer.
