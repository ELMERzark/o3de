# Atom Tools Framework

## Role

Path:

- `Gems/Atom/Tools/AtomToolsFramework`

Gem name:

- `AtomToolsFramework`

This gem is the shared application and tooling foundation for several Atom desktop tools.

## Key Entry Points

- `Code/Source/AtomToolsFrameworkModule.cpp`
- `Code/Source/AtomToolsFrameworkSystemComponent.h`
- `Code/Source/Window/AtomToolsMainWindowSystemComponent.h`
- `Code/Source/PreviewRenderer/PreviewRendererSystemComponent.h`
- `Code/Source/PerformanceMonitor/PerformanceMonitorSystemComponent.h`

## What To Expect

The module registers required system components for:

- core Atom tool framework services
- tool main window support
- preview rendering
- performance monitoring

Many standalone Atom tools build on this gem rather than re-implementing their own base app framework.

## Read First

- `Gems/Atom/Tools/AtomToolsFramework/gem.json`
- `Gems/Atom/Tools/AtomToolsFramework/Code/Source/AtomToolsFrameworkModule.cpp`
- `Gems/Atom/Tools/AtomToolsFramework/Code/Source/AtomToolsFrameworkSystemComponent.h`

## AI Search Hints

- `AtomToolsFrameworkModule`
- `AtomToolsFrameworkSystemComponent`
- `AtomToolsMainWindowSystemComponent`
- `PreviewRendererSystemComponent`
- `AtomToolsDocumentApplication`

## Common Misreads

- This gem is shared infrastructure, not one end-user tool.
- Tool-specific behavior often starts in Material Editor, Pass Canvas, or Shader Management Console on top of this gem.
