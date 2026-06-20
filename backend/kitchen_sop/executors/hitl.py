"""Human-in-the-Loop 模式：在关键步骤执行前暂停，等待人工确认."""

import logging
import os
from typing import Awaitable, Callable, Optional

from ..events import EventType
from ..mcp_client import get_mcp_tools
from ..mcp_pool import MCPConnectionPool
from ..tracker import RunTracker
from ..tracker.models import HumanApprovalRecord
from ..hitl_bridge import HITLBridge
from .base import SkillExecutorContext, log_step_call, log_step_result, log_step_error
from .step_runner import StepRunner, build_step_hooks, build_step_hooks
from .hooks import skill_hooks_scope

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


def _should_request_approval(
    step_index: int,
    tool_name: str,
    arguments: dict,
    hitl_config: list,
) -> Optional[str]:
    """根据 HITL 配置判断当前步骤是否需要人工确认，返回确认提示语或 None."""
    for cfg in hitl_config:
        matched = False
        if "step" in cfg and cfg["step"] == step_index:
            matched = True
        if "tool" in cfg and cfg["tool"] == tool_name:
            matched = True
        if matched:
            prompt = cfg.get("prompt", f"步骤 {step_index} [{tool_name}] 需要确认，是否继续？")
            # 简单模板替换
            for k, v in arguments.items():
                prompt = prompt.replace(f"{{{k}}}", str(v))
            return prompt
    return None


async def _request_human_approval_cli(prompt: str, arguments: dict) -> HumanApprovalRecord:
    """在 CLI 模式下请求人工确认."""
    ha = HumanApprovalRecord(
        requested_at=__import__("datetime").datetime.now().isoformat(timespec="seconds"),
        prompt=prompt,
    )

    print("\n" + "=" * 60)
    print("🛑 Human-in-the-Loop 请求确认")
    print(f"提示: {prompt}")
    print("操作: [Enter/y] 确认 | [n] 终止 | [modify key=value] 修改参数")
    print("=" * 60)

    try:
        user_input = input("你的选择: ").strip()
    except (EOFError, KeyboardInterrupt):
        user_input = "n"

    now = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    ha.approved_at = now
    ha.approved_by = "cli_user"

    if user_input.lower() in ("", "y", "yes"):
        ha.decision = "approved"
        logger.info("👤 用户已确认")
    elif user_input.lower() in ("n", "no"):
        ha.decision = "rejected"
        logger.info("👤 用户已拒绝")
    elif user_input.lower().startswith("modify "):
        ha.decision = "modified"
        modify_part = user_input[7:].strip()
        if "=" in modify_part:
            k, v = modify_part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if v.lower() == "true":
                v = True
            elif v.lower() == "false":
                v = False
            else:
                try:
                    v = int(v)
                except ValueError:
                    pass
            ha.modified_arguments = {k: v}
            logger.info(f"👤 用户修改参数: {k} = {v}")
        else:
            ha.decision = "approved"
            logger.info("👤 修改格式错误，按确认处理")
    else:
        ha.decision = "approved"
        logger.info("👤 默认确认")

    return ha


async def run_hitl_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    variables: Optional[dict] = None,
    tracker: Optional[RunTracker] = None,
    event_broadcaster: EventBroadcaster = None,
    hitl_bridge: Optional[HITLBridge] = None,
    mcp_pool: Optional[MCPConnectionPool] = None,
    enable_checkpoint: bool = False,
):
    """Human-in-the-Loop 模式：顺序执行 SOP，但在配置的关键步骤前暂停等待人工确认."""
    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables
    ) as ctx:
        steps = ctx.steps
        merged_vars = ctx.merged_vars
        skill = ctx.skill

        hitl_config = skill.metadata.get("human_in_the_loop", [])
        if os.environ.get("HITL_ALL_STEPS", "") == "1":
            hitl_config = [{"step": i + 1, "prompt": f"步骤 {i+1} 需要确认"} for i in range(100)]

        if not hitl_config:
            logger.warning("当前 Skill 未配置 human_in_the_loop，将按顺序执行（无中断）")

        logger.info("=" * 60)
        logger.info("🤝 Human-in-the-Loop 模式: 人在回路")
        logger.info(f"   Skill: {skill_name}")
        logger.info(f"   共 {len(steps)} 个步骤")
        if hitl_config:
            logger.info(f"   HITL 配置: {len(hitl_config)} 条规则")
        logger.info("=" * 60)

        async def _execute(session):
            await ctx.validate_steps(session)
            t = tracker or RunTracker(
                skill_name,
                mode="hitl",
                variables=merged_vars,
            )
            if tracker is None:
                async with t:
                    await _run_hitl_steps(t, session, steps, hitl_config, event_broadcaster, hitl_bridge, enable_checkpoint=enable_checkpoint, skill_hooks=ctx.skill_hooks)
            else:
                await _run_hitl_steps(t, session, steps, hitl_config, event_broadcaster, hitl_bridge, enable_checkpoint=enable_checkpoint, skill_hooks=ctx.skill_hooks)

        if mcp_pool is not None:
            await _execute(mcp_pool.session)
        else:
            async with get_mcp_tools() as (tools, session):
                logger.info(
                    f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
                )
                await _execute(session)


async def _run_hitl_steps(
    tracker: RunTracker,
    session,
    steps: list,
    hitl_config: list,
    event_broadcaster: EventBroadcaster,
    hitl_bridge: Optional[HITLBridge],
    enable_checkpoint: bool = False,
    skill_hooks=None,
):
    logger.info(f"   Run ID: {tracker.record.run_id}")
    hooks = build_step_hooks(tracker, event_broadcaster, enable_checkpoint=enable_checkpoint)
    runner = StepRunner(session, tracker, event_broadcaster, hooks=hooks)

    async with skill_hooks_scope(runner, skill_hooks or []):
        for idx, step in enumerate(steps, 1):
            tool_name = step["tool_name"]
            arguments = dict(step["arguments"])
            output_variable = step.get("output_variable")

            approval_prompt = _should_request_approval(idx, tool_name, arguments, hitl_config)
            ha = None

            if approval_prompt:
                if hitl_bridge is not None and event_broadcaster is not None:
                    await event_broadcaster(
                        EventType.HITL_REQUEST.value,
                        {
                            "approval_id": hitl_bridge.approval_id,
                            "prompt": approval_prompt,
                            "step_index": idx,
                            "arguments": arguments,
                        },
                    )
                    result = await hitl_bridge.request_approval(approval_prompt, arguments)
                    decision = result["decision"]
                    modified_args = result.get("modified_arguments", {})

                    ha = HumanApprovalRecord(
                        requested_at=__import__("datetime").datetime.now().isoformat(timespec="seconds"),
                        prompt=approval_prompt,
                        approved_at=__import__("datetime").datetime.now().isoformat(timespec="seconds"),
                        approved_by="web_user",
                        decision=decision,
                        modified_arguments=modified_args if modified_args else None,
                    )
                    if decision == "rejected":
                        step_rec = tracker.start_step(idx, tool_name, arguments)
                        await tracker.fail_step(step_rec, error_message="用户拒绝执行此步骤")
                        logger.error(f"   ❌ 步骤 {idx} 被用户拒绝，执行终止")
                        break
                    elif decision == "modified" and modified_args:
                        arguments.update(modified_args)
                else:
                    ha = await _request_human_approval_cli(approval_prompt, arguments)
                    if ha.decision == "rejected":
                        step_rec = tracker.start_step(idx, tool_name, arguments)
                        await tracker.fail_step(step_rec, error_message="用户拒绝执行此步骤")
                        logger.error(f"   ❌ 步骤 {idx} 被用户拒绝，执行终止")
                        break
                    elif ha.decision == "modified" and ha.modified_arguments:
                        arguments.update(ha.modified_arguments)
            else:
                ha = None

            step_rec = tracker.start_step(idx, tool_name, arguments)
            if ha:
                step_rec.human_approval = ha

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

    logger.info("=" * 60)
    logger.info(f"🎉 HITL 执行完毕！{tracker.record.skill_name} 已完成~")
    logger.info("=" * 60)
