# AzCore

## Module Role

`AzCore` is O3DE's foundation layer. It provides the shared infrastructure that the rest of the engine builds on, including:

- application bootstrap
- module loading
- entity and component primitives
- reflection and serialization
- asset management foundations
- EBus, tasking, Settings Registry, IO, math, and name utilities

If an AI does not yet understand how an O3DE application starts, how system components get assembled, or where reflection contexts come from, `AzCore` is usually the first place to read.

## Key Entry Points

### 1. `AZ::ComponentApplication`

Source:

- `Code/Framework/AzCore/AzCore/Component/ComponentApplication.h`
- `Code/Framework/AzCore/AzCore/Component/ComponentApplication.cpp`

This is the base for O3DE's component-based applications. It is responsible for:

- creating and destroying application-wide infrastructure
- starting allocators and reflection environments
- managing the system entity and ordinary entities
- loading static and dynamic modules
- owning `SerializeContext`, `BehaviorContext`, and `JsonRegistrationContext`
- bootstrapping the `SettingsRegistry`

Start with these types and methods:

- `ComponentApplication::Descriptor`
- `ComponentApplication::StartupParameters`
- `Create(...)`
- `Destroy()`

### 2. `AZ::Module` and `ModuleManager`

Source:

- `Code/Framework/AzCore/AzCore/Module/Module.h`
- `Code/Framework/AzCore/AzCore/Module/Module.cpp`
- `Code/Framework/AzCore/AzCore/Module/ModuleManager.h`
- `Code/Framework/AzCore/AzCore/Module/ModuleManager.cpp`

This is where O3DE defines how modules:

- expose component descriptors
- declare required system components
- get loaded during application startup

Many "why is this system component active" questions are answered by following the module registration path back to here.

### 3. `AzCoreModule`

Source:

- `Code/Framework/AzCore/AzCore/AzCoreModule.cpp`
- `Code/Framework/AzCore/AzCore/AzCoreModule.h`

`AzCoreModule` registers the default foundation components and required system components. The most important ones to remember are:

- `LoggerSystemComponent`
- `EventSchedulerSystemComponent`
- `TaskGraphSystemComponent`
- `EntityActiveSystemComponent`
- `AssetManagerComponent`
- `StreamerComponent`
- `JobManagerComponent`
- `JsonSystemComponent`
- `SliceSystemComponent`
- `UserSettingsComponent`
- `ScriptSystemComponent` when Lua support is enabled

## Directory Map

| Directory | Purpose |
| --- | --- |
| `Component/` | `Entity`, `Component`, `ComponentApplication`, tick-related core types |
| `Module/` | module base classes, dynamic module handles, module manager, environment |
| `Asset/` | `AssetManager`, asset serializers, asset buses, asset data foundations |
| `Serialization/` | `SerializeContext`, `EditContext`, `ObjectStream`, data patches, JSON support |
| `RTTI/` | type information, reflection helpers, behavior context support |
| `EBus/` | O3DE event bus infrastructure |
| `Settings/` | command line, config parsing, settings support |
| `Jobs/`, `Task/`, `Threading/` | concurrency and task execution infrastructure |
| `IO/` | file system, paths, streamer support |
| `Math/` | vectors, matrices, quaternions, geometry helpers |
| `Name/` | `AZ::Name` and the name dictionary |

## Core Mental Model

### 1. System components are not usually hard-coded in the app layer

The common chain is:

1. a module adds component descriptors to `m_descriptors`
2. the module returns required system component type ids from `GetRequiredSystemComponents()`
3. `ComponentApplication` constructs the system entity from that information

So when analyzing why a component exists, do not search only for direct `CreateComponent` calls in app code.

### 2. Reflection is core infrastructure, not just an editor feature

`AzCore` owns the base layers for:

- `SerializeContext` for persistence
- `EditContext` for editor metadata
- `BehaviorContext` for scripting exposure
- JSON registration support

Many component and data type questions eventually lead back to `Reflect(...)`.

### 3. `AssetManager` lives here, but higher-level asset workflows do not stop here

`AzCore/Asset` manages the core asset object model and lifecycle.

But if the question is about:

- asset catalogs
- Asset Processor communication
- runtime asset discovery

then continue into `AzFramework/Asset`.

## Read These Files First

- `Code/Framework/AzCore/AzCore/Component/ComponentApplication.h`
- `Code/Framework/AzCore/AzCore/Module/Module.h`
- `Code/Framework/AzCore/AzCore/Module/ModuleManager.h`
- `Code/Framework/AzCore/AzCore/AzCoreModule.cpp`
- `Code/Framework/AzCore/AzCore/Serialization/SerializeContext.h`
- `Code/Framework/AzCore/AzCore/RTTI/BehaviorContext.h`
- `Code/Framework/AzCore/AzCore/Asset/AssetManager.h`
- `Code/Framework/AzCore/AzCore/Settings/CommandLine.h`

## AI Search Hints

Use precise terms first:

- `ComponentApplication`
- `GetRequiredSystemComponents`
- `CreateDescriptor`
- `Reflect`
- `SerializeContext`
- `BehaviorContext`
- `AssetManager`
- `SettingsRegistry`

## Common Misreads

- `AzCore` is not the editor framework.
- `AzCore` is not a gameplay module.
- Many classes here only provide mechanisms. Product behavior often appears later in `AzFramework`, `AzToolsFramework`, or gems.

## Relationship To Other Modules

- `AzFramework` builds runtime systems on top of `AzCore`.
- `AzToolsFramework` builds editor systems on top of `AzFramework`.
- `AzGameFramework` is a thinner game-bootstrap layer on top of the runtime application layer.
