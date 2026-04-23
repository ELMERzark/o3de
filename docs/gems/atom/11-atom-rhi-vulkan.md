# Atom RHI Vulkan

## Role

Path:

- `Gems/Atom/RHI/Vulkan`

Gem name:

- `Atom_RHI_Vulkan`

This gem is the Vulkan backend for Atom RHI.

## Key Entry Points

- `Code/Source/RHI/Module.cpp`
- `Code/Source/RHI/SystemComponent.h`
- `Code/Source/RHI/ShaderModule.h`
- `Code/Source/RHI.Builders/ShaderPlatformInterfaceSystemComponent.h`
- `Code/Include/Atom/RHI.Reflect/Vulkan/ReflectSystemComponent.h`

## What To Expect

Compared with the other backend gems, this one makes `ShaderModule` especially visible in the top-level entry candidates.

## Read First

- `Gems/Atom/RHI/Vulkan/gem.json`
- `Gems/Atom/RHI/Vulkan/Code/Source/RHI/Module.cpp`
- `Gems/Atom/RHI/Vulkan/Code/Source/RHI/SystemComponent.h`

## AI Search Hints

- `Vulkan`
- `ShaderModule`
- `SystemComponent`
- `ReflectSystemComponent`

## Common Misreads

- Vulkan builder modules and runtime modules are separate concerns in the same gem tree.
