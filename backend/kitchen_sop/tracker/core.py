"""RunTracker 核心：内存状态跟踪器."""

import copy
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ExecutionPlan, RunRecord, StepRecord
from ..config import RUNS_DIR
from .state_backend import StateBackend, get_state_backend

logger = logging.getLogger("kitchen_agent")


class RunTracker:
    """追踪一次 Skill 执行的完整生命周期（仅内存状态）.

    Usage:
        async with RunTracker(skill_name, mode="demo") as tracker:
            step_rec = tracker.start_step(1, "cut_ingredient", {"ingredient": "番茄"})
            try:
                result = await session.call_tool(...)
                await tracker.finish_step(step_rec, result_text="...")
            except Exception as e:
                await tracker.fail_step(step_rec, str(e))
    """

    def __init__(
        self,
        skill_name: str,
        mode: str,
        variables: Optional[dict] = None,
        runs_dir=None,
        backend: Optional[StateBackend] = None,
    ):
        self.record = RunRecord.new(skill_name, mode, variables)
        self.runs_dir = Path(runs_dir) if runs_dir else RUNS_DIR
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._backend = backend or get_state_backend()

    async def __aenter__(self):
        logger.info(f"📊 RunTracker 启动 | run_id={self.record.run_id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.record.ended_at = datetime.now().isoformat(timespec="seconds")
        if exc_type is not None:
            self.record.overall_status = "error"
        else:
            self.record.overall_status = "success"
        await self._persist()
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

    async def finish_step(
        self,
        step: StepRecord,
        result_text: Optional[str] = None,
    ):
        step.ended_at = datetime.now().isoformat(timespec="seconds")
        step.status = "success"
        step.result_text = result_text
        step.duration_ms = self._calc_duration_ms(step.started_at, step.ended_at)

    async def fail_step(
        self,
        step: StepRecord,
        error_message: str,
    ):
        step.ended_at = datetime.now().isoformat(timespec="seconds")
        step.status = "error"
        step.error_message = error_message
        step.duration_ms = self._calc_duration_ms(step.started_at, step.ended_at)

    def update_variables(self, updates: dict):
        """安全深合并更新 variables."""
        if not updates:
            return
        if self.record.variables is None:
            self.record.variables = {}
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(self.record.variables.get(key), dict):
                self.record.variables[key] = copy.deepcopy(self.record.variables[key])
                self.record.variables[key].update(value)
            else:
                self.record.variables[key] = copy.deepcopy(value)
        logger.debug(f"Variables 更新: {updates}")

    async def set_execution_plan(self, plan: ExecutionPlan):
        """把生成的执行计划写入 RunRecord."""
        self.record.execution_plan = plan
        await self._persist()

    async def _persist(self):
        await self._backend.save_run(self.record)
        logger.debug(f"RunTracker 已持久化: {self.record.run_id}")

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
    async def list_runs(
        cls,
        runs_dir=None,
        limit: int = 20,
        backend: Optional[StateBackend] = None,
    ) -> List[RunRecord]:
        backend = backend or get_state_backend()
        return await backend.list_runs(limit=limit)

    @classmethod
    async def load_run(
        cls,
        run_id: str,
        runs_dir=None,
        backend: Optional[StateBackend] = None,
    ) -> Optional[RunRecord]:
        backend = backend or get_state_backend()
        return await backend.load_run(run_id)

    @classmethod
    async def delete_run(
        cls,
        run_id: str,
        backend: Optional[StateBackend] = None,
    ) -> None:
        backend = backend or get_state_backend()
        await backend.delete_run(run_id)
