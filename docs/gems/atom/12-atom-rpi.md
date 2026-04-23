# Atom RPI

## Role

Path:

- `Gems/Atom/RPI`

Gem name:

- `Atom_RPI`

This gem is the rendering pipeline layer built on top of Atom RHI.

## Key Entry Points

- `Code/Source/RPI.Private/Module.cpp`
- `Code/Source/RPI.Private/RPISystemComponent.h`
- `Code/Include/Atom/RPI.Public/Image/ImageTagSystemComponent.h`
- `Code/Include/Atom/RPI.Public/Model/ModelTagSystemComponent.h`

## What To Expect

The main module registers and requires:

- `RPISystemComponent`
- `ImageTagSystemComponent`
- `ModelTagSystemComponent`
- `PassTemplatesAutoLoader`

That makes this gem the main pipeline-level runtime layer and a common place where pass and asset-tag behavior becomes visible.

## Read First

- `Gems/Atom/RPI/gem.json`
- `Gems/Atom/RPI/Code/Source/RPI.Private/Module.cpp`
- `Gems/Atom/RPI/Code/Source/RPI.Private/RPISystemComponent.h`

## AI Search Hints

- `RPISystemComponent`
- `PassTemplatesAutoLoader`
- `ImageTagSystemComponent`
- `ModelTagSystemComponent`
- `RPISystem`

## Common Misreads

- This is not the same layer as backend-specific RHI work.
- Many recognizable renderer features still live above this layer in `Atom_Feature_Common`.
