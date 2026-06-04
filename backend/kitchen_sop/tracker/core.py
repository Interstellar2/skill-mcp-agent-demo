"""RunTracker 核心：上下文管理器 + 持久化 + 查询."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import RunRecord, StepRecord
from ..config import RUNS_DIR

logger = logging.getLogger("kitchen_agent")


class RunTracker:
    """追踪一次 Skill 执行的完整生命周期.

    Usage:
        async with RunTracker(skill_name, mode="demo") as tracker:
            step_rec = tracker.start_step(1, "cut_ingredient", {"ingredient": "番茄"})
            try:
                result = await session.call_tool(...)
                tracker.finish_step(step_rec, result_text="...")
            except Exception as e:
                tracker.fail_step(step_rec, str(e))
    """

    def __init__(
        self,
        skill_name: str,
        mode: str,
        variables: Optional[dict] = None,
        runs_dir = None,
    ):
        self.record = RunRecord.new(skill_name, mode, variables)
        self.runs_dir = Path(runs_dir) if runs_dir else RUNS_DIR
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        logger.info(f"📊 RunTracker 启动 | run_id={self.record.run_id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.record.ended_at = datetime.now().isoformat(timespec="seconds")
        if exc_type is not None:
            self.record.overall_status = "error"
        else:
            self.record.overall_status = "success"
        self._persist()
        logger.info(
            f"📊 RunTracker 结束 | run_id={self.record.run_id} | "
            f"status={self.record.overall_status} | steps={len(self.record.steps)}"
        )
        return False

    def start_step(
        self,
        step_index: int,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> StepRecord:
        step = StepRecord(
            step_index=step_index,
            tool_name=tool_name,
            arguments=arguments,
            status="pending",
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.record.steps.append(step)
        return step

    def finish_step(self, step: StepRecord, result_text: Optional[str] = None):
        step.ended_at = datetime.now().isoformat(timespec="seconds")
        step.status = "success"
        step.result_text = result_text
        step.duration_ms = self._calc_duration_ms(step.started_at, step.ended_at)

    def fail_step(self, step: StepRecord, error_message: str):
        step.ended_at = datetime.now().isoformat(timespec="seconds")
        step.status = "error"
        step.error_message = error_message
        step.duration_ms = self._calc_duration_ms(step.started_at, step.ended_at)

    def _persist(self):
        path = self.runs_dir / f"{self.record.run_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.record.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"RunTracker 已持久化: {path}")

    @staticmethod
    def _calc_duration_ms(start: Optional[str], end: Optional[str]) -> Optional[int]:
        if not start or not end:
            return None
        try:
            t0 = datetime.fromisoformat(start)
            t1 = datetime.fromisoformat(end)
            return int((t1 - t0).total_seconds() * 1000)
        except Exception:
            return None

    @classmethod
    def list_runs(cls, runs_dir = None, limit: int = 20) -> List[RunRecord]:
        d = Path(runs_dir) if runs_dir else RUNS_DIR
        if not d.exists():
            return []
        files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        records = []
        for f in files[:limit]:
            with open(f, "r", encoding="utf-8") as fh:
                records.append(RunRecord.from_dict(json.load(fh)))
        return records

    @classmethod
    def load_run(cls, run_id: str, runs_dir = None) -> Optional[RunRecord]:
        d = Path(runs_dir) if runs_dir else RUNS_DIR
        path = d / f"{run_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return RunRecord.from_dict(json.load(f))
