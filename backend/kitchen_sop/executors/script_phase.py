"""Skill 脚本阶段封装：负责 pre/post 脚本的执行."""

from pathlib import Path
from typing import Optional

from ..skill import ScriptContext, ScriptRunner
from ..skill.memory import SkillMemory


class ScriptPhase:
    """负责运行 Skill 的 pre/post 脚本."""

    def __init__(
        self,
        skill,
        script_runner: ScriptRunner,
        memory: Optional[SkillMemory] = None,
    ):
        self.skill = skill
        self.script_runner = script_runner
        self.memory = memory
        self.scripts_meta = skill.metadata.get("scripts", {}) if skill.metadata else {}

    def run_pre(self, merged_vars: Optional[dict] = None) -> str:
        """执行 pre 脚本，返回 stdout。"""
        pre_script = self.scripts_meta.get("pre")
        if not pre_script:
            return ""
        ctx = ScriptContext(
            self.skill.name,
            merged_vars or {},
            data_dir=self.memory.data_dir if self.memory else None,
        )
        self.script_runner.run(self.skill.dir / pre_script, ctx)
        return ctx.output

    def run_post(self, merged_vars: Optional[dict] = None) -> str:
        """执行 post 脚本，返回 stdout。"""
        post_script = self.scripts_meta.get("post")
        if not post_script:
            return ""
        ctx = ScriptContext(
            self.skill.name,
            merged_vars or {},
            data_dir=self.memory.data_dir if self.memory else None,
        )
        self.script_runner.run(self.skill.dir / post_script, ctx)
        return ctx.output
