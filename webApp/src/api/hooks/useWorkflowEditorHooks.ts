/**
 * SPEC-048 FU-2: React Query hooks for the workflow editor.
 *
 * Endpoints consumed:
 *   GET  /api/vault/workflows/list
 *   GET  /api/workflows/runs/detailed?template_name=&limit=25
 *   POST /api/vault/workflows/new
 *   POST /api/vault/workflows/dry-run
 *   POST /api/vault/workflows/run
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import type {
  WorkflowListItem,
  WorkflowRunEntry,
  DryRunResult,
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  RunWorkflowRequest,
  RunWorkflowResponse,
} from '@/api/types/workflowEditor';
import { toast } from '@/components/ui/toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// --- Fetch functions ---------------------------------------------------------

async function fetchWorkflowList(): Promise<{ workflows: WorkflowListItem[] }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/workflows/list`, {
    headers,
  });
  if (!res.ok) throw new Error(`GET /vault/workflows/list failed: ${res.status}`);
  return res.json();
}

async function fetchWorkflowRuns(
  templateName: string,
  limit: number,
): Promise<WorkflowRunEntry[]> {
  const headers = await authHeaders();
  const params = new URLSearchParams({
    template_name: templateName,
    limit: String(limit),
  });
  const res = await fetch(
    `${API_BASE_URL}/api/workflows/runs/detailed?${params}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /workflows/runs/detailed failed: ${res.status}`);
  return res.json();
}

async function createWorkflow(
  payload: CreateWorkflowRequest,
): Promise<CreateWorkflowResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/workflows/new`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (res.status === 409) {
    throw Object.assign(new Error('A workflow with that name already exists'), {
      status: 409,
    });
  }
  if (!res.ok) throw new Error(`POST /vault/workflows/new failed: ${res.status}`);
  return res.json();
}

async function dryRunWorkflow(templateName: string): Promise<DryRunResult> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/workflows/dry-run`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ template_name: templateName }),
  });
  if (res.status === 404) {
    throw Object.assign(new Error('Template not found'), { status: 404 });
  }
  if (!res.ok)
    throw new Error(`POST /vault/workflows/dry-run failed: ${res.status}`);
  return res.json();
}

async function runWorkflow(
  payload: RunWorkflowRequest,
): Promise<RunWorkflowResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/workflows/run`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (res.status === 404) {
    throw Object.assign(new Error('Template not found'), { status: 404 });
  }
  if (res.status === 422) {
    const body = await res.json();
    throw Object.assign(
      new Error(body.missing ? `Missing parameters: ${body.missing.join(', ')}` : 'Invalid parameters'),
      { status: 422 },
    );
  }
  if (res.status === 503) {
    throw Object.assign(new Error('Workflow engine unavailable'), {
      status: 503,
    });
  }
  if (!res.ok) throw new Error(`POST /vault/workflows/run failed: ${res.status}`);
  return res.json();
}

// --- Queries -----------------------------------------------------------------

/**
 * AC-08: Workflow list with 60s stale time.
 */
export function useWorkflowList() {
  return useQuery({
    queryKey: ['workflow-list'],
    queryFn: fetchWorkflowList,
    staleTime: 60_000,
    select: (data) => data.workflows,
  });
}

/**
 * AC-21: Adaptive polling -- 15s when a run is running/pending, 60s otherwise.
 */
export function useWorkflowRuns(templateName: string) {
  return useQuery({
    queryKey: ['workflow-runs', templateName],
    queryFn: () => fetchWorkflowRuns(templateName, 25),
    enabled: !!templateName,
    staleTime: 10_000,
    refetchInterval: (query) => {
      const hasActiveRun = query.state.data?.some(
        (r: WorkflowRunEntry) =>
          r.status === 'running' || r.status === 'pending',
      );
      return hasActiveRun ? 15_000 : 60_000;
    },
  });
}

// --- Mutations ---------------------------------------------------------------

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-list'] });
    },
    onError: (error: Error & { status?: number }) => {
      if (error.status === 409) {
        toast.error('A workflow with that name already exists');
      } else {
        toast.error('Failed to create workflow');
      }
    },
  });
}

export function useDryRun() {
  return useMutation({
    mutationFn: dryRunWorkflow,
    onError: (error: Error & { status?: number }) => {
      if (error.status === 404) {
        toast.error('Template not found -- save the file first');
      } else {
        toast.error('Dry run failed');
      }
    },
  });
}

export function useRunWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runWorkflow,
    onSuccess: (_data, variables) => {
      toast.success('Workflow started');
      queryClient.invalidateQueries({
        queryKey: ['workflow-runs', variables.template_name],
      });
    },
    onError: (error: Error & { status?: number }) => {
      if (error.status === 503) {
        toast.error('Workflow engine unavailable -- try again later');
      } else if (error.status === 422) {
        toast.error(error.message);
      } else if (error.status === 404) {
        toast.error('Template not found -- save the file first');
      } else {
        toast.error('Failed to start workflow');
      }
    },
  });
}
