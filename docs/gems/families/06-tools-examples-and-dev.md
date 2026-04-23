# Tools, Examples, And Developer Utility Gems

## Why This Family Matters

Not every gem is a major runtime system.

This family groups gems that are best understood as:

- examples
- validation helpers
- developer utilities
- editor-facing debug or convenience tools

These gems are still important because they often provide:

- reference implementations
- test fixtures for integration patterns
- small but useful project tooling

## Typical Inspection Strategy

For these gems, start with:

1. `gem.json`
2. top-level `Code/Source/*Module*`
3. any `SystemComponent`
4. editor view registration or tool window code when present

Because these gems are often small, the fastest path is usually to read the whole module surface quickly rather than search widely.

## Full Family Inventory

- `AFR`
- `AssetValidation`
- `CustomAssetExample`
- `SceneLoggingExample`
- `DevTextures`
- `DebugDraw`
- `FastNoise`
- `LandscapeCanvas`
- `Prefab/PrefabBuilder`
- `PrimitiveAssets`
- `PythonAssetBuilder`
- `QtForPython`
- `SceneProcessing`
- `TestAssetBuilder`
- `TickBusOrderViewer`

## Notes On A Few High-Value Entries

### `AssetValidation`

Useful when the question is about validation rules, validation integration, or asset QA tooling.

### `CustomAssetExample`

Useful as a small reference gem for asset-related integration patterns.

### `SceneProcessing`

Important when the question is really about import or scene pipeline tooling rather than runtime gameplay.

### `PrefabBuilder`

Useful when the problem touches prefab conversion or build-time prefab processing rather than runtime prefab usage.

## AI Search Hints

Use these names first:

- `AssetValidation`
- `CustomAssetExample`
- `SceneProcessing`
- `PrefabBuilder`
- `Builder`
- `RegisterViewClass`
- `SystemComponent`

## Common Misreads

- example gems are not always meant as production framework layers
- tool gems often expose useful patterns but may not be the runtime location of a feature
- some utility gems are better read as integration examples than as central engine systems
