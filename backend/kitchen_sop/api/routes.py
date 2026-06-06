"""REST API 路由实现."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..skill_manager import SkillsManager
from ..tracker import RunTracker
from ..checkpoint import CheckpointManager
from ..config import SKILLS_DIR
from .schemas import (
    CheckpointOut,
    HITLApprovalRequest,
    ResumeRequest,
    RollbackRequest,
    RunRecordOut,
    SkillDetailOut,
    SkillMetaOut,
    StartRunRequest,
    StartRunResponse,
)
from .execution_manager import (
    _active_runs,
    rollback_run_web,
    resume_run_web,
    start_run,
)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/skills", response_model=List[SkillMetaOut])
async def list_skills():
    sm = SkillsManager(SKILLS_DIR)
    result = []
    for name, skill in sm.skills.items():
        content = skill.load_full_content()
        from ..sop_parser import parse_sop_steps

        try:
            steps = parse_sop_steps(content, sm=sm, variables={})
        except Exception:
            steps = []
        result.append(
            SkillMetaOut(
                name=name,
                description=skill.description,
                variables=skill.metadata.get("variables", {}),
                steps_count=len(steps),
                metadata=skill.metadata,
            )
        )
    return result


@router.get("/skills/{skill_name}", response_model=SkillDetailOut)
async def get_skill(skill_name: str):
    sm = SkillsManager(SKILLS_DIR)
    skill = sm.skills.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    content = skill.load_full_content()
    from ..sop_parser import parse_sop_steps

    try:
        steps = parse_sop_steps(content, sm=sm, variables={})
    except Exception:
        steps = []
    return SkillDetailOut(
        name=skill.name,
        description=skill.description,
        raw_markdown=content,
        steps=steps,
        hitl_config=skill.metadata.get("human_in_the_loop", []),
        variables=skill.metadata.get("variables", {}),
    )


@router.post("/runs", response_model=StartRunResponse)
async def create_run(req: StartRunRequest):
    run_id = await start_run(
        skill_name=req.skill_name,
        mode=req.mode,
        variables=req.variables,
        model=req.model,
    )
    return StartRunResponse(run_id=run_id)


@router.get("/runs", response_model=List[RunRecordOut])
async def list_runs(limit: int = 20, offset: int = 0):
    runs = RunTracker.list_runs(limit=limit + offset)
    runs = runs[offset:]
    return [RunRecordOut(**r.to_dict()) for r in runs]


@router.get("/runs/{run_id}", response_model=RunRecordOut)
async def get_run(run_id: str):
    run = RunTracker.load_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunRecordOut(**run.to_dict())


@router.post("/runs/{run_id}/resume")
async def resume_run_endpoint(run_id: str, req: ResumeRequest):
    new_run_id = await resume_run_web(run_id, checkpoint_id=req.checkpoint_id)
    return {"run_id": new_run_id}


@router.post("/runs/{run_id}/rollback")
async def rollback_run_endpoint(run_id: str, req: RollbackRequest):
    new_run_id = await rollback_run_web(run_id, to_step=req.to_step)
    return {"run_id": new_run_id}


@router.post("/runs/{run_id}/approve")
async def approve_run(run_id: str, req: HITLApprovalRequest):
    active = _active_runs.get(run_id)
    if not active or not active.hitl_bridge:
        raise HTTPException(
            status_code=400, detail="No pending HITL approval for this run"
        )
    active.hitl_bridge.submit_approval(req.decision, req.modified_arguments)
    return {"success": True}


@router.get("/runs/{run_id}/checkpoints", response_model=List[CheckpointOut])
async def list_checkpoints(run_id: str):
    cp_mgr = CheckpointManager()
    cps = cp_mgr.list_checkpoints(run_id)
    return [CheckpointOut(**cp.to_dict()) for cp in cps]
