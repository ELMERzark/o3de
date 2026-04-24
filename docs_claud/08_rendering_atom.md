# 08 · 渲染（Atom）深入版

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

## Atom 全景

Atom 是 O3DE 的现代渲染器，作为一组 Gem 组合使用：

| Gem | 层级 | 职责 |
|---|---|---|
| [Gems/Atom/RHI](../Gems/Atom/RHI/) | 底层 | 图形 API 抽象（DX12 / Vulkan / Metal / Null） |
| [Gems/Atom/RPI](../Gems/Atom/RPI/) | 中层 | Render Pipeline Interface：Scene / View / Pass / Shader / Material |
| [Gems/Atom/Feature/Common](../Gems/Atom/Feature/Common/) | 特性层 | 可复用渲染特性（光照、阴影、后处理、mesh…） |
| [Gems/Atom/Tools](../Gems/Atom/Tools/) | 工具 | Material Editor / Shader Management Console / Pass Canvas |
| [Gems/Atom/Bootstrap](../Gems/Atom/Bootstrap/) | 粘合 | 启动时把 Atom 接入 AzFramework Window |
| [Gems/Atom/Asset](../Gems/Atom/Asset/) | Asset | Atom 相关 AssetBuilder（Shader/Material/Model/Image/Pass） |
| [Gems/AtomLyIntegration/CommonFeatures](../Gems/AtomLyIntegration/CommonFeatures/) | 桥接 | Editor / Game 组件 → Feature Processor 的桥 |

**依赖方向**：`RHI → RPI → Feature → 游戏组件`。大多数渲染开发在 Feature 层 + Shader/Pass 资产层。

---

## RHI（Render Hardware Interface）

### Device — GPU 设备

[Gems/Atom/RHI/Code/Include/Atom/RHI/Device.h](../Gems/Atom/RHI/Code/Include/Atom/RHI/Device.h)：

```cpp
class Device : public DeviceObject
{
public:
    ResultCode Init(int deviceIndex, PhysicalDevice& physicalDevice);
    ResultCode BeginFrame();                  // 每帧开始，同步 CPU/GPU 缓冲
    ResultCode EndFrame();                    // 队列刷新
    ResultCode WaitForIdle();                 // 阻塞等 GPU
    ResultCode CompileMemoryStatistics(MemoryStatistics&, MemoryStatisticsReportFlags);
    FormatCapabilities GetFormatCapabilities(Format, FormatCapabilities required) const;
    // ... 物理设备查询
};
```

**每个进程一个主 Device**（multi-GPU 时可以有多个）。大多数 RHI 对象 `Init` 时要传 deviceIndex。

### CommandList — 命令记录

[Gems/Atom/RHI/Code/Include/Atom/RHI/CommandList.h](../Gems/Atom/RHI/Code/Include/Atom/RHI/CommandList.h)：

```cpp
class CommandList
{
public:
    virtual void SetViewports(const Viewport*, uint32_t);
    virtual void SetScissors(const Scissor*, uint32_t);
    virtual void SetShaderResourceGroupForDraw(const DeviceShaderResourceGroup&);
    virtual void SetShaderResourceGroupForDispatch(const DeviceShaderResourceGroup&);
    virtual void Submit(const DeviceDrawItem& drawItem, uint32_t submitIndex = 0);
    virtual void Submit(const DeviceDispatchItem& dispatchItem, uint32_t submitIndex = 0);
    virtual void Submit(const DeviceCopyItem&);
    virtual void BeginPredication(const DeviceBuffer&, uint64_t offset, PredicationOp);
    virtual void EndPredication();
};
```

平台实现在 `Gems/Atom/RHI/<Platform>/Code/Source/RHI/CommandList.h`（DX12 / Vulkan / Metal / Null）。

### SwapChain

```cpp
class SwapChain : public ImagePoolBase
{
public:
    ResultCode Init(int deviceIndex, const SwapChainDescriptor&);
    void Present();                             // 呈现当前帧 + 轮转
    void SetVerticalSyncInterval(uint32_t);     // 0=off, 1=vsync
    ResultCode Resize(const SwapChainDimensions&);
    Image* GetCurrentImage();
    const AttachmentId& GetAttachmentId();
};
```

### Image / Buffer / 其视图

- **Image** / **Buffer**：GPU 资源，由对应 Pool 分配
- **ImageView** / **BufferView**：资源的"着色器绑定视图"（可带 format 转换、子资源范围）
- **ImagePool** / **BufferPool**：批量分配，支持稀疏 / 瞬态
- **AttachmentImage** / **AttachmentImagePool**：专给 pass 的 RT / 深度 / UAV

### PipelineState / PipelineLibrary

```cpp
// PipelineState 封装"一套完整 PSO 状态"
class PipelineState
{
    ResultCode Init(Device&, const PipelineStateDescriptorForDraw& desc);
    ResultCode Init(Device&, const PipelineStateDescriptorForDispatch& desc);
};

// PipelineLibrary 缓存编译过的 PSO（避免下次 game 启动再编）
class PipelineLibrary
{
    ResultCode Init(Device&, PipelineLibraryData*);  // 可从磁盘加载 cache
    ConstPtr<PipelineLibraryData> GetSerializedData() const;  // 存盘
};
```

### ShaderResourceGroup (SRG) — RHI 层

```cpp
class ShaderResourceGroupLayout : public DeviceObject
{
public:
    void AddShaderInput(const ShaderInputBufferDescriptor&);
    void AddShaderInput(const ShaderInputImageDescriptor&);
    void AddShaderInput(const ShaderInputSamplerDescriptor&);
    void AddStaticSampler(const ShaderInputStaticSamplerDescriptor&);
    void SetBindingSlot(uint32_t slot);
    ResultCode Finalize();
};

class ShaderResourceGroup : public Resource
{
public:
    void SetBuffer(RHI::ShaderInputBufferIndex, const DeviceBuffer*, uint32_t offset, uint32_t byteCount);
    void SetImage(RHI::ShaderInputImageIndex, const DeviceImageView*);
    void SetSampler(RHI::ShaderInputSamplerIndex, const Sampler*);
    void SetConstantData(const void*, uint32_t byteCount);
    void Compile();                             // 入 compile queue
};
```

### FrameGraph + Scope — 每帧调度核心

[Gems/Atom/RHI/Code/Include/Atom/RHI/FrameGraph.h](../Gems/Atom/RHI/Code/Include/Atom/RHI/FrameGraph.h)：

```cpp
class FrameGraph
{
public:
    void Begin();
    void BeginScope(Scope& scope);

    // 资源使用声明（FrameGraph 自动算 barrier / aliasing）
    ResultCode UseAttachment(const ImageScopeAttachmentDescriptor&,
                              ScopeAttachmentAccess, ScopeAttachmentUsage,
                              ScopeAttachmentStage);
    ResultCode UseAttachment(const BufferScopeAttachmentDescriptor&, ...);
    ResultCode UseColorAttachments(const ColorAttachmentDescriptors&);
    ResultCode UseDepthStencilAttachment(...);

    ResultCode EndScope();
    ResultCode End();
    ResultCode Compile(const FrameGraphCompileRequest&);
    ResultCode Execute(const FrameGraphExecuteRequest&);
};
```

**Scope** = 一次 GPU 工作分组（一次 pass 的绘制 / 一次 compute dispatch / 一次 copy）。FrameGraph 是 Scope 的 DAG，每帧重建（便于动态 pipeline）。

**ScopeProducer** 是接口：

```cpp
class ScopeProducer
{
public:
    virtual void SetupFrameGraphDependencies(FrameGraphInterface&) = 0;
    virtual void CompileResources(const FrameGraphCompileContext&) = 0;
    virtual void BuildCommandList(const FrameGraphExecuteContext&) = 0;
};
```

`RenderPass`（RPI 层）派生它。用户基本不直接写 ScopeProducer，而是派生 RPI 的 RasterPass/ComputePass/FullscreenTrianglePass。

### 每帧完整流程

```
FrameScheduler::BeginFrame()
  Device::BeginFrame()

  // 1. 让所有 FeatureProcessor "预告" view
  foreach Feature : FeatureProcessor::PrepareViews(packet, outViews)

  // 2. 每个 Pass 挂 scope（build FrameGraph）
  PassSystem::FrameBegin()
    → 遍历 Pass 树 → Pass::BuildInternal（需要时）
    → Pass::FrameBeginInternal → ScopeProducer 接口

  // 3. 模拟（FeatureProcessor 并行更新 CPU 侧数据）
  foreach Feature (jobs 并行): FeatureProcessor::Simulate(packet)

  // 4. 构建渲染（Feature 填充 DrawPacket 到 View）
  foreach Feature: FeatureProcessor::Render(packet)

  // 5. FrameGraph 编译（分配 transient resource、插 barrier）
  FrameGraph::Compile()

  // 6. 执行（CommandList 记录 + Submit 到 GPU 队列）
  FrameGraph::Execute()

FrameScheduler::EndFrame()
  Device::EndFrame()
  SwapChain::Present()
```

---

## RPI（Render Pipeline Interface）

### Scene — 场景

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Scene.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Scene.h)：

```cpp
class Scene final : public SceneRequestBus::Handler
{
public:
    static ScenePtr CreateScene(const SceneDescriptor&);
    void Activate();
    void Deactivate();

    template<class FeatureProcessorType>
    FeatureProcessorType* EnableFeatureProcessor();
    FeatureProcessor* EnableFeatureProcessor(const FeatureProcessorId&);
    void DisableFeatureProcessor(const FeatureProcessorId&);

    template<class T>
    T* GetFeatureProcessor();

    RenderPipeline* GetRenderPipeline(const RenderPipelineId&);
    void AddRenderPipeline(RenderPipelinePtr);

    ShaderResourceGroup* GetShaderResourceGroup();  // PerScene SRG

    DrawListTagRegistry* GetDrawListTagRegistry();  // 管理 DrawList Tag
};
```

**一个进程可多个 Scene**（主世界 Scene + UI Scene + Editor 预览 Scene…）。Scene 挂 FeatureProcessor 和 RenderPipeline，是渲染的"世界"。

### View — 相机视口

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/View.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/View.h)：

```cpp
class View final
{
public:
    enum UsageFlags {
        UsageCamera            = 1 << 0,
        UsageShadow            = 1 << 1,
        UsageReflectiveCubeMap = 1 << 2,
        UsageXR                = 1 << 3,
    };

    static ViewPtr CreateView(const Name& name, UsageFlags flags);

    void SetWorldToViewMatrix(const Matrix4x4&);
    void SetViewToClipMatrix(const Matrix4x4&);
    void SetDrawListMask(const RHI::DrawListMask&);

    // 收 DrawPacket（核心 render API）
    void AddDrawPacket(const RHI::DrawPacket*, float depth = 0.f);
    void AddDrawItem(RHI::DrawListTag, const RHI::DrawItemProperties&);

    RHI::ShaderResourceGroup* GetRHIShaderResourceGroup();  // PerView SRG
};
```

**DrawListMask**：每个 View 只响应被 mask 选中的 DrawListTag（例：阴影 View 只收 `"shadowCaster"` 类 drawList）。

### RenderPipeline — 渲染管线

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/RenderPipeline.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/RenderPipeline.h)：

```cpp
class RenderPipeline
{
public:
    static RenderPipelinePtr CreateRenderPipeline(const RenderPipelineDescriptor&);
    static RenderPipelinePtr CreateRenderPipelineFromAsset(Data::Asset<AnyAsset>);

    void SetDefaultView(ViewPtr);
    ViewPtr GetDefaultView();
    void AddPersistentView(const Name& tag, ViewPtr);

    ParentPass* GetRootPass();
    Pass* FindFirstPass(const Name& passName);   // 用路径查找 pass

    const RenderPipelineId& GetId();
    const Name& GetViewType();                   // "MainCamera" 等
};
```

描述器来自 `.azasset` JSON：

```json
{
    "Type": "JsonSerialization",
    "Version": 1,
    "ClassName": "RenderPipelineDescriptor",
    "ClassData": {
        "Name": "MainPipeline",
        "MainViewTag": "MainCamera",
        "RootPassTemplate": "MainPipeline",
        "MaterialPipelineTag": "MainPipeline",
        "AllowModification": true,
        "RenderSettings": {
            "MultisampleState": { "samples": 2 }
        },
        "DefaultAAMethod": "MSAA"
    }
}
```

### FeatureProcessor — 特性"场景级单例"

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/FeatureProcessor.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/FeatureProcessor.h)：

```cpp
class FeatureProcessor : public SceneNotificationBus::Handler
{
public:
    virtual void Activate();                   // Scene::EnableFeatureProcessor 时
    virtual void Deactivate();

    // 添加 Pass 到 pipeline（可选）
    virtual void AddRenderPasses(RenderPipeline*);

    // 让其它 Feature 知道我需要的 views（如阴影 view）
    virtual void PrepareViews(const PrepareViewsPacket&, AZStd::vector<ViewPtr>& out);

    // 异步模拟（工作线程，更新 CPU 数据）
    virtual void Simulate(const SimulatePacket&);

    // 构建 GPU 命令 / 填 DrawPacket（主线程，可触 job）
    virtual void Render(const RenderPacket&);

    // EBus 消息（场景活动 entity / transform 变化）
    virtual void OnRenderEnd();
};
```

### Pass 基类

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Pass/Pass.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Pass/Pass.h)：

```cpp
class Pass : public AZStd::intrusive_base
{
public:
    const Name& GetName();                  // 单独名字（"Bloom"）
    const Name& GetPathName();              // 完整路径（"Root.SwapChain.Bloom"）
    uint32_t GetTreeDepth();
    uint32_t GetParentChildIndex();

    uint32_t GetInputCount();
    uint32_t GetInputOutputCount();
    uint32_t GetOutputCount();

    // 生命周期（递归调用）
    virtual void BuildInternal();                       // 首次 or 请求重建时
    virtual void InitializeInternal();                  // 资源初始化
    virtual void FrameBeginInternal(FramePrepareParams);
    virtual void FrameEndInternal();

    void QueueForBuildAndInitialization();              // 标记需重建
};
```

### RasterPass / ComputePass / FullscreenTrianglePass

```cpp
class RenderPass : public Pass, public RHI::ScopeProducer
{
public:
    RHI::RenderAttachmentConfiguration GetRenderAttachmentConfiguration();
    Data::Instance<ShaderResourceGroup> GetShaderResourceGroup();  // PerPass SRG
    ViewPtr GetView();
    void BindSrg(const RHI::ShaderResourceGroup*);

    // 子类实现
    virtual void SetupFrameGraphDependencies(RHI::FrameGraphInterface&);
    virtual void CompileResources(const RHI::FrameGraphCompileContext&);
    virtual void BuildCommandListInternal(const RHI::FrameGraphExecuteContext&);
};

class RasterPass : public RenderPass {
public:
    static Ptr<RasterPass> Create(const PassDescriptor&);
    RHI::DrawListTag GetDrawListTag();      // 这个 pass 收哪个 tag 的 draw
    void SetDrawListTag(Name);
};

class ComputePass : public RenderPass {
public:
    static Ptr<ComputePass> Create(const PassDescriptor&);
    void SetTargetThreadCounts(uint32_t x, uint32_t y, uint32_t z);
    Data::Instance<Shader> GetShader();
    void UpdateShaderOptions(const ShaderVariantId&);
};

class FullscreenTrianglePass : public RenderPass { /* 最常用的 post fx pass */ };
class CopyPass    : public RenderPass { /* image → image 复制 */ };
class ParentPass  : public Pass       { /* 容器，包子 pass */ };
```

---

## Pass 系统 — 数据驱动的 pipeline

### `.pass` 资产结构

示例 [Gems/Atom/Feature/Common/Assets/Passes/Bloom.pass](../Gems/Atom/Feature/Common/Assets/Passes/Bloom.pass)：

```json
{
  "PassTemplate": {
    "Name": "BloomPassTemplate",
    "PassClass": "BloomParentPass",         // 对应 C++ 里注册的类
    "Slots": [
      {
        "Name": "InputOutput",
        "SlotType": "InputOutput",            // Input / Output / InputOutput
        "ScopeAttachmentUsage": "Shader"
      }
    ],
    "PassRequests": [
      {
        "Name": "BloomDownsamplePass",
        "TemplateName": "BloomDownsamplePassTemplate",
        "Connections": [
          {
            "LocalSlot": "Input",
            "AttachmentRef": {
              "Pass": "Parent",
              "Attachment": "InputOutput"
            }
          }
        ]
      },
      // ... 更多子 Pass
    ]
  }
}
```

- `Slots` — 定义 pass 的 "IO 接口"（包括 `ScopeAttachmentUsage`：`Shader` / `RenderTarget` / `DepthStencil` / `Resolve` / `InputAttachment`）
- `PassRequests` — 在该 pass 下挂子 pass，通过 `Connections` 把 slot 绑定起来（`AttachmentRef.Pass = "Parent"` 或兄弟 pass 名）
- `PassClass` — 对应 C++ 里某个类（由 `PassFactory` 注册）

### PassFactory 注册

```cpp
PassFactory* factory = PassFactory::Get();
factory->AddPassCreator(Name("BloomParentPass"), &MyBloomParentPass::Create);
```

运行时 `.pass` 的 `PassClass` 字段会查 factory，调对应 `Create`。

### RenderPipelineDescriptor 的 `RootPassTemplate`

指向某个 `.pass` 的 `PassTemplate.Name`。例如 `RootPassTemplate: "MainPipeline"` → 查找全局 PassTemplate 库里名为 "MainPipeline" 的 template，Create 一个 ParentPass，递归展开。

---

## Shader 管线（AZSL → azshader）

### AZSL 语言

HLSL 超集 + 跨 API 增强。示例：

```glsl
#include <viewsrg_all.srgi>      // 预定义 PerView SRG
#include "ObjectSrg.azsli"        // 自定义 SRG

// Shader Option（编译期变体）
option enum class Mode {
    Default, Fancy
} o_mode;

struct VSInput  { float3 m_position : POSITION; };
struct VSOutput { float4 m_position : SV_Position; };

VSOutput MainVS(VSInput input)
{
    VSOutput o;
    float4 world = mul(ObjectSrg::GetWorldMatrix(), float4(input.m_position, 1.0));
    o.m_position = mul(ViewSrg::m_viewProjectionMatrix, world);

    [[branch]]
    if (o_mode == Mode::Fancy) {
        // 编译器为每个 Mode 选择生成单独变体
    }
    return o;
}
```

### `azslc` 编译器

```
.azsl
  ├─ 预处理（#include .azsli）
  ├─ azslc 转换：
  │    • DXIL   (DirectX 12)
  │    • SPIR-V (Vulkan)
  │    • Metal Shading Language
  └─ 输出反射 JSON（SRG 布局、常数、贴图数、option 列表）

全部打包进 .azshader
```

### Shader / ShaderAsset / ShaderVariant

```cpp
class Shader : public Data::InstanceData
{
public:
    static Data::Instance<Shader> FindOrCreate(const Data::Asset<ShaderAsset>&);

    ShaderOptionGroup CreateShaderOptionGroup() const;
    const ShaderVariant& GetVariant(const ShaderVariantId&);
    ShaderVariantSearchResult FindVariantStableId(const ShaderVariantId&);
    void Compile();
};
```

### ShaderOption

```cpp
ShaderOptionGroup group = shader->CreateShaderOptionGroup();
group.SetValue(Name("o_mode"), ShaderOptionValue(1));  // = Mode::Fancy
ShaderVariantId variantId = group.GetShaderVariantId();
const ShaderVariant& variant = shader->GetVariant(variantId);
```

离线变体 vs 在线变体：
- **Supervariant**：离线预编译的变体（Material Canvas 声明的）
- **变体请求**：运行时现场请求，后台编译；命中前先用 default variant

---

## ShaderResourceGroup（RPI 层）

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Shader/ShaderResourceGroup.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Shader/ShaderResourceGroup.h)：

```cpp
class ShaderResourceGroup : public Data::InstanceData
{
public:
    static Data::Instance<ShaderResourceGroup> Create(
        const Data::Asset<ShaderAsset>& shaderAsset,
        const Name& srgName);

    // 查索引
    RHI::ShaderInputBufferIndex  FindShaderInputBufferIndex(const Name&);
    RHI::ShaderInputImageIndex   FindShaderInputImageIndex(const Name&);
    RHI::ShaderInputSamplerIndex FindShaderInputSamplerIndex(const Name&);
    RHI::ShaderInputConstantIndex FindShaderInputConstantIndex(const Name&);

    // 设值（比 RHI 层高级：接 RPI::Image 等而非 DeviceImageView）
    bool SetBuffer (RHI::ShaderInputBufferIndex,  const RPI::Buffer*);
    bool SetImage  (RHI::ShaderInputImageIndex,   const RPI::ImageView*);
    bool SetSampler(RHI::ShaderInputSamplerIndex, const RHI::Sampler*);

    template<class T>
    bool SetConstant(RHI::ShaderInputConstantIndex, const T& value);

    // 提交到 GPU
    void Compile();
    bool IsQueuedForCompile();
};
```

### 频率约定

| 频率 | 更新时机 | 典型内容 |
|---|---|---|
| `PerScene` | 场景加载时一次 | 全局 IBL、环境常数 |
| `PerView` | 每相机 | viewMatrix、cameraPosition、near/far |
| `PerPass` | 每 pass 运行 | Pass input/output textures、pass 参数 |
| `PerMaterial` | 材质属性变化时 | baseColor、roughness、材质贴图 |
| `PerObject` | 每实例变换变化 | worldMatrix、prevWorldMatrix、lightingChannelMask |
| `PerDraw` | 每 DrawPacket | instance index、sub-mesh id |
| `PerInstance` | 硬件实例化 | 骨骼矩阵 buffer offset |

**性能原则**：频率越低（PerScene < PerView < PerObject）更新越便宜；把值尽量放到最低频率能接受的 SRG。

### C++ 结构体自动生成

`.azsl` / `.srgi` 里定义的 SRG 会被 `azslc` 反射，配合 O3DE 工具生成 C++ 头（`Shaders/PerViewSrg.azsli.h`）：

```cpp
namespace ViewSrg {
    struct PerViewSrgData {
        Matrix4x4 m_viewProjectionMatrix;
        Vector3 m_cameraPosition;
        ...
    };
}
```

你可以 `memcpy` 或 `SetConstantData` 批量写。

---

## Material 系统

### `.materialtype` vs `.material`

| 属性 | .materialtype | .material |
|---|---|---|
| 作用 | 材质模板（定义属性、关联 shader、functor） | 具体实例（给属性赋值） |
| 编辑 | Material Canvas（节点图） / JSON | Material Editor（PropertyEditor） |
| 生命周期 | 项目级，稳定 | 资产级，多 |
| 产物 | `.azmaterialtype` | `.azmaterial` |

### Material 运行时 API

[Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Material/Material.h](../Gems/Atom/RPI/Code/Include/Atom/RPI.Public/Material/Material.h)：

```cpp
class Material : public Data::InstanceData
{
public:
    static Data::Instance<Material> Create(const Data::Asset<MaterialAsset>&);

    MaterialPropertyIndex FindPropertyIndex(const Name& propertyId);

    template<typename T>
    bool SetPropertyValue(MaterialPropertyIndex, const T& value);

    template<typename T>
    const T& GetPropertyValue(MaterialPropertyIndex) const;

    const MaterialPropertyFlags& GetPropertyDirtyFlags();
    bool NeedsCompile();
    bool Compile();                 // 把属性值 → ShaderOption + SRG 写

    const ShaderCollection& GetGeneralShaderCollection() const;
    const ShaderCollection& GetShaderCollection(const Name& pipelineTag) const;
    void ForAllShaderItems(AZStd::function<bool(const Name&, const ShaderCollection::Item&)>);
};
```

### Material Functor — 动态 shader 变体

`.materialtype` 可以声明 functor："当属性 X = true 时，启用 shader option Y"。例：

```json
"functors": [
    {
        "type": "UseTexture",
        "args": {
            "textureProperty": "baseColor.texture",
            "shaderOption": "o_baseColor_useTexture"
        }
    }
]
```

运行时 `Material::Compile` 会跑所有 functor，算出最终 ShaderVariantId 并切换 variant。

### 标准 materialtype

- `StandardPBR.materialtype` — 通用 PBR 材质（metallic/roughness 工作流）
- `EnhancedPBR.materialtype` — 扩展 PBR（subsurface、parallax、clearcoat…）
- `MinimalPBR.materialtype` — 低端设备用简化版

---

## 加一个 Feature 的完整走读

以"按组件显示黄色描边"为目标，分 6 步：

### 1) `OutlineFeatureProcessor`（场景单例）

```cpp
// Gems/MyGem/Code/Source/Outline/OutlineFeatureProcessor.h
class OutlineFeatureProcessor
    : public AZ::RPI::FeatureProcessor
{
public:
    AZ_RTTI(OutlineFeatureProcessor,
        "{outline-fp-uuid}", AZ::RPI::FeatureProcessor);
    AZ_CLASS_ALLOCATOR(OutlineFeatureProcessor, AZ::SystemAllocator);

    static void Reflect(AZ::ReflectContext*);

    void Activate() override;
    void Deactivate() override;
    void AddRenderPasses(AZ::RPI::RenderPipeline*) override;
    void Simulate(const SimulatePacket&) override;
    void Render(const RenderPacket&) override;

    // 公共 API（被组件调）
    using Handle = AZ::Data::Instance<OutlineHandle>;
    Handle AddOutline(AZ::EntityId, const AZ::Color& color);
    void RemoveOutline(Handle);
    void UpdateOutline(Handle, const AZ::Color& color);

private:
    struct OutlineData { AZ::Matrix3x4 worldTm; AZ::Color color; };
    IndexedDataVector<OutlineData> m_outlines;
    GpuBufferHandler m_outlineBuffer;          // 上传 OutlineData 到 GPU
    AZ::RHI::Ptr<AZ::RPI::Pass> m_outlinePass;
};
```

- `AddRenderPasses` 在 pipeline 里插入一个 `OutlinePass`
- `Simulate` 不涉及 GPU，更新 m_outlines 状态
- `Render` 把 m_outlines 写入 GPU buffer、compile SRG

### 2) `outline.azsl`（shader）

```glsl
#include <viewsrg_all.srgi>

struct OutlineData {
    row_major float3x4 m_worldTm;
    float4 m_color;
};

ShaderResourceGroup OutlinePassSrg : srg_freq_pass {
    StructuredBuffer<OutlineData> m_outlines;
    Texture2D<float> m_sceneDepth;
    Sampler m_pointSampler;
}

float4 MainPS(float2 uv : TEXCOORD0) : SV_Target0
{
    // 屏幕空间轮廓检测 + 画线（省略）
    return float4(...);
}
```

### 3) `OutlinePass.pass`（JSON）

```json
{
  "PassTemplate": {
    "Name": "OutlinePassTemplate",
    "PassClass": "FullscreenTrianglePass",
    "Slots": [
      { "Name": "InputDepth", "SlotType": "Input", "ScopeAttachmentUsage": "Shader" },
      { "Name": "Output",     "SlotType": "Output", "ScopeAttachmentUsage": "RenderTarget" }
    ],
    "PassData": {
      "$type": "FullscreenTrianglePassData",
      "ShaderAsset": {
        "FilePath": "shaders/outline.shader"
      }
    }
  }
}
```

### 4) `OutlineComponent`（Entity 上挂）

```cpp
class OutlineComponent : public AZ::Component, public AZ::TransformNotificationBus::Handler
{
public:
    AZ_COMPONENT(OutlineComponent, "{outline-comp-uuid}");
    static void Reflect(AZ::ReflectContext*);

    void Activate() override {
        auto scene = AZ::RPI::Scene::GetSceneForEntityId(GetEntityId());
        if (auto fp = scene->GetFeatureProcessor<OutlineFeatureProcessor>()) {
            m_handle = fp->AddOutline(GetEntityId(), m_color);
        }
        AZ::TransformNotificationBus::Handler::BusConnect(GetEntityId());
    }
    void Deactivate() override {
        auto scene = AZ::RPI::Scene::GetSceneForEntityId(GetEntityId());
        if (auto fp = scene->GetFeatureProcessor<OutlineFeatureProcessor>()) {
            fp->RemoveOutline(m_handle);
        }
        AZ::TransformNotificationBus::Handler::BusDisconnect();
    }
    void OnTransformChanged(const AZ::Transform&, const AZ::Transform&) override {
        // 通知 FP 更新 worldTm
    }

private:
    AZ::Color m_color = AZ::Colors::Yellow;
    OutlineFeatureProcessor::Handle m_handle;
};
```

### 5) `EditorOutlineComponent`（Editor 端）

```cpp
class EditorOutlineComponent
    : public AzToolsFramework::Components::EditorComponentBase
{
public:
    AZ_EDITOR_COMPONENT(EditorOutlineComponent,
        "{editor-outline-uuid}", AzToolsFramework::Components::EditorComponentBase);
    static void Reflect(AZ::ReflectContext*);

    void BuildGameEntity(AZ::Entity* gameEntity) override {
        auto* runtime = gameEntity->CreateComponent<OutlineComponent>();
        runtime->m_color = m_color;
    }

private:
    AZ::Color m_color = AZ::Colors::Yellow;
};
```

### 6) 注册到 Gem Module 的 `m_descriptors`

```cpp
m_descriptors.insert(m_descriptors.end(), {
    OutlineComponent::CreateDescriptor(),
    OutlineFeatureProcessor::CreateDescriptor(),
});
```

**Scene Activate 时**，`OutlineFeatureProcessor` 应 `EnableFeatureProcessor`：通过一个 Gem-level SystemComponent：

```cpp
void MyGemSystemComponent::OnSceneCreated(AZ::RPI::Scene* scene) {
    scene->EnableFeatureProcessor<OutlineFeatureProcessor>();
}
```

---

## RenderPipeline 资产示例

[Gems/Atom/Feature/Common/Assets/Passes/MainRenderPipeline.azasset](../Gems/Atom/Feature/Common/Assets/Passes/MainRenderPipeline.azasset)（简化）：

```json
{
  "Type": "JsonSerialization",
  "ClassName": "RenderPipelineDescriptor",
  "ClassData": {
    "Name": "MainPipeline",
    "MainViewTag": "MainCamera",
    "RootPassTemplate": "MainPipeline",
    "MaterialPipelineTag": "MainPipeline",
    "AllowModification": true,
    "RenderSettings": {
      "MultisampleState": { "samples": 2 },
      "DepthAttachmentFormat": "D32_FLOAT_S8X24_UINT"
    },
    "DefaultAAMethod": "MSAA"
  }
}
```

### Editor vs Game Pipeline 差异

| | Editor | Game |
|---|---|---|
| 后处理 | 常简化（性能优先） | 全开 |
| Outline / Gizmo pass | ✓ | ✗ |
| 调试 pass（GBuffer 可视化） | ✓ | ✗ |
| MSAA / TAA | 通常关 | 按 quality level |

一般项目提供 `EditorPipeline.azasset` 和 `GamePipeline.azasset` 两份。

### 运行时切换 pipeline

```cpp
AZStd::shared_ptr<AZ::RPI::Scene> scene = ...;
auto newDesc = /* 加载新 descriptor */;
auto newPipeline = AZ::RPI::RenderPipeline::CreateRenderPipeline(newDesc);
scene->RemoveRenderPipeline(oldPipelineId);
scene->AddRenderPipeline(newPipeline);
```

---

## Bootstrap / WindowContext

[Gems/Atom/Bootstrap/](../Gems/Atom/Bootstrap/)：Atom 和 AzFramework Window 的粘合。

```cpp
class BootstrapSystemComponent
    : public AzFramework::WindowNotificationBus::Handler
{
public:
    void Activate() override {
        AzFramework::WindowNotificationBus::Handler::BusConnect(windowHandle);
    }

    void OnWindowCreated(AzFramework::NativeWindowHandle) override {
        // 1) 创建 ViewportContext（SwapChain + Scene）
        // 2) 加载默认 RenderPipeline asset
        // 3) 把 Scene 挂到 ViewportContext
    }

    void OnWindowResized(uint32_t w, uint32_t h) override {
        // SwapChain::Resize
    }
};
```

`ViewportContext` 持有：SwapChain、RenderPipeline、Scene、默认 View。`AzFramework` 的窗口事件传下来。

---

## Debug / 诊断

### r_ 前缀 CVar（部分）

| CVar | 作用 |
|---|---|
| `r_ReloadShader` | 立即重编所有 shader |
| `r_EnablePass "SsaoPass" 0` | 关掉某 pass |
| `r_ShowPasses` | Pass tree UI |
| `r_ProfileGpu` | GPU timing |
| `r_ShowGpuMemory` | GPU 内存统计 |
| `r_DrawListDebug` | DrawList 内容 |

### ImGui 集成

AtomImGuiTools Gem 提供 Pass tree、Feature Processor 列表、Shader Variant 状态等面板。

### GPU 调试

- **RenderDoc**：直接 attach 到 launcher；各平台都可
- **PIX**：DX12 的选项；GPU frame capture
- **NSight**：Vulkan / DX12 GPU trace

Pass 里 `BuildCommandListInternal` 自动带 `AZ_TRACE_RHI("PassName")` marker（便于抓帧对位）。

---

## Asset 链路（渲染相关）

| Source | Builder | Product |
|---|---|---|
| `.azsl` + `.azsli` | ShaderBuilder（`azslc` wrap） | `.azshader` + 反射 |
| `.materialtype` | MaterialTypeBuilder | `.azmaterialtype` |
| `.material` | MaterialBuilder | `.azmaterial` |
| `.materialcanvas` | MaterialCanvasBuilder | `.materialtype` (中间) |
| `.fbx` / `.gltf` | SceneBuilder（Gems/SceneProcessing） | `.azmodel`, `.azactor`, `.azmotion`, ... |
| `.png`/`.tif`/`.exr` | ImageBuilder | `.streamingimage` + `.texpng` / `.dds` |
| `.pass` | PassBuilder | `.pass`（验证 slot 连接） |
| `.azasset` (RenderPipeline) | AnyAssetBuilder | 同上 |

---

## 常见坑（Atom）

1. **Pass 依赖错配**：`.pass` 里 Pass A 读 Pass B 的 output，但兄弟 pass 顺序反了 → FrameGraph compile 失败 / transient resource hash 不对 → 黑屏。
2. **`.azsli` include 顺序**：SRG 定义要在使用前；公共 SRG 放 `.srgi`，每个 pass / shader include。
3. **非渲染线程调 RPI 场景级 API**：多数 RPI 对象要在 Simulate/Render 内访问。别在业务代码里直接 `scene->GetRenderPipeline()` 然后改。
4. **Material Editor 改了看不到**：AP 没跑完；或 material 和 materialtype 版本不匹配；`r_ReloadMaterial` 强刷。
5. **Editor viewport 和 Game viewport pipeline 不同**：改 Editor 的 pass 只影响 Editor，别忘同步 Game pipeline。
6. **结构化 buffer 上限硬编码**：很多 Feature 的 light / decal 数组大小在 `*.hlsli` 里写死。超了 silent truncate，画面不对。Grep 常量查上限。
7. **ShaderOption 变体爆炸**：每个 bool/enum 是一维；N 个 option 造 2^N 变体。用 supervariant 预编译的只能覆盖子集，其它变体请求时后台编译（可能掉帧）。
8. **FeatureProcessor Render 里做重 CPU 工作**：Render 在关键路径，应把计算放 Simulate（工作线程），Render 只填 buffer / DrawPacket。
9. **`ShaderResourceGroup::Compile` 忘调**：setXxx 了但不 compile → GPU 看到旧值。改完一次性 compile 一次即可。
10. **DrawListTag 没注册**：View / Pass 用了某 tag 但没 `DrawListTagRegistry::AcquireTag` → draw 没收到。

继续：[07_asset_pipeline.md](07_asset_pipeline.md) / [11_conventions_and_patterns.md](11_conventions_and_patterns.md)
