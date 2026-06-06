"""执行管理器：管理活跃的运行任务、Tracker、HITLBridge 与事件广播."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from ..tracker import RunTracker
from ..tracker.checkpoint import CheckpointManager
from ..hitl_bridge import HITLBridge
from ..mcp_pool import get_mcp_pool
from ..executors.demo import run_demo_mode
from ..executors.agent import run_agent_mode
from ..executors.plan_then_execute import run_plan_then_execute_mode
from ..executors.hitl import run_hitl_mode
from ..executors.parallel import run_parallel_mode
from ..executors.resumable import run_resumable_mode
from ..executors.resume import resume_run
from ..executors.rollback import rollback_run

logger = logging.getLogger("kitchen_agent")


@dataclass
class ActiveRun:
    run_id: str
    task: asyncio.Task
    tracker: RunTracker
    hitl_bridge: Optional[HITLBridge] = None
    event_broadcaster: Optional[Callable] = None


_active_runs: Dict[str, ActiveRun] = {}


async def _broadcast(run_id: str, event_type: str, payload: dict):
    from .ws import broadcast_to_run
    await broadcast_to_run(run_id, {"type": event_type, **payload})


async def start_run(
    skill_name: str,
    mode: str,
    variables: Optional[dict] = None,
    model: Optional[str] = None,
) -> str:
    tracker = RunTracker(skill_name, mode=mode, variables=variables)
    await tracker.__aenter__()

    hitl_bridge = HITLBridge(tracker.record.run_id) if mode == "hitl" else None

    async def _broadcaster(event_type: str, payload: dict):
        await _broadcast(tracker.record.run_id, event_type, payload)

    async def _run_task():
        try:
            pool = get_mcp_pool()
            kwargs = {
                "skill_name": skill_name,
                "variables": variables,
                "tracker": tracker,
                "event_broadcaster": _broadcaster,
            }
            if model:
                kwargs["model"] = model

            if mode == "agent":
                await run_agent_mode(**kwargs, mcp_pool=pool)
            elif mode == "plan_then_execute":
                await run_plan_then_execute_mode(**kwargs, mcp_pool=pool)
            elif mode == "hitl":
                await run_hitl_mode(**kwargs, hitl_bridge=hitl_bridge, mcp_pool=pool)
            elif mode == "parallel":
                await run_parallel_mode(**kwargs, mcp_pool=pool)
            elif mode == "resumable":
                await run_resumable_mode(**kwargs, mcp_pool=pool)
            else:
                await run_demo_mode(**kwargs, mcp_pool=pool)
        except Exception as e:
            logger.exception(f"Run {tracker.record.run_id} failed: {e}")
            tracker.record.overall_status = "error"
        finally:
            await tracker.__aexit__(None, None, None)
            await _broadcaster(
                "run_complete",
                {"run_id": tracker.record.run_id, "status": tracker.record.overall_status},
            )
            _active_runs.pop(tracker.record.run_id, None)

    task = asyncio.create_task(_run_task())
    _active_runs[tracker.record.run_id] = ActiveRun(
        run_id=tracker.record.run_id,
        task=task,
        tracker=tracker,
        hitl_bridge=hitl_bridge,
        event_broadcaster=_broadcaster,
    )
    return tracker.record.run_id


async def resume_run_web(run_id: str, checkpoint_id: Optional[str] = None) -> str:
    orig_run = RunTracker.load_run(run_id)
    if not orig_run:
        raise ValueError(f"Run not found: {run_id}")
    cp_mgr = CheckpointManager()
    cp = cp_mgr.get_latest_checkpoint(run_id)
    if not cp:
        raise ValueError(f"No checkpoint found for run: {run_id}")

    tracker = RunTracker(
        orig_run.skill_name, mode="resume", variables=cp.variables
    )
    tracker.record.resumed_from = run_id
    await tracker.__aenter__()

    async def _broadcaster(event_type: str, payload: dict):
        await _broadcast(tracker.record.run_id, event_type, payload)

    async def _task():
        try:
            pool = get_mcp_pool()
            # resume_run 内部会加载原 run 和 checkpoint，我们需要传入 checkpoint_id 的话
            # 目前 resume_run 只支持自动选最新，这里保持兼容
            await resume_run(
                run_id=run_id,
                tracker=tracker,
                event_broadcaster=_broadcaster,
                mcp_pool=pool,
            )
        except Exception as e:
            logger.exception(f"Resume failed: {e}")
            tracker.record.overall_status = "error"
        finally:
            await tracker.__aexit__(None, None, None)
            await _broadcaster(
                "run_complete",
                {"run_id": tracker.record.run_id, "status": tracker.record.overall_status},
            )
            _active_runs.pop(tracker.record.run_id, None)

    task = asyncio.create_task(_task())
    _active_runs[tracker.record.run_id] = ActiveRun(
        run_id=tracker.record.run_id,
        task=task,
        tracker=tracker,
        event_broadcaster=_broadcaster,
    )
    return tracker.record.run_id


async def rollback_run_web(run_id: str, to_step: int) -> str:
    orig_run = RunTracker.load_run(run_id)
    if not orig_run:
        raise ValueError(f"Run not found: {run_id}")

    tracker = RunTracker(
        orig_run.skill_name, mode="rollback", variables=orig_run.variables or {}
    )
    tracker.record.resumed_from = run_id
    tracker.record.rollback_to_step = to_step
    await tracker.__aenter__()

    async def _broadcaster(event_type: str, payload: dict):
        await _broadcast(tracker.record.run_id, event_type, payload)

    async def _task():
        try:
            pool = get_mcp_pool()
            await rollback_run(
                run_id=run_id,
                to_step=to_step,
                tracker=tracker,
                event_broadcaster=_broadcaster,
                mcp_pool=pool,
            )
        except Exception as e:
            logger.exception(f"Rollback failed: {e}")
            tracker.record.overall_status = "error"
        finally:
            await tracker.__aexit__(None, None, None)
            await _broadcaster(
                "run_complete",
                {"run_id": tracker.record.run_id, "status": tracker.record.overall_status},
            )
            _active_runs.pop(tracker.record.run_id, None)

    task = asyncio.create_task(_task())
    _active_runs[tracker.record.run_id] = ActiveRun(
        run_id=tracker.record.run_id,
        task=task,
        tracker=tracker,
        event_broadcaster=_broadcaster,
    )
    return tracker.record.run_id
