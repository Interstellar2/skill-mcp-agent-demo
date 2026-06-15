"""Parallel 恢复策略：从 batches 恢复."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...events import EventType
from ...tracker import RunTracker
from ...tracker.checkpoint import CheckpointManager
from ...tracker.checkpoint_service import CheckpointService
from ...tracker.models import Checkpoint
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner, build_step_hooks
from .base import ResumeStrategy, register_resume

logger = logging.getLogger("kitchen_agent")


@register_resume
class ParallelResumeStrategy(ResumeStrategy):
    name = "parallel"

    def can_handle(self, executor_state: Dict[str, Any]) -> bool:
        return "batches" in executor_state

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
        batches = executor_state["batches"]
        completed = set(executor_state.get("completed_step_indices", []))

        from ..resume import _seed_completed_steps

        _seed_completed_steps(tracker, cp, steps)

        logger.info(f"   新 Run ID: {tracker.record.run_id}")
        logger.info(f"   已完成的步骤: {sorted(completed)}")
        completed_step_indices = list(completed)
        hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=True)
        runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)

        cp_service = CheckpointService(tracker, CheckpointManager(backend=tracker._backend))

        for batch_idx, batch in enumerate(batches, 1):
            if all(i in completed for i in batch):
                logger.info(f"   批次 {batch_idx} 已完整完成，跳过: {batch}")
                continue

            logger.info(f"\n🏃 恢复批次 {batch_idx}/{len(batches)}: 并行执行步骤 {batch}")
            if event_broadcaster:
                await event_broadcaster(
                    EventType.BATCH_START.value,
                    {
                        "batch_index": batch_idx,
                        "step_indices": batch,
                        "total_batches": len(batches),
                    },
                )

            async def _execute_one(step_index: int):
                step = steps[step_index - 1]
                tool_name = step["tool_name"]
                arguments = step["arguments"]
                group_id = step.get("parallel_group_id")
                output_variable = step.get("output_variable")

                step_rec = tracker.start_step(step_index, tool_name, arguments)
                if group_id:
                    step_rec.parallel_group_id = group_id

                logger.info(f"📌 步骤 {step_index}: [{tool_name}] args={arguments}")
                try:
                    text = await runner.run(
                        step_rec,
                        tool_name,
                        arguments,
                        output_variable=output_variable,
                        compensator=step.get("compensator"),
                    )
                    logger.info(f"   ➡️  [{step_index}] {text or '(无返回内容)'}")
                    return (step_index, "success", text)
                except Exception as e:
                    logger.error(f"   ❌ [{step_index}] 调用失败: {e}")
                    return (step_index, "error", str(e))

            results = await asyncio.gather(
                *[_execute_one(i) for i in batch], return_exceptions=True
            )

            for r in results:
                if isinstance(r, tuple) and r[1] == "success":
                    completed_step_indices.append(r[0])

            # 保存批次级 checkpoint
            executor_state = {
                "batches": batches,
                "completed_step_indices": completed_step_indices,
            }
            cp = await cp_service.save_after_step(
                step_index=batch[-1],
                executor_state=executor_state,
            )
            if cp:
                tracker.record.checkpoint_id = cp.checkpoint_id

            if event_broadcaster:
                await event_broadcaster(
                    EventType.BATCH_FINISH.value,
                    {
                        "batch_index": batch_idx,
                        "step_indices": batch,
                    },
                )

            errors = [r for r in results if isinstance(r, Exception) or (isinstance(r, tuple) and r[1] == "error")]
            if errors:
                logger.error("批次执行出错，停止后续步骤")
                break

        logger.info("=" * 60)
        logger.info(f"🎉 并行恢复执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
