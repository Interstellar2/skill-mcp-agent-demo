"""参考资料加载：自动读取 Skill reference/ 目录下的文本文件."""

from pathlib import Path
from typing import Optional


class ReferenceLoader:
    """加载并格式化 Skill 参考资料."""

    @staticmethod
    def format_for_prompt(reference_dir: Path) -> Optional[str]:
        """读取 reference 目录下所有文本文件，拼接为 prompt 格式.

        Args:
            reference_dir: Skill 的 reference/ 目录路径.

        Returns:
            格式化后的参考资料字符串；无资料时返回 None.
        """
        if not reference_dir.exists():
            return None

        files = sorted(f for f in reference_dir.iterdir() if f.is_file())
        if not files:
            return None

        sections = []
        for f in files:
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            sections.append(f"## {f.name}\n{content}")

        return "\n\n".join(sections)
