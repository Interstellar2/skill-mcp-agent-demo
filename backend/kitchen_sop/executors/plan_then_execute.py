"""Plan-then-Execute 模式：先由 LLM 生成结构化执行计划，再严格按计划顺序执行."""

import json
import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI

from ..mcp_client import get_mcp_tools
from ..tracker import RunTracker
from .base import SkillExecutorContext, execute_step, log_step_call, log_step_result, log_step_error

logger = logging.getLogger("kitchen_agent")

PLAN_PROMPT = """你是一位严谨的中餐厨师规划师。请根据以下SOP，制定一个详细的执行计划。

要求：
1. 将SOP中的每个操作转化为一个具体的工具调用步骤
2. 明确每个步骤的工具名称和参数（参数必须是合法的JSON值）
3. 不要执行工具，只输出计划
4. 输出必须是合法的JSON格式

SOP：
{sop}

可用工具列表：
{tools_desc}

请以如下JSON格式输出执行计划，不要包含任何其他文字：
{{
  "steps": [
    {{
      "step_index": 1,
      "tool_name": "工具名",
      "arguments": {{"参数名": "参数值"}},
      "reasoning": "执行此步骤的原因"
    }}
  ],
  "estimated_duration_ms": 60000
}}
"""


async def _generate_plan(
    llm: ChatOpenAI,
    rendered_sop: str,
    tools_desc: str,
    reference_text: str,
) -> list:
    """调用 LLM 生成执行计划，返回步骤列表."""
    prompt = PLAN_PROMPT.format(
        sop=rendered_sop + "\n" + reference_text,
        tools_desc=tools_desc,
    )

    messages = [{"role": "user", "content": prompt}]
    response = await llm.ainvoke(messages)
    content = response.content if hasattr(response, "content") else str(response)

    # 提取 JSON
    try:
        # 尝试直接解析
        plan_data = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        import re
        match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            plan_data = json.loads(match.group(1))
        else:
            match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                plan_data = json.loads(match.group(1))
            else:
                raise ValueError(f"无法从 LLM 响应中解析计划: {content[:200]}")

    steps = plan_data.get("steps", [])
    if not steps:
        raise ValueError("LLM 生成的计划为空")

    logger.info(f"📋 计划已生成，共 {len(steps)} 个步骤")
    for s in steps:
        logger.info(f"   [{s['step_index']}] {s['tool_name']} | args={s['arguments']} | {s.get('reasoning', '')}")

    return steps


async def run_plan_then_execute_mode(
    skill_name: str = "tomato_egg",
    skills_dir=None,
    model: Optional[str] = None,
    variables: Optional[dict] = None,
):
    """Plan-then-Execute 模式：
    Phase 1 - LLM 生成结构化执行计划；
    Phase 2 - 执行器严格按计划顺序调用工具，不依赖 LLM 决策。
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = model or os.environ.get("MODEL", "gpt-4o-mini")

    if not api_key:
        logger.error("未设置 OPENAI_API_KEY，无法运行 Plan-then-Execute 模式")
        logger.info("提示: 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY='your-key'")
        return

    async with SkillExecutorContext(
        skill_name, skills_dir=skills_dir, variables=variables, need_steps=False
    ) as ctx:
        logger.info("=" * 60)
        logger.info("📋 Plan-then-Execute 模式: 计划 → 执行")
        logger.info(f"   模型: {model}")
        logger.info(f"   Skill: {skill_name}")
        logger.info("=" * 60)

        async with get_mcp_tools() as (tools, session):
            tools_desc = "\n".join(
                f"- {t.name}: {t.description}" for t in tools
            )

            llm_kwargs = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                llm_kwargs["base_url"] = base_url
            llm = ChatOpenAI(**llm_kwargs)

            # ========== Phase 1: 生成计划 ==========
            logger.info("🧠 Phase 1: 生成执行计划...")
            try:
                plan_steps = await _generate_plan(llm, ctx.rendered_sop, tools_desc, ctx.reference_text)
            except Exception as e:
                logger.error(f"计划生成失败: {e}")
                return

            # ========== Phase 2: 执行计划 ==========
            logger.info("=" * 60)
            logger.info("🔨 Phase 2: 按序执行计划...")
            logger.info("=" * 60)

            async with RunTracker(
                skill_name, mode="plan_then_execute", variables=ctx.merged_vars
            ) as tracker:
                logger.info(f"   Run ID: {tracker.record.run_id}")

                for step_data in plan_steps:
                    idx = step_data.get("step_index", 0)
                    tool_name = step_data["tool_name"]
                    arguments = step_data.get("arguments", {})
                    reasoning = step_data.get("reasoning", "")

                    step_rec = tracker.start_step(idx, tool_name, arguments)
                    log_step_call(idx, tool_name, arguments)
                    if reasoning:
                        logger.info(f"   理由: {reasoning}")

                    try:
                        text = await execute_step(session, tracker, step_rec, tool_name, arguments)
                        log_step_result(text)
                    except Exception as e:
                        log_step_error(e)
                        logger.info("计划执行中断，后续步骤已跳过")
                        break

                logger.info("=" * 60)
                logger.info(f"🎉 计划执行完毕！{skill_name} 已完成~")
                logger.info("=" * 60)
