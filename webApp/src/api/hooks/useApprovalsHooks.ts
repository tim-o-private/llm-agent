/**
 * React Query hooks for the SPEC-045 Approvals API.
 *
 * Endpoints:
 *   GET  /api/approvals
 *   GET  /api/approvals/count
 *   POST /api/approvals/{id}/approve
 *   POST /api/approvals/{id}/reject
 *   POST /api/approvals/{id}/edit
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import { toast } from '@/components/ui/toast';
import type { ApprovalCard, ApprovalsCount, TodayResponse } from '@/api/types/today';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const APPROVALS_KEY = ['approvals'] as const;
const APPROVALS_COUNT_KEY = ['approvals', 'count'] as const;
const TODAY_KEY = ['today'] as const;

async function fetchApprovals(): Promise<ApprovalCard[]> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals`, { headers });
  if (!res.ok) throw new Error(`GET /approvals failed: ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : data.cards || [];
}

async function fetchApprovalsCount(): Promise<number> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals/count`, { headers });
  if (!res.ok) throw new Error(`GET /approvals/count failed: ${res.status}`);
  const data: ApprovalsCount = await res.json();
  return data.count ?? 0;
}

async function postApprove(id: string, decision_note?: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals/${encodeURIComponent(id)}/approve`, {
    method: 'POST',
    headers,
    body: JSON.stringify(decision_note ? { decision_note } : {}),
  });
  if (!res.ok) throw new Error(`approve failed: ${res.status}`);
}

async function postReject(id: string, reason?: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals/${encodeURIComponent(id)}/reject`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason: reason ?? '' }),
  });
  if (!res.ok) throw new Error(`reject failed: ${res.status}`);
}

async function postEdit(id: string, payload_patch: Record<string, unknown>): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals/${encodeURIComponent(id)}/edit`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ payload_patch }),
  });
  if (!res.ok) throw new Error(`edit failed: ${res.status}`);
}

// --- Queries ---------------------------------------------------------------

export function useApprovals() {
  return useQuery<ApprovalCard[], Error>({
    queryKey: APPROVALS_KEY,
    queryFn: fetchApprovals,
    staleTime: 15_000,
  });
}

export function useApprovalsCount() {
  return useQuery<number, Error>({
    queryKey: APPROVALS_COUNT_KEY,
    queryFn: fetchApprovalsCount,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
    placeholderData: 0,
  });
}

// --- Mutations -------------------------------------------------------------

function removeCardFromToday(qc: ReturnType<typeof useQueryClient>, id: string) {
  qc.setQueryData<TodayResponse>(TODAY_KEY, (old) => {
    if (!old) return old;
    return { ...old, approvals: old.approvals.filter((c) => c.id !== id) };
  });
  qc.setQueryData<ApprovalCard[]>(APPROVALS_KEY, (old) =>
    old ? old.filter((c) => c.id !== id) : old,
  );
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: TODAY_KEY });
  qc.invalidateQueries({ queryKey: APPROVALS_KEY });
  qc.invalidateQueries({ queryKey: APPROVALS_COUNT_KEY });
}

export function useApproveCard() {
  const qc = useQueryClient();
  return useMutation<void, Error, { id: string; decision_note?: string }>({
    mutationFn: ({ id, decision_note }) => postApprove(id, decision_note),
    onSuccess: (_data, { id }) => {
      removeCardFromToday(qc, id);
      invalidateAll(qc);
    },
    onError: (err) => {
      toast.error('Approval failed', err.message);
    },
  });
}

export function useRejectCard() {
  const qc = useQueryClient();
  return useMutation<void, Error, { id: string; reason?: string }>({
    mutationFn: ({ id, reason }) => postReject(id, reason),
    onSuccess: (_data, { id }) => {
      removeCardFromToday(qc, id);
      invalidateAll(qc);
    },
    onError: (err) => {
      toast.error('Rejection failed', err.message);
    },
  });
}

async function postRetry(id: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/approvals/${encodeURIComponent(id)}/retry`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`retry failed: ${res.status}`);
}

export function useRetryCard() {
  const qc = useQueryClient();
  return useMutation<void, Error, { id: string }>({
    mutationFn: ({ id }) => postRetry(id),
    onSuccess: () => {
      invalidateAll(qc);
    },
    onError: (err) => {
      toast.error('Retry failed', err.message);
    },
  });
}

export function useEditCard() {
  const qc = useQueryClient();
  return useMutation<void, Error, { id: string; payload_patch: Record<string, unknown> }>({
    mutationFn: ({ id, payload_patch }) => postEdit(id, payload_patch),
    onSuccess: (_data, { id, payload_patch }) => {
      // Card stays pending — patch the cached payload.
      qc.setQueryData<TodayResponse>(TODAY_KEY, (old) => {
        if (!old) return old;
        return {
          ...old,
          approvals: old.approvals.map((c) =>
            c.id === id
              ? ({ ...c, payload: { ...c.payload, ...payload_patch } } as ApprovalCard)
              : c,
          ),
        };
      });
      qc.invalidateQueries({ queryKey: APPROVALS_KEY });
      qc.invalidateQueries({ queryKey: TODAY_KEY });
    },
    onError: (err) => {
      toast.error('Edit failed', err.message);
    },
  });
}
