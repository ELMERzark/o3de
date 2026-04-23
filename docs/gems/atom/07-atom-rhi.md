# Atom RHI

## Role

Path:

- `Gems/Atom/RHI`

Gem name:

- `Atom_RHI`

This is the low-level rendering hardware interface layer for Atom.

## What It Actually Represents

The manifest depends on backend-specific child gems:

- `Atom_RHI_DX12`
- `Atom_RHI_Metal`
- `Atom_RHI_Vulkan`
- `Atom_RHI_Null`

So this gem is both:

- the common RHI layer
- the hub for platform backend selection

## Key Entry Points

- `Code/Source/Module.cpp`
- `Code/Include/Atom/RHI.Reflect/ReflectSystemComponent.h`
- profiler system components under `Code/Source/RHI.Profiler/*`

## Read First

- `Gems/Atom/RHI/gem.json`
- `Gems/Atom/RHI/Code/Source/Module.cpp`
- `Gems/Atom/RHI/Code/Include/Atom/RHI.Reflect/ReflectSystemComponent.h`

## AI Search Hints

- `PlatformModule`
- `ReflectSystemComponent`
- `FactoryManagerSystemComponent`
- `GraphicsProfilerSystemComponent`

## Common Misreads

- Backend implementation details are mostly in the platform child gems, not only here.
- This is lower-level than `Atom_RPI`.
