/**
 * React Query hooks for the actions approval system.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { supabase } from '@/lib/supabaseClient';
import { toast } from '@/components/ui/toast';

const ACTIONS_QUERY_KEY = 'actions';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Types
export interface PendingAction {
  id: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  status: string;
  created_at: string;
  expires_at: string;
  context: Record<string, unknown>;
}

export interface ActionResult {
  success: boolean;
  message: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface AuditLogEntry {
  id: string;
  tool_name: string;
  approval_status: string;
  execution_status?: string;
  created_at: string;
  session_id?: string;
  agent_name?: string;
}

export interface ToolPreference {
  tool_name: string;
  current_tier: string;
  is_overridable: boolean;
  user_preference?: string;
}

export interface PendingCount {
  count: number;
}

// Helper to get auth headers
async function getAuthHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error('User not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
  };
}

// API functions
async function fetchPendingActions(limit = 50): Promise<PendingAction[]> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/actions/pending?limit=${limit}`, { headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch pending actions' }));
    throw new Error(error.detail || 'Failed to fetch pending actions');
  }
  return response.json();
}

async function fetchPendingCount(): Promise<PendingCount> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/actions/pending/count`, { headers });
  if (!response.ok) throw new Error('Failed to fetch pending count');
  return response.json();
}

async function approveAction(actionId: string): Promise<ActionResult> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/actions/${actionId}/approve`, {
    method: 'POST',
    headers,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to approve action' }));
    throw new Error(error.detail || 'Failed to approve action');
  }
  return response.json();
}

async function rejectAction(actionId: string, reason?: string): Promise<ActionResult> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/api/actions/${actionId}/reject`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to reject action' }));
    throw new Error(error.detail || 'Failed to reject action');
  }
  return response.json();
}

async function fetchAuditHistory(
  limit = 50,
  offset = 0,
  toolName?: string,
  approvalStatus?: string,
): Promise<AuditLogEntry[]> {
  const headers = await getAuthHeaders();
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (toolName) params.append('tool_name', toolName);
  if (approvalStatus) params.append('approval_status', approvalStatus);

  const response = await fetch(`${API_BASE_URL}/api/actions/history?${params}`, { headers });
  if (!response.ok) throw new Error('Failed to fetch audit history');
  return response.json();
}

// Hooks

export function usePendingActions(limit = 50) {
  const user = useAuthStore((state) => state.user);

  return useQuery<PendingAction[], Error>({
    queryKey: [ACTIONS_QUERY_KEY, 'pending', user?.id, limit],
    queryFn: () => fetchPendingActions(limit),
    enabled: !!user,
    refetchInterval: 30000,
  });
}

export function usePendingCount() {
  const user = useAuthStore((state) => state.user);

  return useQuery<PendingCount, Error>({
    queryKey: [ACTIONS_QUERY_KEY, 'pending', 'count', user?.id],
    queryFn: fetchPendingCount,
    enabled: !!user,
    refetchInterval: 10000,
  });
}

export function useApproveAction() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<ActionResult, Error, string>({
    mutationFn: approveAction,
    onSuccess: (result) => {
      if (result.success) {
        toast.success('Action approved and executed');
      } else {
        toast.error('Action approval failed', result.error);
      }
      queryClient.invalidateQueries({ queryKey: [ACTIONS_QUERY_KEY, 'pending', user?.id] });
    },
    onError: (error) => {
      toast.error('Failed to approve action', error.message);
    },
  });
}

export function useRejectAction() {
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  return useMutation<ActionResult, Error, { actionId: string; reason?: string }>({
    mutationFn: ({ actionId, reason }) => rejectAction(actionId, reason),
    onSuccess: () => {
      toast.success('Action rejected');
      queryClient.invalidateQueries({ queryKey: [ACTIONS_QUERY_KEY, 'pending', user?.id] });
    },
    onError: (error) => {
      toast.error('Failed to reject action', error.message);
    },
  });
}

export function useAuditHistory(limit = 50, offset = 0, toolName?: string, approvalStatus?: string) {
  const user = useAuthStore((state) => state.user);

  return useQuery<AuditLogEntry[], Error>({
    queryKey: [ACTIONS_QUERY_KEY, 'history', user?.id, limit, offset, toolName, approvalStatus],
    queryFn: () => fetchAuditHistory(limit, offset, toolName, approvalStatus),
    enabled: !!user,
  });
}
