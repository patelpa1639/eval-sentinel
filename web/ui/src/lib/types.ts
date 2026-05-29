// API contract — frozen. Mirrors the backend SSE/JSON shapes exactly.

export interface ScoreSet {
  overall: number;
  per_category: Record<string, number>;
}

export interface StateResponse {
  dataset: string;
  baseline: ScoreSet;
  current: ScoreSet;
  regressed_categories: string[];
  phoenix_url: string;
}

// --- SSE event shapes (each arrives JSON-encoded in event.data) ---

export type Phase =
  | 'detect'
  | 'root_cause'
  | 'propose'
  | 'verify'
  | 'report'
  | 'approval';

export type ToolResultKind = 'regression' | 'failures' | 'recovery';

export interface PlanEvent {
  type: 'plan';
  text: string;
}
export interface PhaseEvent {
  type: 'phase';
  phase: Phase;
  label: string;
}
export interface ToolCallEvent {
  type: 'tool_call';
  name: string;
  args?: unknown;
}
export interface ToolResultEvent {
  type: 'tool_result';
  name: string;
  kind: ToolResultKind;
  data: unknown;
}
export interface NarrationEvent {
  type: 'narration';
  text: string; // markdown
}
export interface ProposedPromptEvent {
  type: 'proposed_prompt';
  text: string;
}
export interface ReportEvent {
  type: 'report';
  text: string; // markdown
}
export interface ApprovalGateEvent {
  type: 'approval_gate';
  proposed_prompt: string;
  new_experiment_id: string;
}
export interface DoneEvent {
  type: 'done';
}

export type SentinelEvent =
  | PlanEvent
  | PhaseEvent
  | ToolCallEvent
  | ToolResultEvent
  | NarrationEvent
  | ProposedPromptEvent
  | ReportEvent
  | ApprovalGateEvent
  | DoneEvent;

// Shapes carried inside tool_result.data (best-effort; rendered defensively).
export interface RegressionRow {
  category: string;
  baseline: number;
  current: number;
}
export interface FailureRow {
  command: string;
  expected: string;
  predicted: string;
}
export interface RecoveryRow {
  category: string;
  current: number;
  healed: number;
}

export interface ApproveResponse {
  ok: boolean;
  promoted: boolean;
  message: string;
}

export type RunState = 'healthy' | 'regression' | 'healing' | 'healed';
