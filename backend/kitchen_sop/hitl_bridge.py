"""HITL 异步信号桥：每个 run 一个实例，通过 asyncio.Future 阻塞等待人工确认."""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("kitchen_agent")


class HITLBridge:
    """Web 模式下 HITL 信号桥.

    工作流：
    1. executor 调用 request_approval() -> Future 阻塞
    2. WS handler 收到前端 hitl_approval -> submit_approval() -> Future 完成
    3. executor 继续执行
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._pending: Optional[asyncio.Future] = None
        self.approval_id: Optional[str] = None
        self.last_prompt: Optional[str] = None
        self.last_arguments: Optional[dict] = None

    async def request_approval(self, prompt: str, arguments: dict) -> Dict[str, Any]:
        """请求人工确认，阻塞直到收到 submit_approval."""
        self.approval_id = uuid.uuid4().hex[:12]
        self.last_prompt = prompt
        self.last_arguments = arguments
        self._pending = asyncio.get_event_loop().create_future()
        logger.info(f"HITLBridge request_approval: run={self.run_id} approval_id={self.approval_id}")
        try:
            result = await self._pending
            return result
        except asyncio.CancelledError:
            logger.warning(f"HITLBridge request cancelled for run={self.run_id}")
            raise
        finally:
            self._pending = None

    def submit_approval(self, decision: str, modified_arguments: Optional[dict] = None):
        """提交人工决策结果，恢复执行."""
        if self._pending is None or self._pending.done():
            logger.warning(
                f"HITLBridge submit_approval called but no pending future for run {self.run_id}"
            )
            return
        self._pending.set_result(
            {
                "decision": decision,
                "modified_arguments": modified_arguments or {},
            }
        )

    def reject(self):
        """快捷拒绝."""
        self.submit_approval("rejected")
