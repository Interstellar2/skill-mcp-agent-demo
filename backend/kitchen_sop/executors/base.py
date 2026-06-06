"""执行器共享基类与工具函数."""

import logging
from typing import Awaitable, Callable, Optional

from ..skill_manager import SkillsManager
from ..sop_parser import parse_sop_steps
from ..template_engine import render_sop, _resolve_variables, render_template_file
from ..script_runner import ScriptContext, ScriptRunner
from ..reference_loader import ReferenceLoader
from ..config import SKILLS_DIR

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


class SkillExecutorContext:
    """封装所有 executor 共有的 Skill setup / teardown 逻辑.

    Usage:
        async with SkillExecutorContext(skill_name, variables=...) as ctx:
            # ctx.skill, ctx.merged_vars, ctx.steps, ctx.rendered_sop 已就绪
            async with get_mcp_tools() as (tools, session):
                async with RunTracker(...) as tracker:
                    ...
    """

    def __init__(
        self,
        skill_name: str,
        skills_dir=None,
        variables: Optional[dict] = None,
        *,
        need_steps: bool = True,
    ):
        self.skill_name = skill_name
        self.skills_dir = skills_dir
        self.variables = variables
        self.need_steps = need_steps

        # 在 __aenter__ 中填充
        self.sm: Optional[SkillsManager] = None
        self.skill = None
        self.merged_vars: Optional[dict] = None
        self.scripts_meta: Optional[dict] = None
        self.script_runner: Optional[ScriptRunner] = None
        self.raw_sop: Optional[str] = None
        self.rendered_sop: Optional[str] = None
        self.steps: Optional[list] = None
        self.reference_text: Optional[str] = None

    async def __aenter__(self):
        self.sm = SkillsManager(self.skills_dir or SKILLS_DIR)
        self.skill = self.sm.skills.get(self.skill_name)
        if not self.skill:
            raise ValueError(f"找不到 Skill: {self.skill_name}")

        # 合并变量
        self.merged_vars = _resolve_variables(
            self.skill.metadata.get("variables", {}), self.variables
        )
        if self.merged_vars:
            logger.info(f"📋 变量: {self.merged_vars}")

        # Pre script
        self.scripts_meta = self.skill.metadata.get("scripts", {})
        self.script_runner = ScriptRunner()
        pre_script = self.scripts_meta.get("pre")
        if pre_script:
            ctx = ScriptContext(self.skill.name, self.merged_vars)
            self.script_runner.run(self.skill.dir / pre_script, ctx)
            if ctx.output:
                logger.info(f"   脚本输出: {ctx.output}")

        # References
        refs = self.skill.list_references()
        if refs:
            logger.info(
                f"📚 已加载 {len(refs)} 篇参考资料: {', '.join(r.name for r in refs)}"
            )

        # SOP
        self.raw_sop = self.sm.activate_skill(self.skill_name)
        self.rendered_sop = render_sop(self.raw_sop, self.merged_vars)
        if self.need_steps:
            self.steps = parse_sop_steps(
                self.rendered_sop, sm=self.sm, variables=self.merged_vars
            )
            if not self.steps:
                raise ValueError("未从 SOP 中解析出任何工具调用步骤")

        self.reference_text = ReferenceLoader.format_for_prompt(self.skill.reference_dir)
        if self.reference_text:
            logger.info(f"📚 已加载 {len(self.skill.list_references())} 篇参考资料")

        return self

    async def validate_steps(self, session) -> None:
        """用 MCP session 验证已解析的步骤（工具存在性 + 参数 Schema）.

        Args:
            session: 已初始化的 MCP ClientSession。

        Raises:
            SkillValidationError: 验证失败时抛出。
        """
        if not self.steps:
            return
        from ..skill_validator import validate_skill_steps

        result = await session.list_tools()
        validate_skill_steps(self.steps, result.tools)

    async def validate_metadata_tools(self, session) -> None:
        """验证 Skill frontmatter 中声明的工具列表."""
        if not self.skill or not self.skill.metadata:
            return
        declared = self.skill.metadata.get("tools")
        if not declared:
            return
        from ..skill_validator import validate_skill_metadata_tools

        result = await session.list_tools()
        validate_skill_metadata_tools(declared, result.tools)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Post script
        post_script = self.scripts_meta.get("post")
        if post_script and self.script_runner:
            ctx = ScriptContext(self.skill.name, self.merged_vars)
            self.script_runner.run(self.skill.dir / post_script, ctx)
            if ctx.output:
                logger.info(f"   脚本输出: {ctx.output}")

        # Templates
        templates_meta = self.skill.metadata.get("templates", {})
        report_template = templates_meta.get("report") or templates_meta.get("default")
        if report_template and self.skill:
            template_path = self.skill.dir / report_template
            template_vars = {**self.merged_vars, "dish_name": self.skill.name}
            report = render_template_file(template_path, template_vars)
            if report:
                logger.info("=" * 60)
                logger.info("📋 执行报告:")
                logger.info(report)
                logger.info("=" * 60)

        return False


async def execute_step(
    session,
    tracker,
    step_rec,
    tool_name,
    arguments,
    event_broadcaster: EventBroadcaster = None,
) -> Optional[str]:
    """调用 MCP 工具并更新 tracker.

    Returns:
        提取到的 result_text，无内容时返回 None。

    Raises:
        Exception: 工具调用失败时抛出（tracker 已记录错误）。
    """
    if event_broadcaster:
        await event_broadcaster(
            "step_start",
            {
                "step_index": step_rec.step_index,
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

    try:
        result = await session.call_tool(tool_name, arguments=arguments)
    except Exception as e:
        tracker.fail_step(step_rec, error_message=str(e))
        if event_broadcaster:
            await event_broadcaster(
                "step_error",
                {
                    "step_index": step_rec.step_index,
                    "tool_name": tool_name,
                    "error_message": str(e),
                },
            )
        raise

    text = None
    if result.content:
        text = (
            result.content[0].text
            if hasattr(result.content[0], "text")
            else str(result.content[0])
        )
    tracker.finish_step(step_rec, result_text=text)

    if event_broadcaster:
        await event_broadcaster(
            "step_finish",
            {
                "step_index": step_rec.step_index,
                "tool_name": tool_name,
                "result_text": text,
            },
        )
    return text


def log_step_call(idx, tool_name, arguments):
    """统一输出步骤调用日志."""
    logger.info(f"📌 步骤 {idx}: 调用 [{tool_name}]")
    logger.info(f"   参数: {arguments}")


def log_step_result(text: Optional[str]):
    """统一输出步骤结果日志."""
    if text:
        logger.info(f"   ➡️  {text}")
    else:
        logger.info("   ➡️  (无返回内容)")


def log_step_error(e: Exception):
    """统一输出步骤错误日志."""
    logger.error(f"   ❌ 调用失败: {e}")
