# Atom Bootstrap

## Role

Path:

- `Gems/Atom/Bootstrap`

Gem name:

- `Atom_Bootstrap`

This gem provides bootstrap support for Atom startup and early renderer integration.

## Key Entry Points

- `Code/Source/BootstrapModule.cpp`
- `Code/Source/BootstrapSystemComponent.h`
- `Code/Source/Platform/*/BootstrapSystemComponent_Traits_Platform.h`

## What To Expect

The module registers a single required system component:

- `BootstrapSystemComponent`

This keeps the gem focused on early startup and platform-tailored bootstrapping behavior.

## Read First

- `Gems/Atom/Bootstrap/gem.json`
- `Gems/Atom/Bootstrap/Code/Source/BootstrapModule.cpp`
- `Gems/Atom/Bootstrap/Code/Source/BootstrapSystemComponent.h`

## AI Search Hints

- `BootstrapSystemComponent`
- `BootstrapModule`
- `Traits_Platform`

## Common Misreads

- This is not the full rendering pipeline.
- Its role is early setup and bootstrap, not feature implementation.
