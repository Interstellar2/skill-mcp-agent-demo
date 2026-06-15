"""统一事件契约."""

from enum import Enum


class EventType(str, Enum):
    """WebSocket / 执行器事件类型常量.

    枚举值保持与原始裸字符串一致，确保前端协议向后兼容。
    """

    STEP_START = "step_start"
    STEP_FINISH = "step_finish"
    STEP_ERROR = "step_error"

    CHECKPOINT_SAVED = "checkpoint_saved"
    VARIABLES_UPDATED = "variables_updated"

    BATCH_START = "batch_start"
    BATCH_FINISH = "batch_finish"

    AGENT_THOUGHT = "agent_thought"
    HITL_REQUEST = "hitl_request"

    PLAN_GENERATED = "plan_generated"
    RESUME_STARTED = "resume_started"
    ROLLBACK_STARTED = "rollback_started"
    RUN_COMPLETE = "run_complete"

    # WebSocket 控制事件
    INIT = "init"
    PONG = "pong"
    HITL_APPROVAL_ACK = "hitl_approval_ack"
    ERROR = "error"


def build_event(event_type: EventType, payload: dict) -> dict:
    """构造标准事件消息体."""
    return {"type": event_type.value, **payload}
