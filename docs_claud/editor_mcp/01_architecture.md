# 01 · 架构细节：In-Editor MCP Server

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 更新记录：2026-04-24 合并"外部 MCP Server + Editor Bridge"两进程为"跑在 Editor 内的单进程 MCP Server"（去掉 TCP JSON-RPC 层），transport 从 stdio 改为 HTTP/SSE。

---

## 1. 组件边界（最终）

```
┌──────────────────────────────────────────────────────────────────┐
│                          AGENT LAYER                              │
│   Claude Desktop / Cursor / MAF Agent / 任何 MCP Client          │
└───────────────────────────┬──────────────────────────────────────┘
                            │ MCP over HTTP/SSE (localhost:24601)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│          MCP SERVER (Python, 跑在 O3DE Editor 进程内)              │
│                                                                   │
│   启动：Editor.exe --runpython tools/o3de_mcp/boot.py            │
│                                                                   │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  HTTP/SSE Server (asyncio, 在 Python worker 线程)          │  │
│   │   - mcp SDK 注册 @mcp.tool() 装饰器                        │  │
│   │   - 接收 MCP 请求                                           │  │
│   └─────────────────────┬─────────────────────────────────────┘  │
│                         │ 跨线程队列 (asyncio.Queue)               │
│                         ▼                                         │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  Main-Thread Dispatcher (挂 EditorTickBus)                 │  │
│   │   - 每帧 pull queue → 在主线程执行 azlmbr handler           │  │
│   │   - result 塞回 asyncio.Future                              │  │
│   └─────────────────────┬─────────────────────────────────────┘  │
│                         │ 直接 azlmbr.bus.Broadcast / .Event       │
│                         ▼                                         │
│   ┌───────────────────────────────────────────────────────────┐  │
│   │  handlers/                                                  │  │
│   │   entity.py, component.py, transform.py, asset.py, ...     │  │
│   └─────────────────────┬─────────────────────────────────────┘  │
└─────────────────────────┼────────────────────────────────────────┘
                          ▼
         O3DE Editor: entity mgr / component mgr / AP / Atom
```

**没有**独立 MCP Server 进程，**没有** TCP Bridge 跳，**没有** JSON-RPC 中转。MCP 客户端 HTTP 直连编辑器内置的 MCP Server。

---

## 2. 为什么这个形状

| 对比项 | 原方案（双进程 + TCP） | 现方案（单进程 + HTTP） |
|---|---|---|
| 进程数 | 2（MCP Server + Editor+Bridge） | 1（Editor 内置 MCP Server） |
| 跨进程 marshal | JSON-RPC 字符串 2 次 | 无 |
| 工具调用延迟 | ~3-5 ms | <1 ms |
| Claude Desktop 配置 | `command: python -m ...` | `url: http://127.0.0.1:24601` |
| 启动方式 | Editor + MCP Server 分别起 | 只起 Editor |
| MCP Server 崩了 | 独立重启 | 跟编辑器一起挂（但服务端 try/except 后基本不会整崩） |
| 代码量 | Bridge + Server 两套 | 一套 |

关键节省在**部署复杂度**和**代码重复**。

---

## 3. 进程与线程模型

### 3.1 进程

只有 **Editor 进程**。

```bash
# Ubuntu 24.04 / Windows 10 通用
Editor.exe --runpython tools/o3de_mcp/boot.py \
           --runpythonargs "--port 24601 --auth-token <hex>"
```

Claude Desktop `~/.claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "o3de": {
      "url": "http://127.0.0.1:24601/sse",
      "headers": { "Authorization": "Bearer <hex>" }
    }
  }
}
```

### 3.2 线程

Editor 有多个线程，但对我们相关的只有两个：

| 线程 | 跑什么 | 注意 |
|---|---|---|
| **Editor 主线程** | Qt UI + azlmbr EBus 大多数 API | 不能阻塞 |
| **Python worker 线程** | asyncio HTTP server + MCP SDK | 不能直接调 azlmbr |

**azlmbr 不 thread-safe**：大部分 EBus 要求在 Editor 主线程调用。所以架构必须解决"HTTP 请求来自 worker 线程 → 把调用 marshal 回主线程 → 结果送回 worker"的问题。

### 3.3 跨线程 marshal 模式

```
┌────────────────────┐        ┌────────────────────┐
│  Worker thread:    │        │  Main thread:      │
│  HTTP handler      │        │  Tick hook         │
│                    │        │                    │
│  tool_call_fn(…)   │───┐    │   for task in      │
│    future = Fut()  │   │    │   pending_queue:   │
│    q.put(          │   │    │     result =       │
│      (fn,args,fut))│   ▼    │       fn(*args)    │
│    await future    │  ┌──┐  │     task.fut       │
│    return result   │  │  │  │       .set_result( │
│                    │  │Q │  │         result)    │
│                    │  │  │  │                    │
└────────────────────┘  └──┘  └────────────────────┘
                         ↑
                    asyncio.Queue
                    (thread-safe)
```

核心代码骨架：

```python
# tools/o3de_mcp/threading_bridge.py
import asyncio
import azlmbr.legacy.general as general
import azlmbr.tick
from azlmbr.bus import Broadcast, Event

_pending: "asyncio.Queue[tuple]" = asyncio.Queue()
_main_loop_ref = None  # 保存主线程 asyncio event loop（如果有），或 callback 形式

def call_on_main(fn, *args, **kwargs) -> asyncio.Future:
    """从 worker 线程调用，返回在主线程跑完后 resolve 的 future。"""
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending.put_nowait((fn, args, kwargs, fut, loop))
    return fut


def _tick_pump():
    """挂在 Editor tick，每帧尽量清空 pending 队列。"""
    try:
        while True:
            item = _pending.get_nowait()
            fn, args, kwargs, fut, loop = item
            try:
                result = fn(*args, **kwargs)
                loop.call_soon_threadsafe(fut.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(fut.set_exception, e)
    except asyncio.QueueEmpty:
        pass


# boot 时注册：
# azlmbr.tick.TickRequestBus(Broadcast, 'AddTickHandler', _tick_pump)
```

tool handler 用法（`handlers/component.py`）：

```python
async def add_component(entity_id: str, component_type: str):
    def _do():
        # 这里跑在主线程
        eid = _parse_eid(entity_id)
        type_ids = editor.EditorComponentAPIBus(
            Broadcast, 'FindComponentTypeIdsByEntityType',
            [component_type], entity.EntityType().Game)
        outcome = editor.EditorComponentAPIBus(
            Broadcast, 'AddComponentsOfType', eid, type_ids)
        return outcome.GetValue()[0]

    component = await call_on_main(_do)
    return {"component_ref": _stringify_comp_ref(component)}
```

**注意**：如果 O3DE tick 回调不支持我们想要的 "每帧消费队列" 模式，fallback 方案：

1. 用 `EditorTickBus` / `SystemTickBus` 的 `OnTick` 注册一个 Python 函数（通过 `azlmbr.bus.Event` 订阅）
2. 或用 `general.idle_wait_frames(0)` 让 Python 主线程协程让出一帧再 resume

两条路哪条通等 MVP 真跑时验证。

---

## 4. 目录结构（合并后）

```
tools/o3de_mcp/                         ← 只此一处，不再有 server/ 和 bridge/ 两个目录
├── boot.py                              ← Editor --runpython 入口
├── pyproject.toml                       ← 依赖（mcp SDK + aiohttp 或 uvicorn 等）
├── .env.example
├── config.py                            ← 端口、auth token、AUTO_APPROVE 等
├── threading_bridge.py                  ← worker ↔ main 线程 marshal
├── mcp_server.py                        ← mcp.Server 实例 + 注册所有工具
├── serialize.py                         ← JSON ↔ azlmbr 类型
├── ids.py                               ← EntityId/AssetId ↔ 字符串
├── undo.py                              ← EditorCommand undo batch 上下文
├── safety.py                            ← safety_level、HITL、禁操作清单
├── errors.py                            ← 错误码 + traceback 捕获
├── handlers/
│   ├── entity.py
│   ├── component.py
│   ├── transform.py
│   ├── asset.py
│   ├── query.py
│   ├── prefab.py
│   ├── level.py
│   ├── environment.py                   ← 高层封装（组合调用底层 handler）
│   ├── viewport.py
│   ├── history.py
│   └── system.py                        ← 含 exec_python (L3 逃生舱)
├── tools_registry.py                    ← 把 handler 批量注册为 MCP tools
├── tests/
│   ├── smoke_inproc.py                  ← 启 Editor --runpython 跑这个，自测 50 个工具
│   └── fixtures/
│       └── assets/…
└── README.md
```

---

## 5. MCP 工具注册骨架

```python
# mcp_server.py
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from . import handlers

app = Server("o3de-editor")

@app.tool(
    name="entity.create",
    description="Create a new entity, optionally with a parent and initial position.",
)
async def entity_create(
    parent: str | None = None,
    name: str = "",
    position: dict | None = None,
) -> dict:
    return await handlers.entity.create(parent=parent, name=name, position=position)

# ... 其余 ~25 个工具同款注册

async def serve(port: int):
    transport = SseServerTransport("/messages")
    # aiohttp / starlette 挂载 /sse GET + /messages POST
    ...
```

---

## 6. 关键 azlmbr snippets（和之前一致，放在 handlers/ 里）

### 6.1 create_entity

```python
# handlers/entity.py
import azlmbr.bus as bus
import azlmbr.editor as editor
import azlmbr.entity as entity
from ..threading_bridge import call_on_main
from ..ids import parse_eid, stringify_eid

async def create(parent: str | None, name: str, position: dict | None):
    def _do():
        pid = parse_eid(parent) if parent else entity.EntityId()
        new_id = editor.ToolsApplicationRequestBus(
            bus.Broadcast, 'CreateNewEntity', pid)
        if name:
            editor.EditorEntityAPIBus(bus.Event, 'SetName', new_id, name)
        return new_id
    eid = await call_on_main(_do)
    if position:
        await _set_translation(eid, position)
    return {"entity_id": stringify_eid(eid), "name": name}
```

参考：[AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_EntityCRUDCommands_Works.py:16-36](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_EntityCRUDCommands_Works.py#L16)

### 6.2 add_component

```python
async def add(entity_id: str, component_type: str):
    def _do():
        eid = parse_eid(entity_id)
        type_ids = editor.EditorComponentAPIBus(
            bus.Broadcast, 'FindComponentTypeIdsByEntityType',
            [component_type], entity.EntityType().Game)
        if not type_ids:
            raise ValueError(f"Component type not found: {component_type}")
        outcome = editor.EditorComponentAPIBus(
            bus.Broadcast, 'AddComponentsOfType', eid, type_ids)
        if not outcome.IsSuccess():
            raise RuntimeError("AddComponentsOfType failed")
        return outcome.GetValue()[0]
    component = await call_on_main(_do)
    return {"component_ref": stringify_comp_ref(component)}
```

参考：[Editor_ComponentCommands_Works.py:45-69](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_ComponentCommands_Works.py#L45)

### 6.3 set_component_property（最核心的通用写入）

```python
async def set_property(component_ref: str, property_path: str, value: dict):
    def _do():
        component = parse_comp_ref(component_ref)
        py_value = deserialize(value)
        editor.EditorComponentAPIBus(
            bus.Broadcast, 'SetComponentProperty',
            component, property_path, py_value)
        # 回读 verify
        getter = editor.EditorComponentAPIBus(
            bus.Broadcast, 'GetComponentProperty', component, property_path)
        if not getter.IsSuccess():
            raise RuntimeError(f"Verify failed: {property_path}")
        return getter.GetValue()
    new_value = await call_on_main(_do)
    return {"value": serialize(new_value)}
```

参考：[Editor_ComponentPropertyCommands_Works.py:50-112](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_ComponentPropertyCommands_Works.py#L50)

### 6.4 find_asset

```python
# handlers/asset.py
import azlmbr.asset as asset
import azlmbr.math as math

async def find_by_path(path: str):
    def _do():
        aid = asset.AssetCatalogRequestBus(
            bus.Broadcast, 'GetAssetIdByPath', path, math.Uuid(), False)
        if not aid.IsValid():
            raise ValueError(f"Asset not found: {path}")
        return aid
    aid = await call_on_main(_do)
    return {"asset_id": stringify_aid(aid)}
```

参考：[Editor_ComponentAssetCommands_Works.py:86-122](../../AutomatedTesting/Gem/PythonTests/EditorPythonBindings/tests/Editor_ComponentAssetCommands_Works.py#L86)

### 6.5 Undo batch 上下文管理器

```python
# undo.py
from contextlib import contextmanager
import azlmbr.bus as bus
import azlmbr.editor as editor

@contextmanager
def undo_batch(label: str):
    """仅可在主线程使用。"""
    editor.ToolsApplicationRequestBus(bus.Broadcast, 'BeginUndoBatch', label)
    try:
        yield
    finally:
        editor.ToolsApplicationRequestBus(bus.Broadcast, 'EndUndoBatch')
```

handler 用法：handler 内部从 worker 发一个"复合任务"到主线程，整批在同一个 `_do` 里用 `with undo_batch(...)` 包裹。

---

## 7. 数据 marshal（JSON ↔ azlmbr）

统一在 `serialize.py` / `ids.py`：

| JSON | Python (azlmbr) | 说明 |
|---|---|---|
| `"Entity[0xABC]"` | `azlmbr.entity.EntityId(0xABC)` | EntityId 用字符串表示 |
| `"Asset[{uuid}:subid]"` | `azlmbr.asset.AssetId(uuid, subid)` | AssetId 同理 |
| `{"__type":"Vector3","x":1,"y":2,"z":3}` | `azlmbr.math.Vector3(1,2,3)` | 带 `__type` tag 消歧义 |
| `{"__type":"Color","r":0,"g":1,"b":0,"a":1}` | `azlmbr.math.Color(0,1,0,1)` | |
| `{"__type":"Quaternion","x":0,"y":0,"z":0,"w":1}` | `azlmbr.math.Quaternion` | |
| `"550e8400-e29b-..."` | `azlmbr.math.Uuid` | 字符串直接解析 |
| `null` | invalid EntityId | 特例 |

**所有 handler 的入参/出参必过 marshal**。

---

## 8. 错误处理

### 8.1 可预期错误（返回结构化 MCP error）

MCP SDK 的 `@tool` 约定是抛异常 → SDK 转成错误回客户端。我们自己定义一层：

```python
# errors.py
class MCPToolError(Exception):
    def __init__(self, code: str, message: str, **data):
        super().__init__(message)
        self.code = code
        self.data = data

# handler 里
if not aid.IsValid():
    raise MCPToolError("asset_not_found", f"No asset at path: {path}", path=path)
```

常见 code：
- `entity_not_found`
- `component_type_not_found`
- `asset_not_found`
- `property_path_invalid`
- `permission_denied`（HITL 拒绝 / 禁操作清单命中）

### 8.2 不可预期崩溃（Python 异常）

SDK 会把 traceback 一起塞进 MCP response。Agent 看到后能自愈（`AttributeError` 通常意味着调了不存在 API）。

### 8.3 主线程 marshal 异常

`call_on_main(fn)` 里 fn 抛了 → future.set_exception() → worker 线程 await 重新抛 → handler 里传播 → MCP SDK 转换。传播链对用户透明。

---

## 9. 关键决策记录（ADR）

### ADR-001 ~~MCP Server 独立进程 + Editor Bridge~~ → **MCP Server 跑在 Editor 内**

**决定**：单进程架构，MCP Server 作为 Python 脚本通过 `--runpython` 加载进 Editor
**理由**：
- 少一个 TCP 层，延迟和代码量都降
- Claude Desktop 的 MCP 客户端原生支持 HTTP/SSE
- 两层架构带来的"MCP Server 独立重启"收益很弱——Server 只要稳，就不需要频繁重启
- 线程 marshal 问题在哪种架构里都躲不掉（azlmbr 只能主线程），不如直接面对

### ADR-002 ~~Bridge 单并发~~ → **工具调用顺序执行 + 跨线程队列**

**决定**：HTTP 层可多 client 并发，但所有 azlmbr 调用通过单一主线程队列**顺序执行**
**理由**：azlmbr EBus 不 thread-safe；并发会死锁或状态错乱。顺序执行对 <100 次/turn 的工具调用量完全够用。

### ADR-003 ~~JSON-RPC over TCP~~ → **MCP over HTTP/SSE**

**决定**：用官方 mcp SDK 的 SSE transport
**理由**：
- 标准 MCP transport，客户端兼容性最好
- aiohttp/starlette 写起来简单
- 多 client 同时连没问题（比如一个终端 Agent + 一个 Claude Desktop）

### ADR-004 EntityId 用字符串

**决定**：`"Entity[0x12345678]"` 字符串形式
**理由**：schema 里一眼看出语义；防 agent 和普通 int 混淆；来源自 `EntityId.ToString()` 自然格式

### ADR-005 所有 destructive 默认 HITL

见 [04_safety_undo_hitl.md](04_safety_undo_hitl.md)

### ADR-006 **结构化 tool call 为主，`exec_python` 为 L3 逃生舱**

**决定**：Agent 的主要交互形式是结构化 MCP tool（已定义类型的函数调用）；保留一个 `system.exec_python(code, label)` 工具，默认关闭（需同时开启 `AUTO_APPROVE=true` 且 `ALLOW_EXEC_PYTHON=true`），每次调用都 HITL
**理由**：见 [04_safety_undo_hitl.md §15](04_safety_undo_hitl.md#L300+)（新增章节）

---

## 10. 与现有 [`tools/agents/`](../../tools/agents/) 骨架的集成

原来的 `fs_tools` 改文件不变。新加一个 `mcp_tools.py`，包装 MCP client：

```python
# tools/agents/mcp_tools.py
from mcp import ClientSession
from mcp.client.sse import sse_client

class EditorMCP:
    """从 MAF agent 侧连到 Editor 内的 MCP Server。"""
    def __init__(self, url: str = "http://127.0.0.1:24601/sse"):
        self.url = url
        self._client: ClientSession | None = None

    async def connect(self):
        transport = sse_client(self.url)
        self._read, self._write = await transport.__aenter__()
        self._client = ClientSession(self._read, self._write)
        await self._client.initialize()

    async def call(self, tool: str, **params) -> dict:
        result = await self._client.call_tool(tool, params)
        return result.content

    async def close(self):
        await self._client.close()
```

[`tools/agents/workflow.py`](../../tools/agents/workflow.py) 新增一个 Scene Specialist 分支（同 [03_workflows.md](03_workflows.md) §10），只有 plan 里有 `scene_ops` 时才起 MCP 连接。

---

## 11. 进程生命周期与故障恢复

| 事件 | 后果 | 处理 |
|---|---|---|
| Editor 启动 → boot.py 跑 | HTTP server 监听 24601 | 正常 |
| 单次 MCP 工具调用 Python 抛异常 | handler 内 try/except 捕获，返回 MCP error | 继续服务下一个请求 |
| azlmbr 调用崩 Editor | Editor 进程直接没 | MCP client 断开，Agent 收到 connection reset |
| 用户手动关 Editor | HTTP server 随进程死 | 同上 |
| 端口 24601 被占 | boot.py 启动失败 | 改 port 或 kill 占用者；boot.py 在 stdout 明确报错 |
| Main-thread tick 停（Editor 卡死） | pending_queue 越堆越高 | Worker 侧工具调用超时（默认 30s）→ 返回 `timeout` error |

---

## 12. 关联文档

- [00_overview.md](00_overview.md) —— 为什么做这个
- [02_tool_catalog.md](02_tool_catalog.md) —— 所有 MCP 工具的签名
- [03_workflows.md](03_workflows.md) —— Agent 怎么用
- [04_safety_undo_hitl.md](04_safety_undo_hitl.md) —— 安全模型、`exec_python` 逃生舱规则
- [05_roadmap.md](05_roadmap.md) —— 分阶段交付
- [13_ai_context_guide.md](../13_ai_context_guide.md) —— Agent 与仓库交互总则（本文档是它的 Editor 侧扩展）
