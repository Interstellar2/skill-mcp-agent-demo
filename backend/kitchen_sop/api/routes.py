"""REST API 路由实现."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..skill import SkillsManager
from ..tracker import RunTracker
from ..tracker.checkpoint import CheckpointManager
from ..config import SKILLS_DIR
from .schemas import (
    CheckpointOut,
    HITLApprovalRequest,
    ResumeRequest,
    RollbackRequest,
    RunRecordOut,
    SkillDetailOut,
    SkillGenerateDraftRequest,
    SkillGenerateDraftResponse,
    SkillMetaOut,
    SkillPreviewRequest,
    SkillPreviewResponse,
    SkillSaveRequest,
    SkillSaveResponse,
    SkillValidationOut,
    StartRunRequest,
    StartRunResponse,
    ToolOut,
)
from .orchestrator import (
    _active_runs,
    rollback_run_web,
    resume_run_web,
    start_run,
)
from ..mcp_pool import get_mcp_pool
from ..skill import (
    SkillGenerationError,
    SkillValidationError,
    validate_skill_metadata_tools,
    validate_skill_steps,
    render_sop,
    _resolve_variables,
    parse_sop_steps,
    generate_skill_draft,
    preview_skill_draft,
    save_skill,
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
        from ..skill import parse_sop_steps

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
    from ..skill import parse_sop_steps

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


@router.get("/tools", response_model=List[ToolOut])
async def list_tools():
    pool = get_mcp_pool()
    result = await pool.session.list_tools()
    return [
        ToolOut(
            name=t.name,
            description=t.description or "",
            inputSchema=t.inputSchema if isinstance(t.inputSchema, dict) else {},
        )
        for t in result.tools
    ]


@router.post("/skills/{skill_name}/validate", response_model=SkillValidationOut)
async def validate_skill(skill_name: str):
    sm = SkillsManager(SKILLS_DIR)
    skill = sm.skills.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    pool = get_mcp_pool()
    mcp_tools_result = await pool.session.list_tools()
    mcp_tools = mcp_tools_result.tools

    raw_sop = skill.load_full_content()
    merged_vars = _resolve_variables(skill.metadata.get("variables", {}))
    rendered_sop = render_sop(raw_sop, merged_vars)
    try:
        steps = parse_sop_steps(rendered_sop, sm=sm, variables=merged_vars)
    except ValueError as e:
        return SkillValidationOut(
            valid=False,
            errors=[str(e)],
        )

    errors: List[str] = []
    step_errors: List[dict] = []

    try:
        declared = skill.metadata.get("tools", [])
        if declared:
            validate_skill_metadata_tools(declared, mcp_tools)
    except SkillValidationError as e:
        errors.extend(str(e).splitlines())

    try:
        validate_skill_steps(steps, mcp_tools)
    except SkillValidationError as e:
        for line in str(e).splitlines():
            line = line.strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if not line or line.startswith("Skill"):
                continue
            import re as _re
            m = _re.match(r"步骤\s+(\d+):\s*(.*)", line)
            if m:
                step_errors.append({"step_index": int(m.group(1)), "message": m.group(2)})
            else:
                errors.append(line)

    valid = not errors and not step_errors
    return SkillValidationOut(
        valid=valid,
        errors=errors,
        step_errors=step_errors,
    )


@router.post("/skills/generate/draft", response_model=SkillGenerateDraftResponse)
async def generate_draft(req: SkillGenerateDraftRequest):
    pool = get_mcp_pool()
    mcp_tools_result = await pool.session.list_tools()
    mcp_tools = mcp_tools_result.tools

    try:
        draft = await generate_skill_draft(
            prompt=req.prompt,
            model=req.model,
            mcp_tools=mcp_tools,
        )
    except SkillGenerationError as e:
        msg = str(e)
        if "OPENAI_API_KEY" in msg:
            raise HTTPException(status_code=503, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成草稿失败: {e}")

    return SkillGenerateDraftResponse(draft_markdown=draft)


@router.post("/skills/generate/preview", response_model=SkillPreviewResponse)
async def preview_draft(req: SkillPreviewRequest):
    sm = SkillsManager(SKILLS_DIR)
    pool = get_mcp_pool()
    mcp_tools_result = await pool.session.list_tools()
    mcp_tools = mcp_tools_result.tools

    try:
        preview = preview_skill_draft(
            markdown=req.draft_markdown,
            sm=sm,
            mcp_tools=mcp_tools,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"预览解析失败: {e}")

    return SkillPreviewResponse(**preview)


@router.post("/skills/generate/save", response_model=SkillSaveResponse)
async def save_draft(req: SkillSaveRequest):
    try:
        path = save_skill(
            name=req.name,
            markdown=req.draft_markdown,
            skills_dir=SKILLS_DIR,
            overwrite=req.overwrite,
        )
    except SkillGenerationError as e:
        msg = str(e)
        if "已存在" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "非法" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {e}")

    return SkillSaveResponse(path=str(path), name=req.name)
