"""WebExecutionAdapter: 包装 tracker 与事件广播（可选辅助类）."""

from typing import Awaitable, Callable, Optional

from ..tracker import RunTracker

EventBroadcaster = Optional[Callable[[str, dict], Awaitable[None]]]


class WebExecutionAdapter:
    """轻量级包装，用于将 tracker 与 event_broadcaster 绑定.

    实际广播逻辑已直接集成到 execute_step 与各 executor 中，
    此类主要作为语义标记和潜在扩展点保留。
    """

    def __init__(
        self,
        tracker: RunTracker,
        event_broadcaster: EventBroadcaster = None,
    ):
        self.tracker = tracker
        self.event_broadcaster = event_broadcaster
