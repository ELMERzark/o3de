# Atom Debug Camera Component

## Role

Path:

- `Gems/Atom/Component/DebugCamera`

Gem name:

- `Atom_Component_DebugCamera`

This gem provides debug camera-related components for Atom scenes.

## Key Entry Points

- `Code/Source/Module.cpp`
- `Code/Include/Atom/Component/DebugCamera/*`

## What To Expect

The module registers component descriptors such as:

- `CameraControllerComponent`
- `ArcBallControllerComponent`
- `CameraComponent`
- `NoClipControllerComponent`

This gem is component-centric and does not require a system component.

## Read First

- `Gems/Atom/Component/DebugCamera/gem.json`
- `Gems/Atom/Component/DebugCamera/Code/Source/Module.cpp`

## AI Search Hints

- `CameraModule`
- `ArcBallControllerComponent`
- `NoClipControllerComponent`
- `CameraComponent`

## Common Misreads

- This gem is not the main renderer.
- It is a set of debug and control components layered onto Atom.
