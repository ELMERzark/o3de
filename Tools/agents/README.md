# tools/agents — O3DE 多 Agent 开发骨架

**MVP**：三个 Agent（Planner / CPP Specialist / Reviewer）串行跑，协助 O3DE 项目的 C++ 开发。

基于 **Microsoft Agent Framework (Python) + DeepSeek API**，跑在本地 Ubuntu 24.04 / Windows。

设计原理见 [`docs_claud/practice/multi_agent_design.md`](../../docs_claud/practice/multi_agent_design.md)。

---

## 快速上手（Ubuntu 24.04）

```bash
cd tools/agents

# 1. Python 虚拟环境（用仓库自带 python 或系统 python 3.12 都行）
python3 -m venv .venv
source .venv/bin/activate

# 2. 装依赖
pip install -r requirements.txt

# 3. 配置 API key
cp .env.example .env
# 编辑 .env，填 DEEPSEEK_API_KEY

# 4. 跑第一个任务（干跑 dry-run 模式）
python run.py --dry-run "给 Gems/MyGem 加一个 SpinnerComponent，每帧绕 Z 轴旋转"

# 5. 真正跑（会询问每次写文件前确认）
python run.py "同上任务"
```

---

## Windows 快速上手

```bat
cd tools\agents
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
REM 编辑 .env 填 DEEPSEEK_API_KEY
python run.py "任务描述"
```

---

## 目录结构

```
tools/agents/
├── README.md              本文件
├── requirements.txt       依赖
├── .env.example           环境变量模板
├── config.py              模型 / 路径 / 超时 配置
├── safety.py              路径白名单 + 禁写清单
├── fs_tools.py            文件工具 (fs_read/write/grep/list)
├── prompts.py             三 agent 的 system prompt
├── agents_mvp.py          Agent 构造
├── workflow.py            串行 workflow + HITL
├── run.py                 CLI 入口
└── logs/                  运行日志（自动创建）
```

---

## 配置项（在 `.env` 或 `config.py` 里）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 必填 | 去 <https://platform.deepseek.com/api_keys> 拿 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | 不用改 |
| `MODEL_REASONER` | `deepseek-reasoner` | R1，给 Planner/Reviewer |
| `MODEL_CHAT` | `deepseek-chat` | V3，给 Specialist |
| `REPO_ROOT` | 自动推导（`../../`）| 仓库根，所有 fs_ 工具的白名单根 |
| `AUTO_APPROVE` | `false` | `true` = 跳过 HITL 确认（危险） |
| `MAX_PLANNER_TOKENS` | `8000` | Planner 输出上限 |
| `MAX_CODER_TOKENS` | `16000` | Coder 输出上限 |
| `LOG_DIR` | `./logs` | 日志存哪 |

---

## 怎么扩展（加一个新 Specialist）

例：加 Multiplayer Specialist。

1. 在 `prompts.py` 加 `MULTIPLAYER_SPECIALIST_PROMPT`（参考 CPP 的）
2. 在 `agents_mvp.py` 加 `build_multiplayer_specialist(...)`
3. 在 `workflow.py` 的 `WORKFLOWS` 注册新 workflow 或在现有里加一步
4. 在 `run.py` 加命令行开关 `--flavor multiplayer`

---

## 已知限制 / TODO

- [ ] MVP 只实现 Sequential workflow；Supervisor / Magentic 模式见 design doc Week 3
- [ ] 工具层目前只有 fs_*；cmake/ctest/ap 工具待加（Tester agent 上线时）
- [ ] 未接 MAF 的 HumanApproval middleware，HITL 是手写的 input() 提示
- [ ] DeepSeek-R1 的 reasoning token 暂未单独显示（要看 billing）
- [ ] 没有 retry / rate-limit 处理 — 跑大任务前加一下
- [ ] logs/ 目前只落 JSON；没做 Markdown 汇报

---

## 故障排查

| 症状 | 可能原因 / 解法 |
|---|---|
| `ImportError: agent_framework` | `pip install -r requirements.txt`；MAF 版本和代码注释里的对不上时看 `docs_claud/practice/multi_agent_design.md` 第 12 节 |
| `401 Unauthorized` | DEEPSEEK_API_KEY 没设 / 过期 |
| `Agent 说 "path is outside repo"` | 任务里给了绝对路径，用相对（`Gems/MyGem/...`） |
| `fs_write 被 safety 拒了` | 检查 `safety.py` 的 FORBIDDEN_PATHS |
| 一跑就 timeout | R1 慢；把 `REQUEST_TIMEOUT` 调高到 120s+ |
| Reviewer 对 O3DE 惯例不熟 | 检查它是否真读了 `docs_claud/11_conventions_and_patterns.md`；模型换到 R1 |
| DeepSeek 返回空 | 偶发；workflow 有 retry（最多 2 次）|

---

## 安全

- 所有 `fs_write` 默认 HITL 确认（除非 `AUTO_APPROVE=true`）
- 禁写清单：`engine.json` / `.git/` / `build/` / `Cache/` 等（见 `safety.py`）
- **不允许** agent 直接执行 git commit / push / reset 类命令
- Token / API key 只在 `.env`，不要提交到仓库（已在 `.gitignore` 里）
- 日志 `logs/` 可能含代码片段，视为项目私有
