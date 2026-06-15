"""StateBackend 抽象基类."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Checkpoint, RunRecord


class StateBackend(ABC):
    """执行记录与检查点的持久化后端抽象."""

    @abstractmethod
    async def save_run(self, run: RunRecord) -> None:
        ...

    @abstractmethod
    async def load_run(self, run_id: str) -> Optional[RunRecord]:
        ...

    @abstractmethod
    async def list_runs(self, limit: int = 20) -> List[RunRecord]:
        ...

    @abstractmethod
    async def delete_run(self, run_id: str) -> None:
        ...

    @abstractmethod
    async def save_checkpoint(self, checkpoint: Checkpoint) -> Checkpoint:
        ...

    @abstractmethod
    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        ...

    @abstractmethod
    async def list_checkpoints(self, run_id: str) -> List[Checkpoint]:
        ...

    @abstractmethod
    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        ...

    @abstractmethod
    async def delete_run_checkpoints(self, run_id: str) -> None:
        ...
