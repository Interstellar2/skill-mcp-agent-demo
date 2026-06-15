"""执行记录数据模型."""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class HumanApprovalRecord:
    """Human-in-the-Loop 审批记录."""

    requested_at: str
    prompt: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    decision: Optional[str] = None  # "approved", "rejected", "modified"
    modified_arguments: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HumanApprovalRecord":
        return cls(**data)


@dataclass
class PlanStep:
    """Plan-then-Execute 中的计划步骤."""

    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        return cls(**data)


@dataclass
class ExecutionPlan:
    """Plan-then-Execute 生成的执行计划."""

    version: str = "1.0"
    steps: List[PlanStep] = field(default_factory=list)
    estimated_duration_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_duration_ms": self.estimated_duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionPlan":
        steps = [PlanStep.from_dict(s) for s in data.pop("steps", [])]
        return cls(steps=steps, **data)


@dataclass
class Checkpoint:
    """断电续作检查点."""

    checkpoint_id: str
    run_id: str
    step_index: int
    step_status: str  # "before_step" | "after_step"
    variables: Dict[str, Any]
    step_results: List[dict]
    created_at: str
    executor_state: Optional[Dict[str, Any]] = None
    agent_messages: Optional[List[dict]] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(**data)


@dataclass
class StepRecord:
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # "pending" | "success" | "error" | "skipped"
    result_text: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    # --- 新扩展字段 ---
    human_approval: Optional[HumanApprovalRecord] = None
    parallel_group_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    agent_messages: Optional[List[dict]] = None
    compensation_context: Optional[Dict[str, Any]] = None
    compensation_status: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.human_approval:
            d["human_approval"] = self.human_approval.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StepRecord":
        ha = data.pop("human_approval", None)
        if ha:
            data["human_approval"] = HumanApprovalRecord.from_dict(ha)
        return cls(**data)


@dataclass
class RunRecord:
    run_id: str
    skill_name: str
    mode: str  # "demo" | "agent" | "plan_then_execute" | "hitl" | "parallel" | "resume" | "rollback"
    started_at: str
    ended_at: Optional[str] = None
    overall_status: str = "pending"  # "pending" | "success" | "error"
    variables: Optional[Dict[str, Any]] = None
    steps: List[StepRecord] = field(default_factory=list)
    # --- 新扩展字段 ---
    execution_plan: Optional[ExecutionPlan] = None
    resumed_from: Optional[str] = None  # 从哪个 run_id 恢复
    rollback_to_step: Optional[int] = None
    checkpoint_id: Optional[str] = None  # 最后写入的 checkpoint id

    @classmethod
    def new(
        cls,
        skill_name: str,
        mode: str,
        variables: Optional[dict] = None,
        resumed_from: Optional[str] = None,
        rollback_to_step: Optional[int] = None,
    ) -> "RunRecord":
        return cls(
            run_id=uuid.uuid4().hex[:12],
            skill_name=skill_name,
            mode=mode,
            started_at=datetime.now().isoformat(timespec="seconds"),
            variables=variables,
            resumed_from=resumed_from,
            rollback_to_step=rollback_to_step,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        if self.execution_plan:
            d["execution_plan"] = self.execution_plan.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RunRecord":
        steps = [StepRecord.from_dict(s) for s in data.pop("steps", [])]
        plan = data.pop("execution_plan", None)
        if plan:
            data["execution_plan"] = ExecutionPlan.from_dict(plan)
        return cls(steps=steps, **data)
