import type { APISkillMeta, Skill, APIRun, StartRunRequest, ToolInfo, SkillValidationResult, SkillGenerateDraftRequest, SkillGenerateDraftResponse, SkillPreviewRequest, SkillPreviewResponse, SkillSaveRequest, SkillSaveResponse } from '../types'

const API_BASE = '/api'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || res.statusText)
  }
  return res.json()
}

export async function generateSkillDraft(req: SkillGenerateDraftRequest): Promise<SkillGenerateDraftResponse> {
  return apiFetch('/skills/generate/draft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function previewSkillDraft(req: SkillPreviewRequest): Promise<SkillPreviewResponse> {
  return apiFetch('/skills/generate/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function saveSkillDraft(req: SkillSaveRequest): Promise<SkillSaveResponse> {
  return apiFetch('/skills/generate/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function fetchSkills(): Promise<APISkillMeta[]> {
  return apiFetch('/skills')
}

export async function fetchSkill(name: string): Promise<Skill> {
  return apiFetch(`/skills/${encodeURIComponent(name)}`)
}

export async function startRun(req: StartRunRequest): Promise<{ run_id: string }> {
  return apiFetch('/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function fetchRuns(limit = 20, offset = 0): Promise<APIRun[]> {
  return apiFetch(`/runs?limit=${limit}&offset=${offset}`)
}

export async function fetchRun(runId: string): Promise<APIRun> {
  return apiFetch(`/runs/${encodeURIComponent(runId)}`)
}

export async function resumeRun(runId: string, checkpointId?: string): Promise<{ run_id: string }> {
  return apiFetch(`/runs/${encodeURIComponent(runId)}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  })
}

export async function rollbackRun(runId: string, toStep: number): Promise<{ run_id: string }> {
  return apiFetch(`/runs/${encodeURIComponent(runId)}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ to_step: toStep }),
  })
}

export async function sendHITLApproval(runId: string, decision: string, modifiedArguments?: Record<string, unknown>): Promise<void> {
  await apiFetch(`/runs/${encodeURIComponent(runId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, modified_arguments: modifiedArguments }),
  })
}

export async function fetchCheckpoints(runId: string): Promise<{ checkpoint_id: string; run_id: string; step_index: number; step_status: string; created_at: string }[]> {
  return apiFetch(`/runs/${encodeURIComponent(runId)}/checkpoints`)
}

export async function fetchTools(): Promise<ToolInfo[]> {
  return apiFetch('/tools')
}

export async function validateSkill(name: string): Promise<SkillValidationResult> {
  return apiFetch(`/skills/${encodeURIComponent(name)}/validate`, {
    method: 'POST',
  })
}
