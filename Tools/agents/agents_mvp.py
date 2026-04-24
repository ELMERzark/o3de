"""
构造 MVP 的三个 Agent：Planner / CPP Specialist / Reviewer。

说明（读源码前必看）：
    Microsoft Agent Framework (MAF) 的 Python API 在 1.x 期间仍会迭代。
    本文件基于 MAF Python SDK 的主流用法编写，关键 import 如下：

        from agent_framework import ChatAgent
        from agent_framework.openai import OpenAIChatClient

    若你装的 MAF 版本 import 路径或类名不同，主要改两处：
        1) build_chat_client()       —— 换成新 SDK 的 client 构造方式
        2) build_agent()             —— 换成新 SDK 的 ChatAgent / AIAgent 构造

    这个文件刻意把 MAF 相关代码封装在最上方几行，核心业务（prompt + tools +
    model 分配）不依赖 MAF 类型，方便替换。

    DeepSeek 是 OpenAI-compatible 端点，所以直接用 OpenAIChatClient + base_url
    指向 DeepSeek 就能工作。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

# MAF imports ================================================================
# 如报 ImportError 见文件顶部说明。
from agent_framework import ChatAgent  # type: ignore[import]
from agent_framework.openai import OpenAIChatClient  # type: ignore[import]
# ============================================================================

import config
import fs_tools
from prompts import CPP_SPECIALIST_PROMPT, PLANNER_PROMPT, REVIEWER_PROMPT

log = logging.getLogger(__name__)


# ------------------------------------------------------------------- Clients

def build_chat_client(model_id: str) -> OpenAIChatClient:
    """
    构造接 DeepSeek 的 OpenAI-compatible client。
    model_id = 'deepseek-reasoner' (R1) 或 'deepseek-chat' (V3)
    """
    return OpenAIChatClient(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        model_id=model_id,
        # 若 MAF 版本字段名不同试：model= / model_name= / ai_model_id=
    )


# ------------------------------------------------------------------- Agent builder

@dataclass
class AgentBundle:
    """
    一个 Agent 的所有元信息。
    workflow 里按需取，方便换模型 / 调 token 预算。
    """
    name: str
    agent: ChatAgent
    model_id: str
    purpose: str


def build_agent(
    *,
    name: str,
    instructions: str,
    model_id: str,
    tools: list,
    purpose: str,
) -> AgentBundle:
    """
    构造一个 ChatAgent 并包进 AgentBundle。
    """
    client = build_chat_client(model_id)

    agent = ChatAgent(
        chat_client=client,
        name=name,
        instructions=instructions,
        tools=tools,
        # 如 MAF 有 token / temperature 选项，这里加：
        # temperature=0.2,
        # max_tokens=...,
    )
    log.info("built agent name=%s model=%s tools=%d", name, model_id, len(tools))
    return AgentBundle(name=name, agent=agent, model_id=model_id, purpose=purpose)


# ------------------------------------------------------------------- Factories

def build_planner() -> AgentBundle:
    return build_agent(
        name="planner",
        instructions=PLANNER_PROMPT,
        model_id=config.MODEL_REASONER,  # R1：拆任务用 reasoning
        tools=fs_tools.READ_ONLY_TOOLS,  # Planner 不写文件
        purpose="把自然语言任务拆成结构化改动计划",
    )


def build_cpp_specialist() -> AgentBundle:
    return build_agent(
        name="cpp_specialist",
        instructions=CPP_SPECIALIST_PROMPT,
        model_id=config.MODEL_CHAT,      # V3：写代码够用
        tools=fs_tools.ALL_TOOLS,        # 能写文件
        purpose="按 Planner 的计划写 C++ 代码 + 更新 CMake + Module 注册",
    )


def build_reviewer() -> AgentBundle:
    return build_agent(
        name="reviewer",
        instructions=REVIEWER_PROMPT,
        model_id=config.MODEL_REASONER,  # R1：挑刺需要思考
        tools=fs_tools.READ_ONLY_TOOLS,  # Reviewer 不改代码
        purpose="审查 Specialist 的产出是否符合 O3DE 约定",
    )


# ------------------------------------------------------------------- All

def build_all_mvp() -> dict[str, AgentBundle]:
    return {
        "planner": build_planner(),
        "cpp_specialist": build_cpp_specialist(),
        "reviewer": build_reviewer(),
    }
