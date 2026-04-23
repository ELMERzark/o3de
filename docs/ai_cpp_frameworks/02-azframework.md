# AzFramework

## Module Role

`AzFramework` is O3DE's runtime framework layer. It takes the low-level infrastructure from `AzCore` and organizes it into a usable runtime application framework. Its main concerns include:

- application startup and main loop behavior
- file IO and archive setup
- command line and path utilities
- runtime entity contexts
- Asset Processor and Asset Catalog integration
- input systems
- scene, visibility, and spawnable runtime systems

If the question has moved past pure infrastructure and into runtime system coordination, `AzFramework` is usually the right place to start.

## Key Entry Points

### 1. `AzFramework::Application`

Source:

- `Code/Framework/AzFramework/AzFramework/Application/Application.h`
- `Code/Framework/AzFramework/AzFramework/Application/Application.cpp`

This is the runtime application shell. It extends `AZ::ComponentApplication` with:

- command line handling
- a platform event loop abstraction through `Implementation`
- file IO and archive setup
- `RunMainLoop()` and `ExitMainLoop()`
- engine and project path logic
- native UI integration
- instance pool manager support

It is the main base class to understand for runtime application startup.

### 2. `AzFrameworkModule`

Source:

- `Code/Framework/AzFramework/AzFramework/AzFrameworkModule.cpp`
- `Code/Framework/AzFramework/AzFramework/AzFrameworkModule.h`

This module registers many runtime-side system components, including:

- `AssetCatalogComponent`
- `AssetSystemComponent`
- `TransformComponent`
- `NonUniformScaleComponent`
- `GameEntityContextComponent`
- `InputSystemComponent`
- `SceneSystemComponent`
- `SpawnableSystemComponent`
- `QualitySystemComponent`
- `DeviceAttributesSystemComponent`
- `OctreeSystemComponent`
- `Physics::MaterialSystemComponent`

## Directory Map

| Directory | Purpose |
| --- | --- |
| `Application/` | runtime application shell, startup, main loop |
| `API/` | application request and event buses |
| `Asset/` | asset catalog, Asset Processor messages, asset status queries |
| `Entity/` | runtime entity contexts and ownership services |
| `Input/` | input devices, mappings, listeners, system component |
| `Scene/` | scene system support |
| `Spawnable/` | spawnable assets, entity containers, root spawnable management |
| `Visibility/` | visibility and octree system support |
| `Physics/` | runtime-side physics framework components |

## Core Subsystems

### 1. Runtime application shell

Read first:

- `Application/Application.h`
- `API/ApplicationAPI.h`

Focus on:

- `Start(...)`
- `Stop()`
- `StartCommon(...)`
- `PumpSystemEventLoop...`
- `RunMainLoop()`

This is the real parent interface for many runtime launcher and game applications.

### 2. Asset system

Read first:

- `Asset/AssetSystemComponent.h`
- `Asset/AssetCatalogComponent.h`
- `Asset/AssetCatalog.h`

`AssetSystemComponent` handles communication with Asset Processor, including:

- establishing and tearing down connections
- waiting for Asset Processor readiness
- synchronous asset compilation requests
- asset status queries
- some tool-oriented asset requests

If the question is "why is runtime waiting for Asset Processor" or "where is asset status queried," start here.

### 3. Entity context

Read first:

- `Entity/EntityContext.h`
- `Entity/GameEntityContextComponent.h`
- `Entity/EntityContextBus.h`

`EntityContext` is responsible for:

- giving a group of entities a single ownership and lifecycle container
- owning a root entity
- creating, adding, activating, and destroying entities
- organizing independent prefab, level, or world contexts

The class comment makes the split explicit: edit-time entities and runtime entities belong to different contexts.

### 4. Spawnable system

Read first:

- `Spawnable/SpawnableSystemComponent.h`
- `Spawnable/SpawnableEntitiesManager.h`
- `Spawnable/SpawnableAssetHandler.h`

`SpawnableSystemComponent` is attached to both `TickBus` and `SystemTickBus`, and manages root spawnable behavior through `RootSpawnableInterface`:

- assign a root spawnable
- release a root spawnable
- process the spawnable queue
- react to root spawnable assigned, ready, and released events

If the problem is about runtime instantiation of entity collections rather than editor prefab authoring, start here.

## Read These Files First

- `Code/Framework/AzFramework/AzFramework/Application/Application.h`
- `Code/Framework/AzFramework/AzFramework/AzFrameworkModule.cpp`
- `Code/Framework/AzFramework/AzFramework/Asset/AssetSystemComponent.h`
- `Code/Framework/AzFramework/AzFramework/Asset/AssetCatalogComponent.h`
- `Code/Framework/AzFramework/AzFramework/Entity/EntityContext.h`
- `Code/Framework/AzFramework/AzFramework/Entity/GameEntityContextComponent.h`
- `Code/Framework/AzFramework/AzFramework/Input/System/InputSystemComponent.h`
- `Code/Framework/AzFramework/AzFramework/Spawnable/SpawnableSystemComponent.h`

## AI Search Hints

Use focused terms first:

- `AzFramework::Application`
- `StartCommon`
- `AssetSystemComponent`
- `AssetCatalogComponent`
- `EntityContext`
- `GameEntityContextComponent`
- `SpawnableSystemComponent`
- `InputSystemComponent`

## Common Misreads

- Prefab template editing and propagation are mainly in `AzToolsFramework`, not in the main `AzFramework` layer.
- `AzFramework` has entity contexts, but editor entity selection, undo, and editor-only ownership logic are elsewhere.
- runtime asset systems and editor asset browsing are different responsibilities.

## Relationship To Other Modules

- `AzCore` provides the underlying application and component infrastructure.
- `AzFramework` organizes that infrastructure into runtime systems.
- `AzGameFramework` wraps `AzFramework::Application` for game and launcher use cases.
- `AzToolsFramework` extends the same runtime foundation into editor behavior.
