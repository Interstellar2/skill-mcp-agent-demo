"""Skill 调用埋点统计：记录每次调用并汇总."""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..config import PROJECT_ROOT


class AnalyticsTracker:
    """记录 skill 调用到本地 JSONL 文件，并提供聚合统计."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            env_dir = os.environ.get("KITCHEN_ANALYTICS_DATA_DIR")
            data_dir = Path(env_dir) if env_dir else PROJECT_ROOT / "data" / "analytics"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._invocations_path = self.data_dir / "invocations.jsonl"

    def record_invocation(
        self,
        skill_name: str,
        mode: str,
        success: bool,
    ) -> None:
        """追加一条调用记录."""
        entry = {
            "skill_name": skill_name,
            "mode": mode,
            "success": bool(success),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with open(self._invocations_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _read_entries(self) -> list:
        """读取所有调用记录."""
        if not self._invocations_path.exists():
            return []
        entries = []
        with open(self._invocations_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def get_stats(self) -> Dict[str, Dict[str, any]]:
        """返回每个 skill 的调用统计."""
        stats = defaultdict(lambda: {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "last_run_at": None,
        })
        for entry in self._read_entries():
            name = entry.get("skill_name")
            if not name:
                continue
            stats[name]["invocations"] += 1
            if entry.get("success"):
                stats[name]["successes"] += 1
            else:
                stats[name]["failures"] += 1
            ts = entry.get("timestamp")
            if ts and (stats[name]["last_run_at"] is None or ts > stats[name]["last_run_at"]):
                stats[name]["last_run_at"] = ts
        return dict(stats)

    def get_skill_stats(self, skill_name: str) -> Dict[str, any]:
        """返回单个 skill 的调用统计."""
        data = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "last_run_at": None,
        }
        for entry in self._read_entries():
            if entry.get("skill_name") != skill_name:
                continue
            data["invocations"] += 1
            if entry.get("success"):
                data["successes"] += 1
            else:
                data["failures"] += 1
            ts = entry.get("timestamp")
            if ts and (data["last_run_at"] is None or ts > data["last_run_at"]):
                data["last_run_at"] = ts
        return data
