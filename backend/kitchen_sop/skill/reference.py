"""参考资料加载：自动读取 Skill reference/ 目录下的文本文件."""

from pathlib import Path
from typing import List, Optional


class ReferenceLoader:
    """加载并格式化 Skill 参考资料."""

    @staticmethod
    def load_by_name(reference_dir: Path, name: str) -> Optional[str]:
        """按文件名加载单篇参考资料.

        Args:
            reference_dir: Skill 的 reference/ 目录路径.
            name: 文件名（如 `egg_tips.md`）。

        Returns:
            文件内容；文件不存在或读取失败时返回 None.
        """
        if not reference_dir.exists():
            return None
        file_path = reference_dir / name
        if not file_path.is_file():
            return None
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception:
            return None

    @staticmethod
    def format_for_prompt(reference_dir: Path, files: Optional[List[str]] = None) -> Optional[str]:
        """读取 reference 目录下文本文件，拼接为 prompt 格式.

        Args:
            reference_dir: Skill 的 reference/ 目录路径.
            files: 可选，显式指定要加载的文件名列表。未指定时加载全部文件。

        Returns:
            格式化后的参考资料字符串；无资料时返回 None.
        """
        if not reference_dir.exists():
            return None

        if files is None:
            paths = sorted(f for f in reference_dir.iterdir() if f.is_file())
        else:
            paths = []
            for name in files:
                file_path = reference_dir / name
                if file_path.is_file():
                    paths.append(file_path)

        if not paths:
            return None

        sections = []
        for f in paths:
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            sections.append(f"## {f.name}\n{content}")

        return "\n\n".join(sections)
