# Atom Feature Common

## Role

Path:

- `Gems/Atom/Feature/Common`

Gem name:

- `Atom_Feature_Common`

This gem contains many recognizable rendering features and editor-facing feature support on top of RPI and RHI.

## Key Entry Points

- `Code/Source/CommonModule.cpp`
- `Code/Source/CommonSystemComponent.h`
- `Code/Source/CoreLights/CoreLightsSystemComponent.h`
- `Code/Source/FrameCaptureSystemComponent.h`
- `Code/Source/ProfilingCaptureSystemComponent.h`

## What To Expect

The main module registers a set of high-level feature system components, including:

- common runtime system component
- frame capture
- profiling capture
- ImGui feature integration
- skinned mesh support
- core lights

In editor builds it also adds:

- `EditorCommonSystemComponent`
- `MaterialConverterSystemComponent`

## Read First

- `Gems/Atom/Feature/Common/gem.json`
- `Gems/Atom/Feature/Common/Code/Source/CommonModule.cpp`
- `Gems/Atom/Feature/Common/Code/Source/CommonSystemComponent.h`

## AI Search Hints

- `CommonModule`
- `CommonSystemComponent`
- `CoreLightsSystemComponent`
- `FrameCaptureSystemComponent`
- `EditorCommonSystemComponent`

## Common Misreads

- Many visible rendering features show up here rather than in `Atom_RPI` itself.
- This gem is broader than one single feature such as lighting or post-process.
