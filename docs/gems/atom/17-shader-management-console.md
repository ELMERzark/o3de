# Shader Management Console

## Role

Path:

- `Gems/Atom/Tools/ShaderManagementConsole`

Gem name:

- `ShaderManagementConsole`

This tool gem provides shader-variant and shader-usage inspection tooling.

## Key Entry Points

- `Code/Source/main.cpp`
- `Code/Source/ShaderManagementConsoleApplication.h`
- `Code/Source/ShaderManagementConsoleApplication.cpp`
- `Code/Source/ShaderManagementConsoleRequestBus.h`

## What To Expect

The application class derives from `AtomToolsFramework::AtomToolsDocumentApplication` and exposes request-bus helpers for:

- source asset lookup
- finding material assets using a shader
- querying material instance shader items
- listing material asset ids
- source-path generation
- shader option value helpers

## Read First

- `Gems/Atom/Tools/ShaderManagementConsole/gem.json`
- `Gems/Atom/Tools/ShaderManagementConsole/Code/Source/ShaderManagementConsoleApplication.h`

## AI Search Hints

- `ShaderManagementConsoleApplication`
- `ShaderManagementConsoleRequestBus`
- `FindMaterialAssetsUsingShader`
- `GetAllMaterialAssetIds`

## Common Misreads

- This is not the shader builder gem.
- It is a desktop inspection and management tool layered on AtomToolsFramework.
