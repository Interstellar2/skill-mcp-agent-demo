"""Checkpoint 管理器：支持断电续作和回滚."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import RUNS_DIR
from .models import Checkpoint, StepRecord

logger = logging.getLogger("kitchen_agent")

CHECKPOINTS_DIR = RUNS_DIR / "checkpoints"


class CheckpointManager:
    """检查点管理器：保存和加载执行状态快照."""

    def __init__(self, runs_dir=None):
        self.cp_dir = Path(runs_dir) / "checkpoints" if runs_dir else CHECKPOINTS_DIR
        self.cp_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        run_id: str,
        step_index: int,
        step_status: str,
        variables: Dict[str, Any],
        step_results: List[StepRecord],
    ) -> Checkpoint:
        """保存一个检查点."""
        cp = Checkpoint(
            checkpoint_id=uuid.uuid4().hex[:12],
            run_id=run_id,
            step_index=step_index,
            step_status=step_status,
            variables=variables,
            step_results=[s.to_dict() for s in step_results],
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        path = self.cp_dir / f"{run_id}_{cp.checkpoint_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cp.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"Checkpoint 已保存: {path} (step={step_index}, status={step_status})")
        return cp

    def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        """列出某个 run 的所有检查点，按创建时间排序."""
        pattern = f"{run_id}_*.json"
        files = sorted(
            self.cp_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
        )
        cps = []
        for f in files:
            with open(f, "r", encoding="utf-8") as fh:
                cps.append(Checkpoint.from_dict(json.load(fh)))
        return cps

    def get_latest_checkpoint(self, run_id: str) -> Optional[Checkpoint]:
        """获取某个 run 最新的检查点."""
        cps = self.list_checkpoints(run_id)
        return cps[-1] if cps else None

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """通过 checkpoint_id 加载检查点."""
        for f in self.cp_dir.glob(f"*_{checkpoint_id}.json"):
            with open(f, "r", encoding="utf-8") as fh:
                return Checkpoint.from_dict(json.load(fh))
        return None

    def delete_run_checkpoints(self, run_id: str):
        """删除某个 run 的所有检查点."""
        pattern = f"{run_id}_*.json"
        for f in self.cp_dir.glob(pattern):
            f.unlink()
            logger.debug(f"Checkpoint 已删除: {f}")
