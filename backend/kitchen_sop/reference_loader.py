"""Reference document loader for knowledge augmentation."""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("kitchen_agent")


class ReferenceLoader:
    """加载 Skill 目录 reference/ 下的 Markdown 参考资料."""

    @staticmethod
    def load(reference_path: Path) -> str:
        if not reference_path.exists():
            return ""
        return reference_path.read_text(encoding="utf-8")

    @staticmethod
    def load_dir(reference_dir: Path, suffix: str = ".md") -> List[str]:
        if not reference_dir.exists():
            return []
        contents = []
        for f in sorted(reference_dir.iterdir()):
            if f.is_file() and f.suffix == suffix:
                contents.append(f.read_text(encoding="utf-8"))
        return contents

    @staticmethod
    def format_for_prompt(reference_dir: Path, title: str = "参考资料") -> str:
        """将所有参考文档格式化为可插入 LLM prompt 的文本块."""
        docs = ReferenceLoader.load_dir(reference_dir)
        if not docs:
            return ""
        blocks = [f"## {title}\n"]
        for idx, doc in enumerate(docs, 1):
            blocks.append(f"### 参考文档 {idx}\n{doc}\n")
        return "\n".join(blocks)
