# 07 · 资产管线（Asset Pipeline）深入版

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## 宏观视角

O3DE 的资产有两个状态：

- **源资产（source）**：作者编辑、版控的文件，`.prefab` / `.fbx` / `.material` / `.azsl` / `.png`…。放在项目 `Assets/` 或某个启用 Gem 的 `Assets/`。
- **产物资产（product）**：运行时真正读的、已经烘焙成引擎原生格式的文件（`.spawnable`、`.azmodel`、`.azshader`、`.ktx`…）。放在项目构建目录的 `Cache/<platform>/`。

转换由后台进程 **AssetProcessor (AP)** 做：监听源目录、匹配模式、调用对应的 **AssetBuilder**。

```
[作者存 .prefab] ──→ AP 侦测 ──→ PrefabBuilder ──→ [.spawnable in Cache/]
[放入 .fbx  ] ──→ AP 侦测 ──→ SceneBuilder  ──→ [.azmodel/.azactor/...]
[修改 .azsl ] ──→ AP 侦测 ──→ ShaderBuilder ──→ [.azshader + 反射 JSON]
                                   │
                                   └── 通过 SocketConnection 通知 Editor/Launcher 热更新
```

---

## AssetProcessor 进程 / 架构

### GUI vs Batch

| 可执行 | 场景 | 驱动类 |
|---|---|---|
| `AssetProcessor` (Qt GUI) | 开发时长驻，可视化状态 | `GUIApplicationManager` |
| `AssetProcessorBatch` (CLI) | CI 一次性跑 | `BatchApplicationManager` |

两者都派生 `ApplicationManager`（[Code/Tools/AssetProcessor/native/utilities/ApplicationManager.h](../Code/Tools/AssetProcessor/native/utilities/ApplicationManager.h)）。核心接口：

```cpp
class ApplicationManager : public QObject
{
public:
    virtual BeforeRunStatus BeforeRun();  // AZ Framework / Qt / 日志初始化
    virtual bool Run() = 0;               // 派生实现（GUI loop 或 batch loop）
    void RegisterObjectForQuit(QObject*); // 优雅退出管理
};
```

### 核心调度器：AssetProcessorManager

[native/AssetManager/assetProcessorManager.h](../Code/Tools/AssetProcessor/native/AssetManager/assetProcessorManager.h)：

```cpp
class AssetProcessorManager : public QObject, ...
{
public:
    bool IsIdle();                        // 所有 job 完成？
    void SetEnableModtimeSkippingFeature(bool);  // modtime 优化
    void ScanForMissingProductDependencies();    // 缺失依赖诊断
    AZStd::shared_ptr<AssetDatabaseConnection> GetDatabaseConnection();
};
```

内部处理流水：

```
FileWatcher / FileScanner 发现文件变化
    ↓
APM::AssessFileInternal(path, isDelete)
    ↓
计算文件 fingerprint（内容 hash）
    ↓
查 DB 已有记录，对比 fingerprint
    ↓ (不同)
对所有匹配该 pattern 的 Builder，发起 CreateJobs 请求
    ↓
收集 JobDescriptor 列表
    ↓
拓扑排序（按 JobDependency）
    ↓
JobManager → 分发给 BuilderManager 的 Builder 进程池
    ↓
Builder 执行 ProcessJob
    ↓
产物登记到 DB + SocketConnection 通知 Editor/Launcher
```

### Builder 进程池

**每个 Builder 跑在独立进程**（`AssetBuilder.exe`），避免 Builder 崩溃拖累 AP。[native/utilities/BuilderManager.h](../Code/Tools/AssetProcessor/native/utilities/BuilderManager.h)：

```cpp
enum class BuilderPurpose {
    CreateJobs,     // 分析阶段
    ProcessJob,     // 执行阶段
    Registration    // 注册阶段（AP 启动时）
};

class BuilderManager : public BuilderManagerBus::Handler
{
public:
    BuilderRef GetBuilder(BuilderPurpose);
    void ConnectionLost(AZ::u32 connId);
    AZStd::shared_ptr<Builder> AddNewBuilder(BuilderPurpose);

private:
    AZStd::recursive_mutex m_buildersMutex;
    BuilderList m_builderList;
};

class Builder
{
public:
    AZ::Outcome<void, AZStd::string> WaitForConnection();
    bool IsConnected() const;
    bool IsRunning(AZ::u32* exitCode = nullptr) const;

    template<typename TNetRequest, typename TNetResponse, typename TRequest, typename TResponse>
    BuilderRunJobOutcome RunJob(
        const TRequest&, TResponse&,
        AZ::u32 processTimeoutSeconds,
        const AZStd::string& task,
        const AZStd::string& modulePath,
        AssetBuilderSDK::JobCancelListener* = nullptr);

private:
    AZStd::atomic<AZ::u32> m_connectionId = 0;
    AZStd::unique_ptr<AzFramework::ProcessWatcher> m_processWatcher;
};
```

### Editor / Launcher 的 Socket 连接

AP 在启动时开 TCP server，Editor / Launcher 启动时连过来。消息格式是 AzNetworking 紧凑二进制。典型消息：

- Editor → AP: `GetFullSourcePath(assetId)`
- AP → Launcher: `AssetChanged(path, fingerprint)` — 触发热重载
- Launcher → AP: `RequestReady()` — 等待某 source file 编译完

**连接失败时**：可在 `bootstrap.setreg` 设 `"/Amazon/AzCore/Bootstrap/assets/wait_for_connect": false`，让 launcher 即便没连 AP 也能用 Cache/ 现成产物。

### assetdb.sqlite — 核心数据库

[native/AssetDatabase/AssetDatabase.cpp](../Code/Tools/AssetProcessor/native/AssetDatabase/AssetDatabase.cpp) 定义的关键表：

```sql
CREATE TABLE ScanFolders (
    ScanFolderID INTEGER PRIMARY KEY,
    ScanFolder TEXT NOT NULL,          -- 监视的绝对路径
    DisplayName TEXT,
    PortableKey TEXT,
    IsRoot INTEGER
);

CREATE TABLE Sources (
    SourceID INTEGER PRIMARY KEY,
    ScanFolderPK INTEGER,
    SourceName TEXT,                    -- 相对 ScanFolder 的路径
    SourceGuid BLOB,                    -- UUID = SHA1(relative_path)
    AnalysisFingerprint TEXT
);

CREATE TABLE Jobs (
    JobID INTEGER PRIMARY KEY,
    SourcePK INTEGER,
    JobKey TEXT,                        -- "Texture Job" / "Mesh Job"
    Fingerprint INTEGER,                -- 决定是否要重跑
    Platform TEXT,                      -- "pc" / "android" / ...
    BuilderGuid BLOB,
    Status INTEGER,
    JobRunKey INTEGER,
    ErrorCount INTEGER,
    WarningCount INTEGER
);

CREATE TABLE Products (
    ProductID INTEGER PRIMARY KEY,
    JobPK INTEGER,
    ProductName TEXT,
    SubID INTEGER,                      -- 同源多产物区分符
    AssetType BLOB,                     -- UUID of asset type
    Hash INTEGER,
    Flags INTEGER
);

CREATE TABLE SourceDependency (
    SourceDependencyID INTEGER PRIMARY KEY,
    BuilderGuid BLOB,
    SourceGuid BLOB,                    -- 谁依赖
    DependsOnSource TEXT,               -- 依赖谁
    TypeOfDependency INTEGER            -- Order/Fingerprint/OrderOnce/OrderOnly
);

CREATE TABLE ProductDependencies (      -- 运行时真正读的依赖
    ProductDependencyID INTEGER PRIMARY KEY,
    ProductPK INTEGER,
    DependencySourceGuid BLOB,
    DependencySubID INTEGER,
    Platform TEXT,
    DependencyFlags INTEGER,            -- 含 AssetLoadBehavior
    UnresolvedPath TEXT,
    UnresolvedDependencyType INTEGER
);

CREATE TABLE MissingProductDependencies (...)  -- 扫描缺失依赖（诊断）
```

这张表是**一切的事实之源**。用 DB Browser 打开 `<Project>/Cache/assetdb.sqlite` 可以直接看"谁产了谁、上次跑 fingerprint 是啥"，**debug AP 问题必备**。

---

## AssetBuilderSDK — 写 Builder 的全部 API

[Code/Tools/AssetProcessor/AssetBuilderSDK/AssetBuilderSDK/AssetBuilderSDK.h](../Code/Tools/AssetProcessor/AssetBuilderSDK/AssetBuilderSDK/AssetBuilderSDK.h)。

### AssetBuilderDesc — 描述一个 Builder

```cpp
struct AssetBuilderDesc
{
    AZStd::string m_name;                             // Builder 名 (log / UI)
    AZStd::vector<AssetBuilderPattern> m_patterns;    // 文件 glob / regex
    AZ::Uuid m_busId;                                 // Builder 自身 Uuid
    int m_version = 0;                                // 改了行为要涨（强制重跑）
    AssetBuilderType m_builderType = AssetBuilderType::External;  // Internal / External
    AZStd::string m_analysisFingerprint;              // 跳过相同 modtime 文件

    CreateJobFunction  m_createJobFunction;           // std::function<void(req, res)>
    ProcessJobFunction m_processJobFunction;

    AZ::u8 m_flags = 0;                                // 位标志
    AZStd::unordered_map<AZStd::string, AZ::u8> m_flagsByJobKey;
    AZStd::unordered_map<AZStd::string, AZStd::unordered_set<AZ::u32>>
        m_productsToKeepOnFailure;                    // job 失败时保留哪些 SubID 旧产物
};

enum BuilderFlags : AZ::u8
{
    BF_None = 0,
    BF_EmitsNoDependencies = 1 << 0,                  // 产物无运行时依赖（省分析）
    BF_DeleteLastKnownGoodProductOnFailure = 1 << 1   // 失败时清旧产物（保守）
};
```

### AssetBuilderPattern

```cpp
struct AssetBuilderPattern
{
    enum PatternType { Wildcard, Regex };
    AZStd::string m_pattern;
    PatternType m_type;
};

// 例：
AssetBuilderPattern("*.lua", AssetBuilderPattern::Wildcard)
AssetBuilderPattern("^.*Test.*\\.xml$", AssetBuilderPattern::Regex)
```

### CreateJobs 请求 / 响应

```cpp
struct CreateJobsRequest
{
    AZ::Uuid m_builderid;
    AZStd::string m_watchFolder;                      // ScanFolder 绝对路径
    AZStd::string m_sourceFile;                       // 相对 ScanFolder
    AZ::Uuid m_sourceFileUUID;                        // = SHA1(m_sourceFile)
    AZStd::vector<PlatformInfo> m_enabledPlatforms;   // 当前启用的平台清单

    bool HasPlatform(const char* identifier) const;
    bool HasPlatformWithTag(const char* tag) const;
};

struct CreateJobsResponse
{
    CreateJobsResultCode m_result;                    // Success / Failed / ShuttingDown
    AZStd::vector<SourceFileDependency> m_sourceFileDependencyList;
    AZStd::vector<JobDescriptor> m_createJobOutputs;
};

struct JobDescriptor
{
    AZStd::string m_jobKey;                            // "Texture Job" 等，同 source 下多 job 区分
    AZStd::string m_platformIdentifier;
    AZStd::vector<JobDependency> m_jobDependencies;    // 按 job 级排序 / fingerprint
    AZStd::unordered_map<AZ::u32, AZStd::string> m_jobParameters;  // 传给 ProcessJob 的自定义数据
    bool m_critical = false;                           // 失败阻塞 AP 继续？
    bool m_checkExclusiveLock = false;
    int m_priority = 0;
};
```

### ProcessJob 请求 / 响应

```cpp
struct ProcessJobRequest
{
    AZStd::string m_sourceFile;                       // 相对
    AZStd::string m_watchFolder;
    AZStd::string m_fullPath;                         // 绝对
    AZ::Uuid m_builderGuid;
    JobDescriptor m_jobDescription;                    // 包含 CreateJobs 传的 jobParameters
    PlatformInfo m_platformInfo;                      // 当前 job 的平台
    AZStd::string m_tempDirPath;                      // Builder 写临时产物的目录
    AZ::u64 m_jobId;                                   // 也是 JobCancelListener 地址
    AZ::Uuid m_sourceFileUUID;
    AZStd::vector<SourceFileDependency> m_sourceFileDependencyList;
};

struct ProcessJobResponse
{
    ProcessJobResultCode m_resultCode = ProcessJobResult_Failed;
    AZStd::vector<JobProduct> m_outputProducts;        // 至少一个（成功时）
    bool m_requiresSubIdGeneration = true;
    bool m_keepTempFolder = false;                     // 调试用
    AZStd::vector<AZStd::string> m_sourcesToReprocess; // 请重新处理这些源
};

enum ProcessJobResultCode
{
    ProcessJobResult_Success = 0,
    ProcessJobResult_Failed,
    ProcessJobResult_Crashed,
    ProcessJobResult_Cancelled,
    ProcessJobResult_NetworkIssue
};
```

### JobProduct —— 一个产物

```cpp
struct JobProduct
{
    AZStd::string m_productFileName;                  // 产物路径
    AZ::Data::AssetType m_productAssetType = AZ::Uuid::CreateNull();
    AZ::u32 m_productSubID;                            // 同源多产物区分
    AZStd::vector<AZ::u32> m_legacySubIDs;

    AZStd::vector<ProductDependency> m_dependencies;   // 运行时依赖（asset-id 级）
    ProductPathDependencySet m_pathDependencies;       // 旧式路径依赖
    bool m_dependenciesHandled = false;                // 告诉 AP 别猜

    ProductOutputFlags m_outputFlags = ProductOutputFlags::ProductAsset;
    AZStd::string m_outputPathOverride;                // IntermediateAsset 路径覆盖

    static AZ::Data::AssetType InferAssetTypeByProductFileName(const char*);
    static AZ::u32 InferSubIDFromProductFileName(const AZ::Data::AssetType&, const char*);
};

enum ProductOutputFlags : AZ::u32
{
    ProductAsset      = 1,    // 普通产物 → Cache/<platform>/
    IntermediateAsset = 2,    // 中间资产 → IntermediateAssets/
    CachedAsset       = 4
};
```

### 依赖类型

```cpp
struct SourceFileDependency            // 声明"我依赖的源文件"
{
    enum SourceFileDependencyType { Absolute, Wildcards };
    AZStd::string m_sourceFileDependencyPath;
    AZ::Uuid m_sourceFileDependencyUUID;
    SourceFileDependencyType m_sourceDependencyType = Absolute;
};

struct ProductDependency               // 运行时依赖（谁加载会连带谁）
{
    AZ::Data::AssetId m_dependencyId;
    AZ::Data::ProductDependencyInfo::ProductDependencyFlags m_flags;
    // flags 包含 AssetLoadBehavior（PreLoad / QueueLoad / NoLoad）
};

struct JobDependency                   // job 级依赖（影响编译顺序 / fingerprint）
{
    enum JobDependencyType {
        Fingerprint,   // 依赖 job fingerprint 变 → 我重跑
        Order,         // 依赖 job 先跑完，我再跑
        OrderOnce,     // 仅首次等
        OrderOnly      // 顺序但不影响 fingerprint
    };
    SourceFileDependency m_sourceFile;
    AZStd::string m_jobKey;
    AZStd::string m_platformIdentifier;
    JobDependencyType m_type;
    AZStd::vector<AZ::u32> m_productSubIds;          // 可选过滤
};
```

### Builder 注册（在 SystemComponent::Activate）

```cpp
AssetBuilderSDK::AssetBuilderDesc desc;
desc.m_name = "MyBuilder";
desc.m_version = 1;
desc.m_busId = azrtti_typeid<MyBuilderComponent>();
desc.m_patterns.emplace_back("*.xyz", AssetBuilderSDK::AssetBuilderPattern::Wildcard);
desc.m_createJobFunction  = [this](auto& req, auto& resp){ CreateJobs(req, resp);  };
desc.m_processJobFunction = [this](auto& req, auto& resp){ ProcessJob(req, resp); };

AssetBuilderSDK::AssetBuilderBus::Broadcast(
    &AssetBuilderSDK::AssetBuilderBusTraits::RegisterBuilderInformation, desc);
```

注销：

```cpp
AssetBuilderSDK::AssetBuilderBus::Broadcast(
    &AssetBuilderSDK::AssetBuilderBusTraits::UnRegisterBuilderInformation, desc.m_busId);
```

---

## 真实 Builder 走读：CopyDependencyBuilder

来源：[Gems/LmbrCentral/Code/Source/Builders/CopyDependencyBuilder/](../Gems/LmbrCentral/Code/Source/Builders/CopyDependencyBuilder/)

### `CreateJobs`

```cpp
void CopyDependencyBuilderWorker::CreateJobs(
    const AssetBuilderSDK::CreateJobsRequest& request,
    AssetBuilderSDK::CreateJobsResponse& response)
{
    // 1. 关闭中检测 — 别启动新 job
    if (m_isShuttingDown) {
        response.m_result = AssetBuilderSDK::CreateJobsResultCode::ShuttingDown;
        return;
    }

    // 2. 提取源依赖（虚函数，子类按 XML schema / font 等解析）
    auto srcDepsOutcome = GetSourceDependencies(request);
    if (!srcDepsOutcome.IsSuccess()) {
        AZ_Error(AssetBuilderSDK::ErrorWindow, false,
                 srcDepsOutcome.TakeError().c_str());
        response.m_result = AssetBuilderSDK::CreateJobsResultCode::Failed;
        return;
    }
    response.m_sourceFileDependencyList = srcDepsOutcome.TakeValue();

    // 3. 每个启用平台造一个 job
    for (const auto& info : request.m_enabledPlatforms) {
        if (m_skipServer && info.m_identifier == "server") continue;

        AssetBuilderSDK::JobDescriptor desc;
        desc.m_jobKey = m_jobKey;                 // 如 "XMLSchema"
        desc.m_critical = m_critical;
        desc.SetPlatformIdentifier(info.m_identifier.c_str());

        // 把源依赖列表编码到 jobParameters 里，ProcessJob 能读
        const int start = static_cast<int>(desc.m_jobParameters.size());
        const int num   = static_cast<int>(response.m_sourceFileDependencyList.size());
        desc.m_jobParameters[AZ_CRC_CE("sourceDependencyStartPoint")]
            = AZStd::to_string(start);
        desc.m_jobParameters[AZ_CRC_CE("sourceDependenciesNum")]
            = AZStd::to_string(num);
        for (int i = 0; i < num; ++i) {
            desc.m_jobParameters[start + i]
                = response.m_sourceFileDependencyList[i].m_sourceFileDependencyPath;
        }

        response.m_createJobOutputs.push_back(AZStd::move(desc));
    }

    response.m_result = AssetBuilderSDK::CreateJobsResultCode::Success;
}
```

**关键技巧**：
- `jobParameters[AZ_CRC_CE("key")] = value` — 通过 CRC32 作 key 传数据；`ProcessJob` 里 `m_jobParameters[AZ_CRC_CE("key")]` 再读。
- 为每个平台单独造 job；平台特定 Builder 在 `ProcessJob` 里按 `request.m_platformInfo.m_identifier` 分支输出不同产物。

### `ProcessJob`

```cpp
void CopyDependencyBuilderWorker::ProcessJob(
    const AssetBuilderSDK::ProcessJobRequest& request,
    AssetBuilderSDK::ProcessJobResponse& response)
{
    // 1. 构造产物（这里 CopyDependencyBuilder 不转换内容，只登记依赖）
    AZStd::string fileName;
    AzFramework::StringFunc::Path::GetFullFileName(request.m_fullPath.c_str(), fileName);
    AssetBuilderSDK::JobProduct jp(request.m_fullPath, GetAssetType(fileName));

    // 2. 解析产物依赖（虚函数，子类 parseXml）
    if (!ParseProductDependencies(request, jp.m_dependencies, jp.m_pathDependencies)) {
        AZ_Error(AssetBuilderSDK::ErrorWindow, false,
                 "Error outputting product dependencies for %s", fileName.c_str());
        response.m_resultCode = AssetBuilderSDK::ProcessJobResult_Failed;
        return;
    }
    jp.m_dependenciesHandled = true;    // 告诉 AP "我已负责声明，别猜"
    response.m_outputProducts.push_back(jp);

    // 3. 查"需要反向重处理的源"（schema 改了 → 所有引用 schema 的 source 要重跑）
    auto revOutcome = GetSourcesToReprocess(request);
    if (!revOutcome.IsSuccess()) {
        AZ_Error(AssetBuilderSDK::ErrorWindow, false, revOutcome.TakeError().c_str());
        response.m_resultCode = AssetBuilderSDK::ProcessJobResult_Success;  // 仍成功
        return;
    }
    response.m_sourcesToReprocess = revOutcome.TakeValue();
    response.m_resultCode = AssetBuilderSDK::ProcessJobResult_Success;
}
```

**关键点**：
- `m_dependenciesHandled = true` 避免 AP 再去"猜"依赖（节省 + 正确性）。
- 失败处理：即使 `GetSourcesToReprocess` 出错，job 本身仍成功 — 避免"解析 schema 时被阻止编辑资产"。
- `response.m_sourcesToReprocess` 是告诉 AP"这些源也需要再跑"（跨源联动）。

---

## AssetManager / AssetCatalog 运行时

### GetAsset 内部流程

```cpp
template<class T>
Asset<T> AssetManager::GetAsset(
    const AssetId& id,
    AssetLoadBehavior behavior,
    const AssetLoadParameters& params = {});
```

简化流程：

```
1. 查 AssetCatalog（GetAssetInfoById）
    未知 id  → 返回 Error 状态 Asset
2. 查内存缓存 m_assets[id]
    命中已 Ready → 直接返回引用（原子计数 + 1）
    命中 Loading → 返回同一 Asset 对象（共享等待）
3. 未命中：
    a. 调 AssetHandler::CreateAsset(id, type) 分配 AssetData
    b. 通过 AssetCatalog 拿 StreamInfo（源路径、offset、size）
    c. 创建 LoadAssetJob，丢 TaskExecutor
    d. Job 里：Stream 读数据 → AssetHandler::LoadAssetData → asset->status = Ready
    e. 如果 behavior=PreLoad，递归 GetAsset 所有 PreLoad 依赖
    f. 全部 PreLoad 依赖 Ready → 自己才 Ready
4. 发 AssetBus::OnAssetReady(asset)
```

### `FindAsset` vs `GetAsset`

| 函数 | 找不到 | 找到但没加载 | 已加载 |
|---|---|---|---|
| `GetAsset` | 返回 Error Asset，不阻塞 | 触发异步加载，返回 Loading Asset | 返回 Ready Asset |
| `FindAsset` | 返回 null Asset | 返回 null Asset（**不触发加载**） | 返回 Ready Asset |

### `AssetLoadBehavior`

| 值 | 行为 |
|---|---|
| `Default` | 按类型默认 |
| `PreLoad` | 发现即加载；**父资产 Ready 要等它所有 PreLoad 依赖 Ready**（递归） |
| `QueueLoad` | 异步队列；父资产独立 Ready |
| `NoLoad` | 只持 AssetId 不加载（按需手动 `QueueLoad`） |

**实际选择**：
- 材质的贴图 → `PreLoad`（材质就绪前 shader 采样会空纹理）
- 音效引用的 bank → `QueueLoad`（音效组件激活时再等）
- 大的可选关卡块 → `NoLoad`（玩家走近再加载）

### AssetBus — 订阅加载事件

```cpp
class UsesAsset : public AZ::Data::AssetBus::Handler
{
public:
    void Activate() {
        AssetBus::Handler::BusConnect(assetId);
        m_asset = AssetManager::Instance().GetAsset<MyAsset>(
            assetId, AZ::Data::AssetLoadBehavior::PreLoad);
    }
    void Deactivate() { AssetBus::Handler::BusDisconnect(); }

    void OnAssetReady(Asset<AssetData> a)    override { /* 首次可用 */ }
    void OnAssetReloaded(Asset<AssetData> a) override { /* 热更新 */ }
    void OnAssetError(Asset<AssetData> a)    override { /* 失败 */ }
    void OnAssetMoved(Asset<AssetData>, void*)       override {}
    void OnAssetUnloaded(AssetId, AssetType)         override {}

    AZ::Data::Asset<MyAsset> m_asset;
};
```

**细节**：如果 `BusConnect` 时资产已 Ready，`OnAssetReady` 会同步回调一次 —— 不用担心漏。

### AssetCatalog 核心 API

```cpp
class AssetCatalogRequests : public AZ::EBusTraits
{
public:
    static const AZ::EBusHandlerPolicy HandlerPolicy = AZ::EBusHandlerPolicy::Single;
    static const AZ::EBusAddressPolicy AddressPolicy = AZ::EBusAddressPolicy::Single;

    virtual AZStd::string GetAssetPathById(const AssetId& id) = 0;
    virtual AssetId GetAssetIdByPath(const char* path, const AssetType& type,
                                     bool autoRegister) = 0;
    virtual AssetInfo GetAssetInfoById(const AssetId& id) = 0;

    virtual AZ::Outcome<AZStd::vector<ProductDependency>, AZStd::string>
        GetDirectProductDependencies(const AssetId&) = 0;

    virtual AZ::Outcome<AZStd::vector<ProductDependency>, AZStd::string>
        GetAllProductDependencies(const AssetId&) = 0;

    virtual AZ::Outcome<AZStd::vector<ProductDependency>, AZStd::string>
        GetLoadBehaviorProductDependencies(const AssetId&,
            AZStd::unordered_set<AssetId>& noloadSet,
            PreloadAssetListType& preloadAssetList) = 0;
};
```

**最常用**：

```cpp
AZ::Data::AssetId id;
AZ::Data::AssetCatalogRequestBus::BroadcastResult(
    id, &AZ::Data::AssetCatalogRequests::GetAssetIdByPath,
    "materials/default.azmaterial",
    azrtti_typeid<AZ::RPI::MaterialAsset>(),
    false);
```

---

## AssetHandler 派生

### GenericAssetHandler<T> — 最快的自定义 Asset

定义在 [Code/Framework/AzFramework/AzFramework/Asset/GenericAssetHandler.h](../Code/Framework/AzFramework/AzFramework/Asset/GenericAssetHandler.h)：

```cpp
class MyAsset : public AZ::Data::AssetData
{
public:
    AZ_CLASS_ALLOCATOR(MyAsset, AZ::SystemAllocator);
    AZ_RTTI(MyAsset, "{<uuid>}", AZ::Data::AssetData);

    static void Reflect(AZ::ReflectContext* c) {
        if (auto* sc = azrtti_cast<AZ::SerializeContext*>(c)) {
            sc->Class<MyAsset, AZ::Data::AssetData>()
              ->Version(1)
              ->Field("data", &MyAsset::m_data);
        }
    }

    AZStd::vector<AZ::u32> m_data;
};

// 在某 SystemComponent::Activate 里：
using MyAssetHandler = AzFramework::GenericAssetHandler<MyAsset>;
m_handler = AZStd::make_unique<MyAssetHandler>(
    "My Asset",                             // display name
    "MyGem",                                // group
    "myasset",                              // extension (无点)
    AZ::Uuid::CreateNull(),                 // 关联 component type id（可选）
    nullptr,                                // SerializeContext (nullptr = 全局)
    AZ::ObjectStream::ST_BINARY,            // 流类型
    false                                    // autoProcessToCache
);
m_handler->Register();

// Deactivate 里：
m_handler->Unregister();
```

### 自定义 AssetHandler（更细控）

```cpp
class MyAssetHandler : public AZ::Data::AssetHandler
{
public:
    AssetPtr CreateAsset(const AssetId&, const AssetType&) override {
        return aznew MyAsset();
    }

    LoadResult LoadAssetData(
        const Asset<AssetData>& asset,
        AZStd::shared_ptr<AssetDataStream> stream,
        const AssetFilterCB& filter) override
    {
        auto* data = asset.GetAs<MyAsset>();
        if (!AZ::Utils::LoadObjectFromStream(*stream, *data)) {
            return LoadResult::LoadError;
        }
        return LoadResult::LoadComplete;
    }

    bool SaveAssetData(const Asset<AssetData>& asset, IO::GenericStream* stream) override {
        return AZ::Utils::SaveObjectToStream(*stream, AZ::ObjectStream::ST_BINARY,
                                             asset.GetAs<MyAsset>());
    }

    void DestroyAsset(AssetPtr ptr) override { delete ptr; }
    bool CanHandleAsset(const AssetId&) const override { return true; }
    AssetType GetAssetType() const override { return azrtti_typeid<MyAsset>(); }

    void InitAsset(const Asset<AssetData>&, bool reload, bool isEntity) override {}
};
```

---

## Source UUID / Product SubID / Fingerprint

### Source UUID

```
sourceUuid = SHA1(relative_path_of_source_in_scan_folder)
```

- **稳定**：同路径 → 同 UUID。
- **内容无关**：文件改内容 UUID 不变。
- **跨平台一致**。

### Product SubID 规则（必守）

1. **构建稳定**：同源 → 同 SubID 组合。
2. **位置稳定**：移动源文件路径 → SubID 不变。
3. **平台稳定**：不同平台同产物 → 同 SubID。
4. **互斥重现**：同 (source, platform) 多产物 → SubID 互不重。

常见策略：
- 单产物：`subId = 0`
- 按 LOD：`lod0=0, lod1=1, lod2=2`
- 按语义枚举：`diffuse=0, normal=1, roughness=2`
- 由产物名 hash：`subId = hash(productBaseName)`（生成的 SubID 相对稳定但移动会变）

**避免**：基于文件发现顺序、时间戳、路径 hash。

### Fingerprint

```
fingerprint = hash(
    builder_version +
    source_content_hash +
    all_source_dependency_hashes +
    jobParameters +
    job_key +
    platform_identifier
)
```

改变 fingerprint 的动作 → 重跑：

- Builder `m_version++`
- 源文件内容改
- 源依赖列表变
- jobParameters 不同（例如切换了某开关）

---

## Product Dependency（运行时依赖）

### JobProduct::m_dependencies（AssetId 级）

```cpp
jobProduct.m_dependencies.push_back({
    AZ::Data::AssetId(dependencyUuid, dependencySubId),
    AZ::Data::ProductDependencyInfo::CreateFlags(AZ::Data::AssetLoadBehavior::PreLoad)
});
```

**例**：材质产物 `.azmaterial` 依赖纹理产物 `.azimage`，加到 `m_dependencies` 里，运行时 `GetAsset(material, PreLoad)` 会递归把纹理也 PreLoad 加载。

### m_pathDependencies（路径级 — 遗留）

```cpp
ProductPathDependencySet deps;
deps.insert({ "@products@/textures/default.texpng",
              AssetBuilderSDK::ProductPathDependencyType::ProductFile });
jobProduct.m_pathDependencies = deps;
```

新代码推荐用 `m_dependencies`（AssetId）；path-based 只在 "目标资产可能还没编译出来"时备用。

### 遍历依赖

```cpp
AZ::Outcome<AZStd::vector<AZ::Data::ProductDependency>, AZStd::string> out;
AZ::Data::AssetCatalogRequestBus::BroadcastResult(
    out, &AZ::Data::AssetCatalogRequests::GetDirectProductDependencies, assetId);
// 或 GetAllProductDependencies 递归闭包
```

---

## Asset Platforms

### 设置 / 启用

项目级配置文件 `<Project>/AssetProcessorGamePlatformConfig.setreg`：

```json
{
    "Amazon": {
        "AssetProcessor": {
            "Settings": {
                "Platforms": [
                    { "name": "pc",      "tags": ["tools", "editor", "client"] },
                    { "name": "android", "tags": ["mobile", "client"] }
                ],
                "Server Platforms": [
                    { "name": "server", "tags": ["server"] }
                ]
            }
        }
    }
}
```

每平台独立 Cache 目录：`<Project>/Cache/<platform>/`。

### Builder 按平台产不同产物

```cpp
void TextureBuilder::ProcessJob(const ProcessJobRequest& r, ProcessJobResponse& s) {
    if (r.m_platformInfo.HasTag("mobile")) {
        // 输出 ASTC 压缩、512x512
    } else if (r.m_platformInfo.m_identifier == "pc") {
        // 输出 BC7、2048x2048
    }
}
```

---

## Scene Pipeline（FBX / GLTF）

[Code/Tools/SceneAPI/](../Code/Tools/SceneAPI/) 分三层：

| 层 | 职责 |
|---|---|
| `SceneCore` | 内存中的数据模型（Graph / Node / Mesh / Bone / Material） |
| `SceneData` | 配置 / Manifest（`.fbx.assetinfo` JSON） |
| `SceneBuilder` | AssetBuilder SDK 适配 + 跑 importer chain |

### Scene Manifest

同名的 `.fbx.assetinfo` 放在 `.fbx` 旁边，决定导出规则：

```json
{
    "values": [
        {
            "$type": "MeshGroup",
            "name": "Hero_Mesh",
            "selectedRootBoneIndex": -1,
            "rules": {
                "rules": [
                    { "$type": "CoordinateSystemRule", "useAdvancedData": true },
                    { "$type": "MaterialRule", "applyAnyMaterial": false }
                ]
            }
        },
        {
            "$type": "ActorGroup",
            "name": "Hero_Skeleton",
            ...
        }
    ]
}
```

一个 `.fbx` 可产多个产物：`Hero_Mesh.azmodel` + `Hero_Skeleton.azskeleton` + `Hero_Anim.azmotion` + …

### Gems/SceneProcessing

注册 Group 类型、rule 类型、FBX / GLTF importer。想扩展（加自定义 rule / post-processor）→ 在自己 Gem 里派生 `SceneAPI::SceneCore::Processor`。

---

## Asset Bundler / `.pak`

### Workflow

```
开发时：Launcher / Editor → 直接读 Cache/ 松散文件
出货：AssetBundler 把 Cache/ 打进 .pak → 发包
```

命令：

```bash
# 1) 生成 assetList（给定 seed，递归收依赖）
bin/profile/AssetBundlerBatch assetLists \
    --addSeed AutomatedTesting.GameLauncher.Seeds \
    --output MyGame_pc_assetList.assetlist

# 2) 打成 .pak
bin/profile/AssetBundlerBatch bundles \
    --assetListFile MyGame_pc_assetList.assetlist \
    --outputBundlePath Bundles/MyGame.pak \
    --maxSize 2048   # MB

# 3) 产出：MyGame.pak + MyGame.pak.manifest.xml
```

### `.seed` 文件

```json
{
    "assetFileId": "{BUNDLE-ROOT-UUID}",
    "version": 1,
    "seedAssetList": [
        { "path": "levels/main.prefab",      "type": "{PREFAB-TYPE-UUID}" },
        { "path": "ui/mainmenu.uicanvas",    "type": "{UI-TYPE-UUID}" },
        { "path": "materials/default.mtl",   "type": "{MAT-TYPE-UUID}" }
    ]
}
```

"把这些作为根，顺依赖自动拉进来"。

### 运行时挂载

`ArchiveFileIO` 自动识别 `.pak`：同路径 `@products@/xxx` 先查 pak，没命中再查松散。Launcher 启动按配置 auto-mount。

---

## Prefab → Spawnable Builder

[Gems/Prefab/PrefabBuilder/](../Gems/Prefab/PrefabBuilder/)：

```
foo.prefab (JSON, Editor 编辑)
    ↓ PrefabBuilder::ProcessJob
- 加载 .prefab → 展开 Template / Instance / Link
- 递归展开所有嵌套 Prefab 成扁平 Entity 列表
- 根 Entity 标 AliasType::EntryPoint
- 序列化成 binary ObjectStream
    ↓
foo.spawnable (产物)
    ↓ 运行时
SpawnableEntitiesInterface::SpawnAllEntities(ticket)
```

---

## 热重载（Hot Reload）

### 链路

```
1. AP 监控到源文件变化
2. AP 算新 fingerprint，与 DB 对比
3. 不同 → 跑 CreateJobs + ProcessJob
4. 新产物写入 Cache/
5. DB 更新（Products / ProductDependencies）
6. AP 向所有已连 Editor/Launcher 发 AssetNotificationMessage
7. 接收端 AssetManager::ReloadAsset(id)
    - 调用 AssetHandler::LoadAssetData（新内容）
    - 发 AssetBus::OnAssetReloaded(asset)
8. 订阅者响应（渲染系统重建 GPU 资源、Lua 重新解释）
```

### 支持热重载的类型

- **Shader** (`.azsl` → `.azshader`) — 立即生效
- **Material** (`.material` → `.azmaterial`) — 立即生效
- **Lua** (`.lua` → `.luac`) — ScriptComponent 自动重载
- **ScriptCanvas** (`.scriptcanvas`) — 同上
- **Prefab** (`.prefab` → `.spawnable`) — 已挂该 prefab 的 Entity 会尝试更新（复杂场景可能需重新 spawn）
- **Texture** (`.png/.tif` → `.texpng/.dds`) — 渲染系统替换 GPU 纹理

**不 auto-reload**：`AssetData::HandleAutoReload()` 返回 false 的类型（需特殊同步）。

---

## 诊断工具

| 工具 | 用途 |
|---|---|
| **AssetProcessor GUI** 的 "Jobs" / "Assets" / "Logs" | 实时看 job 队列、失败、日志 |
| `assetdb.sqlite`（DB Browser） | 追"谁产了谁、fingerprint 历史" |
| [SerializeContextTools](../Code/Tools/SerializeContextTools/) 的 `dumpfiles` / `convert` CLI | 反射/序列化 dry-run |
| Editor 菜单 **Tools → Asset Processor** | 跳转 GUI |
| `bin/profile/AssetProcessorBatch --help` | CLI 全量参数 |
| `bin/profile/AssetProcessorBatch --scanOnlyEnabledPlatforms=false` | 扫所有平台 |

---

## 常见问题

| 症状 | 原因 / 对策 |
|---|---|
| Editor 打开某资产卡在 "Waiting for asset" | AP 还在编译；开 AP GUI 看队列 |
| 改 `.azsl` 不生效 | Cache 里旧 `.azshader`；AP GUI Reprocess 对应文件；或 `r_ReloadShader 1` |
| `AssetId` 在运行时为 `{0,0}` | Catalog 里没这条 —— 名字写错 / 平台不对 / 资产还没编完 |
| Launcher 连不上 AP | 检查端口（默认 45643）、防火墙；或 `bootstrap.setreg` 关 `wait_for_connect` |
| Builder 改了代码但产物没变 | 忘记 `m_version++`，fingerprint 不变 AP 认为无事 |
| Prefab 改字段加载报 "Failed to convert version" | 要加 SerializeContext 的 `VersionConverter` |
| 资产改后 reload 没触发 | `AssetData::HandleAutoReload()` 被override 成 false；或订阅者未 `BusConnect` |
| `.pak` 打出来缺某资产 | 根 seed 没覆盖；检查 seed → 用 `AssetBundler` GUI 对比 |

## 常见坑

1. **SubID 不稳定**：下次跑 Builder 产相同产物但给了不同 SubID → 运行时 `AssetId` 全变 → prefab / save 引用全断。
2. **Builder `m_version` 没涨**：改代码没效果；记住 "改 CreateJobs / ProcessJob 逻辑 → 涨版本"。
3. **忘声明 SourceFileDependency**：我的源文件 include 别的源，别的改了我没重跑。
4. **忘声明 ProductDependency**：运行时 `GetAsset(A, PreLoad)` 没把 A 用的 B 一起加载，B 晚到显示异常。
5. **路径用硬编码 absolute path**：CI / 其他开发机跑不了。走 `@products@` / `@engroot@` alias。
6. **Editor 端构建 prefab 保存后 AP 没跑**：AP 没连接成功（网络设置），或 prefab 放在 `@projectroot@/Assets` 外的目录（不在 scan folder 里）。
7. **ProcessJob 写到 `m_fullPath` 而不是 `m_tempDirPath`** → 写回源目录污染文件系统。
8. **Builder 崩溃**：AP 会重启它，但频繁崩可能让 AP 进入错误状态。看 `Cache/logs/AssetProcessor/` 日志。
9. **`.pak` 里资产引用了外部未打包资产**：运行时找不到产物；Bundler 有 "missing deps" 检查工具。
10. **多线程写 AssetCatalog**：Catalog 写在主线程 marshal；不要在 Builder 进程里直接改 Catalog。

继续：[08_rendering_atom.md](08_rendering_atom.md) / [12_cookbook_recipes.md](12_cookbook_recipes.md)
