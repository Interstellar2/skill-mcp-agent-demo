"""Redis state backend using redis-py."""

import json
import logging
import os
from typing import List, Optional

from ..models import Checkpoint, RunRecord
from .base import StateBackend

logger = logging.getLogger("kitchen_agent")


class RedisStateBackend(StateBackend):
    """Redis 持久化后端."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        prefix: str = "kitchen_sop",
    ):
        try:
            import redis
        except ImportError as e:
            raise RuntimeError(
                "Redis backend requires redis-py. Install it: pip install redis"
            ) from e

        self.url = redis_url or os.environ.get("KITCHEN_REDIS_URL", "redis://localhost:6379/0")
        self.prefix = prefix or os.environ.get("KITCHEN_REDIS_PREFIX", "kitchen_sop")
        self.client = redis.from_url(self.url, decode_responses=True)

    def _run_key(self, run_id: str) -> str:
        return f"{self.prefix}:run:{run_id}"

    def _cp_key(self, run_id: str, checkpoint_id: str) -> str:
        return f"{self.prefix}:checkpoint:{run_id}:{checkpoint_id}"

    def _cp_index_key(self, run_id: str) -> str:
        return f"{self.prefix}:checkpoints:{run_id}"

    async def save_run(self, run: RunRecord) -> None:
        key = self._run_key(run.run_id)
        self.client.set(key, json.dumps(run.to_dict(), ensure_ascii=False))
        logger.debug(f"Run saved to Redis: {key}")

    async def load_run(self, run_id: str) -> Optional[RunRecord]:
        key = self._run_key(run_id)
        data = self.client.get(key)
        if data is None:
            return None
        return RunRecord.from_dict(json.loads(data))

    async def list_runs(self, limit: int = 20) -> List[RunRecord]:
        pattern = f"{self.prefix}:run:*"
        keys = self.client.keys(pattern)
        # 按 Redis 键名排序（简单近似）
        keys = sorted(keys, reverse=True)[:limit]
        records = []
        for key in keys:
            try:
                data = self.client.get(key)
                if data:
                    records.append(RunRecord.from_dict(json.loads(data)))
            except Exception:
                pass
        return records

    async def delete_run(self, run_id: str) -> None:
        key = self._run_key(run_id)
        self.client.delete(key)

    async def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        key = self._cp_key(checkpoint.run_id, checkpoint.checkpoint_id)
        self.client.set(key, json.dumps(checkpoint.to_dict(), ensure_ascii=False))
        # 维护索引
        index_key = self._cp_index_key(checkpoint.run_id)
        self.client.sadd(index_key, checkpoint.checkpoint_id)
        logger.debug(f"Checkpoint saved to Redis: {key}")
        return checkpoint

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        # 扫描所有 run 的索引
        pattern = f"{self.prefix}:checkpoints:*"
        for index_key in self.client.keys(pattern):
            for cp_id in self.client.smembers(index_key):
                if cp_id == checkpoint_id:
                    run_id = index_key.decode().split(":")[-1] if isinstance(index_key, bytes) else index_key.split(":")[-1]
                    key = self._cp_key(run_id, checkpoint_id)
                    data = self.client.get(key)
                    if data:
                        return Checkpoint.from_dict(json.loads(data))
        return None

    async def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        index_key = self._cp_index_key(run_id)
        cp_ids = self.client.smembers(index_key)
        cps = []
        for cp_id in cp_ids:
            key = self._cp_key(run_id, cp_id)
            data = self.client.get(key)
            if data:
                try:
                    cps.append(Checkpoint.from_dict(json.loads(data)))
                except Exception:
                    pass
        cps.sort(key=lambda c: c.created_at)
        return cps

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        pattern = f"{self.prefix}:checkpoints:*"
        for index_key in self.client.keys(pattern):
            for cp_id in self.client.smembers(index_key):
                if cp_id == checkpoint_id:
                    run_id = index_key.decode().split(":")[-1] if isinstance(index_key, bytes) else index_key.split(":")[-1]
                    key = self._cp_key(run_id, checkpoint_id)
                    self.client.delete(key)
                    self.client.srem(index_key, checkpoint_id)
                    return

    async def delete_run_checkpoints(self, run_id: str) -> None:
        index_key = self._cp_index_key(run_id)
        cp_ids = self.client.smembers(index_key)
        for cp_id in cp_ids:
            key = self._cp_key(run_id, cp_id)
            self.client.delete(key)
        self.client.delete(index_key)
