"""默认顺序恢复策略."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ...tracker.models import Checkpoint
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner, build_step_hooks
from .base import ResumeStrategy, register_resume

logger = logging.getLogger("kitchen_agent")


@register_resume
class SequentialResumeStrategy(ResumeStrategy):
    name = "sequential"

    def can_handle(self, executor_state: Dict[str, Any]) -> bool:
        # 默认兜底策略，总是返回 True，但优先级最低
        return True

    async def resume(
        self,
        tracker: RunTracker,
        session,
        cp: Checkpoint,
        steps: List[dict],
        event_broadcaster: Optional[Callable[[str, dict], Awaitable[None]]],
        **kwargs: Any,
    ):
        if cp.step_status == "after_step":
            resume_from = cp.step_index + 1
        else:
            resume_from = cp.step_index

        if resume_from > len(steps):
            logger.info("所有步骤已执行完毕，无需恢复")
            return

        from ..resume import _seed_completed_steps

        _seed_completed_steps(tracker, cp, steps)
        logger.info(f"   新 Run ID: {tracker.record.run_id}")
        logger.info(f"   将从步骤 {resume_from} 继续执行")
        hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=True)
        runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)

        for idx in range(resume_from, len(steps) + 1):
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
        logger.info(f"🎉 恢复执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
