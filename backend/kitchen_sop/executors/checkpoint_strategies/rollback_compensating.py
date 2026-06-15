"""补偿回滚策略：先反向补偿，再重新执行."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...skill.template import render_sop
from ...tracker import RunTracker
from ...tracker.models import StepRecord
from ..base import log_step_call, log_step_result, log_step_error
from ..step_runner import StepRunner, build_step_hooks
from .base import RollbackStrategy, register_rollback

logger = logging.getLogger("kitchen_agent")


@register_rollback
class RollbackCompensatingStrategy(RollbackStrategy):
    name = "rollback_compensating"

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

        orig_steps: List[StepRecord] = kwargs.get("orig_steps") or []
        orig_context_by_index = {
            s.step_index: s.compensation_context
            for s in orig_steps
            if s.compensation_context
        }
        variables = tracker.record.variables or {}

        # 反向补偿：从最后一步到 to_step（含）
        for idx in range(len(steps), to_step - 1, -1):
            step = steps[idx - 1]
            compensator = step.get("compensator")
            compensation_context = orig_context_by_index.get(idx)
            if compensator and compensation_context:
                comp_tool = compensator.get("tool_name")
                comp_args_raw = compensator.get("arguments", {})
                # 渲染补偿参数：使用 variables + compensation_context
                render_vars = {**variables, **compensation_context}
                comp_args = {}
                for k, v in comp_args_raw.items():
                    comp_args[k] = render_sop(str(v), render_vars)
                    # 类型转换
                    if isinstance(comp_args[k], str):
                        if comp_args[k].lower() == "true":
                            comp_args[k] = True
                        elif comp_args[k].lower() == "false":
                            comp_args[k] = False
                        else:
                            try:
                                comp_args[k] = int(comp_args[k])
                            except ValueError:
                                pass

                logger.info(f"   🔄 补偿步骤 {idx}: [{comp_tool}] args={comp_args}")
                comp_step_rec = tracker.start_step(idx, comp_tool, comp_args)
                try:
                    text = await runner.run(
                        comp_step_rec,
                        comp_tool,
                        comp_args,
                    )
                    comp_step_rec.compensation_status = {
                        "compensated": True,
                        "result_text": text,
                    }
                    logger.info(f"   ➡️  补偿成功: {text}")
                except Exception as e:
                    comp_step_rec.compensation_status = {
                        "compensated": False,
                        "error": str(e),
                    }
                    logger.error(f"   ❌ 补偿失败: {e}")

        # 正向重新执行
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
        logger.info(f"🎉 补偿回滚执行完毕！{tracker.record.skill_name} 已完成~")
        logger.info("=" * 60)
