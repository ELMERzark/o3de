# Rendering And Atom Gems

## Why This Family Matters

This is the largest and most layered gem family in the repository.

It includes:

- the Atom umbrella gem
- RHI and RPI runtime layers
- rendering feature gems
- rendering tool gems
- Atom-to-editor integration gems
- rendering sample content gems

If an AI needs to answer rendering questions, it should usually start here before searching unrelated gems.

## Highest-Value Entry Points

Read these first when inspecting core rendering behavior:

- `Gems/Atom/gem.json`
- `Gems/Atom/RHI/Code/Source/Module.cpp`
- `Gems/Atom/RPI/Code/Source/RPI.Private/Module.h`
- `Gems/Atom/RPI/Code/Source/RPI.Private/RPISystemComponent.h`
- `Gems/Atom/Feature/Common/Code/Source/CommonModule.cpp`
- `Gems/AtomLyIntegration/gem.json`

Recurring patterns in this family:

- umbrella gem delegates to subgems through dependencies and external subdirectories
- runtime layers split between `RHI` and `RPI`
- platform backends appear under `RHI/DX12`, `RHI/Vulkan`, `RHI/Metal`, and `RHI/Null`
- tool gems are separate manifests under `Atom/Tools/*`

## Family Anatomy

### `Atom`

The top-level `Atom` gem is an umbrella manifest, not the only place where rendering code lives.

Use it as the dependency map that ties together:

- `Atom_RHI`
- `Atom_RPI`
- `Atom_Feature_Common`
- material and pass tools
- debug camera and bridge integrations

### `Atom_RHI`

This is the low-level rendering hardware interface layer.

Important children:

- `Atom_RHI_DX12`
- `Atom_RHI_Vulkan`
- `Atom_RHI_Metal`
- `Atom_RHI_Null`

Typical inspection path:

1. `RHI/Code/Source/Module.cpp`
2. platform `SystemComponent`
3. platform-specific device and resource code

### `Atom_RPI`

This is the rendering pipeline and higher-level runtime rendering layer.

Typical inspection path:

1. `RPI.Private/Module.h`
2. `RPISystemComponent`
3. public model and image tag system components
4. pass and feature processor usage from higher layers

### `Atom_Feature_Common`

This gem contains many common rendering features such as:

- lights
- post-process
- profiling capture
- editor common hooks
- skinned mesh support

This is often the place where a "real feature" becomes visible after the base RHI and RPI layers.

## Full Family Inventory

- `Atom`
- `Atom/Asset/ImageProcessingAtom`
- `Atom/Asset/Shader`
- `Atom/Bootstrap`
- `Atom/Component/DebugCamera`
- `Atom/Feature/Common`
- `Atom/RHI`
- `Atom/RHI/DX12`
- `Atom/RHI/Metal`
- `Atom/RHI/Null`
- `Atom/RHI/Vulkan`
- `Atom/RPI`
- `Atom/Tools/AtomToolsFramework`
- `Atom/Tools/MaterialCanvas`
- `Atom/Tools/MaterialEditor`
- `Atom/Tools/PassCanvas`
- `Atom/Tools/ShaderManagementConsole`
- `AtomContent`
- `AtomContent/ReferenceMaterials`
- `AtomContent/Sponza`
- `AtomContent/TestData`
- `AtomLyIntegration`
- `AtomLyIntegration/AtomBridge`
- `AtomLyIntegration/AtomFont`
- `AtomLyIntegration/AtomImGuiTools`
- `AtomLyIntegration/AtomRenderOptions`
- `AtomLyIntegration/AtomViewportDisplayIcons`
- `AtomLyIntegration/AtomViewportDisplayInfo`
- `AtomLyIntegration/CommonFeatures`
- `AtomLyIntegration/EditorModeFeedback`
- `AtomLyIntegration/EMotionFXAtom`
- `AtomLyIntegration/ImguiAtom`
- `AtomLyIntegration/TechnicalArt/DccScriptingInterface`
- `AtomTressFX`
- `DiffuseProbeGrid`
- `DevTextures`
- `Meshlets`
- `PrimitiveAssets`
- `SkyAtmosphere`
- `Stars`

## AI Search Hints

Use these names first:

- `RPISystemComponent`
- `CommonSystemComponent`
- `PlatformModule`
- `ReflectSystemComponent`
- `FeatureProcessor`
- `MaterialEditor`
- `PassCanvas`
- `AtomToolsFramework`

## Common Misreads

- the `Atom` gem itself is not where all rendering implementation lives
- content gems such as `Sponza` and `ReferenceMaterials` are assets, not core runtime logic
- many editor-visible rendering features actually live in `AtomLyIntegration`, not only in `Atom`
