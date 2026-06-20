"""Skill 参考资料解析：负责根据 frontmatter 加载 reference."""

from typing import List, Optional

from ..skill import ReferenceLoader


class ReferenceResolver:
    """负责解析并格式化 Skill 参考资料."""

    def __init__(self, skill):
        self.skill = skill

    def list_reference_files(self) -> List[str]:
        """返回实际存在的参考文件名列表."""
        refs = self.skill.list_references()
        return [r.name for r in refs]

    def resolve(self) -> Optional[str]:
        """根据 frontmatter `references` 显式加载；未指定则加载全部."""
        ref_files = self.skill.metadata.get("references") if self.skill.metadata else None
        return ReferenceLoader.format_for_prompt(self.skill.reference_dir, files=ref_files)

    @property
    def explicit_references(self) -> List[str]:
        """frontmatter 中显式声明的 references 列表."""
        return self.skill.reference_files
