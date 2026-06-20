import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..config import SKILLS_DIR
from .parser import parse_gotchas


logger = logging.getLogger("kitchen_agent")


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    dir: Path
    content: Optional[str] = None
    metadata: Optional[Dict] = None
    gotchas: List[str] = field(default_factory=list)

    def load_full_content(self) -> str:
        if self.content is None:
            with open(self.path, "r", encoding="utf-8") as f:
                self.content = f.read()
        return self.content

    @property
    def scripts_dir(self) -> Path:
        return self.dir / "scripts"

    @property
    def reference_dir(self) -> Path:
        return self.dir / "reference"

    @property
    def templates_dir(self) -> Path:
        return self.dir / "templates"

    @property
    def reference_files(self) -> List[str]:
        """frontmatter `references` 列表；未指定时返回空列表."""
        if not self.metadata:
            return []
        refs = self.metadata.get("references", [])
        return refs if isinstance(refs, list) else []

    def list_scripts(self) -> List[Path]:
        if not self.scripts_dir.exists():
            return []
        return [f for f in self.scripts_dir.iterdir() if f.is_file()]

    def list_references(self) -> List[Path]:
        if not self.reference_dir.exists():
            return []
        return [f for f in self.reference_dir.iterdir() if f.is_file()]

    def list_templates(self) -> List[Path]:
        if not self.templates_dir.exists():
            return []
        return [f for f in self.templates_dir.iterdir() if f.is_file()]


class SkillsManager:
    def __init__(self, skills_directory = None):
        self.skills_directory = Path(skills_directory) if skills_directory else SKILLS_DIR
        self.skills: Dict[str, Skill] = {}
        self._discover_skills()

    def _discover_skills(self):
        if not self.skills_directory.exists():
            return
        for item in self.skills_directory.iterdir():
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    try:
                        skill = self._parse_skill(item, skill_file)
                        self.skills[skill.name] = skill
                    except Exception as e:
                        print(f"加载技能失败 {item}: {e}")

    def _parse_skill(self, skill_dir: Path, skill_file: Path) -> Skill:
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1])
                except yaml.YAMLError as e:
                    print(f"frontmatter 解析失败: {e}")

        description = metadata.get("description", "无描述")
        self._warn_description(skill_dir.name, description)

        gotchas = parse_gotchas(content)

        return Skill(
            name=metadata.get("name", skill_dir.name),
            description=description,
            path=skill_file,
            dir=skill_dir,
            metadata=metadata,
            gotchas=gotchas,
        )

    @staticmethod
    def _warn_description(skill_name: str, description: str) -> None:
        """对 description 做启发式检查并打 warning."""
        if len(description) > 250:
            logger.warning(
                f"Skill '{skill_name}' 的 description 长度为 {len(description)}，"
                f"超过 250 字符，Claude Code 只能看到前 250 字符。"
            )
        trigger_prefixes = (
            "当", "如果", "如果用户", "当需要", "当用户", "当要", "use when",
            "call when", "trigger when", "when", "if ", "if you",
        )
        lowered = description.lower()
        if not any(lowered.startswith(p) for p in trigger_prefixes):
            logger.warning(
                f"Skill '{skill_name}' 的 description 看起来不像触发式描述: "
                f"{description[:50]}..."
            )

    def activate_skill(self, skill_name: str) -> Optional[str]:
        skill = self.skills.get(skill_name)
        if skill:
            return skill.load_full_content()
        return None
