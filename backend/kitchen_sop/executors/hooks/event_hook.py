"""EventHook：广播步骤生命周期事件."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from ...events import EventType
from .base import StepHook

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner


class EventHook(StepHook):
    """广播 step_start / step_finish / step_error 等事件."""

    async def on_before(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> None:
        if runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.STEP_START.value,
                {
                    "step_index": step_rec.step_index,
                    "tool_name": tool_name,
                    "arguments": arguments,
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
        if runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.STEP_FINISH.value,
                {
                    "step_index": step_rec.step_index,
                    "tool_name": tool_name,
                    "result_text": result_text,
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
        if runner.event_broadcaster:
            await runner.event_broadcaster(
                EventType.STEP_ERROR.value,
                {
                    "step_index": step_rec.step_index,
                    "tool_name": tool_name,
                    "error_message": str(error),
                },
            )
