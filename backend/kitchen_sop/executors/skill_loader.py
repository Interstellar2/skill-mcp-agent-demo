"""Skill 加载相关职责封装，避免 SkillExecutorContext 成为上帝组件."""

from pathlib import Path
from typing import Dict, Optional

from ..config import SKILLS_DIR
from ..skill import SkillsManager


class SkillLoader:
    """负责发现并加载单个 Skill."""

    def __init__(self, skills_dir=None):
        self.skills_directory = Path(skills_dir) if skills_dir else SKILLS_DIR
        self._sm = SkillsManager(self.skills_directory)

    def load(self, skill_name: str):
        """加载 Skill；找不到时抛出 ValueError."""
        skill = self._sm.skills.get(skill_name)
        if not skill:
            raise ValueError(f"找不到 Skill: {skill_name}")
        return skill, self._sm

    @property
    def skills(self) -> Dict[str, any]:
        return self._sm.skills
