"""Checkpoint 管理器：只做 CRUD，不处理保留策略与本地目录创建."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Checkpoint, StepRecord
from .state_backend import StateBackend, get_state_backend

logger = logging.getLogger("kitchen_agent")


class CheckpointManager:
    """检查点管理器：保存和加载执行状态快照."""

    def __init__(self, backend: Optional[StateBackend] = None):
        self._backend = backend or get_state_backend()

    @property
    def backend(self) -> StateBackend:
        return self._backend

    async def save_checkpoint(
        self,
        run_id: str,
        step_index: int,
        step_status: str,
        variables: Dict[str, Any],
        step_results: List[StepRecord],
        executor_state: Optional[Dict[str, Any]] = None,
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
            executor_state=executor_state,
        )
        await self._backend.save_checkpoint(cp)
        logger.debug(f"Checkpoint 已保存: {cp.checkpoint_id} (step={step_index}, status={step_status})")
        return cp

    async def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        """列出某个 run 的所有检查点，按创建时间排序."""
        return await self._backend.list_checkpoints(run_id)

    async def get_latest_checkpoint(self, run_id: str) -> Optional[Checkpoint]:
        """获取某个 run 最新的检查点."""
        cps = await self.list_checkpoints(run_id)
        return cps[-1] if cps else None

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """通过 checkpoint_id 加载检查点."""
        return await self._backend.load_checkpoint(checkpoint_id)

    async def delete_run_checkpoints(self, run_id: str):
        """删除某个 run 的所有检查点."""
        await self._backend.delete_run_checkpoints(run_id)
        logger.debug(f"Run checkpoints deleted: {run_id}")
