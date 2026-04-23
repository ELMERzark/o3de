# Atom RHI DX12

## Role

Path:

- `Gems/Atom/RHI/DX12`

Gem name:

- `Atom_RHI_DX12`

This gem is the DirectX 12 backend for Atom RHI.

## Key Entry Points

- `Code/Source/RHI/Module.cpp`
- `Code/Source/RHI/SystemComponent.h`
- `Code/Source/RHI.Builders/ShaderPlatformInterfaceSystemComponent.h`
- `Code/Include/Atom/RHI.Reflect/DX12/ReflectSystemComponent.h`

## What To Expect

This gem has multiple layers:

- runtime DX12 module and system component
- shader platform interface for builders
- DX12 reflect support
- platform-specific builder stubs for unsupported host platforms

## Read First

- `Gems/Atom/RHI/DX12/gem.json`
- `Gems/Atom/RHI/DX12/Code/Source/RHI/Module.cpp`
- `Gems/Atom/RHI/DX12/Code/Source/RHI/SystemComponent.h`

## AI Search Hints

- `SystemComponent`
- `ShaderPlatformInterfaceSystemComponent`
- `ReflectSystemComponent`
- `DX12`

## Common Misreads

- The presence of builder modules does not mean the gem is builder-only.
- The runtime backend and builder support live side by side.
