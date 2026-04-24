# 18 · DCC 工具集成（Blender / Maya / Houdini / 3ds Max）

> 基于 O3DE `development` @ `aa2f89cb7e` (2026-04-24) 采集。版本漂移说明见 [00_index.md](00_index.md#文档元数据重要)。

美术 → 引擎的内容管线是项目最容易踩坑的地方。本章讲 O3DE 怎么和外部 DCC 工具协作。

---

## 三条独立的路

O3DE 资产管线里，美术内容进引擎有三条互相独立的路径：

```
路径 A（推荐 / 通用）：                        路径 B（深度集成）：
  DCC 里建模 / 动画 / 材质                       DCC 里跑 Python 脚本
          ↓ 导出 FBX / GLTF                           ↓ 直接操作 O3DE
  放进项目 Assets/ 目录                          （DccScriptingInterface）
          ↓ AssetProcessor 侦测                       ↓
  SceneBuilder 解析                              自动触发资产转换
          ↓
  .azmodel / .azactor / .azmotion               路径 C（素材库）：
                                                  Substance / Marmoset / ArmorPaint 等
                                                  出贴图 / 材质资产，走 A 路径
```

**大多数项目用路径 A**。路径 B 是有复杂自动化需求时的选项。本章覆盖三条。

---

## 路径 A：FBX / GLTF 通用流水线（最常用）

### DCC 工具里的导出设置

**Blender**:
- File → Export → FBX
- 选项：
  - `Scale: 1.0`（O3DE 默认米制）
  - `Forward: -Z Forward`, `Up: Y Up`（O3DE 坐标系）
  - `Apply Unit Transform: on`
  - `Use Space Transform: on`
  - `Armature → Only Deform Bones: on`（避免控制骨进引擎）
  - `Bake Animation: on`（动画项目）

**Maya**:
- File → Send to Unreal / Export Selection → FBX
- FBX 选项面板：
  - Units: Centimeters（Maya 默认）或项目统一
  - Axis Conversion: Y-up
  - Animation: Baked Animation
  - Embedded Media: off（贴图单独管）

**3ds Max**:
- File → Export → FBX
- 同上，Y-up，米制

**共同要点**：
- **三角化**：Quad 入引擎会被再次三角化，可能和美术预期不一样；导出前先 triangulate 可控结果。
- **UV**：至少一套 UV（UV0 用于纹理；UV1 用于 lightmap 若需要）。
- **Tangent Space**：让 DCC 导出切线向量（否则引擎会重算，可能和美术的法线贴图不对）。
- **Scale**：别带 non-uniform scale；Apply/Freeze Transform 再导出。

### 放进项目

```
<Project>/Assets/
├── art/
│   ├── character/
│   │   ├── hero.fbx             ← 源文件
│   │   ├── hero.fbx.assetinfo   ← Scene Manifest（可选，AP 会用默认）
│   │   └── textures/
│   │       ├── hero_diffuse.png
│   │       └── hero_normal.png
│   └── level/
│       └── ...
```

AssetProcessor 自动侦测 `.fbx` → 跑 SceneBuilder → 产 `.azmodel` 等。

### Scene Manifest `.fbx.assetinfo`

和 FBX 同名 + `.assetinfo` 后缀的 JSON，控制导出规则。最小示例：

```json
{
    "values": [
        {
            "$type": "{07B356B7-3635-40B5-878A-FAC4EFD5AD86} MeshGroup",
            "id": "{MESH-GROUP-UUID}",
            "name": "Hero",
            "nodeSelectionList": {
                "selectedNodes": ["RootNode.Character"],
                "unselectedNodes": []
            },
            "rules": {
                "rules": [
                    {
                        "$type": "CoordinateSystemRule",
                        "useAdvancedData": false,
                        "originNodeName": "",
                        "translation": [0.0, 0.0, 0.0],
                        "rotation": [0.0, 0.0, 0.0, 1.0],
                        "scale": 1.0
                    },
                    {
                        "$type": "MaterialRule",
                        "includeMaterials": true,
                        "removeMaterials": false,
                        "updateMaterials": false
                    }
                ]
            }
        }
    ]
}
```

**怎么生成**：
- Editor 里打开 `.fbx` → 自动弹 Scene Settings 编辑器 → 配完保存 = `.fbx.assetinfo` 落盘
- 或手写 JSON
- 或通过 Python `azlmbr.scene` API 批量生成

**一个 FBX 可以产多种产物**（用不同 Group）：
- `MeshGroup` → `.azmodel`（静态网格）
- `ActorGroup` → `.azactor`（角色骨骼）
- `MotionGroup` → `.azmotion`（动画片段）
- `SkeletonGroup` → `.azskeleton`
- `PhysicsMeshGroup` → 给物理用的简化碰撞 mesh

### 材质 / 贴图流水

O3DE 不直接用 FBX 内嵌材质。FBX 里的 material 节点只是"名字标记"，引擎根据这些名字在 `.material` 文件里找真正的材质定义。

推荐流程：

1. DCC 里材质**只起名字**（例如 `M_Hero_Body`）。
2. 贴图 `.png/.tif/.exr` 独立放 `textures/`。
3. 在 Editor 里用 **Material Editor** 创建 `<name>.material`（基于 StandardPBR）：
   - Base Color Map → 指向 `hero_diffuse.png`
   - Normal Map → `hero_normal.png`
   - Metallic/Roughness → ORM 贴图
4. Prefab 里的 `MeshComponent` 的 "Material override" 指 `.material` 文件。

### 贴图命名约定（建议）

| 后缀 | 贴图类型 | 导入设置 |
|---|---|---|
| `_BaseColor` / `_Diffuse` / `_D` | 反照率 | sRGB |
| `_Normal` / `_N` | 法线 | Linear / BC5_UNORM |
| `_ORM` | Occlusion/Roughness/Metallic packed | Linear |
| `_Emissive` / `_E` | 自发光 | sRGB |
| `_Mask` / `_A` | 遮罩 / 通道数据 | Linear |
| `_Height` / `_HM` | 视差 | Linear |

后缀让 ImageProcessingAtom Gem 选合适的压缩格式（BC1/BC5/BC7）。

### FBX 更新循环

- 美术改 `.fbx` → 保存 → AP 自动重编 → Editor 里打开场景**自动刷新**（asset hot reload）
- 不用关闭 Editor
- 如果改了 Scene Manifest（加了新 Group 等），Editor 可能要重新打开 Prefab

---

## 路径 B：DccScriptingInterface (DCCsi)

O3DE 有一个官方 Gem 专门做 DCC 深度集成：**[Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/](../Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/)**，简称 **DCCsi**。

### DCCsi 提供什么

一个 Python 框架，把 DCC 端的 Python 和 O3DE 的 Python 连起来：

- 标准化环境（统一 Python 版本、依赖管理）
- 工具启动器（从 Editor 打开 Maya/Blender 并预装 addon）
- Shared Python 库 `azpy`（几何 / 颜色 / 文件操作）
- 自动化模板（批量导出、命名规范检查、资产验证）

### 支持的 DCC

`Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/Tools/DCC/` 下每个目录是一个 DCC 集成：

```
Tools/DCC/
├── Blender/        ← 最活跃
├── Maya/
├── 3dsMax/
├── Houdini/
├── Substance/      ← Substance Painter / Designer
├── Marmoset/       ← Marmoset Toolbag
├── ArmorPaint/
```

### 初次配置（运行 foundation.py）

DCCsi 需要装自己的 Python 依赖。启用 Gem 后：

```bash
cd Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface
python.cmd foundation.py
```

这会：
1. 在 Gem 下建 `3rdParty/`
2. pip install 所需 Python 包（pyside2、pathlib、attrs 等）
3. 生成 `settings.local.json`（本地路径配置）

### Blender 集成详解

最常用，资料最全。目录 `Tools/DCC/Blender/`：

```
Blender/
├── bootstrap.py           启动脚本（Blender 启动时跑）
├── addons/                打包给 Blender 的 addon
│   └── SceneExporter      → Blender 面板里出现 "O3DE Scene Exporter"
├── Scripts/
│   └── <辅助脚本>
├── config.py              配置
├── constants.py
├── discovery.py           自动发现 Blender 安装位置
├── settings.json          默认设置
├── settings.local.json.example   用户改这个
└── start.py               从 O3DE Editor 启动 Blender 的入口
```

### 启动 Blender 从 O3DE

Editor 菜单（DCCsi 启用后多出几个入口）或 Python console：

```python
# Editor Python Console 里
import Tools.DCC.Blender.start as blender_start
blender_start.launch()
```

Blender 启动时会：
- 把 DCCsi 的路径加到 `sys.path`
- 加载 addons 目录下的 addon
- 环境变量指向当前 O3DE 项目

### Blender 里的一键导出流程

安装 O3DE Scene Exporter addon 后：

1. Blender 菜单：**O3DE → Export Selected**
2. 选目标 Prefab / 路径
3. Addon：
   - 自动把选中物体导出为 `.fbx`
   - 生成对应 `.fbx.assetinfo`（根据材质命名等自动填）
   - 可选：**同时在 O3DE 里建 Prefab** 引用这个新 FBX

### Maya 集成要点

Maya 集成比 Blender 历史悠久但维护较少。目录：`Tools/DCC/Maya/`。

- `config.py` 读 Maya 版本、MAYA_APP_DIR 等
- `Scripts/` 下有 MEL + Python 混合脚本
- `Shaders/` 有 Maya Hypershade 的材质模板（尽量像 Atom 的 PBR 预览）
- `Env_Dev.bat.example` 复制改名 → 配环境变量启动

运行 Maya：

```bash
# Windows，设好 Env_Dev.bat 里的 MAYA_APP_DIR 和 O3DE 路径后
Env_Dev.bat
```

Maya 里可以：
- 用 Python Console：`import azpy; azpy.export_scene(...)`
- 装 shelf 工具：一键"发送到 O3DE"

### DCC 端 Python 和 O3DE Python 的关系

**重要事实**：
- Blender / Maya **都有自己的 Python 解释器**（不同版本，不可互换）
- O3DE Editor 有自己的 Python 解释器（`python/runtime/`）
- DCCsi 不是让 DCC 用 O3DE 的 Python；**是两个独立 Python 之间的协议和共享工具库**

通信方式：
- **文件系统**（最简单）：DCC 写 `.fbx` + `.json` 配置；O3DE 的 AP 侦测
- **Socket**（高级）：DCCsi 有 `start_service.py`，启动一个 tcp 服务让 DCC 端发消息触发 O3DE 操作
- **命令行**：DCC 通过 subprocess 调 `o3de.bat <command>`

---

## 路径 C：Substance 贴图 / Marmoset 烘焙

这条路径**不用 DCCsi**，纯粹是"DCC 出贴图 → 放 textures/ → AP 自动编"。

### Substance Painter

1. SP 里烘焙 + 绘画 → 导出 PBR Textures
2. 导出预设选 "O3DE Atom PBR"（或自建）
3. 贴图按命名约定放到 `Assets/textures/`
4. Material Editor 里新建 `.material`，各 slot 指这些贴图

DCCsi 里的 `Tools/DCC/Substance/` 有模板导出预设。

### Marmoset Toolbag

用途：
- 法线烘焙（高模 → 低模）
- Render preview 对比 Atom（Atom Material Preview 工具也能做，但 Marmoset 更成熟）

### ArmorPaint

免费开源的 SP 替代。DCCsi 下也有集成模板。

---

## Scene Pipeline 扩展（自定义 Processor）

[Code/Tools/SceneAPI/](../Code/Tools/SceneAPI/) 是引擎端的 Scene 处理框架；[Gems/SceneProcessing/](../Gems/SceneProcessing/) 注册默认 processor。

需要给 FBX 导入加自定义规则（例如"自动为名字含 `_col` 的 mesh 生成 PhysX collider"）时：

1. 新建一个 Gem（或挂到已有 Editor-only Gem）。
2. 派生 `SceneAPI::SceneCore::Processor`：
   ```cpp
   class MyProcessor : public SceneCore::LoadingComponent
   {
       AZ::SceneAPI::Events::ProcessingResult OnEnabled(
           SceneCore::ProcessingEventContext& ctx);
   };
   ```
3. 在 SystemComponent::Activate 注册。
4. 在 `.fbx.assetinfo` 里可以添加自定义 rule 类型。

参考：[Gems/SceneLoggingExample/](../Gems/SceneLoggingExample/) 就是一个最小自定义 Processor 示例。

---

## 坐标系 / 单位 / 命名约定

### 坐标系

O3DE 默认：**右手，Z up**（和 Maya 默认 Y up 不同）。

- Maya → O3DE：FBX 导出时 `Up Axis: Y` 或 `Z`，Axis Conversion 让 FBX SDK 转换。
- Blender → O3DE：Blender 默认 Z up 匹配；导出时 Forward `-Y`, Up `Z`。
- Unity → O3DE：Unity Y up；需要转换。

### 单位

O3DE 内部用**米**。

- DCC 里的 1 单位 = 1 米（推荐所有人统一）。
- Maya 默认 cm，可以在 Preferences 改或 export 时设 Scale factor。
- Blender 默认 m（天然匹配）。

### 命名规范（建议）

```
SM_<name>      static mesh       (StaticMesh → .azmodel)
SK_<name>      skeletal mesh     (Skeleton → .azskeleton)
ANIM_<name>    animation         (.azmotion)
T_<name>_D     texture diffuse
T_<name>_N     texture normal
M_<name>       material          (.material)
MI_<name>      material instance
FX_<name>      particle / vfx
P_<name>       prefab
```

大项目会在 DCCsi addon 里集成命名检查器（导出前跑 lint）。

---

## 典型动作游戏资产流水（端到端）

```
1) 建模（Maya/Blender）
   └─ SK_Hero.fbx（含 skeleton + skinned mesh）
   └─ 顺带出 SM_Hero_Weapon.fbx（武器静态）

2) UV + 烘焙 AO（Blender / Marmoset）
   └─ 产 low-poly FBX + AO 贴图

3) 材质（Substance Painter）
   └─ 出 6 张贴图：BaseColor / Normal / ORM / Emissive / Mask / Height

4) 导出到项目
   Assets/art/hero/
     SK_Hero.fbx
     SK_Hero.fbx.assetinfo   (一键导出时 addon 生成)
     textures/
       T_Hero_Body_D.png
       T_Hero_Body_N.png
       T_Hero_Body_ORM.png

5) AP 自动编译
   └─ SK_Hero.azactor + SK_Hero.azskeleton + T_*.streamingimage

6) Editor 手动步骤
   ├─ Material Editor: 新建 M_Hero_Body.material (StandardPBR)
   │   └─ 各 slot 指向贴图
   ├─ 拖 .azactor 到视口 → 生成 Entity with ActorComponent
   ├─ Material Override: 指向 M_Hero_Body.material
   └─ 保存为 Prefab: P_Hero.prefab

7) 动画
   ANIM_Hero_Idle.fbx → ActorGroup/MotionGroup → .azmotion
   └─ AnimGraphComponent 里引用

8) 联动检查
   在 level 里拖 P_Hero.prefab → 运行 → 看效果
```

这整套在项目配好 DCCsi + 约定后，第 4-7 步美术一人可完成，不用程序介入。

---

## 常见坑 / 踩过的问题

1. **Maya cm / Blender m / 项目 m 混用** → 模型变大/变小 100 倍。统一米制 + FBX 导出 Apply Unit Transform。
2. **导出带 scale 没 freeze** → Transform 进引擎后子 Entity 变形。Freeze Transform / Apply Scale。
3. **Y-up / Z-up 搞错** → 模型旋转 90°。FBX 里正确设 Axis Conversion。
4. **FBX 嵌入贴图** → 贴图被 AP 当一般资产处理但路径嵌在 FBX 里，很难引用。**关闭 Embedded Media**。
5. **FBX 里材质名字改了** → `.material` 里的 slot assignment 找不到。用**命名稳定** + Material override in Prefab。
6. **Normal Map 方向约定**（DirectX vs OpenGL）→ 光照看起来"里外翻"。Atom 用 OpenGL-style Y+；从 Substance 导出时选对应预设。
7. **动画导出包含 rest pose frame** → 首帧抖动。导出前确认起始帧是第 1 帧（不是第 0 帧或 pose 帧）。
8. **骨骼数量超 shader 上限**（StandardPBR 默认 255 骨）→ 部分骨丢失；拆 mesh 或改 shader 常量。
9. **FBX 版本过新 / 过旧**：FBX SDK 更新时兼容性断裂。Maya 2022 → FBX 2020 binary 一般稳妥。
10. **AP 报 "Failed to import scene"**：打开 Editor 的 Scene Settings 手动看错误；通常是 mesh / material 结构异常（孤立顶点、NaN UV 等）。

---

## Editor 内对 DCC 资产的操作（Python）

批量处理 FBX 时，在 Editor Python Console：

```python
import azlmbr.scene as scene
import azlmbr.bus as bus

# 列举某目录下所有 FBX
import os
for root, dirs, files in os.walk('path/to/art'):
    for f in files:
        if f.endswith('.fbx'):
            fbx_path = os.path.join(root, f)
            # 读取/修改 SceneManifest（.fbx.assetinfo）
            manifest = scene.SceneManifestRequestsBus(
                bus.Broadcast, 'LoadManifest', fbx_path + '.assetinfo')
            # 修改 group settings...
            scene.SceneManifestRequestsBus(
                bus.Broadcast, 'SaveManifest', manifest, fbx_path + '.assetinfo')
```

---

## 相关 Gem / 工具

| 工具 | 位置 / Gem |
|---|---|
| DccScriptingInterface (DCCsi) | `Gems/AtomLyIntegration/TechnicalArt/DccScriptingInterface/` |
| SceneProcessing（默认 Processor） | `Gems/SceneProcessing/` |
| SceneAPI 源码 | `Code/Tools/SceneAPI/` |
| Material Editor | `Gems/Atom/Tools/MaterialEditor/` |
| Material Canvas | `Gems/Atom/Tools/MaterialCanvas/` |
| ImageProcessingAtom（贴图编译） | `Gems/Atom/Asset/ImageProcessingAtom/` |
| SceneLoggingExample（学自定义 Processor） | `Gems/SceneLoggingExample/` |

继续：[19_new_project_checklist.md](19_new_project_checklist.md)、[07_asset_pipeline.md](07_asset_pipeline.md)。
