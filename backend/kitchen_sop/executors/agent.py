"""Agent 模式：使用 LangChain + LLM 自主决策调用工具."""

import logging
import os
from typing import Awaitable, Callable, Optional

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.callbacks import AsyncCallbackHandler

from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..tracker import RunTracker
from .base import SkillExecutorContext

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


class AgentThoughtCallback(AsyncCallbackHandler):
    """拦截 Agent 推理过程并通过 event_broadcaster 广播."""

    def __init__(self, event_broadcaster: EventBroadcaster):
        self.event_broadcaster = event_broadcaster

    async def on_agent_action(self, action, **kwargs):
        if self.event_broadcaster:
            await self.event_broadcaster(
                "agent_thought",
                {
                    "type": "action",
                    "tool": getattr(action, "tool", None),
                    "tool_input": getattr(action, "tool_input", None),
                    "log": getattr(action, "log", None),
                },
            )

    async def on_tool_start(self, serialized, input_str, **kwargs):
        if self.event_broadcaster:
            await self.event_broadcaster(
                "agent_thought",
                {
                    "type": "tool_start",
                    "tool": serialized.get("name") if serialized else None,
                    "input": input_str,
                },
            )

    async def on_tool_end(self, output, **kwargs):
        if self.event_broadcaster:
            await self.event_broadcaster(
                "agent_thought",
                {
                    "type": "tool_end",
                    "output": str(output) if output else None,
                },
            )


async def run_agent_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    model: Optional[str] = None,
    query: str = "请按照 SOP 制作番茄炒鸡蛋",
    variables: Optional[dict] = None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
):
    """Agent 模式: 使用 LangChain + LLM，让大模型根据 SOP 自主决策调用工具."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = model or os.environ.get("MODEL", "gpt-4o-mini")

    if not api_key:
        logger.error("未设置 OPENAI_API_KEY，无法运行 Agent 模式")
        logger.info("提示: 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY='your-key'")
        logger.info("   或使用 Demo 模式: python main.py --demo")
        return

    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables, need_steps=False
    ) as ctx:
        logger.info("=" * 60)
        logger.info("🤖 Agent 模式: 启动 LangChain Agent")
        logger.info(f"   模型: {model}")
        logger.info(f"   Base URL: {base_url or '默认'}")
        logger.info(f"   Skill: {skill_name}")
        logger.info("=" * 60)

        async def _execute(session, tools):
            logger.info(f"🔧 已加载 {len(tools)} 个 MCP 工具:")
            for t in tools:
                logger.info(f"   - {t.name}: {t.description[:50]}...")

            llm_kwargs = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                llm_kwargs["base_url"] = base_url

            llm = ChatOpenAI(**llm_kwargs)

            system_prompt = f"""你是一位专业的中餐厨师助手。你的任务是根据给定的标准操作流程（SOP），一步一步地调用厨房工具来完成菜肴的制作。

## 当前 SOP

{ctx.rendered_sop}
{ctx.reference_text}
## 工作规则

1. 严格按照 SOP 的步骤顺序操作，不要跳过任何步骤。
2. 每个步骤中，根据 SOP 的参数要求调用对应工具。
3. 调用工具后，等待结果再继续下一步。
4. 如果某一步调用失败，尝试修复参数后重试一次。
5. 完成后向用户汇报成果。
"""

            t = tracker or RunTracker(
                skill_name, mode="agent", variables=ctx.merged_vars
            )
            if tracker is None:
                async with t:
                    await _run_agent(t, session, tools, llm, system_prompt, query, event_broadcaster)
            else:
                await _run_agent(t, session, tools, llm, system_prompt, query, event_broadcaster)

        if mcp_pool is not None:
            await _execute(mcp_pool.session, mcp_pool.tools)
        else:
            async with get_mcp_tools() as (tools, session):
                await _execute(session, tools)


async def _run_agent(
    tracker: RunTracker,
    session,
    tools,
    llm,
    system_prompt: str,
    query: str,
    event_broadcaster: EventBroadcaster,
):
    logger.info(f"   Run ID: {tracker.record.run_id}")

    original_call_tool = session.call_tool

    async def tracked_call_tool(tool_name, arguments):
        step_rec = tracker.start_step(
            len(tracker.record.steps) + 1, tool_name, arguments
        )
        if event_broadcaster:
            await event_broadcaster(
                "step_start",
                {
                    "step_index": step_rec.step_index,
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
            )
        try:
            result = await original_call_tool(tool_name, arguments=arguments)
            text = None
            if result.content:
                text = (
                    result.content[0].text
                    if hasattr(result.content[0], "text")
                    else str(result.content[0])
                )
            tracker.finish_step(step_rec, result_text=text)
            if event_broadcaster:
                await event_broadcaster(
                    "step_finish",
                    {
                        "step_index": step_rec.step_index,
                        "tool_name": tool_name,
                        "result_text": text,
                    },
                )
            return result
        except Exception as e:
            tracker.fail_step(step_rec, error_message=str(e))
            if event_broadcaster:
                await event_broadcaster(
                    "step_error",
                    {
                        "step_index": step_rec.step_index,
                        "tool_name": tool_name,
                        "error_message": str(e),
                    },
                )
            raise

    session.call_tool = tracked_call_tool

    callbacks = []
    if event_broadcaster:
        callbacks.append(AgentThoughtCallback(event_broadcaster))

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    logger.info(f"🚀 开始执行: {query}")
    result = await agent.ainvoke(
        {"messages": [("user", query)]},
        config={"callbacks": callbacks} if callbacks else None,
    )

    output = "(无输出)"
    if result.get("messages"):
        last_msg = result["messages"][-1]
        output = getattr(last_msg, "content", str(last_msg))

    logger.info("=" * 60)
    logger.info("📋 Agent 最终回答:")
    logger.info(output)
    logger.info("=" * 60)
