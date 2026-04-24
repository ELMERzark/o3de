## 资源与资产流水线 (Asset / AssetProcessor)

概述:

- 资产流水线负责导入、转换、索引与引擎加载。关键组件包括 Asset Processor、Asset Catalog 与 Runtime Loading。

示例路径:

- [Code/Tools/AssetProcessor](Code/Tools/AssetProcessor)
- [Code/Asset](Code/Asset)

结构化占位:

- **ImportersAndProcessors**: 列表：每种 asset type 的 importer/processor 文件。
- **RuntimeLoading**: AssetId -> AssetInstance 的解析与异步加载点。
- **ExtractionTasks**:
  1. 列出 AssetProcessor 中的转换步骤与对应的 handler 文件。
  2. 解析 AssetCatalog 查询接口与数据库 schema（如存在）。
 
关键组件与代表文件：
- AssetProcessor 工具与 native utilities：[Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h](Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h#L1) 和 [Code/Tools/AssetProcessor/native/utilities/UuidManager.h](Code/Tools/AssetProcessor/native/utilities/UuidManager.h#L1)
- Builder / AssetBuilderSDK 示例：SceneBuilder 中的 [Code/Tools/SceneAPI/SceneBuilder/SceneImporter.cpp](Code/Tools/SceneAPI/SceneBuilder/SceneImporter.cpp#L1)
- 平台特性与 traits：例如 [Code/Tools/AssetProcessor/Platform/Windows/AssetProcessor_Traits_Windows.h](Code/Tools/AssetProcessor/Platform/Windows/AssetProcessor_Traits_Windows.h#L1)
- 运行时 AssetManager / AssetCatalog：通过 `AZ::Data::AssetManager` 与 `AZ::Data::AssetCatalogRequestBus`，见多个 Gems 使用示例 (例如 [Gems/EMotionFX/Code/Source/Integration/System/SystemComponent.cpp](Gems/EMotionFX/Code/Source/Integration/System/SystemComponent.cpp#L1))

后续自动化提取任务（更细粒度）：
1. 从 `Code/Tools/AssetProcessor/native/` 读取并提取类与函数签名（含行号）：PlatformConfiguration, UuidManager, ProductOutputUtil。
2. 在所有 builder/gem 中查找 `AssetBuilderSDK` 使用点，提取 builder 注册入口与被支持的扩展名。
3. 收集 `AZ::Data::AssetCatalogRequests` 与 `AzFramework::AssetSystemRequestBus` 的调用位置并列出典型查询。 
4. 输出 builder -> 输入扩展 -> 生成 product 类型 的映射表，供后续 AIs 深度解析。

### Key API signatures extracted (representative)

- **PlatformConfiguration (class)** — parse platform/gem config, manage scan folders and recognizers:
  - `explicit PlatformConfiguration(QObject* pParent = nullptr);`
  - `static void Reflect(AZ::ReflectContext* context);`
  - `bool InitializeFromConfigFiles(const QString& absoluteSystemRoot, const QString& absoluteAssetRoot, const QString& projectPath, bool addPlatformConfigs = true, bool addGemsConfigs = true);`
  - `static bool MergeConfigFileToSettingsRegistry(AZ::SettingsRegistryInterface& settingsRegistry, const AZ::IO::PathView& filePathView);`
  - `const AZStd::vector<AssetBuilderSDK::PlatformInfo>& GetEnabledPlatforms() const;`
  - `void AddScanFolder(const AssetProcessor::ScanFolderInfo& source, bool isUnitTesting = false);`
  - `bool GetMatchingRecognizers(QString fileName, RecognizerPointerContainer& output) const;`
  - `QString FindFirstMatchingFile(QString relativeName, bool skipIntermediateScanFolder = false, const AssetProcessor::ScanFolderInfo** scanFolderInfo = nullptr) const;`

- **IUuidRequests (interface)** — UUID lookup/generation API used by AssetProcessor:
  - `virtual AZ::Outcome<AZ::Uuid, AZStd::string> GetUuid(const SourceAssetReference& sourceAsset) = 0;`
  - `virtual AZ::Outcome<AZStd::unordered_set<AZ::Uuid>, AZStd::string> GetLegacyUuids(const SourceAssetReference& sourceAsset) = 0;`
  - `virtual AZStd::vector<AZ::IO::Path> FindFilesByUuid(AZ::Uuid uuid) = 0;`
  - `virtual AZStd::optional<AZ::IO::Path> FindHighestPriorityFileByUuid(AZ::Uuid uuid) = 0;`
  - `virtual void FileChanged(AZ::IO::PathView file) = 0;`

- **UuidManager (class, implements IUuidRequests)** — cache + generate UUIDs:
  - `static void Reflect(AZ::ReflectContext* context);`
  - `AZ::Outcome<AZ::Uuid, AZStd::string> GetUuid(const SourceAssetReference& sourceAsset) override;`
  - `void FileChanged(AZ::IO::PathView file) override;`
  - `void EnableGenerationForTypes(AZStd::unordered_set<AZStd::string> types) override;`

- **ProductOutputUtil (struct)** — helpers to compute interim/final product paths and finalize products:
  - `static AZStd::string GetInterimPrefix(AZ::s64 scanfolderId);`
  - `static AZStd::string GetFinalPrefix(AZ::s64 scanfolderId);`
  - `static void GetInterimProductPath(QString& outputFilename, AZ::s64 sourceScanfolderId);`
  - `static void GetFinalProductPath(QString& outputFilename, AZ::s64 sourceScanfolderId);`
  - `static void FinalizeProduct(AZStd::shared_ptr<AssetDatabaseConnection> db, const PlatformConfiguration* platformConfig, const SourceAssetReference& sourceAsset, AZStd::vector<AssetBuilderSDK::JobProduct>& products, AZStd::string_view platformIdentifier);`

### Next extraction step

- Iterate files listed under the representative files to add line-numbered signatures and any `Reflect()` or `AZ::Interface` registrations into this doc.

### Line-numbered references (verified)

- PlatformConfiguration:
  - [Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h](Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h#L146) — `static void Reflect(AZ::ReflectContext* context);`
  - [Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h](Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.h#L154) — `bool InitializeFromConfigFiles(const QString& absoluteSystemRoot, const QString& absoluteAssetRoot, const QString& projectPath, bool addPlatformConfigs = true, bool addGemsConfigs = true);`

- UuidManager / IUuidRequests:
  - [Code/Tools/AssetProcessor/native/utilities/UuidManager.h](Code/Tools/AssetProcessor/native/utilities/UuidManager.h#L34) — `virtual AZ::Outcome<AZ::Uuid, AZStd::string> GetUuid(const SourceAssetReference& sourceAsset) = 0;` (interface)
  - [Code/Tools/AssetProcessor/native/utilities/UuidManager.h](Code/Tools/AssetProcessor/native/utilities/UuidManager.h#L90) — `AZ::Outcome<AZ::Uuid, AZStd::string> GetUuid(const SourceAssetReference& sourceAsset) override;` (implementation)
  - [Code/Tools/AssetProcessor/native/utilities/UuidManager.h](Code/Tools/AssetProcessor/native/utilities/UuidManager.h#L76) — `static void Reflect(AZ::ReflectContext* context);`

- ProductOutputUtil:
  - [Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.h](Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.h#L23) — `static AZStd::string GetInterimPrefix(AZ::s64 scanfolderId);`
  - [Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.h](Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.h#L36) — `static void FinalizeProduct(...)`

  ### Deep-traversal findings (method bodies, Reflect / registrations)

  - `PlatformConfiguration` implementations (summary):
    - [Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.cpp](Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.cpp#L653) — `bool PlatformConfiguration::InitializeFromConfigFiles(...)` parses ordered config files and gem manifests to populate enabled platforms and scan folders.
    - [Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.cpp](Code/Tools/AssetProcessor/native/utilities/PlatformConfiguration.cpp#L1109) — `void PlatformConfiguration::Reflect(AZ::ReflectContext* context)` currently forwards reflection to `AssetCacheServerMatcher::Reflect(serializeContext)` (serialize-only exposure).
    - Notable registrations/usages: `PlatformConfiguration` populates `m_enabledPlatforms`, `m_scanFolders`, and caches intermediate scanfolder id for fast lookup; used by AssetProcessor manager and scan/rescan flows.

  - `UuidManager` implementations (summary):
    - [Code/Tools/AssetProcessor/native/utilities/UuidManager.cpp](Code/Tools/AssetProcessor/native/utilities/UuidManager.cpp#L1) — `void UuidManager::Reflect(AZ::ReflectContext* context)` reflects `UuidSettings` to the `SerializeContext`.
    - [Code/Tools/AssetProcessor/native/utilities/UuidManager.cpp](Code/Tools/AssetProcessor/native/utilities/UuidManager.cpp#L36) — `AZ::Outcome<AZ::Uuid, AZStd::string> UuidManager::GetUuid(...)` obtains or creates a metadata UUID entry and returns the canonical UUID.
    - Key behaviors: maintains an in-memory cache (`m_uuids`, `m_existingUuids`, `m_existingLegacyUuids`), responds to `FileChanged`/`FileRemoved` to invalidate cache, and exposes `EnableGenerationForTypes` to control which file extensions use generated UUIDs.
    - Registration points: `UuidManager::Reflect` is invoked at startup (example: `ApplicationManagerBase.cpp` calls `AssetProcessor::UuidManager::Reflect(context);`) and `UuidManager` implements `AZ::Interface<IUuidRequests>` for global access via `AZ::Interface<IUuidRequests>::Get()`.

  - `ProductOutputUtil` implementations (summary):
    - [Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.cpp](Code/Tools/AssetProcessor/native/utilities/ProductOutputUtil.cpp#L1) — contains implementations for `GetInterimPrefix`, `GetFinalPrefix`, `GetInterimProductPath`, `GetFinalProductPath`, `GetPaths`, `FinalizeProduct`, `ComputeFinalProductName`, `DoFileRename`, `RenameProduct`.
    - `FinalizeProduct(...)` (see file) coordinates final naming of products, interacts with `AZ::Interface<IUuidRequests>` to decide metadata generation, queries the asset database (`AssetDatabaseConnection`) to find existing products, and performs renames via `AssetUtilities::MoveFileWithTimeout` while notifying `IMetadataUpdates` via `AZ::Interface<IMetadataUpdates>::Get()`.
    - Usage: called by asset manager / rcjob flows when finalizing build outputs; supports resolving prefix collisions and moving metadata files alongside products.

  These deep-traversal notes will be expanded into per-function summaries and cross-reference tables in the next pass (including call graphs and EBus registration enumerations).
