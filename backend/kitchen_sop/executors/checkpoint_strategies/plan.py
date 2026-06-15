"""Plan 恢复策略：从 plan_steps 恢复."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ...tracker.models import Checkpoint, ExecutionPlan, PlanStep
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner, build_step_hooks
from .base import ResumeStrategy, register_resume

logger = logging.getLogger("kitchen_agent")


@register_resume
class PlanResumeStrategy(ResumeStrategy):
    name = "plan"

    def can_handle(self, executor_state: Dict[str, Any]) -> bool:
        return "plan_steps" in executor_state

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
        plan_steps = executor_state["plan_steps"]

        from ..resume import _seed_completed_steps

        _seed_completed_steps(tracker, cp, plan_steps)
        execution_plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_index=s.get("step_index", i + 1),
                    tool_name=s["tool_name"],
                    arguments=s.get("arguments", {}),
                    reasoning=s.get("reasoning", ""),
                )
                for i, s in enumerate(plan_steps)
            ]
        )
        await tracker.set_execution_plan(execution_plan)

        current_idx = executor_state.get("current_step_index", cp.step_index)
        resume_from = current_idx + 1 if cp.step_status == "after_step" else current_idx

        logger.info(f"   新 Run ID: {tracker.record.run_id}")
        logger.info(f"   将从计划步骤 {resume_from} 继续执行")
        hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=True)
        runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)

        for step_data in plan_steps:
            idx = step_data.get("step_index", 0)
            if idx < resume_from:
                continue
            tool_name = step_data["tool_name"]
            arguments = step_data.get("arguments", {})
            reasoning = step_data.get("reasoning", "")
            output_variable = step_data.get("output_variable")

            step_checkpoint_state = {
                "plan_steps": plan_steps,
                "current_step_index": idx,
            }

            step_rec = tracker.start_step(idx, tool_name, arguments)
            log_step_call(idx, tool_name, arguments)
            if reasoning:
                logger.info(f"   理由: {reasoning}")
            try:
                text = await runner.run(
                    step_rec,
                    tool_name,
                    arguments,
                    output_variable=output_variable,
                    step_checkpoint_state=step_checkpoint_state,
                    compensator=step_data.get("compensator"),
                )
                log_step_result(text)
            except Exception as e:
                log_step_error(e)
                logger.info("计划执行中断，后续步骤已跳过")
                break

        logger.info("=" * 60)
        logger.info(f"🎉 计划恢复执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
