# O3DE × DeepSeek × Microsoft Agent Framework 多 Agent 开发设计

> 编写日期：2026-04-24
> 目标：在 Ubuntu 24.04 本地开发机跑一套多 Agent 系统，协助 O3DE 项目的 C++ / 资产 / 构建 / 联网 等日常开发。
> 配套代码骨架：[`tools/agents/`](../../tools/agents/)
> 仓库知识底座：[`docs_claud/`](../) 的 20 份 md

---

## 1. 一句话概括

**三层 × 多专员**：
顶层 **Supervisor**（Magentic 模式）动态路由任务 → 中层 **Planner** 拆解 + **Reviewer** 质控 → 底层若干 **Specialist** 并行干活。
DeepSeek **R1** 做决策（Planner / Reviewer / Supervisor），**V3** / **Coder** 做执行（各 Specialist）。
全部 Agent 共享 `docs_claud/` 作为知识底座 + `AGENTS.md` 作为行为守则。

---

## 2. 为什么这样设计

### 2.1 O3DE 开发的特点

改一个 Component 往往牵扯 4-6 处：`.h` / `.cpp` / `*_files.cmake` / `Module::m_descriptors` / 可能的 Editor 组件 / 可能的反射 Version 涨。

**单个 Agent 很难都记住**。让每个 Specialist 只读自己那 2-3 份 `docs_claud/*.md`，质量明显优于"一个大 agent 读所有"。

### 2.2 为什么用 Magentic 而不是 GroupChat

| 模式 | 利 | 弊 |
|---|---|---|
| **Sequential Workflow** | 简单可控 | 死板，不能动态路由 |
| **GroupChat** | Agents 互相对话 | token 飙升、容易跑题 |
| **Magentic（Supervisor）** | 中心化调度，agent 不互相污染 | 需要好的 Supervisor prompt |

MVP 先用 Sequential（最简）；稳定后升 Magentic。

### 2.3 为什么 Reviewer 必须独立

让 Coder agent 自己 review = 几乎查不出 bug。Reviewer **用不同 system prompt + 故意挑刺角色**，并把 Coder 的输出当成 outsider 的代码审视。发现的问题明显更多。

### 2.4 DeepSeek 模型分工

| 用途 | 模型 | 理由 |
|---|---|---|
| Planner / Reviewer / Supervisor | `deepseek-reasoner`（R1）| 慢但准，拆任务 / 挑 bug 需要思考 |
| Coder / Specialist | `deepseek-chat`（V3）| 快，写大量 boilerplate 够用 |
| `*_files.cmake` 补丁、批量改名 | V3 或 Coder | 低复杂度、快、省 |

**关键**：所有 agent 都不用 R1 会很慢 + 贵；全用 V3 会 review 不到位。混着用省 30-50% 成本。

---

## 3. 架构图

```
                ┌─────────────────────────────────────────────────┐
                │           User (Ubuntu 24.04 dev machine)       │
                │   自然语言任务："给 HealthComponent 加网络同步"  │
                └──────────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │   Supervisor Agent (Magentic)        │
                    │   Model: DeepSeek-R1                 │
                    │   读: AGENTS.md + docs_claud/00+13   │
                    │   职责: 分派 / 汇总 / 人在回路        │
                    └──────────┬───────────────┬──────────┘
                               │               │
          ┌────────────────────▼────┐   ┌─────▼──────────────────┐
          │   Planner Agent         │   │   Reviewer Agent        │
          │   Model: DeepSeek-R1    │   │   Model: DeepSeek-R1    │
          │   产出: 文件清单+决策    │   │   对照 11 conventions   │
          └────────────────────┬────┘   └─────▲──────────────────┘
                               │               │
                  ┌────────────┼───────────────┼──────────────┐
                  ▼            ▼               │              ▼
          ┌───────────────┬────────────────┬──────────┬────────────┐
          │ C++ Component │ Multiplayer    │ Build/   │ Asset/     │
          │ Specialist    │ Specialist     │ CMake    │ Pipeline   │
          │ V3/Coder      │ R1/V3          │ V3       │ V3         │
          │ docs: 02,03   │ docs: 10       │ docs: 06 │ docs: 07,18│
          └───────┬───────┴────────┬───────┴────┬─────┴─────┬──────┘
                  │                │            │           │
                  └────────┬───────┴────────────┴───────────┘
                           ▼
            ┌──────────────────────────────────────┐
            │   Tool Layer (MAF Function Tools)    │
            │   fs_read/write/edit, grep, list     │
            │   (v2+) shell, cmake, ctest, o3de    │
            └──────────────────────────────────────┘
                           │
                           ▼
                 O3DE repo + build/
```

---

## 4. Agent 角色清单

| Agent | 模型 | 必读 docs | 工具 | 产出 |
|---|---|---|---|---|
| **Supervisor** | R1 | `AGENTS.md` + `00_index` + `13_ai_context_guide` | 调用其他 agent | 最终响应 + 状态 |
| **Planner** | R1 | `00` + 按任务选 2-3 份 | `fs_grep`, `fs_read`, `fs_list` | 文件改动清单 + 决策 + Uuid 占位 |
| **C++ Specialist** | V3 | `02_azcore` + `03_azframework` + `11_conventions` | `fs_read/write/grep` | `.h/.cpp` + `*_files.cmake` diff |
| **Editor Specialist** | V3 | `04_aztoolsframework` + `11` | 同上 | Editor 组件 + EditContext / BuildGameEntity |
| **Multiplayer Specialist** | R1 (AutoGen XML 复杂) | `10_networking_physics` | 同上 + `o3de_cli` | `.AutoComponent.xml` + C++ |
| **Rendering Specialist** | R1 | `08_rendering_atom` | `fs_read/write` | `.azsl` / `.pass` / `.materialtype` |
| **Build Specialist** | V3 | `06_build_and_cmake` + `05_gems_and_modules` | `fs_read/write`, `cmake_configure`(v2) | CMake + `*_files.cmake` 更新 |
| **Asset Specialist** | V3 | `07_asset_pipeline` + `18_dcc_integration` | `fs_read/write`, `ap_batch`(v2) | Builder 代码 + Scene Manifest |
| **Reviewer** | R1 | `11_conventions` + `15_debugging_toolkit` | `fs_read/grep` | Findings 列表（**不改代码**） |
| **Tester** | V3 | `15` + `17_ci_cd_guide` | `cmake_build`, `ctest`, `ap_batch` | 构建 / 测试报告 |

---

## 5. 工具设计（按 MVP / v2 分）

### MVP（骨架即有）

| 工具 | 功能 | 护栏 |
|---|---|---|
| `fs_read(path)` | 读仓库内任意文件 | 路径白名单：仅 REPO_ROOT 下 |
| `fs_list(path)` | 列目录 | 同上 |
| `fs_grep(pattern, glob)` | ripgrep 内容搜索 | 截断 200 行 |
| `fs_write(path, content)` | 写 / 新建文件 | **HITL 必确认** + 禁写清单（`engine.json` / `.git/` / `build/` 等） |

### v2 扩展

| 工具 | 功能 | 何时加 |
|---|---|---|
| `shell_run(cmd, cwd)` | 跑任意 shell | 须 HITL；建议白名单 |
| `cmake_configure(preset)` | 封装 `cmake --preset` | 有 Build Specialist 时 |
| `cmake_build(target)` | `cmake --build` | 有 Tester 时 |
| `ctest_run(labels)` | 跑 smoke / main 测试 | 有 Tester 时 |
| `ap_batch(platforms)` | 跑 AssetProcessorBatch | 有 Asset Specialist 时 |
| `o3de_cli(args)` | `scripts/o3de.sh` 封装 | 需要 create-gem / enable-gem 时 |
| `git_status_readonly()` | 只读 git status / diff --stat | 给 Reviewer 用 |

### 护栏（所有工具必守）

- **禁写清单**：`engine.json` / `project.json` 的 stable UUID 字段、`3rdParty/` / `build/` / `Cache/` / `.git/` 目录。
- **人在回路**：`fs_write` / 所有 shell 命令 **默认要求用户 yes/no**（除非配置 `AUTO_APPROVE=true`）。
- **路径白名单**：所有 fs_* 先 resolve 绝对路径，确保在 `REPO_ROOT` 下。
- **token 上限**：每个工具返回截断（`fs_read` 最多 200 KB，`fs_grep` 200 行）。

---

## 6. 工作流示例

### Sequential（MVP）

```
task → Planner → CPP Specialist → Reviewer → 人工 apply diff
```

**步骤**：

1. 用户提 `task = "给 HealthComponent 加 damage 方法"`
2. Planner（R1）读 `docs_claud/00` + 按任务判断读 `02` + `03`，grep 相关代码
3. Planner 输出 `plan = {"files": [...], "decisions": [...], "uuids": [...]}`
4. CPP Specialist（V3）接到 plan + 必要 docs，依次 `fs_read` 每个要改的文件、`fs_write` 新内容（每次 HITL 确认）
5. Reviewer（R1）读改动后的文件 + `docs_claud/11`，输出 `review = {"findings": [...], "severity": ...}`
6. 人工决定：接受 / 让某 Specialist 再来一轮 / 放弃

### Magentic（v2 升级）

```
task → Supervisor 循环 {
    决定下一步调谁 → 调用该 Agent → 看结果 → 继续 or 收尾
}
```

Supervisor 动态判断："这个任务涉及渲染 → 调 Rendering Specialist"，"改动大 → 先让 Planner 出方案"，"结果看起来可疑 → 让 Reviewer 审"。

---

## 7. 实施路线图

| 周 | 目标 | 交付物 |
|---|---|---|
| **Week 1** | 三 Agent + 四工具跑通 | Planner + CPP Specialist + Reviewer 线性链路，能改一个组件 |
| **Week 2** | 加 Tester + 构建闭环 | 系统能"写完代码 → cmake --build → 报告成功 / 失败 → 让 Specialist 修" |
| **Week 3** | Supervisor + Magentic | 不用手动选 Specialist，Supervisor 自动路由 |
| **Week 4+** | 各专项 Specialist | Multiplayer / Rendering / Asset / Editor，按项目需要 |

**MVP 成功标准**：用户给一个 "加个简单组件" 的任务 → 20 分钟内自动产出可编译的代码 + review 报告。

---

## 8. 关键风险与护栏

| 风险 | 护栏 |
|---|---|
| **幻觉编 API** | Specialist prompt 写死 "不确定就 fs_grep 实际代码"；Reviewer 检查 |
| **写坏文件** | 所有 `fs_write` HITL；禁写清单；写前自动 diff 给用户看 |
| **Context 爆** | 每个 Specialist 只读 2-3 份 docs；截断工具返回；长任务分批 |
| **Token 花费** | R1 只给 Planner / Reviewer；Specialist 用 V3；定期看 billing |
| **无限循环** | Supervisor / Magentic 加 `max_iterations` 护栏（例 10 步） |
| **跨平台差异** | 工具层适配 Ubuntu / Windows（优先 Ubuntu，检测 `os.name`） |
| **隐私** | DeepSeek 是第三方 API，不要塞敏感数据；可选本地 Ollama 备份 |

---

## 9. 骨架代码位置

MVP 代码在 [`tools/agents/`](../../tools/agents/)：

```
tools/agents/
├── README.md              使用说明
├── requirements.txt       依赖
├── .env.example           环境变量模板
├── config.py              模型 / 路径配置
├── safety.py              路径白名单 + 禁写清单
├── fs_tools.py            MVP 四工具：read/write/grep/list
├── prompts.py             三 agent 的 system prompt
├── agents_mvp.py          Planner + CPP Specialist + Reviewer
├── workflow.py            串行 workflow + HITL
└── run.py                 CLI 入口
```

---

## 10. 用法示例（预期）

```bash
cd tools/agents
pip install -r requirements.txt
cp .env.example .env
# 填 DEEPSEEK_API_KEY
python run.py "给 Gems/MyGem 加一个 SpinnerComponent，每帧绕 Z 轴旋转"
```

输出：

```
[Planner] 读 docs_claud/02, grep 现有 SpinnerComponent...
[Planner] 方案：
  - Code/Source/SpinnerComponent.{h,cpp}  (新建)
  - Code/Source/MyGemModule.cpp           (+1 行 descriptor)
  - Code/mygem_private_files.cmake        (+2 行)
  UUID 占位: {<gen>}

[CPP Specialist] 开始实施...
  → fs_write: SpinnerComponent.h [y/N]? y
  → fs_write: SpinnerComponent.cpp [y/N]? y
  → fs_write: MyGemModule.cpp [y/N]? y
  → fs_write: mygem_private_files.cmake [y/N]? y

[Reviewer] 审查...
  ✓ AZStd containers used
  ✓ AZ_CLASS_ALLOCATOR present
  ⚠ UUID 未替换（占位）
  ⚠ EditContext 未加 (如果需要 Editor 可见)

Done. 下一步: 生成 UUID 替换占位；加 Editor 组件（？）
```

---

## 11. 接下来的决策点

继续走之前你需要定：

1. **模型配置**：DeepSeek `deepseek-chat` / `deepseek-reasoner` 两个 model id 够用；还是考虑用 DeepSeek-Coder API 单独接？
2. **HITL 粒度**：每个 `fs_write` 都确认（慢但安全）vs 每个 Agent 结束时确认（快但有风险）？
3. **日志落盘**：每次 agent 调用的输入/输出要不要存 `tools/agents/logs/` ？（便于复盘）
4. **成本监控**：要不要在 workflow 结束时打一份 token 用量报告？

这些在 `config.py` 里都已经留好开关，试跑后再调。

---

## 12. 参考

- Microsoft Agent Framework Python 文档：<https://learn.microsoft.com/en-us/agent-framework/>
- DeepSeek API 文档（OpenAI-compatible）：<https://api-docs.deepseek.com/>
- `docs_claud/` 里的 20 份 O3DE 专项文档（知识底座）
- `AGENTS.md`（仓库根，所有 agent 的行为守则）
