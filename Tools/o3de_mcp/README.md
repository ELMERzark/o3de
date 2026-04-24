# o3de_mcp — O3DE Editor 内置 MCP Server

**MVP**：让 AI Agent 通过 MCP（Model Context Protocol）直接操作 O3DE 编辑器 —— 创建 entity、加组件、设属性、换材质、换天空盒 …… 像一个不知疲倦的 TA。

设计文档：[`docs_claud/editor_mcp/`](../../docs_claud/editor_mcp/)

---

## 架构一句话

```
[Agent (Claude Desktop / MAF / Cursor)]
        │  MCP over HTTP/SSE (localhost:24601)
        ▼
[MCP Server (本包，跑在 O3DE Editor 进程内)]
        │  azlmbr.*  (worker 线程 → 主线程 marshal)
        ▼
[O3DE Editor (scene / components / assets)]
```

**单进程架构**：MCP Server 通过 `Editor --runpython boot.py` 加载到 Editor 的 Python VM 里。不再有独立 MCP Server 进程，也没有 TCP Bridge。

---

## 快速上手（Ubuntu 24.04 / Windows 10）

### 1. 装依赖到 Editor 的 Python 环境

⚠ **注意**：必须装到 Editor 用的 Python，不是系统 Python。路径通常：
- Windows: `<repo>/python/runtime/python-3.12-windows-x64/python/python.exe`
- Linux: `<repo>/python/runtime/python-3.12-linux-x64/python/bin/python3`

```bash
# 找到 Editor 用的 python，然后：
<editor-python> -m pip install -r Tools/o3de_mcp/requirements.txt
```

### 2. 配置

```bash
cd Tools/o3de_mcp
cp .env.example .env
# 编辑 .env，填 AUTH_TOKEN（随便一个 hex）、调端口（默认 24601）
```

### 3. 启动 Editor + MCP Server

```bash
# Ubuntu
./build/linux/bin/profile/Editor \
    --runpython Tools/o3de_mcp/boot.py \
    --runpythonargs "--port 24601"
```

```bat
REM Windows
build\windows\bin\profile\Editor.exe ^
    --runpython Tools\o3de_mcp\boot.py ^
    --runpythonargs "--port 24601"
```

看到日志 `MCP Server listening on http://127.0.0.1:24601/sse` 就是起来了。

### 4. 验证：跑 smoke test

```bash
# 另一终端
cd Tools/o3de_mcp
<editor-python> -m tests.smoke_external
```

预期输出：
```
✓ MCP handshake OK
✓ list_tools → 20 tools discovered
✓ entity.create → Entity[...]
✓ component.add Mesh → Comp[...]
...
ALL GREEN.
```

### 5. 接 Claude Desktop（可选）

`~/.claude/claude_desktop_config.json` 加：
```json
{
  "mcpServers": {
    "o3de": {
      "url": "http://127.0.0.1:24601/sse",
      "headers": { "Authorization": "Bearer <your-hex-from-.env>" }
    }
  }
}
```

---

## 目录结构

```
Tools/o3de_mcp/
├── README.md                本文件
├── requirements.txt         依赖
├── .env.example
├── .gitignore
├── boot.py                  <-- Editor --runpython 入口
├── config.py                <-- 端口 / auth / 超时 / safety 开关
├── threading_bridge.py      <-- worker ↔ 主线程 marshal（核心）
├── mcp_server.py            <-- mcp.Server + SSE transport + tool 注册
├── serialize.py             <-- JSON ↔ azlmbr 类型
├── ids.py                   <-- EntityId/AssetId ↔ 字符串
├── errors.py                <-- MCPToolError + traceback
├── handlers/
│   ├── __init__.py
│   ├── entity.py            <-- 6 个 entity 工具
│   ├── component.py         <-- 7 个 component 工具
│   ├── transform.py         <-- 4 个 transform 工具
│   ├── asset.py             <-- 1 个 asset 工具
│   └── query.py             <-- 3 个 query 工具
└── tests/
    ├── __init__.py
    ├── smoke_inproc.py      <-- 从 Editor 内部调 handler 自测
    └── smoke_external.py    <-- 外部 MCP client 连进来自测
```

---

## 已实现的 21 个工具

| 分组 | 工具 |
|---|---|
| entity | create / delete / set_parent / rename / list_children / get_info |
| component | list_types / add / remove / list_on_entity / set_property / get_property / get_property_tree |
| transform | set_translation / set_rotation_euler / set_scale / get |
| asset | find_by_path |
| query | find_by_name / find_by_component_type / scene_snapshot |

`component.set_property` 走 `EditorComponentAPIBus::SetComponentProperty` 通用入口，**一个工具覆盖所有组件的所有属性**。

---

## MVP 已知限制

- [ ] HITL 只有 console `input()` 版；v1 加 Editor 内 UI 弹窗
- [ ] Undo batch 未自动包裹；v1 自动化
- [ ] 认证只校验 Bearer token；v1 加 rate-limit
- [ ] 未测 headless 模式（`--NullRenderer --BatchMode`），想 CI 用要先验证
- [ ] 没有环境 / 材质的高层便捷工具（`environment.set_skybox` 等）；v1 加
- [ ] 没有 `system.exec_python` 逃生舱；v1 加（见 [04_safety_undo_hitl.md §15](../../docs_claud/editor_mcp/04_safety_undo_hitl.md)）

---

## 故障排查

| 症状 | 解法 |
|---|---|
| `ImportError: mcp` | `pip install mcp` 装到 Editor 的 Python；不是系统 Python |
| Editor 启动卡住 | boot.py 的 asyncio 可能阻塞了主线程；见 [01_architecture.md §3](../../docs_claud/editor_mcp/01_architecture.md) 换 tick-pump 方案 |
| `Connection refused` on localhost:24601 | 检查 Editor 日志有没有 `MCP Server listening` 行；端口被占？改 .env |
| `401 Unauthorized` | AUTH_TOKEN 不对；客户端的 `Authorization: Bearer <token>` 要和 .env 匹配 |
| `azlmbr 调用返回空` | 通常 EBus handler 还没注册好；检查 `general.idle_wait_frames(1)` 能否让出让 handler 起来 |
| `component_type_not_found` | 组件类型名要用**显示名**（如 `"Mesh"`），不是 C++ 类名 |

详细失败码 + 重试策略：[03_workflows.md §8](../../docs_claud/editor_mcp/03_workflows.md)。

---

## 下一步

- 跑通 MVP（上面 1-4 步）
- 参考 [05_roadmap.md v1](../../docs_claud/editor_mcp/05_roadmap.md) 加高层工具 + 安全机制
