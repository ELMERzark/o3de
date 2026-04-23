# UI, Audio, Animation, And Gameplay Gems

## Why This Family Matters

This family contains many of the player-visible and author-visible systems used by actual projects:

- UI
- audio
- animation and cinematics
- gameplay helper gems
- input-facing gems

These gems are frequently combined in sample and game projects.

## Highest-Value Entry Points

Read these first:

- `Gems/LyShine/gem.json`
- `Gems/LyShine/Code/Source/LyShineModule.cpp`
- `Gems/Maestro/Code/Source/MaestroModule.cpp`
- `Gems/Maestro/Code/Source/MaestroSystemComponent.h`
- `Gems/EMotionFX/Code/Source/Integration/System/AnimationModule.cpp`
- `Gems/AudioSystem/gem.json`

## Family Anatomy

### LyShine

LyShine is the main runtime UI gem and a major editor-facing UI authoring system.

`LyShineModule.cpp` is a strong source file to start with because it registers a large number of UI components such as:

- canvas
- element
- transform
- image
- text
- button
- dropdown
- slider
- scroll box
- layout components
- tooltip and spawner components

### Maestro

Maestro provides Track View and cinematics behavior.

The `MaestroSystemComponent` wraps the movie system and hooks into cry system lifecycle events.

### EMotionFX

EMotionFX is the animation stack and has both runtime integration and tooling layers.

Useful entry points include:

- `Integration/System/SystemComponent.h`
- `Integration/System/AnimationModule.cpp`

### Gameplay helper gems

This family also contains many smaller runtime-facing helper gems that projects frequently depend on for camera, input, state, and presentation behavior.

## Full Family Inventory

- `AudioSystem`
- `BarrierInput`
- `Camera`
- `CameraFramework`
- `EMotionFX`
- `GameState`
- `GameStateSamples`
- `Gestures`
- `ImGui`
- `LmbrCentral`
- `LyShine`
- `LyShineExamples`
- `Maestro`
- `MessagePopup`
- `Microphone`
- `MiniAudio`
- `MotionMatching`
- `OpenParticleSystem`
- `ScriptedEntityTweener`
- `StartingPointCamera`
- `StartingPointInput`
- `StartingPointMovement`
- `TextureAtlas`
- `UiBasics`
- `VideoPlaybackFramework`
- `VirtualGamepad`

## AI Search Hints

Use these names first:

- `LyShineModule`
- `LyShineSystemComponent`
- `MaestroSystemComponent`
- `AnimationModule`
- `SystemComponent`
- `StartingPoint`
- `CameraFramework`
- `GameState`

## Common Misreads

- LyShine is much more than a single UI widget library
- Maestro and EMotionFX solve different animation problems and should not be conflated
- helper gems like `StartingPoint*` are often sample or starter logic, not deep engine framework layers
