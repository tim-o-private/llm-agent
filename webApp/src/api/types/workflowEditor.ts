/**
 * SPEC-048 Workflow Editor types.
 *
 * Matches the backend workflow_editor_router.py response models.
 */

export interface WorkflowListItem {
  name: string;
  filename: string;
  description: string;
  trigger_summary: string;
  next_run_at: string | null;
}

export interface WorkflowRunEntry {
  id: string;
  template_name: string;
  status:
    | 'pending'
    | 'running'
    | 'waiting_for_approval'
    | 'completed'
    | 'failed'
    | 'cancelled';
  current_step: string;
  error: string | null;
  parameters: Record<string, unknown>;
  step_outputs: Record<string, string>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DryRunStep {
  name: string;
  agent: string;
  depends_on: string[];
  tools: string[];
}

export interface DryRunParameter {
  name: string;
  required: boolean;
  description: string;
}

export interface DryRunResult {
  valid: boolean;
  errors: string[];
  steps: DryRunStep[];
  parameters: DryRunParameter[];
}

export interface RunWorkflowRequest {
  template_name: string;
  parameters?: Record<string, unknown>;
}

export interface RunWorkflowResponse {
  run_id: string;
}

export interface CreateWorkflowRequest {
  name: string;
}

export interface CreateWorkflowResponse {
  path: string;
}
