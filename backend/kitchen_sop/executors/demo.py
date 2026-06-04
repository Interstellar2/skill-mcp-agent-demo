"""Demo 模式：无需 LLM，直接按 SOP 步骤顺序执行."""

import logging
from typing import Optional

from ..skill_manager import SkillsManager
from ..mcp_client import get_mcp_tools
from ..sop_parser import parse_sop_steps
from ..template_engine import render_sop, _resolve_variables, render_template_file
from ..tracker import RunTracker
from ..script_runner import ScriptContext, ScriptRunner
from ..reference_loader import ReferenceLoader
from ..config import SKILLS_DIR


logger = logging.getLogger("kitchen_agent")


async def run_demo_mode(
    skill_name: str = "tomato_egg",
    skills_dir = None,
    variables: Optional[dict] = None,
):
    """Demo 模式: 直接按 SOP 步骤顺序调用 MCP 工具，无需 API Key.

    适合快速演示 Skill + MCP 的联动效果.
    """
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

    # --- Reference: 加载并提示 ---
    refs = skill.list_references()
    if refs:
        logger.info(f"📚 已加载 {len(refs)} 篇参考资料: {', '.join(r.name for r in refs)}")

    raw_sop = sm.activate_skill(skill_name)
    rendered_sop = render_sop(raw_sop, merged_vars)
    steps = parse_sop_steps(rendered_sop, sm=sm, variables=merged_vars)
    if not steps:
        logger.warning("未从 SOP 中解析出任何工具调用步骤")
        return

    logger.info("=" * 60)
    logger.info("🍳 Demo 模式: 按 SOP 顺序执行")
    logger.info(f"   Skill: {skill_name}")
    logger.info(f"   共 {len(steps)} 个步骤")
    logger.info("=" * 60)

    async with get_mcp_tools() as (tools, session):
        logger.info(
            f"🔧 已连接 MCP 服务器，可用工具: {', '.join(t.name for t in tools)}"
        )

        async with RunTracker(
            skill_name, mode="demo", variables=merged_vars
        ) as tracker:
            logger.info(f"   Run ID: {tracker.record.run_id}")

            for idx, step in enumerate(steps, 1):
                tool_name = step["tool_name"]
                arguments = step["arguments"]

                step_rec = tracker.start_step(idx, tool_name, arguments)
                logger.info(f"📌 步骤 {idx}: 调用 [{tool_name}]")
                logger.info(f"   参数: {arguments}")

                try:
                    result = await session.call_tool(tool_name, arguments=arguments)
                    if result.content:
                        text = (
                            result.content[0].text
                            if hasattr(result.content[0], "text")
                            else str(result.content[0])
                        )
                        tracker.finish_step(step_rec, result_text=text)
                        logger.info(f"   ➡️  {text}")
                    else:
                        tracker.finish_step(step_rec)
                        logger.info("   ➡️  (无返回内容)")
                except Exception as e:
                    tracker.fail_step(step_rec, error_message=str(e))
                    logger.error(f"   ❌ 调用失败: {e}")

            logger.info("=" * 60)
            logger.info(f"🎉 SOP 执行完毕！{skill_name} 已完成~")
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
