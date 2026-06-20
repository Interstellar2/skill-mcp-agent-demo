"""Skill hook 解析：负责根据 frontmatter 构建 skill 级 hooks."""

from typing import List

from ..skill import Skill
from .hooks import StepHook, build_skill_hooks


class HookResolver:
    """负责解析 Skill frontmatter 中的 hooks 配置."""

    def __init__(self, skill: Skill):
        self.skill = skill

    def resolve(self) -> List[StepHook]:
        """构建并返回 skill 级 hook 实例列表."""
        return build_skill_hooks(self.skill.metadata or {})

    @property
    def hook_names(self) -> List[str]:
        """返回 frontmatter 中声明的 hook 名称列表."""
        if not self.skill.metadata:
            return []
        hooks = self.skill.metadata.get("hooks", [])
        return hooks if isinstance(hooks, list) else []
