"""Checkpoint resume and rollback strategy base classes and registry."""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...tracker import RunTracker
from ...tracker.models import Checkpoint

_RESUME_STRATEGIES: List["ResumeStrategy"] = []
_ROLLBACK_STRATEGIES: List["RollbackStrategy"] = []


def register_resume(cls):
    """Decorator to register a ResumeStrategy."""
    _RESUME_STRATEGIES.append(cls())
    return cls


def register_rollback(cls):
    """Decorator to register a RollbackStrategy."""
    _ROLLBACK_STRATEGIES.append(cls())
    return cls


def get_resume_strategy(executor_state: Optional[Dict[str, Any]]) -> "ResumeStrategy":
    """根据 executor_state 选择合适的 ResumeStrategy."""
    state = executor_state or {}
    for strategy in _RESUME_STRATEGIES:
        if strategy.can_handle(state):
            return strategy
    # 默认顺序恢复
    from .sequential import SequentialResumeStrategy

    return SequentialResumeStrategy()


def get_rollback_strategy(compensate: bool = False) -> "RollbackStrategy":
    """选择 RollbackStrategy."""
    for strategy in _ROLLBACK_STRATEGIES:
        if strategy.name == ("rollback_compensating" if compensate else "rollback_sequential"):
            return strategy
    if compensate:
        from .rollback_compensating import RollbackCompensatingStrategy

        return RollbackCompensatingStrategy()
    from .rollback_sequential import RollbackSequentialStrategy

    return RollbackSequentialStrategy()


class ResumeStrategy(ABC):
    """恢复策略抽象基类."""

    name: str = "resume"

    @abstractmethod
    def can_handle(self, executor_state: Dict[str, Any]) -> bool:
        """判断该策略是否能处理给定的 executor_state."""
        ...

    @abstractmethod
    async def resume(
        self,
        tracker: RunTracker,
        session,
        cp: Checkpoint,
        steps: List[dict],
        event_broadcaster: Optional[Callable[[str, dict], Awaitable[None]]],
        **kwargs: Any,
    ):
        """执行恢复逻辑."""
        ...


class RollbackStrategy(ABC):
    """回滚策略抽象基类."""

    name: str = "rollback"

    @abstractmethod
    async def rollback(
        self,
        tracker: RunTracker,
        session,
        steps: List[dict],
        to_step: int,
        event_broadcaster: Optional[Callable[[str, dict], Awaitable[None]]],
        **kwargs: Any,
    ):
        """执行回滚逻辑."""
        ...
