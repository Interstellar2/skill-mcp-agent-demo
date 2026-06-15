export interface SkillStep {
  id: string;
  number: number;
  title: string;
  tool: string | null;
  sub_skill: string | null;
  raw: string;
}

export interface Skill {
  name: string;
  description: string;
  tools: string[];
  scripts: Record<string, string>;
  templates: Record<string, string>;
  variables: Record<string, unknown>;
  steps: SkillStep[];
  raw: string;
}

export interface APIStep {
  step_index: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  result_text?: string;
  error_message?: string;
  started_at?: string;
  ended_at?: string;
  duration_ms?: number;
  parallel_group_id?: string;
  checkpoint_id?: string;
  human_approval?: Record<string, unknown>;
}

export interface APIRun {
  run_id: string;
  skill_name: string;
  mode: string;
  started_at: string;
  ended_at?: string;
  overall_status: string;
  variables?: Record<string, unknown>;
  steps: APIStep[];
  resumed_from?: string;
  rollback_to_step?: number;
  execution_plan?: Record<string, unknown>;
}

export interface APISkillMeta {
  name: string;
  description: string;
  variables: Record<string, unknown>;
  steps_count: number;
  metadata: Record<string, unknown>;
}

export interface WSMessage {
  type: string;
  [key: string]: unknown;
}

export interface StartRunRequest {
  skill_name: string;
  mode: string;
  variables?: Record<string, unknown>;
  model?: string;
}

export interface AgentThought {
  type: string;
  tool?: string;
  input?: unknown;
  output?: string;
  log?: string;
  timestamp: number;
}

export interface ParallelBatch {
  batch_index: number;
  step_indices: number[];
  total_batches: number;
}

export interface ToolInfo {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface SkillValidationResult {
  valid: boolean;
  errors: string[];
  step_errors: { step_index: number | null; message: string }[];
}

export interface SkillGenerateDraftRequest {
  prompt: string;
  model?: string;
}

export interface SkillGenerateDraftResponse {
  draft_markdown: string;
}

export interface SkillPreviewRequest {
  draft_markdown: string;
}

export interface ParsedStep {
  tool_name: string;
  arguments: Record<string, unknown>;
  parallel_group_id?: string | null;
  depends_on?: string[];
}

export interface SkillPreviewResponse {
  metadata: Record<string, unknown>;
  steps: ParsedStep[];
  errors: string[];
  step_errors: { step_index: number | null; message: string }[];
  valid: boolean;
}

export interface SkillSaveRequest {
  name: string;
  draft_markdown: string;
  overwrite?: boolean;
}

export interface SkillSaveResponse {
  path: string;
  name: string;
}
