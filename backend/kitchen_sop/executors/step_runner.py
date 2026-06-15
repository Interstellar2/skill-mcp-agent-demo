"""StepRunner: 统一封装单步 MCP 工具调用，通过 hooks 编排副作用."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..tracker import RunTracker
from ..tracker.checkpoint import CheckpointManager
from ..tracker.checkpoint_service import CheckpointService
from ..tracker.models import StepRecord
from .hooks.agent_message_hook import AgentMessageHook
from .hooks.base import StepHook
from .hooks.checkpoint_hook import CheckpointHook
from .hooks.compensation_hook import CompensationHook
from .hooks.event_hook import EventHook
from .hooks.variable_hook import VariableHook

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


class StepRunner:
    """封装单步工具调用的完整生命周期，所有副作用通过 StepHook 注入."""

    def __init__(
        self,
        session,
        tracker: RunTracker,
        event_broadcaster: EventBroadcaster = None,
        hooks: Optional[List[StepHook]] = None,
    ):
        self.session = session
        self.tracker = tracker
        self.event_broadcaster = event_broadcaster
        self.hooks = hooks or []

        # 每次 run() 调用时由调用方传入的状态，hooks 可通过 runner 访问
        self.output_variable: Optional[str] = None
        self.step_checkpoint_state: Optional[Dict[str, Any]] = None
        self.compensation_context: Optional[Dict[str, Any]] = None
        self.compensator: Optional[Dict[str, Any]] = None

    async def run(
        self,
        step_rec: StepRecord,
        tool_name: str,
        arguments: Dict[str, Any],
        output_variable: Optional[str] = None,
        step_checkpoint_state: Optional[Dict[str, Any]] = None,
        compensation_context: Optional[Dict[str, Any]] = None,
        compensator: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """调用 MCP 工具并更新 tracker.

        Returns:
            提取到的 result_text，无内容时返回 None。
        Raises:
            Exception: 工具调用失败时抛出（tracker 已记录错误）。
        """
        self.output_variable = output_variable
        self.step_checkpoint_state = step_checkpoint_state
        self.compensation_context = compensation_context
        self.compensator = compensator

        for hook in self.hooks:
            await hook.on_before(self, step_rec, tool_name, arguments)

        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
        except Exception as e:
            await self.tracker.fail_step(step_rec, error_message=str(e))
            for hook in self.hooks:
                await hook.on_error(self, step_rec, tool_name, arguments, e)
            raise

        text = None
        if result.content:
            text = (
                result.content[0].text
                if hasattr(result.content[0], "text")
                else str(result.content[0])
            )

        await self.tracker.finish_step(step_rec, result_text=text)

        for hook in self.hooks:
            await hook.on_after(self, step_rec, tool_name, arguments, text)

        return text


def build_step_hooks(
    tracker: RunTracker,
    event_broadcaster: EventBroadcaster = None,
    enable_checkpoint: bool = False,
):
    """构造标准 StepRunner hooks 列表.

    顺序：
      - on_before: [EventHook, CheckpointHook]
      - on_after: [CheckpointHook, VariableHook, CompensationHook, AgentMessageHook, EventHook]
      - on_error: [CheckpointHook, EventHook]
    """
    hooks = [EventHook(), VariableHook(), CompensationHook(), AgentMessageHook()]
    if enable_checkpoint:
        cp_manager = CheckpointManager(backend=tracker._backend)
        cp_service = CheckpointService(tracker, cp_manager)
        cp_hook = CheckpointHook(cp_service)
        # 事件 hook 在 checkpoint hook 之后，保证 checkpoint_saved 先于 step_finish
        hooks = [EventHook(), cp_hook, VariableHook(), CompensationHook(), AgentMessageHook(), EventHook()]
    return hooks
