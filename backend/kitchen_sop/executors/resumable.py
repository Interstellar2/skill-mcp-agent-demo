"""Checkpoint Resumable 模式：顺序执行并自动保存检查点."""

import logging
from typing import Optional

from ..mcp_client import get_mcp_tools
from ..tracker import RunTracker
from .base import SkillExecutorContext, execute_step, log_step_call, log_step_result, log_step_error

logger = logging.getLogger("kitchen_agent")


async def run_resumable_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    variables: Optional[dict] = None,
):
    """Resumable 顺序执行模式：与 demo 类似，但启用 checkpoint.

    适用于需要断电续作的场景，每次执行都会保存检查点。
    """
    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables
    ) as ctx:
        steps = ctx.steps

        logger.info("=" * 60)
        logger.info("💾 Resumable 模式: 顺序执行 + 自动检查点")
        logger.info(f"   Skill: {skill_name}")
        logger.info(f"   共 {len(steps)} 个步骤")
        logger.info("=" * 60)

        async with get_mcp_tools() as (tools, session):
            logger.info(
                f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
            )

            async with RunTracker(
                skill_name, mode="resumable", variables=ctx.merged_vars, enable_checkpoint=True
            ) as tracker:
                logger.info(f"   Run ID: {tracker.record.run_id}")

                for idx, step in enumerate(steps, 1):
                    tool_name = step["tool_name"]
                    arguments = step["arguments"]

                    # 执行前保存检查点
                    tracker.save_before_step_checkpoint(idx, tool_name, arguments)

                    step_rec = tracker.start_step(idx, tool_name, arguments)
                    log_step_call(idx, tool_name, arguments)

                    try:
                        text = await execute_step(session, tracker, step_rec, tool_name, arguments)
                        log_step_result(text)
                    except Exception as e:
                        log_step_error(e)
                        logger.info(f"💾 检查点已保存，可使用 --resume {tracker.record.run_id} 恢复")
                        break

                logger.info("=" * 60)
                logger.info(f"🎉 执行完毕！{skill_name} 已完成~")
                logger.info("=" * 60)
