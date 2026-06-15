"""CompensationHook：从 JSON 返回中提取 compensation_context."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, TYPE_CHECKING

from .base import StepHook

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner


class CompensationHook(StepHook):
    """当步骤配置 compensator 且返回为 JSON dict 时，提取 compensation_context."""

    async def on_before(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> None:
        # 如果外部传入了 compensation_context（如回滚时），直接设置
        if runner.compensation_context is not None:
            step_rec.compensation_context = runner.compensation_context

    async def on_after(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        result_text: Optional[str],
    ) -> None:
        if runner.compensator is None:
            return
        try:
            data = json.loads(result_text) if result_text else None
            if isinstance(data, dict):
                step_rec.compensation_context = data
        except Exception:
            pass

    async def on_error(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        error: Exception,
    ) -> None:
        pass
