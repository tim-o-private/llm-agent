/**
 * React Query hooks for the SPEC-045 Today API.
 *
 * Endpoints consumed:
 *   GET  /api/today
 *   GET  /api/today/source
 *   POST /api/today/notes
 *   POST /api/today/todo/toggle
 *   POST /api/today/regenerate
 *   GET  /api/workflows/runs?template_name=regenerate-today&limit=1
 */

import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import { toast } from '@/components/ui/toast';
import type { NoteItem, TodayResponse, WorkflowRun } from '@/api/types/today';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const TODAY_KEY = ['today'] as const;
const TODAY_SOURCE_KEY = ['today', 'source'] as const;
const REGEN_STATUS_KEY = ['today', 'regeneration-status'] as const;
const REGEN_MUTATION_KEY = ['today', 'regenerate'] as const;

export { REGEN_MUTATION_KEY };

async function fetchToday(): Promise<TodayResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/today`, { headers });
  if (!res.ok) throw new Error(`GET /today failed: ${res.status}`);
  return res.json();
}

async function fetchTodaySource(): Promise<string> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/today/source`, { headers });
  if (!res.ok) throw new Error(`GET /today/source failed: ${res.status}`);
  const data = await res.json();
  return data.body ?? '';
}

async function postNote(text: string): Promise<NoteItem> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/today/notes`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`POST /today/notes failed: ${res.status}`);
  return res.json();
}

async function postTodoToggle(line_id: string, checked: boolean): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/today/todo/toggle`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ line_id, checked }),
  });
  if (!res.ok) throw new Error(`POST /today/todo/toggle failed: ${res.status}`);
}

async function postRegenerate(): Promise<{ run_id: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/today/regenerate`, {
    method: 'POST',
    headers,
  });
  if (!res.ok && res.status !== 202) {
    throw new Error(`POST /today/regenerate failed: ${res.status}`);
  }
  return res.json();
}

async function fetchLatestRegenRun(): Promise<WorkflowRun | null> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/workflows/runs?template_name=regenerate-today&limit=1`,
    { headers },
  );
  if (!res.ok) return null;
  const data = await res.json();
  const runs: WorkflowRun[] = Array.isArray(data) ? data : data.runs || [];
  return runs.length > 0 ? runs[0] : null;
}

// --- Queries ---------------------------------------------------------------

export function useToday() {
  return useQuery<TodayResponse, Error>({
    queryKey: TODAY_KEY,
    queryFn: fetchToday,
    staleTime: 30_000,
  });
}

export function useTodaySource(enabled: boolean) {
  return useQuery<string, Error>({
    queryKey: TODAY_SOURCE_KEY,
    queryFn: fetchTodaySource,
    enabled,
    staleTime: 30_000,
  });
}

// --- Mutations -------------------------------------------------------------

export function useAppendNote() {
  const qc = useQueryClient();
  return useMutation<NoteItem, Error, string>({
    mutationFn: (text: string) => postNote(text),
    onSuccess: (saved) => {
      // Optimistic: append to cached today.notes immediately.
      qc.setQueryData<TodayResponse>(TODAY_KEY, (old) => {
        if (!old) return old;
        return { ...old, notes: [...old.notes, saved] };
      });
      qc.invalidateQueries({ queryKey: TODAY_KEY });
      qc.invalidateQueries({ queryKey: TODAY_SOURCE_KEY });
    },
    onError: (err) => {
      toast.error("Couldn't save note. Try again.", err.message);
    },
  });
}

export function useToggleTodo() {
  const qc = useQueryClient();
  return useMutation<void, Error, { line_id: string; checked: boolean }>({
    mutationFn: ({ line_id, checked }) => postTodoToggle(line_id, checked),
    onMutate: async ({ line_id, checked }) => {
      await qc.cancelQueries({ queryKey: TODAY_KEY });
      const prev = qc.getQueryData<TodayResponse>(TODAY_KEY);
      qc.setQueryData<TodayResponse>(TODAY_KEY, (old) => {
        if (!old) return old;
        return {
          ...old,
          to_do: old.to_do.map((t) => (t.line_id === line_id ? { ...t, checked } : t)),
        };
      });
      return { prev };
    },
    onError: (err, _vars, ctx) => {
      const prev = (ctx as { prev?: TodayResponse } | undefined)?.prev;
      if (prev) qc.setQueryData(TODAY_KEY, prev);
      toast.error("Couldn't update. Try again.", err.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TODAY_KEY });
    },
  });
}

export function useRegenerateToday() {
  const qc = useQueryClient();
  return useMutation<{ run_id: string }, Error, void>({
    mutationKey: REGEN_MUTATION_KEY,
    mutationFn: () => postRegenerate(),
    onSuccess: () => {
      toast.default('Regenerating — Today will refresh within ~30s.');
      qc.invalidateQueries({ queryKey: REGEN_STATUS_KEY });
    },
    onError: (err) => {
      toast.error('Regeneration failed', err.message);
    },
  });
}

/**
 * Polls /api/workflows/runs?template_name=regenerate-today&limit=1 while a
 * regeneration is actually in flight. On mount we do a one-shot fetch; the
 * interval only starts once a non-terminal run is observed, or while the caller
 * signals that a regenerate mutation is pending.
 *
 * When a newer `completed` run is observed (newer than last seen), invalidates
 * the Today query so the UI refetches.
 */
export function useRegenerationStatus(enabled: boolean = false) {
  const qc = useQueryClient();
  const lastCompletedRef = useRef<string | null>(null);

  const query = useQuery<WorkflowRun | null, Error>({
    queryKey: REGEN_STATUS_KEY,
    queryFn: fetchLatestRegenRun,
    refetchInterval: (q) => {
      const data = q.state.data as WorkflowRun | null | undefined;
      const nonTerminal = data?.status === 'pending' || data?.status === 'running';
      return enabled || nonTerminal ? 30_000 : false;
    },
    refetchIntervalInBackground: false,
  });

  const run = query.data;
  useEffect(() => {
    if (!run) return;
    const completedAt = run.completed_at || null;
    if (run.status === 'completed' && completedAt && completedAt !== lastCompletedRef.current) {
      if (lastCompletedRef.current !== null) {
        qc.invalidateQueries({ queryKey: TODAY_KEY });
        qc.invalidateQueries({ queryKey: TODAY_SOURCE_KEY });
      }
      lastCompletedRef.current = completedAt;
    }
  }, [run, qc]);

  return query;
}
