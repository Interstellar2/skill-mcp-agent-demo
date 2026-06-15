"""Agent 消息记录器."""

import copy
import logging
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import AsyncCallbackHandler

logger = logging.getLogger("kitchen_agent")


class AgentMessageRecorder(AsyncCallbackHandler):
    """记录 Agent 对话消息历史，用于 checkpoint 与恢复."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def _snapshot(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self.messages)

    async def on_chat_model_start(self, serialized, messages, **kwargs):
        # 不处理
        pass

    def _add_message(self, msg: Dict[str, Any]):
        self.messages.append(msg)

    def record_human(self, content: str):
        self._add_message({"type": "human", "content": content})

    def record_ai(self, content: str, tool_calls: Optional[List[Dict]] = None):
        self._add_message({"type": "ai", "content": content, "tool_calls": tool_calls or []})

    def record_tool(self, content: str, tool_call_id: str):
        self._add_message({"type": "tool", "content": content, "tool_call_id": tool_call_id})
