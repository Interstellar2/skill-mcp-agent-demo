"""TrackedToolFactory：把 LangChain 工具包装为通过 StepRunner 调用并记录消息."""

import logging
import types
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ..step_runner import StepRunner
from ..hooks import SkillHookRegistry
from .message_recorder import AgentMessageRecorder

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


def wrap_tools_with_step_runner(
    tools,
    session,
    tracker: RunTracker,
    event_broadcaster: EventBroadcaster,
    recorder: AgentMessageRecorder,
    system_prompt: str,
    query: str,
    model: str,
    hooks_factory=None,
    skill_hooks=None,
):
    """将 LangChain 工具实例包装为通过 StepRunner 调用的版本，并记录消息快照.

    Args:
        hooks_factory: 可选的 callable，接收 tracker 返回 StepRunner hooks 列表。
            用于 Agent 模式注入自定义 hooks（默认 None 使用标准 hooks）。
        skill_hooks: 可选的 skill 级 hook 列表，会在执行期间注入 runner。

    Returns:
        (wrapped_tools, runner, registry) 元组。registry 可能为 None。
    """
    runner = StepRunner(
        session,
        tracker,
        event_broadcaster,
        hooks=hooks_factory(tracker) if hooks_factory else None,
    )

    registry = None
    if skill_hooks:
        registry = SkillHookRegistry(runner, skill_hooks)
        registry.register()

    def _make_tracked_arun(original_tool):
        async def tracked_arun(self, tool_input, run_manager=None):
            tool_name = getattr(original_tool, "name", None) or getattr(self, "name", "unknown")
            arguments = dict(tool_input) if isinstance(tool_input, dict) else {"input": tool_input}

            step_rec = tracker.start_step(
                len(tracker.record.steps) + 1, tool_name, arguments
            )
            tool_call_id = str(uuid.uuid4())
            recorder.record_ai(content="", tool_calls=[{"id": tool_call_id, "name": tool_name, "args": arguments}])
            messages_snapshot = recorder._snapshot()
            step_checkpoint_state = {
                "agent_messages": messages_snapshot,
                "agent_system_prompt": system_prompt,
                "agent_query": query,
                "agent_model": model,
            }
            try:
                text = await runner.run(
                    step_rec,
                    tool_name,
                    arguments,
                    step_checkpoint_state=step_checkpoint_state,
                )
                recorder.record_tool(content=text or "", tool_call_id=tool_call_id)
                return text or ""
            except Exception as e:
                recorder.record_tool(content=str(e), tool_call_id=tool_call_id)
                raise

        return tracked_arun

    wrapped = []
    for tool in tools:
        tool._arun = types.MethodType(_make_tracked_arun(tool), tool)
        wrapped.append(tool)
    return wrapped, runner, registry
