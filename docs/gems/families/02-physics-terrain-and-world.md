# Physics, Terrain, And World Gems

## Why This Family Matters

This family covers world simulation and world composition systems, including:

- physics
- cloth
- terrain
- surface data and vegetation
- procedural world signals
- navigation

These gems are often read together because gameplay-facing world behavior crosses all of them.

## Highest-Value Entry Points

Read these first:

- `Gems/PhysX/Core/PhysX5/gem.json`
- `Gems/PhysX/Core/PhysX5/Source/Module.cpp`
- `Gems/Terrain/Code/Source/TerrainModule.cpp`
- `Gems/Terrain/Code/Source/Components/TerrainSystemComponent.h`
- `Gems/Terrain/Code/Source/Components/TerrainSurfaceDataSystemComponent.h`
- `Gems/Vegetation/gem.json`
- `Gems/SurfaceData/gem.json`

## Family Anatomy

### PhysX

The PhysX family is split across multiple manifests:

- `PhysXCommon`
- `PhysX` for PhysX4
- `PhysX5`
- debug tool variants for each major version

The `PhysX5` gem explicitly provides the `Physics` service and is the main modern runtime target in this repo snapshot.

### Terrain

The Terrain gem has both runtime and editor-side module structure.

Useful entry files:

- `Code/Source/TerrainModule.cpp`
- `Code/Source/EditorTerrainModule.cpp`
- `Code/Source/Components/TerrainSystemComponent.h`
- `Code/Source/EditorComponents/EditorTerrainSystemComponent.h`

This gem is a good example of a family where the runtime and editor layers live side by side.

### SurfaceData And Vegetation

These gems frequently work together with terrain and gradients.

When the question is about how terrain-related surface tags or placement logic works, do not read Terrain alone.

## Full Family Inventory

- `PhysX/Common`
- `PhysX/Core/PhysX4`
- `PhysX/Core/PhysX5`
- `PhysX/Debug/PhysX4`
- `PhysX/Debug/PhysX5`
- `NvCloth`
- `Terrain`
- `SurfaceData`
- `Vegetation`
- `GradientSignal`
- `RecastNavigation`
- `WhiteBox`
- `FastNoise`
- `LandscapeCanvas`
- `DebugDraw`

## AI Search Hints

Use these names first:

- `PhysX5`
- `TerrainModule`
- `TerrainSystemComponent`
- `TerrainSurfaceDataSystemComponent`
- `EditorTerrainSystemComponent`
- `Vegetation`
- `SurfaceData`
- `RecastNavigation`

## Common Misreads

- not all world behavior is inside Terrain
- PhysX version gems are separate manifests and should not be conflated
- editor terrain behavior has its own module path in addition to runtime terrain systems
