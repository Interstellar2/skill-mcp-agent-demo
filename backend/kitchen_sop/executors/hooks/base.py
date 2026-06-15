"""StepHook 抽象基类."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...tracker.models import StepRecord
    from ..step_runner import StepRunner


class StepHook(ABC):
    """单步执行生命周期钩子.

    StepRunner 按固定顺序编排 hooks；新增副作用只需实现本接口并注册到 runner。
    """

    @abstractmethod
    async def on_before(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> None:
        """在 call_tool 之前调用."""
        ...

    @abstractmethod
    async def on_after(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        result_text: Optional[str],
    ) -> None:
        """在 call_tool 成功返回后调用."""
        ...

    @abstractmethod
    async def on_error(
        self,
        runner: "StepRunner",
        step_rec: "StepRecord",
        tool_name: str,
        arguments: Dict[str, Any],
        error: Exception,
    ) -> None:
        """在 call_tool 抛出异常后调用."""
        ...
