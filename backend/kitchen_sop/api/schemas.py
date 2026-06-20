"""FastAPI Pydantic 请求/响应模型."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillMetaOut(BaseModel):
    name: str
    description: str
    variables: Dict[str, Any] = {}
    steps_count: int = 0
    metadata: Dict[str, Any] = {}
    gotchas: List[str] = []
    reference_files: List[str] = []


class SkillDetailOut(BaseModel):
    name: str
    description: str
    raw_markdown: str
    steps: List[Dict[str, Any]] = []
    hitl_config: List[Dict[str, Any]] = []
    variables: Dict[str, Any] = {}
    gotchas: List[str] = []
    reference_files: List[str] = []


class StartRunRequest(BaseModel):
    skill_name: str
    mode: str = "demo"
    variables: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    enable_checkpoint: Optional[bool] = False


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
    agent_messages: Optional[List[Dict[str, Any]]] = None
    compensation_context: Optional[Dict[str, Any]] = None
    compensation_status: Optional[Dict[str, Any]] = None


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
    checkpoint_id: Optional[str] = None


class ResumeRequest(BaseModel):
    checkpoint_id: Optional[str] = None


class RollbackRequest(BaseModel):
    to_step: int
    checkpoint_id: Optional[str] = None
    compensate: Optional[bool] = False


class HITLApprovalRequest(BaseModel):
    decision: str
    modified_arguments: Optional[Dict[str, Any]] = None


class CheckpointOut(BaseModel):
    checkpoint_id: str
    run_id: str
    step_index: int
    step_status: str
    created_at: str
    agent_messages: Optional[List[Dict[str, Any]]] = None
    executor_state: Optional[Dict[str, Any]] = None


class WSMessage(BaseModel):
    type: str
    payload: Dict[str, Any] = {}


class ToolOut(BaseModel):
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict, alias="inputSchema")


class SkillValidationErrorItem(BaseModel):
    step_index: Optional[int] = None
    message: str


class SkillValidationOut(BaseModel):
    valid: bool
    errors: List[str] = []
    step_errors: List[SkillValidationErrorItem] = []


class SkillGenerateDraftRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class SkillGenerateDraftResponse(BaseModel):
    draft_markdown: str


class SkillPreviewRequest(BaseModel):
    draft_markdown: str


class SkillPreviewResponse(BaseModel):
    metadata: Dict[str, Any] = {}
    steps: List[Dict[str, Any]] = []
    errors: List[str] = []
    step_errors: List[SkillValidationErrorItem] = []
    valid: bool = False


class SkillSaveRequest(BaseModel):
    name: str
    draft_markdown: str
    overwrite: bool = False


class SkillSaveResponse(BaseModel):
    path: str
    name: str


class SkillAnalyticsOut(BaseModel):
    skill_name: str
    invocations: int = 0
    successes: int = 0
    failures: int = 0
    last_run_at: Optional[str] = None
