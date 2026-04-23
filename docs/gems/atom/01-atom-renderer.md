# Atom Renderer

## Role

Path:

- `Gems/Atom`

Gem name:

- `Atom`

This is the umbrella manifest for the Atom family. It ties together the main runtime and tool subgems through dependencies and external subdirectories.

## What It Actually Does

The top-level `Atom` gem is mainly a dependency graph and package boundary. The real implementation is distributed into child gems such as:

- `Atom_RHI`
- `Atom_RPI`
- `Atom_Feature_Common`
- `Atom_Bootstrap`
- `AtomToolsFramework`
- Material and pass tool gems

## Read First

- `Gems/Atom/gem.json`
- `Gems/Atom/RHI/gem.json`
- `Gems/Atom/RPI/gem.json`
- `Gems/Atom/Feature/Common/gem.json`

## AI Search Hints

- `Atom`
- `external_subdirectories`
- `Atom_RHI`
- `Atom_RPI`
- `Atom_Feature_Common`

## Common Misreads

- Do not expect a single `AtomModule.cpp` at the top level.
- Treat this gem as the umbrella map for the family.
