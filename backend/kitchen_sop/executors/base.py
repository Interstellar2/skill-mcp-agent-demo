"""执行器共享基类与工具函数."""

import logging
from typing import Awaitable, Callable, Optional

from ..skill import (
    parse_sop_steps,
    render_sop,
    _resolve_variables,
    render_template_file,
    ScriptRunner,
)
from ..skill.memory import SkillMemory
from .hook_resolver import HookResolver
from .reference_resolver import ReferenceResolver
from .script_phase import ScriptPhase
from .skill_loader import SkillLoader

logger = logging.getLogger("kitchen_agent")

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


class SkillExecutorContext:
    """封装所有 executor 共有的 Skill setup / teardown 逻辑.

    本类只做编排，具体职责委托给：
    - SkillLoader：加载 Skill
    - ScriptPhase：pre/post 脚本
    - ReferenceResolver：参考资料解析
    - HookResolver：skill 级 hook 解析
    - SkillMemory：skill 持久记忆

    Usage:
        async with SkillExecutorContext(skill_name, variables=...) as ctx:
            # ctx.skill, ctx.merged_vars, ctx.steps, ctx.rendered_sop, ctx.memory 已就绪
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
        self.skill = None
        self.sm = None
        self.merged_vars: Optional[dict] = None
        self.raw_sop: Optional[str] = None
        self.rendered_sop: Optional[str] = None
        self.steps: Optional[list] = None
        self.reference_text: Optional[str] = None
        self.memory: Optional[SkillMemory] = None
        self.skill_hooks = []

        # 协作者
        self._script_phase: Optional[ScriptPhase] = None

    async def __aenter__(self):
        # 1. 加载 Skill
        loader = SkillLoader(self.skills_dir)
        self.skill, self.sm = loader.load(self.skill_name)

        # 2. Skill 记忆
        self.memory = SkillMemory(self.skill.name)

        # 3. 合并变量
        self.merged_vars = _resolve_variables(
            self.skill.metadata.get("variables", {}), self.variables
        )
        if self.merged_vars:
            logger.info(f"📋 变量: {self.merged_vars}")

        # 4. Pre script
        self._script_phase = ScriptPhase(
            self.skill, ScriptRunner(), memory=self.memory
        )
        pre_output = self._script_phase.run_pre(self.merged_vars)
        if pre_output:
            logger.info(f"   脚本输出: {pre_output}")

        # 5. 参考资料
        reference_resolver = ReferenceResolver(self.skill)
        refs = reference_resolver.list_reference_files()
        if refs:
            logger.info(
                f"📚 Skill 参考资料目录共有 {len(refs)} 篇: {', '.join(refs)}"
            )
        self.reference_text = reference_resolver.resolve()
        if self.reference_text:
            explicit = reference_resolver.explicit_references
            logger.info(
                f"📚 已注入 prompt 的参考资料: {', '.join(explicit) or '全部'}"
            )

        # 6. SOP 渲染与步骤解析
        self.raw_sop = self.sm.activate_skill(self.skill_name)
        self.rendered_sop = render_sop(self.raw_sop, self.merged_vars)
        if self.need_steps:
            self.steps = parse_sop_steps(
                self.rendered_sop, sm=self.sm, variables=self.merged_vars
            )
            if not self.steps:
                raise ValueError("未从 SOP 中解析出任何工具调用步骤")

        # 7. Skill 级临时 hooks
        hook_resolver = HookResolver(self.skill)
        self.skill_hooks = hook_resolver.resolve()
        if self.skill_hooks:
            logger.info(f"🔒 已启用 skill 级 hooks: {hook_resolver.hook_names}")

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
        from ..skill import validate_skill_steps

        result = await session.list_tools()
        validate_skill_steps(self.steps, result.tools)

    async def validate_metadata_tools(self, session) -> None:
        """验证 Skill frontmatter 中声明的工具列表."""
        if not self.skill or not self.skill.metadata:
            return
        declared = self.skill.metadata.get("tools")
        if not declared:
            return
        from ..skill import validate_skill_metadata_tools

        result = await session.list_tools()
        validate_skill_metadata_tools(declared, result.tools)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 保存 skill 记忆
        if self.memory:
            try:
                self.memory.touch_last_run()
                await self.memory.save()
            except Exception:
                logger.exception("保存 Skill 记忆失败")

        # Post script
        if self._script_phase:
            post_output = self._script_phase.run_post(self.merged_vars)
            if post_output:
                logger.info(f"   脚本输出: {post_output}")

        # Templates
        templates_meta = self.skill.metadata.get("templates", {}) if self.skill else {}
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
