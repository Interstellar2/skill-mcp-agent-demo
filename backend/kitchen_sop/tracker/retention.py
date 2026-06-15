"""Checkpoint 保留策略与清理执行器."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..tracker.models import Checkpoint
from ..tracker.state_backend import StateBackend

logger = logging.getLogger("kitchen_agent")


@dataclass
class CheckpointRetentionPolicy:
    """Checkpoint 保留策略."""

    keep_last_n: Optional[int] = 20
    keep_latest_per_step: bool = True
    ttl_hours: Optional[int] = None


class RetentionPolicyEnforcer:
    """按保留策略清理旧 checkpoint，只依赖 StateBackend."""

    def __init__(self, backend: StateBackend):
        self._backend = backend

    async def apply_policy(
        self,
        run_id: str,
        policy: Optional[CheckpointRetentionPolicy] = None,
    ) -> None:
        """按保留策略清理旧 checkpoint."""
        policy = policy or CheckpointRetentionPolicy()
        if not policy:
            return

        cps = await self._backend.list_checkpoints(run_id)
        if not cps:
            return

        to_delete = set()

        # TTL 策略
        if policy.ttl_hours:
            cutoff = datetime.now() - timedelta(hours=policy.ttl_hours)
            for cp in cps:
                try:
                    created = datetime.fromisoformat(cp.created_at)
                    if created < cutoff:
                        to_delete.add(cp.checkpoint_id)
                except Exception:
                    pass

        # 保留最新 N 个
        if policy.keep_last_n is not None:
            sorted_by_time = sorted(
                cps,
                key=lambda c: datetime.fromisoformat(c.created_at),
                reverse=True,
            )
            for cp in sorted_by_time[policy.keep_last_n :]:
                to_delete.add(cp.checkpoint_id)

        # 同一步骤只保留最新
        if policy.keep_latest_per_step:
            by_step: Dict[int, List[Checkpoint]] = {}
            for cp in cps:
                by_step.setdefault(cp.step_index, []).append(cp)
            for step_cps in by_step.values():
                sorted_by_time = sorted(
                    step_cps,
                    key=lambda c: datetime.fromisoformat(c.created_at),
                    reverse=True,
                )
                for cp in sorted_by_time[1:]:
                    to_delete.add(cp.checkpoint_id)

        for cp_id in to_delete:
            await self._backend.delete_checkpoint(cp_id)
            logger.debug(f"Checkpoint 按策略已删除: {cp_id}")
