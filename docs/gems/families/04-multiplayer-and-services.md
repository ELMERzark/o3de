# Multiplayer And Services Gems

## Why This Family Matters

This family groups networking-heavy, service-style, and platform-support gems that often appear together in project dependency sets.

It is the first place to look for:

- multiplayer runtime
- multiplayer compression or Script Canvas support
- user identity or persistence helpers
- certificate, save, and related support gems

## Highest-Value Entry Points

Read these first:

- `Gems/Multiplayer/gem.json`
- `Gems/Multiplayer/Code/Source/MultiplayerGem.h`
- `Gems/Multiplayer/Code/Source/MultiplayerSystemComponent.h`
- `Gems/Multiplayer/Multiplayer_ScriptCanvas/Code/Source/ScriptCanvasMultiplayerModule.cpp`
- `Gems/MultiplayerCompression/gem.json`

## Family Anatomy

### Multiplayer

The Multiplayer gem is a runtime framework gem that bridges gameplay code to the transport layer.

The `MultiplayerSystemComponent` is especially important because it combines:

- session notifications
- networking connection listener behavior
- root spawnable notifications
- level load blocking behavior
- network entity management
- network time

This is a cross-system orchestration component, not a tiny wrapper.

### Multiplayer extension gems

This family also includes:

- `Multiplayer_ScriptCanvas`
- `MultiplayerCompression`

These are extensions, not replacements for the main multiplayer runtime gem.

### Service-style helpers

Several small gems in this family support identity, saves, certificates, remote workflows, or platform-integrated behavior.

## Full Family Inventory

- `Multiplayer`
- `Multiplayer/Multiplayer_ScriptCanvas`
- `MultiplayerCompression`
- `Achievements`
- `Presence`
- `InAppPurchases`
- `LocalUser`
- `SaveData`
- `CertificateManager`
- `CrashReporting`
- `Compression`
- `Archive`
- `Profiler`
- `RemoteTools`
- `Streamer`
- `Streamer/StreamerProfiler`

## AI Search Hints

Use these names first:

- `MultiplayerModule`
- `MultiplayerSystemComponent`
- `NetworkEntityManager`
- `NetworkTime`
- `SessionNotificationBus`
- `IConnectionListener`
- `Streamer`
- `SaveData`

## Common Misreads

- multiplayer runtime logic is not the same thing as the lower-level `AzNetworking` transport layer
- many support gems here are helpers and infrastructure, not feature-rich gameplay systems
- extension gems in this family usually depend on the main multiplayer gem rather than replacing it
