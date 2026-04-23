# AtomCore

## Module Role

`AtomCore` is not the full renderer. It is a shared support layer used by the Atom rendering stack. In the current tree its main value is concentrated in two areas:

- runtime instance reuse and lifecycle support
- lightweight containers and utility types

If the question is "why is this Atom runtime object reused instead of rebuilt every time," the first place to look is `AtomCore/Instance`.

## Directory Map

| Directory | Purpose |
| --- | --- |
| `Instance/` | `Instance`, `InstanceData`, `InstanceId`, and `InstanceDatabase` |
| `Utils/` | small utility helpers such as `ScopedValue` |
| `std/` | Atom-specific containers and concurrency helpers |

## Core Subsystem

### 1. Instance database

Read first:

- `Code/Framework/AtomCore/AtomCore/Instance/InstanceDatabase.h`
- `Code/Framework/AtomCore/AtomCore/Instance/InstanceData.h`
- `Code/Framework/AtomCore/AtomCore/Instance/InstanceId.h`
- `Code/Framework/AtomCore/AtomCore/Instance/Instance.h`

`InstanceDatabase` is designed to:

- deduplicate runtime objects created from assets
- provide `Find` and `FindOrCreate`
- keep a stable relationship between instance ids and source assets
- let higher layers control creation and deletion through `InstanceHandler`

The header comments also make two important points explicit:

- the database does not own the instances, it returns them as `Data::Instance<>`
- the system is thread-safe, though instance creation is protected by locking

### 2. Lightweight utility layer

Useful but usually not the first place to start:

- `std/containers/small_vector.h`
- `std/containers/vector_set.h`
- `std/containers/fixed_vector_set.h`
- `std/containers/lru_cache.h`
- `std/parallel/concurrency_checker.h`
- `Utils/ScopedValue.h`

These files are more like a toolbox than a business-logic entry point.

## Core Mental Model

### 1. `AtomCore` is a support layer, not RHI or RPI itself

If the AI needs to analyze:

- render pipeline behavior
- shader binding
- scene graph behavior
- pass system logic

then `AtomCore` will not be enough. Continue into higher-level Atom modules or gems.

### 2. The instance model fits asset-driven reusable runtime objects

`InstanceDatabase` is a good fit when:

- an asset produces one or more runtime objects
- the same `InstanceId` should reuse the same object
- object construction needs a custom handler

That is why Atom often uses an asset-to-instance split instead of exposing only asset objects.

## Read These Files First

- `Code/Framework/AtomCore/AtomCore/Instance/InstanceDatabase.h`
- `Code/Framework/AtomCore/AtomCore/Instance/InstanceData.h`
- `Code/Framework/AtomCore/AtomCore/Instance/InstanceId.h`
- `Code/Framework/AtomCore/AtomCore/Instance/Instance.h`
- `Code/Framework/AtomCore/AtomCore/std/containers/small_vector.h`
- `Code/Framework/AtomCore/AtomCore/std/containers/lru_cache.h`

## AI Search Hints

Use these names first:

- `InstanceDatabase`
- `FindOrCreate`
- `InstanceHandler`
- `InstanceId`
- `InstanceData`

## Common Misreads

- `AtomCore` is not the full rendering implementation.
- It mainly provides reuse mechanisms and shared containers.
- If the AI searches only here for renderer behavior, it will usually miss the real feature code.

## Relationship To Other Modules

- `AtomCore` supports higher-level Atom modules.
- It sits next to `AzCore` in the broad foundation layer, but with a rendering-oriented focus instead of general engine infrastructure.
