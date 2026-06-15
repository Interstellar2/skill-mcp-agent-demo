"""Agent 恢复策略：通过 replay 消息恢复 Agent 执行."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ...tracker.models import Checkpoint
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner
from ..agent import reconstruct_lc_messages, run_agent_mode
from .base import ResumeStrategy, register_resume

logger = logging.getLogger("kitchen_agent")


@register_resume
class AgentResumeStrategy(ResumeStrategy):
    name = "agent"

    def can_handle(self, executor_state: Dict[str, Any]) -> bool:
        return "agent_messages" in executor_state

    async def resume(
        self,
        tracker: RunTracker,
        session,
        cp: Checkpoint,
        steps: List[dict],
        event_broadcaster: Optional[Callable[[str, dict], Awaitable[None]]],
        **kwargs: Any,
    ):
        executor_state = cp.executor_state or {}
        agent_messages = executor_state.get("agent_messages", [])
        system_prompt = executor_state.get("agent_system_prompt", "")
        query = executor_state.get("agent_query", "请按照 SOP 制作番茄炒鸡蛋")
        model = executor_state.get("agent_model", "gpt-4o-mini")

        logger.info(f"   新 Run ID: {tracker.record.run_id}")
        logger.info(f"   将从 Agent 消息历史恢复，共 {len(agent_messages)} 条消息")

        # 直接调用 run_agent_mode 的 resume 路径（通过 initial_messages）
        await run_agent_mode(
            skill_name=tracker.record.skill_name,
            model=model,
            query=query,
            tracker=tracker,
            event_broadcaster=event_broadcaster,
            mcp_pool=kwargs.get("mcp_pool"),
            initial_messages=agent_messages,
        )

        logger.info("=" * 60)
        logger.info(f"🎉 Agent 恢复执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
