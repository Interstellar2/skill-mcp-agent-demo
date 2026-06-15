"""执行管理器：管理活跃的运行任务、Tracker、HITLBridge 与事件广播."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from ..events import EventType
from ..tracker import RunTracker
from ..tracker.checkpoint import CheckpointManager
from ..tracker.state_backend import get_state_backend
from ..hitl_bridge import HITLBridge
from ..mcp_pool import get_mcp_pool
from ..executors.agent.agent_runner import run_agent_mode
from ..executors.demo import run_demo_mode
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


def _make_broadcaster(run_id: str):
    async def broadcaster(event_type: str, payload: dict):
        await _broadcast(run_id, event_type, payload)
    return broadcaster


async def launch_run(
    tracker_factory: Callable[[], RunTracker],
    executor: Callable[[], Awaitable[None]],
    initial_event: Optional[Dict[str, Any]] = None,
    hitl_bridge: Optional[HITLBridge] = None,
) -> str:
    """统一包装运行生命周期：创建 tracker、启动 executor task、广播 run_complete.

    Args:
        tracker_factory: 返回已 __aenter__ 的 RunTracker 的工厂。
        executor: 已绑定参数的 executor 协程。
        initial_event: 执行前广播的初始化事件（如 resume_started/rollback_started）。
        hitl_bridge: 可选的 HITLBridge。
    """
    tracker = tracker_factory()
    broadcaster = _make_broadcaster(tracker.record.run_id)

    async def _task():
        try:
            if initial_event:
                await broadcaster(initial_event["type"], initial_event.get("payload", {}))
            await executor()
        except Exception as e:
            logger.exception(f"Run {tracker.record.run_id} failed: {e}")
            tracker.record.overall_status = "error"
        finally:
            await tracker.__aexit__(None, None, None)
            await broadcaster(
                EventType.RUN_COMPLETE.value,
                {"run_id": tracker.record.run_id, "status": tracker.record.overall_status},
            )
            _active_runs.pop(tracker.record.run_id, None)

    task = asyncio.create_task(_task())
    _active_runs[tracker.record.run_id] = ActiveRun(
        run_id=tracker.record.run_id,
        task=task,
        tracker=tracker,
        hitl_bridge=hitl_bridge,
        event_broadcaster=broadcaster,
    )
    return tracker.record.run_id


async def start_run(
    skill_name: str,
    mode: str,
    variables: Optional[dict] = None,
    model: Optional[str] = None,
    enable_checkpoint: bool = False,
) -> str:
    backend = get_state_backend()
    tracker = RunTracker(skill_name, mode=mode, variables=variables, backend=backend)
    await tracker.__aenter__()

    hitl_bridge = HITLBridge(tracker.record.run_id) if mode == "hitl" else None

    def _executor_factory():
        pool = get_mcp_pool()
        kwargs = {
            "skill_name": skill_name,
            "variables": variables,
            "tracker": tracker,
            "event_broadcaster": _make_broadcaster(tracker.record.run_id),
        }
        if model:
            kwargs["model"] = model
        if mode in ("demo", "agent", "plan_then_execute", "hitl", "parallel"):
            kwargs["enable_checkpoint"] = enable_checkpoint

        if mode == "agent":
            return run_agent_mode(**kwargs, mcp_pool=pool)
        elif mode == "plan_then_execute":
            return run_plan_then_execute_mode(**kwargs, mcp_pool=pool)
        elif mode == "hitl":
            return run_hitl_mode(**kwargs, hitl_bridge=hitl_bridge, mcp_pool=pool)
        elif mode == "parallel":
            return run_parallel_mode(**kwargs, mcp_pool=pool)
        elif mode == "resumable":
            return run_resumable_mode(**kwargs, mcp_pool=pool)
        else:
            return run_demo_mode(**kwargs, mcp_pool=pool)

    return await launch_run(
        tracker_factory=lambda: tracker,
        executor=lambda: _executor_factory(),
        hitl_bridge=hitl_bridge,
    )


async def resume_run_web(run_id: str, checkpoint_id: Optional[str] = None) -> str:
    backend = get_state_backend()
    orig_run = await RunTracker.load_run(run_id, backend=backend)
    if not orig_run:
        raise ValueError(f"Run not found: {run_id}")
    cp_mgr = CheckpointManager(backend=backend)
    if checkpoint_id:
        cp = await cp_mgr.load_checkpoint(checkpoint_id)
    else:
        cp = await cp_mgr.get_latest_checkpoint(run_id)
    if not cp:
        raise ValueError(f"No checkpoint found for run: {run_id}")

    tracker = RunTracker(
        orig_run.skill_name, mode="resume", variables=cp.variables, backend=backend
    )
    tracker.record.resumed_from = run_id
    await tracker.__aenter__()

    async def _executor():
        pool = get_mcp_pool()
        await resume_run(
            run_id=run_id,
            checkpoint_id=checkpoint_id,
            tracker=tracker,
            event_broadcaster=_make_broadcaster(tracker.record.run_id),
            mcp_pool=pool,
            backend=backend,
        )

    return await launch_run(
        tracker_factory=lambda: tracker,
        executor=_executor,
        initial_event={
            "type": EventType.RESUME_STARTED.value,
            "payload": {
                "run_id": run_id,
                "new_run_id": tracker.record.run_id,
                "checkpoint_id": cp.checkpoint_id,
            },
        },
    )


async def rollback_run_web(
    run_id: str,
    to_step: int,
    checkpoint_id: Optional[str] = None,
    compensate: bool = False,
) -> str:
    backend = get_state_backend()
    orig_run = await RunTracker.load_run(run_id, backend=backend)
    if not orig_run:
        raise ValueError(f"Run not found: {run_id}")

    variables = orig_run.variables or {}
    if checkpoint_id:
        cp = await CheckpointManager(backend=backend).load_checkpoint(checkpoint_id)
        if not cp:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        variables = cp.variables

    tracker = RunTracker(
        orig_run.skill_name, mode="rollback", variables=variables, backend=backend
    )
    tracker.record.resumed_from = run_id
    tracker.record.rollback_to_step = to_step
    await tracker.__aenter__()

    async def _executor():
        pool = get_mcp_pool()
        await rollback_run(
            run_id=run_id,
            to_step=to_step,
            checkpoint_id=checkpoint_id,
            compensate=compensate,
            tracker=tracker,
            event_broadcaster=_make_broadcaster(tracker.record.run_id),
            mcp_pool=pool,
            backend=backend,
        )

    return await launch_run(
        tracker_factory=lambda: tracker,
        executor=_executor,
        initial_event={
            "type": EventType.ROLLBACK_STARTED.value,
            "payload": {
                "run_id": run_id,
                "new_run_id": tracker.record.run_id,
                "to_step": to_step,
                "checkpoint_id": checkpoint_id,
            },
        },
    )
