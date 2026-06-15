"""Local JSON state backend: atomic writes to RUNS_DIR / checkpoints/."""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import Checkpoint, RunRecord
from .base import StateBackend

logger = logging.getLogger("kitchen_agent")


class LocalJSONStateBackend(StateBackend):
    """默认本地 JSON 后端."""

    def __init__(self, runs_dir: Optional[Path] = None):
        from ...config import RUNS_DIR
        self.runs_dir = Path(runs_dir) if runs_dir else RUNS_DIR
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.cp_dir = self.runs_dir / "checkpoints"
        self.cp_dir.mkdir(parents=True, exist_ok=True)

    def _atomic_write_json(self, path: Path, data: dict):
        path = Path(path)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    async def save_run(self, run: RunRecord) -> None:
        path = self.runs_dir / f"{run.run_id}.json"
        self._atomic_write_json(path, run.to_dict())
        logger.debug(f"Run saved: {path}")

    async def load_run(self, run_id: str) -> Optional[RunRecord]:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return RunRecord.from_dict(json.load(f))

    async def list_runs(self, limit: int = 20) -> List[RunRecord]:
        if not self.runs_dir.exists():
            return []
        files = sorted(self.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        records = []
        for f in files[:limit]:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    records.append(RunRecord.from_dict(json.load(fh)))
            except Exception:
                logger.warning(f"无法读取 run 文件: {f}")
        return records

    async def delete_run(self, run_id: str) -> None:
        path = self.runs_dir / f"{run_id}.json"
        if path.exists():
            path.unlink()

    async def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        path = self.cp_dir / f"{checkpoint.run_id}_{checkpoint.checkpoint_id}.json"
        self._atomic_write_json(path, checkpoint.to_dict())
        logger.debug(f"Checkpoint saved: {path}")
        return checkpoint

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        for f in self.cp_dir.glob(f"*_{checkpoint_id}.json"):
            if f.name.startswith("."):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    return Checkpoint.from_dict(json.load(fh))
            except Exception:
                logger.warning(f"无法读取 checkpoint 文件: {f}")
        return None

    async def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        pattern = f"{run_id}_*.json"
        files = sorted(
            [f for f in self.cp_dir.glob(pattern) if not f.name.startswith(".")],
            key=lambda p: p.stat().st_mtime,
        )
        cps = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    cps.append(Checkpoint.from_dict(json.load(fh)))
            except Exception:
                logger.warning(f"无法读取 checkpoint 文件: {f}")
        return cps

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        for f in self.cp_dir.glob(f"*_{checkpoint_id}.json"):
            if f.name.startswith("."):
                continue
            try:
                f.unlink()
                logger.debug(f"Checkpoint deleted: {f}")
            except OSError:
                pass

    async def delete_run_checkpoints(self, run_id: str) -> None:
        pattern = f"{run_id}_*.json"
        for f in self.cp_dir.glob(pattern):
            if f.name.startswith("."):
                continue
            try:
                f.unlink()
                logger.debug(f"Checkpoint deleted: {f}")
            except OSError:
                pass
