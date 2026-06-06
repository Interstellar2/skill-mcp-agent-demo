"""FastAPI Pydantic 请求/响应模型."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillMetaOut(BaseModel):
    name: str
    description: str
    variables: Dict[str, Any] = {}
    steps_count: int = 0
    metadata: Dict[str, Any] = {}


class SkillDetailOut(BaseModel):
    name: str
    description: str
    raw_markdown: str
    steps: List[Dict[str, Any]] = []
    hitl_config: List[Dict[str, Any]] = []
    variables: Dict[str, Any] = {}


class StartRunRequest(BaseModel):
    skill_name: str
    mode: str = "demo"
    variables: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class StartRunResponse(BaseModel):
    run_id: str


class StepRecordOut(BaseModel):
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: str
    result_text: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    parallel_group_id: Optional[str] = None
    checkpoint_id: Optional[str] = None
    human_approval: Optional[Dict[str, Any]] = None


class RunRecordOut(BaseModel):
    run_id: str
    skill_name: str
    mode: str
    started_at: str
    ended_at: Optional[str] = None
    overall_status: str = "pending"
    variables: Optional[Dict[str, Any]] = None
    steps: List[StepRecordOut] = []
    resumed_from: Optional[str] = None
    rollback_to_step: Optional[int] = None
    execution_plan: Optional[Dict[str, Any]] = None


class ResumeRequest(BaseModel):
    checkpoint_id: Optional[str] = None


class RollbackRequest(BaseModel):
    to_step: int


class HITLApprovalRequest(BaseModel):
    decision: str
    modified_arguments: Optional[Dict[str, Any]] = None


class CheckpointOut(BaseModel):
    checkpoint_id: str
    run_id: str
    step_index: int
    step_status: str
    created_at: str


class WSMessage(BaseModel):
    type: str
    payload: Dict[str, Any] = {}
