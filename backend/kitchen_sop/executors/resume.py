"""从检查点恢复执行（orchestrator，使用策略模式）."""

import logging
from typing import Awaitable, Callable, List, Optional

from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..tracker.checkpoint import CheckpointManager
from ..tracker.state_backend import StateBackend, get_state_backend
from ..skill import parse_sop_steps, render_sop, SkillsManager, validate_skill_steps
from ..tracker import RunTracker
from ..config import SKILLS_DIR
from .checkpoint_strategies import get_resume_strategy

from ..tracker.models import StepRecord

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


async def resume_run(
    run_id: str,
    skills_dir=None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
    checkpoint_id: Optional[str] = None,
    backend: Optional[StateBackend] = None,
):
    """从某个 run 的检查点恢复执行.

    若指定 checkpoint_id，则精确加载该检查点；否则使用最新检查点。
    """
    backend = backend or get_state_backend()
    cp_mgr = CheckpointManager(backend=backend)
    if checkpoint_id:
        cp = await cp_mgr.load_checkpoint(checkpoint_id)
    else:
        cp = await cp_mgr.get_latest_checkpoint(run_id)
    if not cp:
        logger.error(f"Run {run_id} 没有找到检查点，无法恢复")
        return

    orig_run = await RunTracker.load_run(run_id, backend=backend)
    if not orig_run:
        logger.error(f"找不到原始执行记录: {run_id}")
        return

    skill_name = orig_run.skill_name
    variables = cp.variables

    sm = SkillsManager(skills_dir or SKILLS_DIR)
    skill = sm.skills.get(skill_name)
    if not skill:
        logger.error(f"找不到 Skill: {skill_name}")
        return

    # 解析 SOP 步骤（用于顺序/并行恢复）
    raw_sop = sm.activate_skill(skill_name)
    rendered_sop = render_sop(raw_sop, variables)
    steps = parse_sop_steps(rendered_sop, sm=sm, variables=variables)
    if not steps:
        logger.warning("未从 SOP 中解析出任何工具调用步骤（Agent 恢复可能不需要）")

    logger.info("=" * 60)
    logger.info("🔄 Resume 模式: 从检查点恢复执行")
    logger.info(f"   原 Run ID: {run_id}")
    logger.info(f"   Checkpoint: {cp.checkpoint_id} (step={cp.step_index}, status={cp.step_status})")
    logger.info("=" * 60)

    async def _execute(session):
        if steps:
            result = await session.list_tools()
            validate_skill_steps(steps, result.tools)

        t = tracker or RunTracker(
            skill_name, mode="resume", variables=variables, backend=backend
        )
        if tracker is None:
            async with t:
                t.record.resumed_from = run_id
                strategy = get_resume_strategy(cp.executor_state)
                await strategy.resume(t, session, cp, steps, event_broadcaster, mcp_pool=mcp_pool)
        else:
            tracker.record.resumed_from = run_id
            strategy = get_resume_strategy(cp.executor_state)
            await strategy.resume(tracker, session, cp, steps, event_broadcaster, mcp_pool=mcp_pool)

    if mcp_pool is not None:
        await _execute(mcp_pool.session)
    else:
        async with get_mcp_tools() as (tools, session):
            await _execute(session)


def _seed_completed_steps(tracker: RunTracker, cp, steps: List[dict]):
    """将检查点中已完成的步骤种子恢复到新 tracker 中."""
    tracker.record.variables = cp.variables
    completed_indices = set()
    for step_dict in cp.step_results:
        step_index = step_dict.get("step_index")
        status = step_dict.get("status")
        if status == "success" and step_index is not None:
            completed_indices.add(step_index)
    for step_dict in cp.step_results:
        step_index = step_dict.get("step_index")
        if step_index in completed_indices:
            try:
                tracker.record.steps.append(StepRecord.from_dict(step_dict))
            except Exception:
                logger.warning(f"无法恢复步骤记录: {step_dict}")
    logger.info(f"   已恢复 {len(tracker.record.steps)} 个已完成步骤")
