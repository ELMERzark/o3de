# 04 · 安全模型：Undo / HITL / 禁操作

> 编写日期：2026-04-24
> 基于 O3DE development @ aa2f89cb7e
> 让 Agent 有能力 ≠ 让 Agent 无节制。这份文档是 MCP Server (Editor 内) / Agent 两层的安全契约。

---

## 1. 威胁模型

| 威胁 | 实例 | 严重度 |
|---|---|---|
| Agent 批量误删 | `entity.delete_all_with_component("Mesh")` | ⛔ 灾难 |
| Agent 覆写场景 | `level.save` 到错 path，覆盖生产关卡 | ⛔ 灾难 |
| Agent 跑死循环 | 无限加 entity → Editor OOM | ⚠️ 高 |
| Agent 误改资产路径 | set_property 写错 AssetId → missing 红框 | ⚠️ 中 |
| Agent 留脏状态 | Editor 标 dirty 但没 save；用户下次打开一堆意外改动 | ⚠️ 中 |
| Agent 污染 prefab | 在同一个 prefab 里层层嵌套 override | ⚠️ 中 |
| MCP Server 被别的进程连上 | 本机其它程序连 24601 port | ⚠️ 中 |
| Agent 调系统级工具 | run_console_command("map newlevel") | ⚠️ 低（已白名单） |

每条都有对应护栏（下文）。

---

## 2. 四级 HITL 策略

不同 MCP 工具按危险度分四级：

| 级 | 示例工具 | 默认行为 | `AUTO_APPROVE` 下 |
|---|---|---|---|
| **L0 安全** | `query.*`, `asset.find_by_path`, `component.get_property_tree` | 直接执行 | 执行 |
| **L1 非破坏写** | `component.set_property`, `transform.set_*` | 直接执行 + 记录 | 执行 |
| **L2 创建/结构性** | `entity.create`, `component.add`, `prefab.instantiate` | batch 聚合后问一次 | 执行 |
| **L3 破坏性** | `entity.delete`, `level.save`, `level.open`, `prefab.delete_instance`, `system.run_editor_console_command` | **强制一问一答** | ⚠️ 执行（危险） |

**实现**：每个 MCP 工具定义里加 `safety_level` 字段：

```python
@mcp.tool(safety_level="L3")
async def entity_delete(entity_id: str, cascade: bool = True):
    ...
```

MCP Server 或上层 Agent client 读 level 决定是否问用户。

### 2.1 L3 的"强制一问一答"实现

哪怕 `AUTO_APPROVE=true`，L3 操作也应在 config 里显式开 `ALLOW_DESTRUCTIVE=true` 才放行。两道开关，不会误触。

```python
# 例：
if tool.safety_level == "L3":
    if not (config.AUTO_APPROVE and config.ALLOW_DESTRUCTIVE):
        if not _ask_user(f"允许 destructive 操作 {tool.name}?"):
            return {"ok": False, "error": "user_denied"}
```

---

## 3. Undo Batch 规则

### 3.1 每个 op 一个 batch（标配）

Scene Specialist 的 handler 默认 `history.begin_batch(label)` 开头 / `end_batch` 收尾。
**batch 失败时自动 `history.undo` 整单回滚**。

### 3.2 Agent turn 一个 batch（可选）

Planner 的整个 plan 可以包在**一个大 batch** 里：

```python
mcp.call("history.begin_batch", {"label":f"AI turn: {plan['task_summary']}"})
try:
    for op in plan["scene_ops"]:
        execute_op(op)   # 内部是子 batch，嵌套 OK
    mcp.call("history.end_batch", {})
except:
    mcp.call("history.end_batch", {})
    raise
```

用户一键 Undo = 整个 AI turn 消失。

### 3.3 批次标签约定

```
AI turn: <task_summary>             # 最外层
  AI op: set_skybox — studio_hdri   # 单 op
    component.set_property ...      # MCP 子调用（自动包的）
```

Editor 的 Undo 菜单里用户看到的是**最外层**；展开能看每层，调试友好。

### 3.4 不能 undo 的操作

`level.save` 落盘不可逆。所以 save 前 **一定** `end_batch` 把所有未保存改动聚拢，让 Editor 知道这是一个原子点，再 save。**save 本身不开 undo batch**。

---

## 4. 禁操作清单（handler 层硬拒）

即便 Agent 生成的参数通过了 tool schema 校验，handler 也应在执行前过一层禁操作清单。白名单不是万能，关键路径要拉黑：

```python
# tools/o3de_mcp/safety.py
DENIED_ENTITY_NAMES = {
    # 拒绝删除 Level 根
    "__Level_Root__",
}

DENIED_CONSOLE_COMMANDS_PATTERNS = [
    r"^map\s+",          # 换 level 走 level.open
    r"^quit",            # 不许 agent 退编辑器
    r"^exit",
    r"^r_fullscreen",    # 改显示模式要用户同意
    r"^sys_",            # 系统类全拦
]

DENIED_ASSET_WRITES = [
    # 不许修改 engine-provided 资产（Agent 只能用，不能改 engine 目录里的）
    "engineassets/",
    "editor/",           # editor 图标 / 预设不该改
]

def check_denied(method: str, params: dict):
    if method == "entity.delete":
        # 查 name, 查父链里有没有 Level 根
        ...
    if method == "system.run_editor_console_command":
        cmd = params.get("command","")
        for pat in DENIED_CONSOLE_COMMANDS_PATTERNS:
            if re.match(pat, cmd):
                raise PermissionError(f"denied console command: {cmd}")
    ...
```

**handler 拒绝 → 抛 `MCPToolError("permission_denied", ...)` → MCP SDK 转成 error 回客户端，Agent 看得到明确原因。**

---

## 5. 资产 write 路径保护

参考 [`tools/agents/safety.py`](../../tools/agents/safety.py) 的 FORBIDDEN_PATHS 已经覆盖 `.git/` / `build/` / `Cache/` / `3rdParty/`。MCP 工具**不直接写磁盘文件**（fs_write 类操作走 `tools/agents/fs_tools.py`），所以这层 OK。

但 **`prefab.save` / `level.save`** 会落盘。处理：

- prefab.save 的目标 path 必须在 Project 目录下（不是 `Gems/` 或引擎目录）
- level.save 不许 save-as 到非 Project 目录
- **save 前**强制 diff（或至少 dirty check）给用户确认

---

## 6. 并发 / 锁

### 6.1 多 client 可同时连

HTTP/SSE transport 允许多个 MCP Client（Claude Desktop + MAF Agent + test harness）同时连上 Editor。不拒绝并发连接。

### 6.2 azlmbr 调用串行化

但 azlmbr 必须主线程执行（不 thread-safe）。所有来自多 client 的 tool 调用通过**同一个跨线程队列**排队进主线程，**实质上串行**。两个 client 同时调 `entity.create`，结果是先到先做。

### 6.3 锁范围（可选，仅给 HTTP handler 用）

```python
# mcp_server.py
_tool_lock = asyncio.Lock()   # 可选：想让 tool 级别完全串行时用

async def _invoke_tool(tool_name, params):
    async with _tool_lock:
        return await handler(**params)  # 内部走 call_on_main
```

**通常不需要**这个锁——跨线程队列本来就是串行的。加 `_tool_lock` 只有一个用途：让整个 tool handler（含多次 `call_on_main`）原子化，不被另一个 tool 插队。大部分工具不需要这个粒度；需要原子性的工具内部用 `undo_batch` 包裹就够了。

---

## 7. 配额与超时

| 资源 | 限制 | 触发后 |
|---|---|---|
| 单工具调用超时 | 30s | 返回 `timeout` 错误 |
| 单 MCP 工具调用链累计 | 60s | 中断 |
| 单 Agent turn 总 MCP 调用数 | 200 | 要求用户"继续吗？" |
| 单次 batch_place_instances count | 100 | 拒绝 + 建议拆 |
| 场景总 entity 数 | 10000 | warning（不拒） |
| pending queue 深度 | 50 | HTTP handler 返回 `overloaded` |

配置放 [`tools/o3de_mcp/config.py`](../../tools/o3de_mcp/config.py)。

---

## 8. dirty state 管理

Editor 的 "level is dirty" 状态：用户手工改了但没 save。Agent 进来前必须看一眼：

```python
# Scene Specialist 开场
status = mcp.call("level.get_dirty_state", {})
if status["is_dirty"]:
    # 告诉用户并停下
    raise ConsentRequired(
        "Level has unsaved changes. Save / discard first, or confirm Agent may operate on dirty state."
    )
```

**为什么**：Agent 如果在 dirty state 上跑，Undo 历史混在一起，用户分不清"哪些是我改的 / 哪些是 AI 改的"。

工具：
- `level.get_dirty_state` —— 新增 L0 工具
- Agent 处理：拒绝干活 / 问用户 / 加 bookmark（v2）

---

## 9. 审计日志

**每一次** MCP 工具调用都记：

```jsonl
{"ts":"2026-04-24T15:30:15.001Z","agent":"scene_spec","turn_id":"uuid","tool":"entity.delete","params":{...},"result":{...},"hitl_decision":"approved","user":"thesd@..."}
```

落 `tools/agents/logs/run_*/mcp_audit.jsonl`。

**为什么必须**：
- 事后复盘"AI 到底改了啥"
- 调试"咦场景怎么变了" → 搜 audit
- 把审计 feed 给 Reviewer 看 —— 不光看结果，还看**过程**

---

## 10. 几个常见错误 pattern 及护栏

### 10.1 "Agent 自己给自己授权"

**失败模式**：Agent prompt 里写"如果需要可以 AUTO_APPROVE"。
**护栏**：`AUTO_APPROVE` 只能从 env 或 config 来，**MCP 工具层根本不暴露修改能力**。工具目录里不提供 `system.set_auto_approve`。

### 10.2 "Agent loop 无限重试失败操作"

**失败模式**：asset_not_found → retry → again fail → again retry ...
**护栏**：
- MCP Server 在 tool 层加 retry 上限（默认 2 次）
- Agent workflow 层加 turn-level 调用数上限（上文 §7）
- Specialist prompt 里写死"同一个 tool 同一个参数最多重试 1 次"

### 10.3 "Agent 绕过 MCP 直接调 azlmbr"

**失败模式**：Agent 发现 MCP 工具没暴露的 API，想 `system.run_editor_console_command("pyRunScript my.py")` 走后门。
**护栏**：
- Console command 白名单（仅放行 `r_getScreenshot`、`ed_...` 等）
- Python 脚本执行不在 MCP 工具面里；真需要新 API 走"加一个新 MCP 工具"的流程

### 10.4 "Agent 改完忘 save，用户看不到"

**失败模式**：op 完成但 Editor 是 dirty，用户重启 Editor 改动全丢。
**护栏**：
- Scene Spec 结束时 summary 里**明确标注** "need_save: true/false"
- Reviewer 检查 summary，"如果改了但没 save，标 minor finding"
- 不自动 save —— save 必须 HITL

---

## 11. MCP Server 自保护

MCP Server 跑在 Editor 进程内，Editor 和 MCP Server 共命运 —— 它崩了 Editor 也难幸免。所以 handler 写得要比普通 Python 更防御：

- **每工具 `try/except`**：handler 抛了不影响下一个请求；绝不让异常传到 HTTP transport 外
- **保活 ping**：提供 `GET /health` 端点（~~不是 MCP 工具~~，是独立的 HTTP route），Agent client 可轮询；超过 15s 未响应视为 Editor 卡死
- **OOM 保护**：`query.scene_snapshot` 有 max_entities 限制（默认 2000），防止 10w entity 场景把 JSON 撑爆 LLM context
- **循环保护**：任何列表返回默认 limit=500 + pagination cursor
- **主线程泵保护**：pending queue 超过 50 → 新请求直接返回 `overloaded`，避免队列无限涨

---

## 12. 用户关闭 Editor 怎么办

Agent 半路操作，用户 Alt+F4 关了 Editor（没 save）。MCP Server 这边 HTTP/SSE 的 TCP 连接断开。

- MCP Server：跟着 Editor 进程结束（它在 Editor Python VM 里）
- MCP Server：检测到连接断开 → 标记 "editor offline"
- Pending MCP tool 调用：全部返回 `{ok:false, error:{code:"editor_disconnected"}}`
- Agent 看到这个错误：**停止本 turn，不重启 editor**。重启由用户决定

---

## 13. 隐私 / 数据外泄

- Agent 调 DeepSeek API 的 context 里**绝不塞**完整 asset binary 或 .prefab 文件内容
- 只塞：entity name / id / component types / property names + 值（可能含路径）
- **路径是值得注意的**：`Projects/MySecretGame/Levels/...` 泄露了项目结构。对敏感项目：
  - 做一层 path rewrite（项目根替换为 `<PROJECT>`）
  - 或不要把 scene_snapshot 发给第三方 API，只给本地模型

---

## 14. checklist：新增工具前过一遍

每加一个 MCP 工具，在 PR 里回答：

- [ ] `safety_level` 是 L0/L1/L2/L3？
- [ ] destructive → 是否加 `history.*` undo 包裹？
- [ ] 参数输入是否校验？（path 合法性、enum 值范围）
- [ ] 失败返回是否给 Agent **可操作**的错误信息？（不是只说 "failed"）
- [ ] 能否被 `denied.py` 拦？如不应拦，是否在 whitelist 里？
- [ ] 单元测试：正例 + 1-2 个 denied 负例
- [ ] 审计日志字段全吗？

这 7 条不过 → 工具不合格。

---

## 15. `system.exec_python` 逃生舱

这是一个**特殊工具**：允许 Agent 把一段 Python 代码塞给 Editor 的 Python VM 直接执行。它违反"结构化工具优先"的原则，所以规则比其它工具严格得多。

### 15.1 何时该用、何时不该用

**该用**：
- 结构化工具目录真的没覆盖某个 azlmbr API
- 急事：demo 前 5 分钟要做一个工具目录没有的组合
- 临时性的探索：Agent 试某个 API 看返回什么结构

**不该用**：
- 为了"灵活"而默认用 —— 这是滑向"Agent 全用 exec_python" 的陷阱，结构化的 schema / safety / 可审计全丢
- 做的事正好能用现有结构化工具完成 —— 先用现有的
- 想跳过 HITL —— 逃生舱**每次**都 HITL，不是捷径

### 15.2 双开关：默认关，开启要两个配置都打开

```python
# config.py
ALLOW_EXEC_PYTHON = False   # 默认 False
# 即使 AUTO_APPROVE=True，exec_python 也必须这一项单独为 True
```

就算 `AUTO_APPROVE=true`，`system.exec_python` **仍然**要求用户每次 `y/n` 确认；不受 AUTO_APPROVE 影响。

### 15.3 执行前的强制步骤

```
═══════════════════════════════════════════════════════════════
  ⚠️  Agent 请求执行 Python 逃生舱
═══════════════════════════════════════════════════════════════
  Label: AI exec: 想读一下 PhysX 配置组件的 intermediate 字段

  Code:
  ─────────────────────────────────────────────────────────────
  import azlmbr.bus as bus
  import azlmbr.editor as editor
  ...（完整代码打印，40 行以内不截断）
  ─────────────────────────────────────────────────────────────
  Safety notes:
    - 没发现明显的 os.system / subprocess / 文件 I/O 调用
    - 检测到：对 EditorComponentAPIBus 的读调用
    - 不在 denied 列表

  批准执行？[y/N]:
═══════════════════════════════════════════════════════════════
```

"Safety notes" 是启发式 AST 扫描（不能防所有坏事，但能拦明显的）：
- 关键字扫描 `os.system` / `subprocess` / `open(` / `shutil.` / `eval(` / `__import__(`
- 网络：`socket` / `urllib` / `requests`
- 命中 → 在 notes 里明确标红，用户看到后再决定

### 15.4 `exec_python` 不是"可以绕过 denied 清单"的万能钥匙

即使用户 y 了，有些东西仍然被**进程级**拦截：

- 如果 code 里显式 `import os; os.system(...)` → handler 在 exec 前扫到关键字 → 拒绝（不管用户怎么答）
- 修改 `engine.json` / `project.json` / `.git/` → handler 在 exec 前 hook 文件系统调用 → 拒绝

这是**多层防御**：HITL 提醒用户，关键词扫描做硬拦截，哪怕用户手滑 y 了也不能真跑出 system-level 破坏。

### 15.5 审计

exec_python 的每次调用必须记：

```json
{
  "ts": "...",
  "tool": "system.exec_python",
  "label": "...",
  "code_full": "...",            // 完整保留，不截断
  "hitl_decision": "approved",
  "denied_patterns_matched": [],
  "result_json": {...},
  "exec_duration_ms": 12
}
```

code_full 不截断是关键 —— 事后出问题要能完整复现。

### 15.6 渐进废弃 pattern

如果 audit log 里出现**同一个 code pattern 被 Agent 用 ≥ 3 次**：

1. 这就是在告诉你工具目录缺一个正式工具
2. 下一步动作：把那段 code 改写成 `handlers/xxx.py` 的正式 handler
3. 在 [02_tool_catalog.md](02_tool_catalog.md) 加一行
4. 跑几次验证
5. 下次 Agent 遇到这个需求，走正式工具，不再走 exec_python

**`exec_python` 调用量**应该随着时间**下降**（工具目录在成长）。如果它一直在涨 → 架构走歪了，停下来审视。

### 15.7 生产环境禁用

团队版（v3）在 [Gem 化](05_roadmap.md) 后：
- 团队共享 Editor：`ALLOW_EXEC_PYTHON` **不允许**从 MCP 配置打开，必须改 Gem 的 C++ 编译常量 → 需要重编引擎
- 个人本地：Python 一个 env 变量就开，方便探索
