# ImageProcessingAtom

## Role

Path:

- `Gems/Atom/Asset/ImageProcessingAtom`

Gem name:

- `ImageProcessingAtom`

This gem provides Atom-focused image processing support, editor-side image handling, thumbnails, and builder integration.

## Key Entry Points

- `Code/Source/ImageProcessingModule.cpp`
- `Code/Source/ImageProcessingSystemComponent.h`
- `Code/Source/Thumbnail/ImageThumbnailSystemComponent.h`
- `Code/Source/ImageBuilderComponent.h`

## What To Expect

The module registers three important pieces:

- image thumbnail system component
- image processing system component
- builder plugin component

This means the gem crosses editor UI, preview, and asset pipeline concerns.

## Read First

- `Gems/Atom/Asset/ImageProcessingAtom/gem.json`
- `Gems/Atom/Asset/ImageProcessingAtom/Code/Source/ImageProcessingModule.cpp`
- `Gems/Atom/Asset/ImageProcessingAtom/Code/Source/ImageProcessingSystemComponent.h`

## AI Search Hints

- `ImageProcessingSystemComponent`
- `ImageThumbnailSystemComponent`
- `PreviewerRequestBus`
- `ImageBuilderWorker`

## Common Misreads

- This is not only a builder gem.
- It also integrates with Asset Browser preview and editor-side image operations.
