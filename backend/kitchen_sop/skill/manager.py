import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..config import SKILLS_DIR


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    dir: Path
    content: Optional[str] = None
    metadata: Optional[Dict] = None

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

        return Skill(
            name=metadata.get("name", skill_dir.name),
            description=metadata.get("description", "无描述"),
            path=skill_file,
            dir=skill_dir,
            metadata=metadata,
        )

    def activate_skill(self, skill_name: str) -> Optional[str]:
        skill = self.skills.get(skill_name)
        if skill:
            return skill.load_full_content()
        return None
