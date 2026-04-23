# Asset Workflows

## Why This File Matters

`Code/Editor` contains several user-facing asset workflows that sit on top of lower-level framework systems:

- Asset Browser pane
- Asset Editor pane
- Asset Importer flow
- asset database location hookup

These are related, but they are not the same subsystem.

## Main Areas

### 1. Asset Browser pane

Read first:

- `Code/Editor/AzAssetBrowser/AzAssetBrowserWindow.h`
- `Code/Editor/AzAssetBrowser/AzAssetBrowserWindow.cpp`
- `Code/Editor/AzAssetBrowser/AzAssetBrowserRequestHandler.h`
- `Code/Editor/AzAssetBrowser/AzAssetBrowserRequestHandler.cpp`

`AzAssetBrowserWindow` is the editor-facing pane widget. It:

- obtains the framework `AssetBrowserModel`
- builds filter and list models on top of it
- manages tree, list, thumbnail, and table view modes
- handles selection and double-click behavior
- supports favorites and search widget integration
- can open the pane and select a requested asset

`AzAssetBrowserRequestHandler` is a key integration class. It handles:

- Asset Browser context menu augmentation
- source opener and creator integration
- opening assets in the associated editor
- drag-and-drop behavior
- folder and asset selection routing

Use the request handler when the question is about cross-pane integration, openers, or drag-and-drop behavior.

### 2. Asset Editor pane

Read first:

- `Code/Editor/AssetEditor/AssetEditorWindow.h`
- `Code/Editor/AssetEditor/AssetEditorWindow.cpp`
- `Code/Editor/AssetEditor/AssetEditorRequestsHandler.h`
- `Code/Editor/AssetEditor/AssetEditorRequestsHandler.cpp`

`AssetEditorWindow` is a pane wrapper around the asset editor widget. It exposes:

- create asset
- open asset
- open asset by id
- save asset as

It also has `RegisterViewClass()` helpers, which makes it fit the normal pane registration flow.

If an asset is opened "in the editor" from another place, follow the request handler and the Asset Browser open path into here.

### 3. Asset Importer

Read first:

- `Code/Editor/AssetImporter/AssetImporterManager/AssetImporterManager.h`
- `Code/Editor/AssetImporter/AssetImporterManager/AssetImporterManager.cpp`
- `Code/Editor/AssetImporter/AssetImporterManager/AssetImporterDragAndDropHandler.h`
- `Code/Editor/AssetImporter/AssetImporterManager/AssetImporterDragAndDropHandler.cpp`

`AssetImporterManager` drives the import flow for:

- browsing for external files
- drag-and-drop import
- choosing destination directories
- copy vs move behavior
- overwrite, keep-both, skip, and apply-to-all decisions

It explicitly guards against importing files already inside the project and blocks crate file import.

This is the user-facing "bring files into the project" flow, not the same thing as Asset Browser.

### 4. Asset database hookup

Read first:

- `Code/Editor/AssetDatabase/AssetDatabaseLocationListener.h`
- `Code/Editor/AssetDatabase/AssetDatabaseLocationListener.cpp`

This listener provides the editor side of asset database location lookup and connection access.

It is lightweight, but useful when tracing how editor-side tools find the asset database.

## Core Mental Model

### 1. Asset Browser is a pane, not the whole asset system

The pane is built on top of the framework asset browser model and request buses.
If the issue is in data population, the root cause may be outside `Code/Editor`.

### 2. Asset Importer is about bringing files in

Asset Importer is primarily concerned with:

- selecting source files
- validating them
- choosing destination paths
- copying or moving them into the project

It is a different concern than browsing already-known assets.

### 3. Asset Editor is the pane wrapper, not the whole asset editing backend

The editor pane is where the workflow surfaces in `Code/Editor`, but the real editing logic may continue into `AzToolsFramework` or asset-type-specific systems.

## Read These Files First

- `Code/Editor/AzAssetBrowser/AzAssetBrowserWindow.h`
- `Code/Editor/AzAssetBrowser/AzAssetBrowserRequestHandler.h`
- `Code/Editor/AssetEditor/AssetEditorWindow.h`
- `Code/Editor/AssetEditor/AssetEditorRequestsHandler.h`
- `Code/Editor/AssetImporter/AssetImporterManager/AssetImporterManager.h`
- `Code/Editor/AssetDatabase/AssetDatabaseLocationListener.h`

## AI Search Hints

Use these names first:

- `AzAssetBrowserWindow`
- `AzAssetBrowserRequestHandler`
- `OpenAssetInAssociatedEditor`
- `AssetEditorWindow`
- `AssetImporterManager`
- `RegisterViewClass`
- `AssetDatabaseLocationListener`

## Common Misreads

- Asset Browser and Asset Importer are not the same workflow.
- Asset Browser open behavior often goes through request buses and handlers, not direct widget calls.
- Asset Editor pane code is only part of the full asset editing path.

## What To Read Next

If the question is really about the editor viewport instead of assets, continue with:

- [04-viewport-and-interaction.md](04-viewport-and-interaction.md)
