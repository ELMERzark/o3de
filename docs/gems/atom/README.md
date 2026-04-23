# Atom Family AI Guide

This folder breaks down the `Gems/Atom` family into per-gem notes.

Covered manifests:

1. `Atom`
2. `Atom/Asset/ImageProcessingAtom`
3. `Atom/Asset/Shader`
4. `Atom/Bootstrap`
5. `Atom/Component/DebugCamera`
6. `Atom/Feature/Common`
7. `Atom/RHI`
8. `Atom/RHI/DX12`
9. `Atom/RHI/Metal`
10. `Atom/RHI/Null`
11. `Atom/RHI/Vulkan`
12. `Atom/RPI`
13. `Atom/Tools/AtomToolsFramework`
14. `Atom/Tools/MaterialCanvas`
15. `Atom/Tools/MaterialEditor`
16. `Atom/Tools/PassCanvas`
17. `Atom/Tools/ShaderManagementConsole`

## Reading Order

If the AI needs to understand Atom from the bottom up:

1. [01-atom-renderer.md](01-atom-renderer.md)
2. [07-atom-rhi.md](07-atom-rhi.md)
3. [12-atom-rpi.md](12-atom-rpi.md)
4. [06-atom-feature-common.md](06-atom-feature-common.md)
5. [04-atom-bootstrap.md](04-atom-bootstrap.md)
6. [13-atom-tools-framework.md](13-atom-tools-framework.md)
7. the individual tool gems

## Fast Routing Table

| If the question is about | Read first |
| --- | --- |
| what the top-level Atom manifest represents | [01-atom-renderer.md](01-atom-renderer.md) |
| low-level graphics backend abstraction | [07-atom-rhi.md](07-atom-rhi.md) |
| DX12-specific backend code | [08-atom-rhi-dx12.md](08-atom-rhi-dx12.md) |
| Vulkan-specific backend code | [11-atom-rhi-vulkan.md](11-atom-rhi-vulkan.md) |
| Metal-specific backend code | [09-atom-rhi-metal.md](09-atom-rhi-metal.md) |
| null renderer backend | [10-atom-rhi-null.md](10-atom-rhi-null.md) |
| rendering pipeline and pass execution layer | [12-atom-rpi.md](12-atom-rpi.md) |
| common lights, post-process, frame capture, editor feature support | [06-atom-feature-common.md](06-atom-feature-common.md) |
| Atom-wide tool application support | [13-atom-tools-framework.md](13-atom-tools-framework.md) |
| Material Editor | [15-material-editor.md](15-material-editor.md) |
| Material Canvas | [14-material-canvas.md](14-material-canvas.md) |
| Pass Canvas | [16-pass-canvas.md](16-pass-canvas.md) |
| shader inspection and variant tooling | [17-shader-management-console.md](17-shader-management-console.md) |
| image processing and thumbnails | [02-imageprocessingatom.md](02-imageprocessingatom.md) |
| shader builder gem | [03-atomshader.md](03-atomshader.md) |
| debug camera components | [05-debug-camera.md](05-debug-camera.md) |

## Important Boundaries

- `Atom` is an umbrella manifest. It is not the only implementation location.
- `Atom_RHI` is lower-level than `Atom_RPI`.
- `Atom_RPI` is where the main rendering pipeline system component becomes visible.
- `Atom_Feature_Common` is where many recognizable rendering features are registered.
- `AtomToolsFramework` is shared tooling infrastructure, while Material Editor or Pass Canvas are product tools on top of it.
