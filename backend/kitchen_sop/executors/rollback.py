"""回滚到指定步骤重新执行."""

import logging
from typing import Awaitable, Callable, Optional

from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..sop_parser import parse_sop_steps
from ..template_engine import render_sop
from ..tracker import RunTracker
from ..skill_manager import SkillsManager
from ..config import SKILLS_DIR
from .base import execute_step, log_step_call, log_step_result, log_step_error
from ..skill_validator import validate_skill_steps

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


async def rollback_run(
    run_id: str,
    to_step: int,
    skills_dir=None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
):
    """回滚到指定步骤重新执行.

    工作流程：
    1. 加载原 run 记录
    2. 创建新 run，标记 resumed_from=原run_id, rollback_to_step=to_step
    3. 从步骤 to_step 开始重新执行所有后续步骤
    """
    orig_run = RunTracker.load_run(run_id)
    if not orig_run:
        logger.error(f"找不到原始执行记录: {run_id}")
        return

    skill_name = orig_run.skill_name
    variables = orig_run.variables or {}

    sm = SkillsManager(skills_dir or SKILLS_DIR)
    skill = sm.skills.get(skill_name)
    if not skill:
        logger.error(f"找不到 Skill: {skill_name}")
        return

    raw_sop = sm.activate_skill(skill_name)
    rendered_sop = render_sop(raw_sop, variables)
    steps = parse_sop_steps(rendered_sop, sm=sm, variables=variables)
    if not steps:
        logger.warning("未从 SOP 中解析出任何工具调用步骤")
        return

    if to_step < 1 or to_step > len(steps):
        logger.error(f"回滚目标步骤 {to_step} 超出范围 (1-{len(steps)})")
        return

    logger.info("=" * 60)
    logger.info(f"↩️  Rollback 模式: 回滚到步骤 {to_step} 重新执行")
    logger.info(f"   原 Run ID: {run_id}")
    logger.info(f"   Skill: {skill_name}")
    logger.info(f"   将从步骤 {to_step} 开始重新执行")
    logger.info("=" * 60)

    async def _execute(session):
        result = await session.list_tools()
        validate_skill_steps(steps, result.tools)
        t = tracker or RunTracker(
            skill_name,
            mode="rollback",
            variables=variables,
        )
        if tracker is None:
            async with t:
                t.record.resumed_from = run_id
                t.record.rollback_to_step = to_step
                await _run_rollback(t, session, steps, to_step, event_broadcaster)
        else:
            tracker.record.resumed_from = run_id
            tracker.record.rollback_to_step = to_step
            await _run_rollback(tracker, session, steps, to_step, event_broadcaster)

    if mcp_pool is not None:
        await _execute(mcp_pool.session)
    else:
        async with get_mcp_tools() as (tools, session):
            await _execute(session)


async def _run_rollback(
    tracker: RunTracker,
    session,
    steps: list,
    to_step: int,
    event_broadcaster: EventBroadcaster,
):
    logger.info(f"   新 Run ID: {tracker.record.run_id}")

    for idx in range(to_step, len(steps) + 1):
        step = steps[idx - 1]
        tool_name = step["tool_name"]
        arguments = step["arguments"]

        step_rec = tracker.start_step(idx, tool_name, arguments)
        log_step_call(idx, tool_name, arguments)

        try:
            text = await execute_step(
                session, tracker, step_rec, tool_name, arguments,
                event_broadcaster=event_broadcaster,
            )
            log_step_result(text)
        except Exception as e:
            log_step_error(e)
            break

    logger.info("=" * 60)
    logger.info(f"🎉 回滚重执行完毕！{tracker.record.skill_name} 已完成~")
    logger.info("=" * 60)
