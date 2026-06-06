"""从检查点恢复执行."""

import logging
from typing import Awaitable, Callable, Optional

from ..checkpoint import CheckpointManager
from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..sop_parser import parse_sop_steps
from ..template_engine import render_sop
from ..tracker import RunTracker
from ..tracker.models import StepRecord
from ..skill_manager import SkillsManager
from ..config import SKILLS_DIR
from .base import execute_step, log_step_call, log_step_result, log_step_error
from ..skill_validator import validate_skill_steps

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


async def resume_run(
    run_id: str,
    skills_dir=None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
):
    """从某个 run 的最新检查点恢复执行.

    工作流程：
    1. 加载原 run 记录和最新 checkpoint
    2. 创建新 run，标记 resumed_from=原run_id
    3. 从 checkpoint 的 step_index 开始继续执行
    """
    cp_mgr = CheckpointManager()
    cp = cp_mgr.get_latest_checkpoint(run_id)
    if not cp:
        logger.error(f"Run {run_id} 没有找到检查点，无法恢复")
        return

    orig_run = RunTracker.load_run(run_id)
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

    raw_sop = sm.activate_skill(skill_name)
    rendered_sop = render_sop(raw_sop, variables)
    steps = parse_sop_steps(rendered_sop, sm=sm, variables=variables)
    if not steps:
        logger.warning("未从 SOP 中解析出任何工具调用步骤")
        return

    if cp.step_status == "after_step":
        resume_from = cp.step_index + 1
    else:
        resume_from = cp.step_index

    if resume_from > len(steps):
        logger.info("所有步骤已执行完毕，无需恢复")
        return

    logger.info("=" * 60)
    logger.info("🔄 Resume 模式: 从检查点恢复执行")
    logger.info(f"   原 Run ID: {run_id}")
    logger.info(f"   Checkpoint: {cp.checkpoint_id} (step={cp.step_index}, status={cp.step_status})")
    logger.info(f"   将从步骤 {resume_from} 继续执行")
    logger.info("=" * 60)

    async def _execute(session):
        result = await session.list_tools()
        validate_skill_steps(steps, result.tools)
        t = tracker or RunTracker(skill_name, mode="resume", variables=variables)
        if tracker is None:
            async with t:
                t.record.resumed_from = run_id
                await _run_resume(t, session, steps, resume_from, cp, event_broadcaster)
        else:
            tracker.record.resumed_from = run_id
            await _run_resume(tracker, session, steps, resume_from, cp, event_broadcaster)

    if mcp_pool is not None:
        await _execute(mcp_pool.session)
    else:
        async with get_mcp_tools() as (tools, session):
            await _execute(session)


async def _run_resume(
    tracker: RunTracker,
    session,
    steps: list,
    resume_from: int,
    cp,
    event_broadcaster: EventBroadcaster,
):
    logger.info(f"   新 Run ID: {tracker.record.run_id}")

    for sr_dict in cp.step_results:
        if sr_dict["step_index"] < resume_from and sr_dict["status"] == "success":
            old_step = StepRecord.from_dict(sr_dict)
            tracker.record.steps.append(old_step)

    for idx in range(resume_from, len(steps) + 1):
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
    logger.info(f"🎉 恢复执行完毕！{tracker.record.skill_name} 已完成~")
    logger.info("=" * 60)
