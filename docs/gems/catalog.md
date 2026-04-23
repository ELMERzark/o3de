# O3DE Gems Catalog

Generated from `gem.json` manifests under `Gems/`.

Total manifests: 117

## Family Counts

- `Achievements`: 1
- `AFR`: 1
- `Archive`: 1
- `AssetValidation`: 1
- `Atom`: 17
- `AtomContent`: 4
- `AtomLyIntegration`: 12
- `AtomTressFX`: 1
- `AudioSystem`: 1
- `BarrierInput`: 1
- `Camera`: 1
- `CameraFramework`: 1
- `CertificateManager`: 1
- `Compression`: 1
- `CrashReporting`: 1
- `CustomAssetExample`: 1
- `DebugDraw`: 1
- `DevTextures`: 1
- `DiffuseProbeGrid`: 1
- `EditorPythonBindings`: 1
- `EMotionFX`: 1
- `ExpressionEvaluation`: 1
- `FastNoise`: 1
- `GameState`: 1
- `GameStateSamples`: 1
- `Gestures`: 1
- `GradientSignal`: 1
- `GraphCanvas`: 1
- `GraphModel`: 1
- `ImGui`: 1
- `InAppPurchases`: 1
- `LandscapeCanvas`: 1
- `LmbrCentral`: 1
- `LocalUser`: 1
- `LyShine`: 1
- `LyShineExamples`: 1
- `Maestro`: 1
- `Meshlets`: 1
- `MessagePopup`: 1
- `Microphone`: 1
- `MiniAudio`: 1
- `MotionMatching`: 1
- `Multiplayer`: 2
- `MultiplayerCompression`: 1
- `NvCloth`: 1
- `OpenParticleSystem`: 1
- `PhysX`: 5
- `Prefab`: 1
- `Presence`: 1
- `PrimitiveAssets`: 1
- `Profiler`: 1
- `PythonAssetBuilder`: 1
- `QtForPython`: 1
- `RecastNavigation`: 1
- `RemoteTools`: 1
- `SaveData`: 1
- `SceneLoggingExample`: 1
- `SceneProcessing`: 1
- `ScriptAutomation`: 1
- `ScriptCanvas`: 1
- `ScriptCanvasDeveloper`: 1
- `ScriptCanvasPhysics`: 1
- `ScriptCanvasTesting`: 1
- `ScriptedEntityTweener`: 1
- `ScriptEvents`: 1
- `SkyAtmosphere`: 1
- `Stars`: 1
- `StartingPointCamera`: 1
- `StartingPointInput`: 1
- `StartingPointMovement`: 1
- `Streamer`: 2
- `SurfaceData`: 1
- `Terrain`: 1
- `TestAssetBuilder`: 1
- `TextureAtlas`: 1
- `TickBusOrderViewer`: 1
- `UiBasics`: 1
- `Vegetation`: 1
- `VideoPlaybackFramework`: 1
- `VirtualGamepad`: 1
- `WhiteBox`: 1

## Inventory

### Achievements (1)

- `Achievements` at `Gems/Achievements`
  Gem name: `Achievements`
  Type: `Code`
  Dependencies: None
  Summary: The Achievements Gem provides a target platform agnostic interface for retrieving achievement details and unlocking achievements.

### AFR (1)

- `AFR` at `Gems/AFR`
  Gem name: `AFR`
  Type: `Code`
  Dependencies: None
  Summary: This gem enables alternate frame rendering (AFR) by alterating rendering tasks over the GPUs. The Gem is enabled by passing --afr <pipelinename> (as well as --device-count <#gpus> with the number of GPUs to use) to the executable on the command line. <pipelinename> should be a (at least partial) match for a RenderPipeline name, for which AFR should execute. This RenderPipeline needs to have a CopyToSwapChain pass at the end. If no <pipelinename> is passed, AFR is applied to the first pipeline that posses such a CopyToSwapChain pass.

### Archive (1)

- `Archive` at `Gems/Archive`
  Gem name: `Archive`
  Type: `Code`
  Dependencies: Compression
  Summary: The Archive Gem provides reading and writing support of file contents to the O3AR archive format with optional per file compression support.

### AssetValidation (1)

- `Asset Validation` at `Gems/AssetValidation`
  Gem name: `AssetValidation`
  Type: `Code`
  Dependencies: None
  Summary: The Asset Validation Gem provides seed-related commands to ensure assets have valid seeds for asset bundling.

### Atom (17)

- `Atom Renderer` at `Gems/Atom`
  Gem name: `Atom`
  Type: `Code`
  Dependencies: Atom_Feature_Common, AtomShader, Atom_Bootstrap, Atom_Component_DebugCamera, Atom_RHI, Atom_RPI, AtomToolsFramework, MaterialCanvas, MaterialEditor, PassCanvas, ShaderManagementConsole, Atom_AtomBridge
  External subdirectories: Asset/ImageProcessingAtom, Asset/Shader, Bootstrap, Component/DebugCamera, Feature/Common, RHI, RPI, Tools/AtomToolsFramework, Tools/MaterialCanvas, Tools/MaterialEditor, Tools/PassCanvas, Tools/ShaderManagementConsole
  Summary: The Atom Renderer Gem provides Atom Renderer and its associated tools (such as Material Editor), utilites, libraries, and interfaces.

- `Atom Image Processing` at `Gems/Atom\Asset\ImageProcessingAtom`
  Gem name: `ImageProcessingAtom`
  Type: `Code`
  Dependencies: Atom_RPI, Atom_RHI
  Summary: Image processing for Atom

- `Atom Shader Builder` at `Gems/Atom\Asset\Shader`
  Gem name: `AtomShader`
  Type: `Code`
  Dependencies: Atom_RHI, Atom_RPI
  Summary: Atom Shader Builder

- `Atom Bootstrap` at `Gems/Atom\Bootstrap`
  Gem name: `Atom_Bootstrap`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: Atom Bootstrap

- `Atom Debug Camera Component` at `Gems/Atom\Component\DebugCamera`
  Gem name: `Atom_Component_DebugCamera`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: Debug Camera component for Atom

- `Atom Feature Common` at `Gems/Atom\Feature\Common`
  Gem name: `Atom_Feature_Common`
  Type: `Code`
  Dependencies: Atom_RPI, ImGui, Atom_RHI
  Summary: Common features for Atom

- `Atom RHI` at `Gems/Atom\RHI`
  Gem name: `Atom_RHI`
  Type: `Code`
  Dependencies: Atom_RHI_DX12, Atom_RHI_Metal, Atom_RHI_Vulkan, Atom_RHI_Null
  External subdirectories: DX12, Metal, Null, Vulkan
  Summary: RHI for Atom

- `Atom RHI DX12` at `Gems/Atom\RHI\DX12`
  Gem name: `Atom_RHI_DX12`
  Type: `Code`
  Dependencies: None
  Summary: DX12 RHI for Atom

- `Atom RHI Metal` at `Gems/Atom\RHI\Metal`
  Gem name: `Atom_RHI_Metal`
  Type: `Code`
  Dependencies: None
  Summary: Metal RHI for Atom

- `Atom RHI Null` at `Gems/Atom\RHI\Null`
  Gem name: `Atom_RHI_Null`
  Type: `Code`
  Dependencies: None
  Summary: Atom Null RHI

- `Atom RHI Vulkan` at `Gems/Atom\RHI\Vulkan`
  Gem name: `Atom_RHI_Vulkan`
  Type: `Code`
  Dependencies: None
  Summary: Vulcan RHI for Atom

- `Atom API` at `Gems/Atom\RPI`
  Gem name: `Atom_RPI`
  Type: `Code`
  Dependencies: Atom_RHI
  Summary: RPI for Atom

- `Atom Tools Framework` at `Gems/Atom\Tools\AtomToolsFramework`
  Gem name: `AtomToolsFramework`
  Type: `Code`
  Dependencies: Atom_RPI, Atom_RHI, Atom_Bootstrap, GraphCanvas, GraphModel
  Summary: Tools Framework for Atom

- `Atom Material Canvas` at `Gems/Atom\Tools\MaterialCanvas`
  Gem name: `MaterialCanvas`
  Type: `Tool`
  Dependencies: AtomToolsFramework, Atom_RPI, Atom_RHI, Atom_Feature_Common, ImageProcessingAtom, Atom_Component_DebugCamera, CommonFeaturesAtom
  Summary: Editor for creating, modifying, and previewing materials

- `Atom Material Editor` at `Gems/Atom\Tools\MaterialEditor`
  Gem name: `MaterialEditor`
  Type: `Tool`
  Dependencies: AtomToolsFramework, Atom_RPI, Atom_RHI, Atom_Feature_Common, ImageProcessingAtom, Atom_Component_DebugCamera, CommonFeaturesAtom
  Summary: Editor for creating, modifying, and previewing materials

- `Atom Pass Canvas` at `Gems/Atom\Tools\PassCanvas`
  Gem name: `PassCanvas`
  Type: `Tool`
  Dependencies: AtomToolsFramework, Atom_RPI, Atom_RHI, Atom_Feature_Common, ImageProcessingAtom, Atom_Component_DebugCamera, CommonFeaturesAtom
  Summary: Editor for creating, modifying, and previewing passes

- `Atom Shader Management Console` at `Gems/Atom\Tools\ShaderManagementConsole`
  Gem name: `ShaderManagementConsole`
  Type: `Tool`
  Dependencies: AtomToolsFramework, Atom_RPI, Atom_RHI, Atom_Feature_Common, ImageProcessingAtom, Atom_Component_DebugCamera, CommonFeaturesAtom
  Summary: Tool for generating and inspecting shader variant lists

### AtomContent (4)

- `Atom Content` at `Gems/AtomContent`
  Gem name: `AtomContent`
  Type: `Asset`
  Dependencies: Sponza, ReferenceMaterials
  External subdirectories: Sponza, ReferenceMaterials, TestData
  Summary: The Atom Content Gem provides assets for Atom Renderer and a modified version of the <a href='https://renderman.pixar.com/look-development-studio'>Pixar Look Development Studio</a>.

- `PBR Reference Materials` at `Gems/AtomContent\ReferenceMaterials`
  Gem name: `ReferenceMaterials`
  Type: `Asset`
  Dependencies: None
  Summary: Atom Asset Gem with a library of reference materials for StandardPBR (and others in the future)

- `Sponza` at `Gems/AtomContent\Sponza`
  Gem name: `Sponza`
  Type: `Asset`
  Dependencies: None
  Summary: A standard test scene for Global Illumination (forked from crytek sponza scene)

- `Atom Test Data` at `Gems/AtomContent\TestData`
  Gem name: `Atom_TestData`
  Type: `Asset`
  Dependencies: None
  Summary: A set of Test Asset Data to use with Atom

### AtomLyIntegration (12)

- `Atom O3DE Integration` at `Gems/AtomLyIntegration`
  Gem name: `AtomLyIntegration`
  Type: `Code`
  Dependencies: Atom_AtomBridge, AtomFont, AtomImGuiTools, AtomRenderOptions, AtomViewportDisplayIcons, AtomViewportDisplayInfo, CommonFeaturesAtom, EditorModeFeedback, EMotionFX_Atom, ImguiAtom
  External subdirectories: AtomBridge, AtomFont, AtomImGuiTools, AtomRenderOptions, AtomViewportDisplayIcons, AtomViewportDisplayInfo, CommonFeatures, EditorModeFeedback, EMotionFXAtom, ImguiAtom, TechnicalArt/DccScriptingInterface
  Summary: The Atom O3DE Integration Gem provides components, libraries, and functionality to support and integrate Atom Renderer in Open 3D Engine.

- `Atom Bridge` at `Gems/AtomLyIntegration\AtomBridge`
  Gem name: `Atom_AtomBridge`
  Type: `Code`
  Dependencies: Atom_RPI, Atom_Bootstrap, Atom_RHI, Atom_RHI_Null, Atom_Feature_Common, Atom_Component_DebugCamera, AtomImGuiTools, AtomRenderOptions, CommonFeaturesAtom, EMotionFX_Atom, ImguiAtom, AtomFont, AtomViewportDisplayInfo, AtomShader, ImageProcessingAtom, AtomToolsFramework, AtomViewportDisplayIcons, MaterialCanvas, MaterialEditor, PassCanvas, ShaderManagementConsole
  Summary: Atom Bridge

- `Atom Font` at `Gems/AtomLyIntegration\AtomFont`
  Gem name: `AtomFont`
  Type: `Code`
  Dependencies: Atom_RHI, Atom_RPI
  Summary: Font Rendering for Atom

- `Atom ImGui` at `Gems/AtomLyIntegration\AtomImGuiTools`
  Gem name: `AtomImGuiTools`
  Type: `Tool`
  Dependencies: ImguiAtom
  Summary: ImGui tools for Atom

- `Atom Render Options` at `Gems/AtomLyIntegration\AtomRenderOptions`
  Gem name: `AtomRenderOptions`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: Allow to toggle and edit render passes in the viewport

- `Atom Viewport Display Icons` at `Gems/AtomLyIntegration\AtomViewportDisplayIcons`
  Gem name: `AtomViewportDisplayIcons`
  Type: `Code`
  Dependencies: Atom_RHI, Atom_RPI, Atom_Bootstrap
  Summary: Viewport display icons for Atom

- `Atom Viewport Display Info` at `Gems/AtomLyIntegration\AtomViewportDisplayInfo`
  Gem name: `AtomViewportDisplayInfo`
  Type: `Code`
  Dependencies: Atom_RHI, Atom_RPI
  Summary: Viewport Display Information for Atom

- `Common Features Atom` at `Gems/AtomLyIntegration\CommonFeatures`
  Gem name: `CommonFeaturesAtom`
  Type: `Code`
  Dependencies: Atom_Feature_Common, LmbrCentral, GradientSignal, SurfaceData, Atom_Bootstrap, Atom_RPI, AtomToolsFramework
  Summary: Common features for Atom

- `Editor Mode Feedback` at `Gems/AtomLyIntegration\EditorModeFeedback`
  Gem name: `EditorModeFeedback`
  Type: `Code`
  Dependencies: Atom_Feature_Common, Atom_RPI, Atom_RHI, CommonFeaturesAtom
  Summary: Editor Mode Visual Feedback Effects for Atom

- `EMotionFX Atom` at `Gems/AtomLyIntegration\EMotionFXAtom`
  Gem name: `EMotionFX_Atom`
  Type: `Code`
  Dependencies: EMotionFX, Atom_Feature_Common, Atom_RPI, Atom_RHI, CommonFeaturesAtom
  Summary: EmotionFX for Atom

- `Imgui Atom` at `Gems/AtomLyIntegration\ImguiAtom`
  Gem name: `ImguiAtom`
  Type: `Code`
  Dependencies: ImGui, Atom_Feature_Common
  Summary: ImGui support for Atom

- `Atom DccScriptingInterface (DCCsi)` at `Gems/AtomLyIntegration\TechnicalArt\DccScriptingInterface`
  Gem name: `DccScriptingInterface`
  Type: `Code`
  Dependencies: QtForPython
  Summary: A python framework for working with various DCC tools and workflows.

### AtomTressFX (1)

- `Atom TressFX` at `Gems/AtomTressFX`
  Gem name: `AtomTressFX`
  Type: `Code`
  Dependencies: None
  Summary: Atom TressFX Gem provides a cutting edge hair and fur simulation and rendering in Atom enhancing the AMD TressFX 4.1. The open source TressFX can be found here: https://github.com/GPUOpen-Effects/TressFX

### AudioSystem (1)

- `Audio System` at `Gems/AudioSystem`
  Gem name: `AudioSystem`
  Type: `Code`
  Dependencies: LmbrCentral
  Summary: The Audio System Gem provides the Audio Translation Layer (ATL) and Audio Controls Editor, which add support for audio in Open 3D Engine.

### BarrierInput (1)

- `Barrier Input` at `Gems/BarrierInput`
  Gem name: `BarrierInput`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: The Barrier Input Gem allows the Open 3D Engine to function as a Barrier client so that it can receive input from a remote Barrier server.

### Camera (1)

- `Camera` at `Gems/Camera`
  Gem name: `Camera`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: The Camera Gem provides a basic camera component that defines a frustum for runtime rendering.

### CameraFramework (1)

- `Camera Framework` at `Gems/CameraFramework`
  Gem name: `CameraFramework`
  Type: `Code`
  Dependencies: None
  Summary: The Camera Framework Gem provides a base for implementing more complex camera systems.

### CertificateManager (1)

- `Certificate Manager` at `Gems/CertificateManager`
  Gem name: `CertificateManager`
  Type: `Code`
  Dependencies: None
  Summary: The Certificate Manager Gem provides access to authentication files for secure game connections from Amazon S3, files on disk, and other 3rd party sources.

### Compression (1)

- `Compression` at `Gems/Compression`
  Gem name: `Compression`
  Type: `Code`
  Dependencies: None
  Summary: Compression Interface Gem which provides an API for registering Compression Algoirithms interfaces with. Comes with a sub gem implementation for LZ4 Compression

### CrashReporting (1)

- `Crash Reporting` at `Gems/CrashReporting`
  Gem name: `CrashReporting`
  Type: `Code`
  Dependencies: None
  Summary: The Crash Reporting Gem provides support for external crash reporting for Open 3D Engine projects.

### CustomAssetExample (1)

- `Custom Asset Example` at `Gems/CustomAssetExample`
  Gem name: `CustomAssetExample`
  Type: `Code`
  Dependencies: None
  Summary: The Custom Asset Example Gem provides example code for creating a custom asset for Open 3D Engine's asset pipeline.

### DebugDraw (1)

- `Debug Draw` at `Gems/DebugDraw`
  Gem name: `DebugDraw`
  Type: `Code`
  Dependencies: Atom_RPI, Atom_Bootstrap
  Summary: The Debug Draw Gem provides Editor and runtime debug visualization features for Open 3D Engine.

### DevTextures (1)

- `Dev Textures` at `Gems/DevTextures`
  Gem name: `DevTextures`
  Type: `Asset`
  Dependencies: None
  Summary: The Dev Textures Gem provides a collection of general purpose texture assets useful for prototypes and preproduction.

### DiffuseProbeGrid (1)

- `DiffuseProbeGrid` at `Gems/DiffuseProbeGrid`
  Gem name: `DiffuseProbeGrid`
  Type: `Code`
  Dependencies: Atom_RPI, Atom, LmbrCentral
  Summary: The DiffuseProbeGrid Gem implements Diffuse Global Illumination using the Nvidia RTX-GI SDK. It renders global illumination on any meshes inside a user-placed volume, and can be set to real-time or baked.

### EditorPythonBindings (1)

- `Editor Python Bindings` at `Gems/EditorPythonBindings`
  Gem name: `EditorPythonBindings`
  Type: `Tool`
  Dependencies: None
  Summary: The Editor Python Bindings Gem provides Python commands for Open 3D Engine Editor functions.

### EMotionFX (1)

- `EMotion FX Animation` at `Gems/EMotionFX`
  Gem name: `EMotionFX`
  Type: `Code`
  Dependencies: Atom_RPI, LmbrCentral
  Summary: The EMotion FX Animation Gem provides Open 3D Engine's animation system for rigged actors and includes Animation Editor, a tool for creating animated behaviors, simulated objects, and colliders for rigged actors.

### ExpressionEvaluation (1)

- `Expression Evaluation` at `Gems/ExpressionEvaluation`
  Gem name: `ExpressionEvaluation`
  Type: `Code`
  Dependencies: None
  Summary: The Expression Evaluation Gem provides a method for parsing and executing string expressions in Open 3D Engine.

### FastNoise (1)

- `Fast Noise` at `Gems/FastNoise`
  Gem name: `FastNoise`
  Type: `Code`
  Dependencies: GradientSignal, LmbrCentral, SurfaceData
  Summary: The FastNoise Gradient Gem uses the third-party, open source FastNoise library to provide a variety of high-performance noise generation algorithms.

### GameState (1)

- `Game State` at `Gems/GameState`
  Gem name: `GameState`
  Type: `Code`
  Dependencies: None
  Summary: The Game State Gem provides a generic framework to determine and manage game states and game state transitions in Open 3D Engine.

### GameStateSamples (1)

- `Game State Samples` at `Gems/GameStateSamples`
  Gem name: `GameStateSamples`
  Type: `Code`
  Dependencies: GameState, LocalUser, LyShine, SaveData, MessagePopup, LmbrCentral, UiBasics, LyShineExamples
  Summary: The Game State Samples Gem provides a set of sample game states (built on top of the Game State Gem), including primary user selection, main menu, level loading, level running, and level paused.

### Gestures (1)

- `Gestures` at `Gems/Gestures`
  Gem name: `Gestures`
  Type: `Code`
  Dependencies: Atom_RPI
  Summary: The Gestures Gem provides detection for common gesture-based input actions on iOS and Android devices.

### GradientSignal (1)

- `Gradient Signal` at `Gems/GradientSignal`
  Gem name: `GradientSignal`
  Type: `Code`
  Dependencies: SurfaceData, ImageProcessingAtom, LmbrCentral
  Summary: The Gradient Signal Gem provides a number of components for generating, modifying, and mixing gradient signals.

### GraphCanvas (1)

- `Graph Canvas` at `Gems/GraphCanvas`
  Gem name: `GraphCanvas`
  Type: `Tool`
  Dependencies: None
  Summary: The Graph Canvas Gem provides a C++ framework for creating custom graphical node based editors for Open 3D Engine.

### GraphModel (1)

- `Graph Model` at `Gems/GraphModel`
  Gem name: `GraphModel`
  Type: `Code`
  Dependencies: GraphCanvas
  Summary: The Graph Model Gem provides a generic node graph data model framework for Open 3D Engine.

### ImGui (1)

- `Immediate Mode GUI (IMGUI)` at `Gems/ImGui`
  Gem name: `ImGui`
  Type: `Tool`
  Dependencies: LmbrCentral
  Summary: The Immediate Mode GUI Gem provides the 3rdParty library IMGUI which can be used to create run time immediate mode overlays for debugging and profiling information in Open 3D Engine.

### InAppPurchases (1)

- `In-App Purchases` at `Gems/InAppPurchases`
  Gem name: `InAppPurchases`
  Type: `Code`
  Dependencies: None
  Summary: The In-App Purchases Gem provides functionality for in app purchases for iOS and Android.

### LandscapeCanvas (1)

- `Landscape Canvas` at `Gems/LandscapeCanvas`
  Gem name: `LandscapeCanvas`
  Type: `Tool`
  Dependencies: GraphModel, GradientSignal, SurfaceData, LmbrCentral, GraphCanvas
  Summary: The Landscape Canvas Gem provides the Landscape Canvas editor, a node-based graph tool for authoring gradient-based workflows to populate the landscape, such as dynamic vegetation and/or terrain.

### LmbrCentral (1)

- `O3DE Core (LmbrCentral)` at `Gems/LmbrCentral`
  Gem name: `LmbrCentral`
  Type: `Code`
  Dependencies: None
  Summary: The O3DE Core (LmbrCentral) Gem provides required code and assets for running Open 3D Engine Editor.

### LocalUser (1)

- `Local User` at `Gems/LocalUser`
  Gem name: `LocalUser`
  Type: `Code`
  Dependencies: None
  Summary: The Local User Gem provides functionality for mapping local user ids to local player slots and managing local user profiles.

### LyShine (1)

- `LyShine` at `Gems/LyShine`
  Gem name: `LyShine`
  Type: `Code`
  Dependencies: LmbrCentral, Atom_RPI, Atom, Atom_Bootstrap, AtomFont, TextureAtlas, AtomToolsFramework, UiBasics
  Summary: The LyShine Gem provides the runtime UI system and creation tools for Open 3D Engine projects.

### LyShineExamples (1)

- `LyShine Examples` at `Gems/LyShineExamples`
  Gem name: `LyShineExamples`
  Type: `Code`
  Dependencies: LmbrCentral, LyShine
  Summary: The LyShine Examples Gem provides example code and assets for LyShine, the runtime UI system and editor for Open 3D Engine projects.

### Maestro (1)

- `Maestro Cinematics` at `Gems/Maestro`
  Gem name: `Maestro`
  Type: `Code`
  Dependencies: LmbrCentral, Atom, Atom_Bootstrap, Atom_RHI, Atom_RPI
  Summary: The Maestro Cinematics Gem provides Track View, Open 3D Engine's animated sequence and cinematics editor.

### Meshlets (1)

- `Meshlets` at `Gems/Meshlets`
  Gem name: `Meshlets`
  Type: `Code`
  Dependencies: None
  Summary: The Meshlets Gem is a POC for rendering meshes solely on the GPU using meshlets / mesh clusters.

### MessagePopup (1)

- `Message Popup` at `Gems/MessagePopup`
  Gem name: `MessagePopup`
  Type: `Code`
  Dependencies: LyShine
  Summary: The Message Popup Gem provides an example implementation of popup messages using LyShine in Open 3D Engine.

### Microphone (1)

- `Microphone` at `Gems/Microphone`
  Gem name: `Microphone`
  Type: `Code`
  Dependencies: AudioSystem
  Summary: The Microphone Gem provides support for audio input through microphones.

### MiniAudio (1)

- `MiniAudio` at `Gems/MiniAudio`
  Gem name: `MiniAudio`
  Type: `Code`
  Dependencies: None
  Summary: The MiniAudio Gem provides support for audio playback using MiniAudio (https://miniaud.io)

### MotionMatching (1)

- `Motion Matching` at `Gems/MotionMatching`
  Gem name: `MotionMatching`
  Type: `Code`
  Dependencies: EMotionFX
  Summary: Motion matching is a data-driven animation technique that synthesizes motions based on existing animation data and the current character and input contexts.

### Multiplayer (2)

- `Multiplayer` at `Gems/Multiplayer`
  Gem name: `Multiplayer`
  Type: `Code`
  Dependencies: CertificateManager, Atom_Feature_Common, ImGui
  External subdirectories: Multiplayer_ScriptCanvas
  Summary: The Multiplayer Gem provides a public API for multiplayer functionality such as connecting and hosting.

- `Multiplayer Script Canvas` at `Gems/Multiplayer\Multiplayer_ScriptCanvas`
  Gem name: `Multiplayer_ScriptCanvas`
  Type: `Code`
  Dependencies: ScriptCanvas
  Summary: The Script Canvas Multiplayer Gem provides Script Canvas nodes for multiplayer logic.

### MultiplayerCompression (1)

- `Multiplayer Compression` at `Gems/MultiplayerCompression`
  Gem name: `MultiplayerCompression`
  Type: `Code`
  Dependencies: None
  Summary: The Multiplayer Compression Gem provides an open source Compressor for use with AzNetworking's transport layer.

### NvCloth (1)

- `NVIDIA Cloth (NvCloth)` at `Gems/NvCloth`
  Gem name: `NvCloth`
  Type: `Code`
  Dependencies: CommonFeaturesAtom, EMotionFX
  Summary: The NVIDIA Cloth Gem provides functionality to create fast, realistic cloth simulation with the NVIDIA Cloth library.

### OpenParticleSystem (1)

- `(Preview) OpenParticleSystem` at `Gems/OpenParticleSystem`
  Gem name: `OpenParticleSystem`
  Type: `Code`
  Dependencies: None
  Summary: WARNING: This gem is in preview, file formats and data may change before official release. The OpenParticleSystem Gem provides a particle system framework alongside a dedicated toolset for creating natural phenomena (such as flames, smoke, rainfall, and snowfall) and specialized effects (including explosions), leveraging vast numbers of micro-particle elements and dynamic motion simulations to achieve realistic visual representations.

### PhysX (5)

- `PhysX Common` at `Gems/PhysX\Common`
  Gem name: `PhysXCommon`
  Type: `Code`
  Dependencies: None
  Summary: The PhysX Common Gem provides the necessary assets and common libraries to support the PhysX Gems in the catalog.

- `PhysX4` at `Gems/PhysX\Core\PhysX4`
  Gem name: `PhysX`
  Type: `Code`
  Dependencies: PhysXCommon, LmbrCentral, CommonFeaturesAtom
  Summary: Deprecation Notice: The PhysX4 Gem will be deprecated in a future release and no longer supported. Please use the o3de script command 'upgrade-physx-gem' on your existing PhysX enabled project. (See release notes for details).

- `PhysX5` at `Gems/PhysX\Core\PhysX5`
  Gem name: `PhysX5`
  Type: `Code`
  Dependencies: PhysXCommon, LmbrCentral, CommonFeaturesAtom
  Summary: The PhysX5 Gem provides physics simulation with NVIDIA PhysX including static and dynamic rigid body simulation, force regions, ragdolls, articulations, and dynamic PhysX joints. This Gem is based on version 5 of the <a href='https://developer.nvidia.com/physx-sdk'>NVIDIA PhysX SDK</a>, and is not compatible with the PhysX4 Gem.

- `PhysX4 Debug` at `Gems/PhysX\Debug\PhysX4`
  Gem name: `PhysXDebug`
  Type: `Tool`
  Dependencies: PhysX, ImGui
  Summary: Deprecation Notice: The PhysX4 Debug Gem, along with the PhysX4 Gem will be deprecated in a future release and no longer supported. Please use the o3de script command 'upgrade-physx-gem' on your existing PhysX enabled project. (See release notes for details).

- `PhysX5 Debug` at `Gems/PhysX\Debug\PhysX5`
  Gem name: `PhysX5Debug`
  Type: `Tool`
  Dependencies: PhysX5, ImGui
  Summary: The PhysX5 Debug Gem, in conjunction with the PhysX5 Gem, provides debugging functionality and visualizations for NVIDIA PhysX in Open 3D Engine.

### Prefab (1)

- `Prefab Builder` at `Gems/Prefab\PrefabBuilder`
  Gem name: `PrefabBuilder`
  Type: `Code`
  Dependencies: None
  Summary: The Prefab Builder Gem provides an Asset Processor module for prefabs, which are complex assets built by combining smaller entities.

### Presence (1)

- `Presence` at `Gems/Presence`
  Gem name: `Presence`
  Type: `Code`
  Dependencies: None
  Summary: The Presence Gem provides a target platform agnostic interface for Presence services.

### PrimitiveAssets (1)

- `Primitive Assets` at `Gems/PrimitiveAssets`
  Gem name: `PrimitiveAssets`
  Type: `Asset`
  Dependencies: None
  Summary: The Primitive Assets Gem provides primitive shape mesh assets with physics enabled.

### Profiler (1)

- `Profiler` at `Gems/Profiler`
  Gem name: `Profiler`
  Type: `Code`
  Dependencies: ImGui
  Summary: A collection of utilities for capturing performance data

### PythonAssetBuilder (1)

- `Python Asset Builder` at `Gems/PythonAssetBuilder`
  Gem name: `PythonAssetBuilder`
  Type: `Code`
  Dependencies: EditorPythonBindings
  Summary: The Python Asset Builder Gem provides functionality to implement custom asset builders in Python for Asset Processor.

### QtForPython (1)

- `Qt for Python` at `Gems/QtForPython`
  Gem name: `QtForPython`
  Type: `Tool`
  Dependencies: EditorPythonBindings
  Summary: The Qt for Python Gem provides the PySide2 Python libraries to manage Qt widgets.

### RecastNavigation (1)

- `RecastNavigation` at `Gems/RecastNavigation`
  Gem name: `RecastNavigation`
  Type: `Code`
  Dependencies: None
  Summary: Recast Navigation gem provides navigation features using Recast/Detour library that can be found at https://github.com/recastnavigation/recastnavigation

### RemoteTools (1)

- `Remote Tools Connection` at `Gems/RemoteTools`
  Gem name: `RemoteTools`
  Type: `Code`
  Dependencies: None
  Summary: The Remote Tools Connection Gem implements a public API for connecting remote debug and tools O3DE applications.

### SaveData (1)

- `Save Data` at `Gems/SaveData`
  Gem name: `SaveData`
  Type: `Code`
  Dependencies: None
  Summary: The Save Data Gem provides a platform independent API to save and load persistent user data in Open 3D Engine projects.

### SceneLoggingExample (1)

- `Scene Logging Example` at `Gems/SceneLoggingExample`
  Gem name: `SceneLoggingExample`
  Type: `Code`
  Dependencies: None
  Summary: The Scene Logging Example Gem demonstrates the basics of extending the Open 3D Engine Scene API by adding additional logging to the pipeline.

### SceneProcessing (1)

- `Scene Processing` at `Gems/SceneProcessing`
  Gem name: `SceneProcessing`
  Type: `Tool`
  Dependencies: None
  Summary: The Scene Processing Gem provides Scene Settings, a tool you can use to specify the default settings for processing asset files for actors, meshes, motions, and PhysX.

### ScriptAutomation (1)

- `ScriptAutomation` at `Gems/ScriptAutomation`
  Gem name: `ScriptAutomation`
  Type: `Code`
  Dependencies: None
  Summary: A collection of specialized script bindings useful for automation in the game launcher

### ScriptCanvas (1)

- `Script Canvas` at `Gems/ScriptCanvas`
  Gem name: `ScriptCanvas`
  Type: `Tool`
  Dependencies: ScriptEvents, ExpressionEvaluation, GraphCanvas
  Summary: The Script Canvas Gem provides Open 3D Engine's visual scripting environment, Script Canvas.

### ScriptCanvasDeveloper (1)

- `Script Canvas Developer` at `Gems/ScriptCanvasDeveloper`
  Gem name: `ScriptCanvasDeveloper`
  Type: `Tool`
  Dependencies: ScriptCanvas, GraphCanvas
  Summary: The Script Canvas Developer Gem provides a suite of utility features for the development and debugging of Script Canvas systems.

### ScriptCanvasPhysics (1)

- `Script Canvas Physics` at `Gems/ScriptCanvasPhysics`
  Gem name: `ScriptCanvasPhysics`
  Type: `Code`
  Dependencies: ScriptCanvas
  Summary: The Script Canvas Physics Gem provides Script Canvas nodes for physics scene queries such as raycasts.

### ScriptCanvasTesting (1)

- `Script Canvas Testing` at `Gems/ScriptCanvasTesting`
  Gem name: `ScriptCanvasTesting`
  Type: `Tool`
  Dependencies: ScriptCanvas, GraphCanvas, ScriptEvents
  Summary: The Script Canvas Testing Gem provides a framework for testing for and with Script Canvas.

### ScriptedEntityTweener (1)

- `Scripted Entity Tweener` at `Gems/ScriptedEntityTweener`
  Gem name: `ScriptedEntityTweener`
  Type: `Tool`
  Dependencies: None
  Summary: The Scripted Entity Tweener Gem provides a script driven animation system for Open 3D Engine projects.

### ScriptEvents (1)

- `Script Events` at `Gems/ScriptEvents`
  Gem name: `ScriptEvents`
  Type: `Code`
  Dependencies: None
  Summary: The Script Events Gem provides a framework for creating event assets usable from any scripting solution in Open 3D Engine.

### SkyAtmosphere (1)

- `Sky Atmosphere` at `Gems/SkyAtmosphere`
  Gem name: `SkyAtmosphere`
  Type: `Code`
  Dependencies: Atom_RPI, CommonFeaturesAtom
  Summary: The Sky Atmosphere Gem provides a physically based model for sky atmosphere.

### Stars (1)

- `Stars` at `Gems/Stars`
  Gem name: `Stars`
  Type: `Code`
  Dependencies: None
  Summary: The Stars gem provides ability to render physically-based animated resolution-independant distant stars.

### StartingPointCamera (1)

- `Starting Point Camera` at `Gems/StartingPointCamera`
  Gem name: `StartingPointCamera`
  Type: `Code`
  Dependencies: CameraFramework, LmbrCentral
  Summary: The Starting Point Camera Gem provides the behaviors used with the Camera Framework Gem to define a camera rig.

### StartingPointInput (1)

- `Starting Point Input` at `Gems/StartingPointInput`
  Gem name: `StartingPointInput`
  Type: `Code`
  Dependencies: ScriptCanvas
  Summary: The Starting Point Input Gem provides functionality to map low-level input events to high-level actions.

### StartingPointMovement (1)

- `Starting Point Movement` at `Gems/StartingPointMovement`
  Gem name: `StartingPointMovement`
  Type: `Code`
  Dependencies: None
  Summary: The Starting Point Movement Gem provides a series of Lua scripts that listen and respond to input events and trigger transform operations such as translation and rotation.

### Streamer (2)

- `Streamer` at `Gems/Streamer`
  Gem name: `Streamer`
  Type: `Code`
  Dependencies: None
  External subdirectories: StreamerProfiler
  Summary: The parent gem for AZ::IO::Streamer related implementations.

- `Streamer Profiler` at `Gems/Streamer\StreamerProfiler`
  Gem name: `StreamerProfiler`
  Type: `Code`
  Dependencies: None
  Summary: A profiler that extracts and displays information collected from AZ::IO::Streamer.

### SurfaceData (1)

- `Surface Data` at `Gems/SurfaceData`
  Gem name: `SurfaceData`
  Type: `Code`
  Dependencies: LmbrCentral, Atom_RPI, Atom_Feature_Common
  Summary: The Surface Data Gem provides functionality to emit signals or tags from surfaces such as meshes and terrain.

### Terrain (1)

- `Terrain` at `Gems/Terrain`
  Gem name: `Terrain`
  Type: `Code`
  Dependencies: Atom_RPI, Atom, GradientSignal, SurfaceData, LmbrCentral
  Summary: The Terrain Gem is an experimental terrain system. The terrain system maps height, color, and surface data to regions of the world, provides gradient-based and shape-based authoring tools and workflows, includes specialized rendering for efficient display, and integrates with physics for physical simulation.

### TestAssetBuilder (1)

- `Test Asset Builder` at `Gems/TestAssetBuilder`
  Gem name: `TestAssetBuilder`
  Type: `Code`
  Dependencies: None
  Summary: The Test Asset Builder Gem is used to feature test Asset Processor.

### TextureAtlas (1)

- `Texture Atlas` at `Gems/TextureAtlas`
  Gem name: `TextureAtlas`
  Type: `Code`
  Dependencies: Atom_RPI, ImageProcessingAtom
  Summary: The Texture Atlas Gem provides the formatting for texture atlases from 2D textures for LyShine.

### TickBusOrderViewer (1)

- `Tick Bus Order Viewer` at `Gems/TickBusOrderViewer`
  Gem name: `TickBusOrderViewer`
  Type: `Tool`
  Dependencies: None
  Summary: The Tick Bus Order Viewer Gem provides a console variable that displays the order of runtime tick events.

### UiBasics (1)

- `UI Basics` at `Gems/UiBasics`
  Gem name: `UiBasics`
  Type: `Asset`
  Dependencies: None
  Summary: The UI Basics Gem provides a collection of basic UI prefabs such as image, text, and button, that can be used with LyShine, the Open 3D Engine runtime User Interface system and editor.

### Vegetation (1)

- `Vegetation` at `Gems/Vegetation`
  Gem name: `Vegetation`
  Type: `Code`
  Dependencies: LmbrCentral, SurfaceData, CommonFeaturesAtom, GradientSignal
  Summary: The Vegetation Gem provides tools to place natural-looking vegetation in Open 3D Engine.

### VideoPlaybackFramework (1)

- `Video Playback Framework` at `Gems/VideoPlaybackFramework`
  Gem name: `VideoPlaybackFramework`
  Type: `Code`
  Dependencies: None
  Summary: The Video Playback Framework Gem provides the interface to play back video.

### VirtualGamepad (1)

- `Virtual Gamepad` at `Gems/VirtualGamepad`
  Gem name: `VirtualGamepad`
  Type: `Code`
  Dependencies: LyShine, UiBasics
  Summary: The Virtual Gamepad Gem provides controls that emulate a gamepad on touch screen devices.

### WhiteBox (1)

- `White Box` at `Gems/WhiteBox`
  Gem name: `WhiteBox`
  Type: `Tool`
  Dependencies: Atom_RPI, Atom_Feature_Common, CommonFeaturesAtom, EditorPythonBindings
  Summary: The White Box Gem provides White Box rapid design components for Open 3D Engine.

