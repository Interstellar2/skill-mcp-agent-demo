"""回滚到指定步骤重新执行（orchestrator，使用策略模式）."""

import logging
from typing import Awaitable, Callable, Optional

from ..tracker.checkpoint import CheckpointManager
from ..tracker.state_backend import StateBackend, get_state_backend
from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..skill import parse_sop_steps, render_sop, SkillsManager, validate_skill_steps
from ..tracker import RunTracker
from ..config import SKILLS_DIR
from .checkpoint_strategies import get_rollback_strategy

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


async def rollback_run(
    run_id: str,
    to_step: int,
    skills_dir=None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
    checkpoint_id: Optional[str] = None,
    compensate: bool = False,
    backend: Optional[StateBackend] = None,
):
    """回滚到指定步骤重新执行.

    若指定 checkpoint_id，则使用 checkpoint 中的 variables 作为起始状态；
    否则使用原 run 的初始 variables。
    """
    backend = backend or get_state_backend()
    orig_run = await RunTracker.load_run(run_id, backend=backend)
    if not orig_run:
        logger.error(f"找不到原始执行记录: {run_id}")
        return

    skill_name = orig_run.skill_name

    if checkpoint_id:
        cp = await CheckpointManager(backend=backend).load_checkpoint(checkpoint_id)
        if not cp:
            logger.error(f"找不到检查点: {checkpoint_id}")
            return
        variables = cp.variables
        logger.info(f"   使用 Checkpoint: {cp.checkpoint_id} 作为起始状态")
    else:
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
            backend=backend,
        )
        if tracker is None:
            async with t:
                t.record.resumed_from = run_id
                t.record.rollback_to_step = to_step
                strategy = get_rollback_strategy(compensate)
                await strategy.rollback(t, session, steps, to_step, event_broadcaster, orig_steps=orig_run.steps)
        else:
            tracker.record.resumed_from = run_id
            tracker.record.rollback_to_step = to_step
            strategy = get_rollback_strategy(compensate)
            await strategy.rollback(tracker, session, steps, to_step, event_broadcaster, orig_steps=orig_run.steps)

    if mcp_pool is not None:
        await _execute(mcp_pool.session)
    else:
        async with get_mcp_tools() as (tools, session):
            await _execute(session)
