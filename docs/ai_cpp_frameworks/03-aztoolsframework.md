# AzToolsFramework

## Module Role

`AzToolsFramework` is O3DE's editor framework layer. It sits on top of `AzFramework` and adds editor semantics such as:

- editor application behavior
- editor entity management
- selection, highlighting, and dirty tracking
- undo and redo
- prefab editing
- Asset Browser
- viewport interaction, component modes, and property editing
- source control and other tool-oriented systems

If the question includes `Editor`, `Prefab`, `Asset Browser`, `Undo`, or `Selection`, `AzToolsFramework` is usually the right first stop.

## Key Entry Points

### 1. `AzToolsFramework::ToolsApplication`

Source:

- `Code/Framework/AzToolsFramework/AzToolsFramework/Application/ToolsApplication.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/Application/ToolsApplication.cpp`

It extends `AzFramework::Application` with a large amount of editor behavior:

- selected and highlighted entity tracking
- dirty entity tracking
- undo and redo stacks with batching
- editor entity creation, deletion, and lookup
- isolation mode
- prefab propagation coordination hooks

The header alone shows that this is a major editor behavior hub, not just a startup shell.

### 2. `AzToolsFrameworkModule`

Source:

- `Code/Framework/AzToolsFramework/AzToolsFramework/AzToolsFrameworkModule.cpp`

This module registers many editor-side component descriptors. The most important categories in the current file are:

- editor entity components
- `PrefabSystemComponent`
- `AssetBrowserComponent`
- `ActionManagerSystemComponent`
- `EditorInteractionSystemComponent`
- `PerforceComponent`
- `ThumbnailerComponent`
- `ViewBookmarkSystemComponent`

This is a fast way to confirm whether an editor feature belongs to core AzToolsFramework.

## Directory Map

| Directory | Purpose |
| --- | --- |
| `Application/` | `ToolsApplication` and editor entity manager |
| `Prefab/` | prefab templates, instances, links, overrides, propagation, undo, spawnable conversion |
| `AssetBrowser/` | asset database caching, entry tree, models, filters, views, thumbnails |
| `ToolsComponents/` | editor component base classes, selection, lock, visibility, editor variants |
| `ViewportSelection/` | viewport picking and editor interaction systems |
| `ActionManager/` | editor action system |
| `SourceControl/` | source control integration |
| `UI/` | property editor, prefab UI, and other editor widgets |

## Core Subsystems

### 1. Editor app and entity operations

Read first:

- `Application/ToolsApplication.h`
- `Application/EditorEntityManager.h`
- `API/ToolsApplicationAPI.h`

This area answers questions like:

- where editor entity selection and deselection is coordinated
- how dirty entities are tracked
- where undo batches begin and end
- how editor entities are created and deleted

### 2. Prefab editing system

Read first:

- `Prefab/PrefabSystemComponent.h`
- `Prefab/PrefabLoader.h`
- `Prefab/Instance/Instance.h`
- `Prefab/Link/Link.h`
- `Prefab/PrefabPublicInterface.h`

`PrefabSystemComponent` is the central editor-side prefab system node. Its header already shows concentrated responsibilities:

- manage templates and links
- instantiate prefabs by file path or template id
- create prefabs
- mark templates dirty
- save dirty templates
- update template DOM data
- propagate template changes to instances

If the question is "how prefab saving, propagation, overrides, or template updates work in the editor," this is the most reliable starting point.

### 3. Asset Browser

Read first:

- `AssetBrowser/AssetBrowserComponent.h`
- `AssetBrowser/AssetBrowserModel.h`
- `AssetBrowser/AssetBrowserFilterModel.h`
- `AssetBrowser/Entries/AssetBrowserEntry.h`

The `AssetBrowserComponent` comment already summarizes its purpose:

- cache asset database entries
- watch database changes
- push changes into Asset Browser views

Its data model is a tree of entries. The core entry types are:

- `RootAssetBrowserEntry`
- `FolderAssetBrowserEntry`
- `SourceAssetBrowserEntry`
- `ProductAssetBrowserEntry`

When analyzing Asset Browser behavior, start with the data model and entry tree before diving into UI widgets.

## Read These Files First

- `Code/Framework/AzToolsFramework/AzToolsFramework/Application/ToolsApplication.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/AzToolsFrameworkModule.cpp`
- `Code/Framework/AzToolsFramework/AzToolsFramework/Prefab/PrefabSystemComponent.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/Prefab/PrefabLoader.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/AssetBrowser/AssetBrowserComponent.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/AssetBrowser/AssetBrowserModel.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/AssetBrowser/Entries/AssetBrowserEntry.h`
- `Code/Framework/AzToolsFramework/AzToolsFramework/ToolsComponents/EditorComponentBase.h`

## AI Search Hints

Use precise names first:

- `ToolsApplication`
- `PrefabSystemComponent`
- `PrefabLoader`
- `AssetBrowserComponent`
- `AssetBrowserModel`
- `EditorEntityManager`
- `UndoStack`
- `EditorInteractionSystemComponent`

## Common Misreads

- Runtime spawnable instantiation is not the same thing as editor prefab authoring. Runtime behavior is more in `AzFramework/Spawnable`, while editor template propagation is in `AzToolsFramework/Prefab`.
- Asset Browser is not the runtime asset system. It is an editor asset browsing and asset database caching system.
- Many editor features are split across buses, handlers, and components. Do not look only for a main window implementation.

## Relationship To Other Modules

- `AzToolsFramework` inherits the runtime application shell and base systems from `AzFramework`.
- It layers editor semantics on top of runtime entities and asset systems.
- Many real editor workflows require reading both `AzToolsFramework` and `AzFramework` together.
