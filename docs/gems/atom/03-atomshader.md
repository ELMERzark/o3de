# Atom Shader Builder

## Role

Path:

- `Gems/Atom/Asset/Shader`

Gem name:

- `AtomShader`

This gem is the shader-builder side of Atom. It is primarily about shader asset processing rather than runtime shading behavior.

## Key Entry Points

- `Code/Source/Editor/AzslShaderBuilderModule.cpp`
- `Code/Source/Editor/AzslShaderBuilderSystemComponent.h`

## What To Expect

The module registers `AzslShaderBuilderSystemComponent` as the required system component.

This is a strong sign that this gem is focused on shader build pipeline support rather than final renderer feature execution.

## Read First

- `Gems/Atom/Asset/Shader/gem.json`
- `Gems/Atom/Asset/Shader/Code/Source/Editor/AzslShaderBuilderModule.cpp`
- `Gems/Atom/Asset/Shader/Code/Source/Editor/AzslShaderBuilderSystemComponent.h`

## AI Search Hints

- `AzslShaderBuilderModule`
- `AzslShaderBuilderSystemComponent`
- `Builders`
- `Shader`

## Common Misreads

- This gem is not the same thing as runtime shader dispatch in RPI or RHI.
- It is mainly part of the shader asset pipeline.
