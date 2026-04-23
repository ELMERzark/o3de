# O3DE Framework C++ AI Guide

This document set is for AIs that need to understand O3DE engine C++ code quickly.

The goal is not to replace API docs. The goal is to provide a stable source map:

- tell an AI which directory to read first for a given question
- explain each module's startup entry points, key classes, system components, and common flows
- reduce blind full-repo searching in a very large codebase

## Current Scope

This first batch only covers the most important modules under `Code/Framework`:

- `AzCore`
- `AzFramework`
- `AzToolsFramework`
- `AzGameFramework`
- `AtomCore`
- `AzNetworking`

This batch intentionally does not cover:

- `build/`
- `Code/Editor`
- `Gems/*`
- `Code/Tools/*`

Those areas are larger and more context-heavy, and are better documented after the framework layer is mapped.

## Recommended Reading Order

If an AI needs to understand how the engine framework is built up, read in this order:

1. [01-azcore.md](01-azcore.md)
2. [02-azframework.md](02-azframework.md)
3. [04-azgameframework.md](04-azgameframework.md)
4. [03-aztoolsframework.md](03-aztoolsframework.md)
5. [06-aznetworking.md](06-aznetworking.md)
6. [05-atomcore.md](05-atomcore.md)

## Fast Routing Table

| If the question is about | Read first |
| --- | --- |
| component system, entities, module loading, reflection, serialization, Settings Registry | [01-azcore.md](01-azcore.md) |
| runtime app startup, Asset Processor, input, scenes, runtime entity contexts, spawnables | [02-azframework.md](02-azframework.md) |
| editor app behavior, prefab editing, undo/redo, Asset Browser, editor entities, viewport interaction | [03-aztoolsframework.md](03-aztoolsframework.md) |
| game or launcher startup, pak mounting, headless or console mode | [04-azgameframework.md](04-azgameframework.md) |
| Atom instance reuse, lightweight containers, shared Atom utility types | [05-atomcore.md](05-atomcore.md) |
| network interfaces, connection layer, packet layer, network serializers, TCP or UDP transport | [06-aznetworking.md](06-aznetworking.md) |

## How To Use These Docs

1. Start with the module role section to confirm the problem belongs to that module.
2. Then read the key entry points section to find the primary classes and registration code.
3. Only after that use the AI search hints for targeted code search.

## Important Boundaries

- `AzCore` is foundational infrastructure, not gameplay logic.
- `AzFramework` is the runtime framework layer that turns core primitives into usable runtime systems.
- `AzToolsFramework` is the editor layer. Many prefab, Asset Browser, and undo questions belong here instead of `AzFramework`.
- `AzGameFramework` is thin. It is mostly game or launcher application bootstrap, not the main gameplay framework.
- `AtomCore` is not the full renderer. It is shared support code for the Atom stack.
- `AzNetworking` provides networking abstractions and transport infrastructure. Higher-level multiplayer protocol logic may live elsewhere.

## Suggested Next Batch

If this documentation is expanded, good next targets are:

1. `Code/Editor`
2. `Gems/Atom/*`
3. `Gems/ScriptCanvas/*`
4. `Gems/PhysX/*` or whichever physics gems are actually enabled
5. `Gems/Multiplayer/*`
