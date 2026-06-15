"""VariableHook：解析工具返回并更新 tracker variables."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from ...events import EventType
from .base import StepHook

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner

logger = logging.getLogger("kitchen_agent")


class VariableHook(StepHook):
    """解析输出变量并更新 tracker，广播 variables_updated 事件."""

    async def on_before(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> None:
        pass

    async def on_after(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        result_text: Optional[str],
    ) -> None:
        updates = _parse_output_variables(result_text, runner.output_variable)
        if updates:
            runner.tracker.update_variables(updates)
            logger.debug(f"步骤输出变量更新: {updates}")
            if runner.event_broadcaster:
                await runner.event_broadcaster(
                    EventType.VARIABLES_UPDATED.value,
                    {"step_index": step_rec.step_index, "updates": updates},
                )

    async def on_error(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        error: Exception,
    ) -> None:
        pass


def _parse_output_variables(
    text: Optional[str],
    output_variable: Optional[str] = None,
) -> Dict[str, Any]:
    """尝试从工具返回文本解析 JSON 并提取变量更新."""
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    if output_variable and output_variable in data:
        return {output_variable: data[output_variable]}

    if "variables" in data and isinstance(data["variables"], dict):
        return dict(data["variables"])

    return {}
