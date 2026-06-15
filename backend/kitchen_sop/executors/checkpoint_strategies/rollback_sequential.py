"""顺序回滚策略：从目标步骤重新执行."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner, build_step_hooks
from .base import RollbackStrategy, register_rollback

logger = logging.getLogger("kitchen_agent")


@register_rollback
class RollbackSequentialStrategy(RollbackStrategy):
    name = "rollback_sequential"

    async def rollback(
        self,
        tracker: RunTracker,
        session,
        steps: List[dict],
        to_step: int,
        event_broadcaster: Optional[Callable[[str, dict], Awaitable[None]]],
        **kwargs: Any,
    ):
        logger.info(f"   新 Run ID: {tracker.record.run_id}")
        hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=True)
        runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)

        for idx in range(to_step, len(steps) + 1):
            step = steps[idx - 1]
            tool_name = step["tool_name"]
            arguments = step["arguments"]
            output_variable = step.get("output_variable")

            step_rec = tracker.start_step(idx, tool_name, arguments)
            log_step_call(idx, tool_name, arguments)
            try:
                text = await runner.run(
                    step_rec,
                    tool_name,
                    arguments,
                    output_variable=output_variable,
                    compensator=step.get("compensator"),
                )
                log_step_result(text)
            except Exception as e:
                log_step_error(e)
                break

        logger.info("=" * 60)
        logger.info(f"🎉 回滚重执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
