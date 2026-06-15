"""CheckpointHook：在 before/after/error 时调用 CheckpointService."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from ...events import EventType
from ...tracker.checkpoint_service import CheckpointService
from .base import StepHook

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner


class CheckpointHook(StepHook):
    """保存 before/after/error checkpoint，并广播 checkpoint_saved 事件."""

    def __init__(self, checkpoint_service: CheckpointService):
        self.cp_service = checkpoint_service

    async def on_before(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> None:
        cp = await self.cp_service.save_before_step(
            step_index=step_rec.step_index,
            tool_name=tool_name,
            arguments=arguments,
            executor_state=runner.step_checkpoint_state,
        )
        if cp and runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.CHECKPOINT_SAVED.value,
                {
                    "step_index": step_rec.step_index,
                    "checkpoint_id": cp.checkpoint_id,
                    "step_status": "before_step",
                },
            )

    async def on_after(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        result_text: Optional[str],
    ) -> None:
        cp = await self.cp_service.save_after_step(
            step=step_rec,
            executor_state=runner.step_checkpoint_state,
        )
        if cp and runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.CHECKPOINT_SAVED.value,
                {
                    "step_index": step_rec.step_index,
                    "checkpoint_id": cp.checkpoint_id,
                    "step_status": "after_step",
                },
            )

    async def on_error(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        error: Exception,
    ) -> None:
        cp = await self.cp_service.save_on_error(
            step=step_rec,
            executor_state=runner.step_checkpoint_state,
        )
        if cp and runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.CHECKPOINT_SAVED.value,
                {
                    "step_index": step_rec.step_index,
                    "checkpoint_id": cp.checkpoint_id,
                    "step_status": "error",
                },
            )
