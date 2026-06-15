"""StateBackend exports and factory."""

from typing import Optional

from .base import StateBackend
from .local_json import LocalJSONStateBackend

__all__ = ["StateBackend", "LocalJSONStateBackend", "S3StateBackend", "RedisStateBackend", "get_state_backend"]


_STATE_BACKEND_INSTANCE: Optional[StateBackend] = None


def get_state_backend() -> StateBackend:
    """获取全局默认 StateBackend 实例（单例）."""
    global _STATE_BACKEND_INSTANCE
    if _STATE_BACKEND_INSTANCE is None:
        from ...config import STATE_BACKEND

        backend_name = STATE_BACKEND
        if backend_name == "s3":
            from .s3 import S3StateBackend
            _STATE_BACKEND_INSTANCE = S3StateBackend()
        elif backend_name == "redis":
            from .redis import RedisStateBackend
            _STATE_BACKEND_INSTANCE = RedisStateBackend()
        else:
            _STATE_BACKEND_INSTANCE = LocalJSONStateBackend()
    return _STATE_BACKEND_INSTANCE
