"""Agent 模式：使用 LangChain + LLM 自主决策调用工具."""

import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..skill_manager import SkillsManager
from ..mcp_client import get_mcp_tools
from ..template_engine import render_sop, _resolve_variables, render_template_file
from ..tracker import RunTracker
from ..script_runner import ScriptContext, ScriptRunner
from ..reference_loader import ReferenceLoader
from ..config import SKILLS_DIR


logger = logging.getLogger("kitchen_agent")


async def run_agent_mode(
    skill_name: str = "tomato_egg",
    skills_dir = None,
    model: Optional[str] = None,
    query: str = "请按照 SOP 制作番茄炒鸡蛋",
    variables: Optional[dict] = None,
):
    """Agent 模式: 使用 LangChain + LLM，让大模型根据 SOP 自主决策调用工具.

    配置来源优先级: 函数参数 > .env / 环境变量 > 默认值.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = model or os.environ.get("MODEL", "gpt-4o-mini")

    if not api_key:
        logger.error("未设置 OPENAI_API_KEY，无法运行 Agent 模式")
        logger.info("提示: 在项目根目录创建 .env 文件，写入 OPENAI_API_KEY='your-key'")
        logger.info("   或使用 Demo 模式: python main.py --demo")
        return

    # 加载 Skill
    sm = SkillsManager(skills_dir or SKILLS_DIR)
    skill = sm.skills.get(skill_name)
    if not skill:
        logger.error(f"找不到 Skill: {skill_name}")
        return

    # 合并变量默认值与 CLI 覆盖值
    merged_vars = _resolve_variables(skill.metadata.get("variables", {}), variables)
    if merged_vars:
        logger.info(f"📋 变量: {merged_vars}")

    # --- Scripts: pre hook ---
    scripts_meta = skill.metadata.get("scripts", {})
    script_runner = ScriptRunner()
    pre_script = scripts_meta.get("pre")
    if pre_script:
        ctx = ScriptContext(skill.name, merged_vars)
        script_runner.run(skill.dir / pre_script, ctx)
        if ctx.output:
            logger.info(f"   脚本输出: {ctx.output}")

    raw_sop = sm.activate_skill(skill_name)
    rendered_sop = render_sop(raw_sop, merged_vars)

    logger.info("=" * 60)
    logger.info("🤖 Agent 模式: 启动 LangChain Agent")
    logger.info(f"   模型: {model}")
    logger.info(f"   Base URL: {base_url or '默认'}")
    logger.info(f"   Skill: {skill_name}")
    logger.info("=" * 60)

    # --- Reference: 拼接到 system prompt ---
    reference_text = ReferenceLoader.format_for_prompt(skill.reference_dir)
    if reference_text:
        logger.info(f"📚 已加载 {len(skill.list_references())} 篇参考资料")

    # 连接 MCP 并加载工具
    async with get_mcp_tools() as (tools, session):
        logger.info(f"🔧 已加载 {len(tools)} 个 MCP 工具:")
        for t in tools:
            logger.info(f"   - {t.name}: {t.description[:50]}...")

        llm_kwargs = {"model": model, "temperature": 0, "api_key": api_key}
        if base_url:
            llm_kwargs["base_url"] = base_url

        llm = ChatOpenAI(**llm_kwargs)

        system_prompt = f"""你是一位专业的中餐厨师助手。你的任务是根据给定的标准操作流程（SOP），一步一步地调用厨房工具来完成菜肴的制作。

## 当前 SOP

{rendered_sop}
{reference_text}
## 工作规则

1. 严格按照 SOP 的步骤顺序操作，不要跳过任何步骤。
2. 每个步骤中，根据 SOP 的参数要求调用对应工具。
3. 调用工具后，等待结果再继续下一步。
4. 如果某一步调用失败，尝试修复参数后重试一次。
5. 完成后向用户汇报成果。
"""

        async with RunTracker(
            skill_name, mode="agent", variables=merged_vars
        ) as tracker:
            logger.info(f"   Run ID: {tracker.record.run_id}")

            # Monkey-patch session.call_tool 以记录每一次工具调用
            original_call_tool = session.call_tool

            async def tracked_call_tool(tool_name, arguments):
                step_rec = tracker.start_step(
                    len(tracker.record.steps) + 1, tool_name, arguments
                )
                try:
                    result = await original_call_tool(tool_name, arguments=arguments)
                    text = None
                    if result.content:
                        text = (
                            result.content[0].text
                            if hasattr(result.content[0], "text")
                            else str(result.content[0])
                        )
                    tracker.finish_step(step_rec, result_text=text)
                    return result
                except Exception as e:
                    tracker.fail_step(step_rec, error_message=str(e))
                    raise

            session.call_tool = tracked_call_tool

            agent = create_agent(
                model=llm,
                tools=tools,
                system_prompt=system_prompt,
            )

            logger.info(f"🚀 开始执行: {query}")
            result = await agent.ainvoke({"messages": [("user", query)]})

            # 提取最后一条 AI 消息的内容
            output = "(无输出)"
            if result.get("messages"):
                last_msg = result["messages"][-1]
                output = getattr(last_msg, "content", str(last_msg))

            logger.info("=" * 60)
            logger.info("📋 Agent 最终回答:")
            logger.info(output)
            logger.info("=" * 60)

    # --- Scripts: post hook ---
    post_script = scripts_meta.get("post")
    if post_script:
        ctx = ScriptContext(skill.name, merged_vars)
        script_runner.run(skill.dir / post_script, ctx)
        if ctx.output:
            logger.info(f"   脚本输出: {ctx.output}")

    # --- Templates: 渲染输出 ---
    templates_meta = skill.metadata.get("templates", {})
    report_template = templates_meta.get("report") or templates_meta.get("default")
    if report_template:
        template_path = skill.dir / report_template
        template_vars = {**merged_vars, "dish_name": skill.name}
        report = render_template_file(template_path, template_vars)
        if report:
            logger.info("=" * 60)
            logger.info("📋 执行报告:")
            logger.info(report)
            logger.info("=" * 60)
