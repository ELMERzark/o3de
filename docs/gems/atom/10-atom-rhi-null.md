# Atom RHI Null

## Role

Path:

- `Gems/Atom/RHI/Null`

Gem name:

- `Atom_RHI_Null`

This gem is the null renderer backend for Atom RHI.

## Key Entry Points

- `Code/Source/RHI/Module.cpp`
- `Code/Source/RHI/SystemComponent.h`
- `Code/Source/RHI.Builders/ShaderPlatformInterfaceSystemComponent.h`
- `Code/Include/Atom/RHI.Reflect/Null/ReflectSystemComponent.h`

## What To Expect

This backend is useful when analyzing:

- headless or minimal rendering paths
- configuration or fallback backend behavior
- tooling scenarios that do not need a real graphics backend

## Read First

- `Gems/Atom/RHI/Null/gem.json`
- `Gems/Atom/RHI/Null/Code/Source/RHI/Module.cpp`
- `Gems/Atom/RHI/Null/Code/Source/RHI/SystemComponent.h`

## AI Search Hints

- `Null`
- `SystemComponent`
- `ReflectSystemComponent`
- `ShaderPlatformInterfaceSystemComponent`

## Common Misreads

- This is a real backend implementation path, not just a test stub.
