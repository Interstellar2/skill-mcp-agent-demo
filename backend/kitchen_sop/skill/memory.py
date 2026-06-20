"""Skill 持久记忆：按 skill 存储 key-value 数据."""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import PROJECT_ROOT


class SkillMemory:
    """单个 Skill 的持久化记忆.

    数据以 JSON 形式保存在 `data/skills/<skill_name>.json`，可通过环境变量
    `KITCHEN_SKILL_DATA_DIR` 覆盖存储目录。
    """

    def __init__(self, skill_name: str, data_dir: Optional[Path] = None):
        self.skill_name = skill_name
        if data_dir is None:
            env_dir = os.environ.get("KITCHEN_SKILL_DATA_DIR")
            data_dir = Path(env_dir) if env_dir else PROJECT_ROOT / "data" / "skills"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._data_path = self.data_dir / f"{skill_name}.json"
        self._data = self._load()

    def _load(self) -> dict:
        if not self._data_path.exists():
            return {}
        try:
            return json.loads(self._data_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """读取记忆项."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """写入记忆项（需调用 save 才会持久化）."""
        self._data[key] = value

    def touch_last_run(self) -> None:
        """更新最后运行时间."""
        self._data["last_run_at"] = datetime.now().isoformat(timespec="seconds")

    def _save_sync(self) -> None:
        """原子写入磁盘."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.data_dir), suffix=".json", prefix=f".{self.skill_name}_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            raise
        os.replace(tmp_path, self._data_path)

    async def save(self) -> None:
        """异步保存记忆到磁盘."""
        await asyncio.to_thread(self._save_sync)
