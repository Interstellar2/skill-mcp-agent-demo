"""执行记录数据模型."""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StepRecord:
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # "pending" | "success" | "error"
    result_text: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class RunRecord:
    run_id: str
    skill_name: str
    mode: str  # "demo" | "agent"
    started_at: str
    ended_at: Optional[str] = None
    overall_status: str = "pending"  # "pending" | "success" | "error"
    variables: Optional[Dict[str, Any]] = None
    steps: List[StepRecord] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        skill_name: str,
        mode: str,
        variables: Optional[dict] = None,
    ) -> "RunRecord":
        return cls(
            run_id=uuid.uuid4().hex[:12],
            skill_name=skill_name,
            mode=mode,
            started_at=datetime.now().isoformat(timespec="seconds"),
            variables=variables,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        steps = [StepRecord(**s) for s in data.pop("steps", [])]
        return cls(steps=steps, **data)
