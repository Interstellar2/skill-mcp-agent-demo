"""AgentMessageHook：透传 agent 消息历史到 step_rec."""

from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

from .base import StepHook

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner


class AgentMessageHook(StepHook):
    """将 step_checkpoint_state 中的 agent_messages 写入 step_rec."""

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
        result_text: Any,
    ) -> None:
        state = runner.step_checkpoint_state
        if state and state.get("agent_messages"):
            step_rec.agent_messages = state["agent_messages"]

    async def on_error(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        error: Exception,
    ) -> None:
        pass
