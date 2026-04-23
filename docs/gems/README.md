# O3DE Gems AI Guide

This document set maps gem manifests under `Gems/` and gives an AI a stable way to navigate gem code.

This batch is based on `gem.json` manifests found in the repository.

Current manifest count:

- `117` gem manifests
- `91` code gems
- `19` tool gems
- `7` asset gems

## What This Batch Covers

This batch does two things:

1. it gives every manifest-backed gem a place in the docs
2. it provides higher-value navigation notes for major gem families

The most important file for full coverage is:

- [catalog.md](catalog.md)

That file is a generated manifest inventory covering all `117` gems.

## Family Guides

- [01-rendering-and-atom.md](families/01-rendering-and-atom.md)
- [02-physics-terrain-and-world.md](families/02-physics-terrain-and-world.md)
- [03-scripting-and-graph.md](families/03-scripting-and-graph.md)
- [04-multiplayer-and-services.md](families/04-multiplayer-and-services.md)
- [05-ui-audio-animation-and-gameplay.md](families/05-ui-audio-animation-and-gameplay.md)
- [06-tools-examples-and-dev.md](families/06-tools-examples-and-dev.md)

## How To Read A Gem

For most code gems, the fastest inspection order is:

1. `gem.json`
2. `Code/Source/*Module.cpp` or `*Module.h`
3. `*SystemComponent.h` and `*SystemComponent.cpp`
4. `Code/Include/*` public API and buses
5. editor-side modules or editor system components when present

Common patterns:

- runtime gem: `Module` + `SystemComponent`
- editor-aware gem: runtime module plus editor module or editor system component
- builder gem: builder module, builder worker, or asset pipeline component
- asset gem: mostly manifests, assets, and little or no C++

## Important Caveat

This guide tracks manifest-backed gems only.

Some top-level folders under `Gems/` may exist without a local `gem.json`. They are not treated here as standalone gems.

## Fast Routing Table

| If the question is about | Read first |
| --- | --- |
| Atom renderer, RHI, RPI, material tools, rendering integration gems | [01-rendering-and-atom.md](families/01-rendering-and-atom.md) |
| PhysX, terrain, vegetation, navigation, world composition | [02-physics-terrain-and-world.md](families/02-physics-terrain-and-world.md) |
| Script Canvas, graph tooling, Python-facing tooling, build pipeline gems | [03-scripting-and-graph.md](families/03-scripting-and-graph.md) |
| multiplayer, persistence, identity, platform and service-style gems | [04-multiplayer-and-services.md](families/04-multiplayer-and-services.md) |
| UI, audio, animation, gameplay helpers, input, cinematics | [05-ui-audio-animation-and-gameplay.md](families/05-ui-audio-animation-and-gameplay.md) |
| examples, validation, debug helpers, developer-facing utility gems | [06-tools-examples-and-dev.md](families/06-tools-examples-and-dev.md) |

## Suggested Next Batch

After this foundation, the best next step is to deep-dive one family at a time:

1. Atom and AtomLyIntegration
2. PhysX plus Terrain plus Vegetation
3. ScriptCanvas family
4. Multiplayer family
5. LyShine plus Maestro plus EMotionFX
