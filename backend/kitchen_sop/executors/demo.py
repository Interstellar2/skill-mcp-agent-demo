"""Demo 模式：无需 LLM，直接按 SOP 步骤顺序执行."""

import logging
from typing import Awaitable, Callable, Optional

from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..tracker import RunTracker
from .base import SkillExecutorContext, log_step_call, log_step_result, log_step_error
from .step_runner import StepRunner, build_step_hooks

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


async def run_demo_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    variables: Optional[dict] = None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
    enable_checkpoint: bool = False,
):
    """Demo 模式: 直接按 SOP 步骤顺序调用 MCP 工具，无需 API Key.

    适合快速演示 Skill + MCP 的联动效果.
    """
    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables
    ) as ctx:
        steps = ctx.steps

        logger.info("=" * 60)
        logger.info("🍳 Demo 模式: 按 SOP 顺序执行")
        logger.info(f"   Skill: {skill_name}")
        logger.info(f"   共 {len(steps)} 个步骤")
        logger.info("=" * 60)

        async def _execute(session):
            await ctx.validate_steps(session)
            if tracker is None:
                async with RunTracker(
                    skill_name,
                    mode="demo",
                    variables=ctx.merged_vars,
                ) as t:
                    await _run_steps(t, session, steps, event_broadcaster, enable_checkpoint=enable_checkpoint)
            else:
                await _run_steps(tracker, session, steps, event_broadcaster, enable_checkpoint=enable_checkpoint)

        if mcp_pool is not None:
            await _execute(mcp_pool.session)
        else:
            async with get_mcp_tools() as (tools, session):
                logger.info(
                    f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
                )
                await _execute(session)


async def _run_steps(
    tracker: RunTracker,
    session,
    steps: list,
    event_broadcaster: EventBroadcaster,
    enable_checkpoint: bool = False,
):
    logger.info(f"   Run ID: {tracker.record.run_id}")
    hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=enable_checkpoint)
    runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)
    for idx, step in enumerate(steps, 1):
        tool_name = step["tool_name"]
        arguments = step["arguments"]
        output_variable = step.get("output_variable")

        step_rec = tracker.start_step(idx, tool_name, arguments)
        log_step_call(idx, tool_name, arguments)

        try:
            text = await runner.run(
                step_rec,
                tool_name,
                arguments,
                output_variable=output_variable,
                compensator=step.get("compensator"),
            )
            log_step_result(text)
        except Exception as e:
            log_step_error(e)

    logger.info("=" * 60)
    logger.info(f"🎉 SOP 执行完毕！{tracker.record.skill_name} 已完成~")
    logger.info("=" * 60)
