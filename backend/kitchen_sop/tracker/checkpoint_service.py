"""CheckpointService：决定何时保存 checkpoint，并写入 CheckpointManager."""

import logging
from typing import Any, Dict, Optional

from .core import RunTracker
from .checkpoint import CheckpointManager
from .models import Checkpoint, StepRecord
from .retention import CheckpointRetentionPolicy, RetentionPolicyEnforcer

logger = logging.getLogger("kitchen_agent")


class CheckpointService:
    """封装 checkpoint 保存时机与保留策略.

    RunTracker 只维护内存 RunRecord；本服务负责在 before/after/error
    三个时机把状态快照写入 CheckpointManager，并触发保留策略清理。
    """

    def __init__(
        self,
        tracker: RunTracker,
        cp_manager: CheckpointManager,
        retention_policy: Optional[CheckpointRetentionPolicy] = None,
        retention_enforcer: Optional[RetentionPolicyEnforcer] = None,
    ):
        self.tracker = tracker
        self.cp_manager = cp_manager
        self.retention_policy = retention_policy or CheckpointRetentionPolicy()
        self.retention_enforcer = retention_enforcer or RetentionPolicyEnforcer(
            cp_manager.backend
        )

    async def save_before_step(
        self,
        step_index: int,
        tool_name: str,
        arguments: Dict[str, Any],
        executor_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Checkpoint]:
        """在执行某步之前保存检查点."""
        cp = await self.cp_manager.save_checkpoint(
            run_id=self.tracker.record.run_id,
            step_index=step_index,
            step_status="before_step",
            variables=self.tracker.record.variables or {},
            step_results=self.tracker.record.steps,
            executor_state=executor_state,
        )
        self.tracker.record.checkpoint_id = cp.checkpoint_id
        await self._apply_retention()
        return cp

    async def save_after_step(
        self,
        step: Optional[StepRecord] = None,
        step_index: Optional[int] = None,
        executor_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Checkpoint]:
        """在步骤成功后保存检查点."""
        idx = step.step_index if step else step_index
        if idx is None:
            return None
        cp = await self.cp_manager.save_checkpoint(
            run_id=self.tracker.record.run_id,
            step_index=idx,
            step_status="after_step",
            variables=self.tracker.record.variables or {},
            step_results=self.tracker.record.steps,
            executor_state=executor_state,
        )
        if step:
            step.checkpoint_id = cp.checkpoint_id
        self.tracker.record.checkpoint_id = cp.checkpoint_id
        await self._apply_retention()
        return cp

    async def save_on_error(
        self,
        step: Optional[StepRecord] = None,
        step_index: Optional[int] = None,
        executor_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Checkpoint]:
        """在步骤失败后保存检查点."""
        idx = step.step_index if step else step_index
        if idx is None:
            return None
        cp = await self.cp_manager.save_checkpoint(
            run_id=self.tracker.record.run_id,
            step_index=idx,
            step_status="error",
            variables=self.tracker.record.variables or {},
            step_results=self.tracker.record.steps,
            executor_state=executor_state,
        )
        if step:
            step.checkpoint_id = cp.checkpoint_id
        self.tracker.record.checkpoint_id = cp.checkpoint_id
        await self._apply_retention()
        return cp

    async def _apply_retention(self) -> None:
        if self.retention_enforcer:
            await self.retention_enforcer.apply_policy(
                self.tracker.record.run_id, self.retention_policy
            )
