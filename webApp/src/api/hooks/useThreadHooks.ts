/**
 * React Query hooks for the SPEC-054 Thread API.
 *
 * Endpoints:
 *   GET  /api/vault/threads          — list active/watching threads
 *   GET  /api/vault/threads/{slug}   — read a thread-doc
 *   POST /api/vault/threads/{slug}/status — change thread status
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import type { ThreadSummary, ThreadDoc, ThreadListResponse, ThreadStatus } from '@/api/types/thread';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const THREADS_KEY = ['threads'] as const;
const THREAD_KEY = (slug: string) => ['threads', slug] as const;

// --- Fetch helpers ---

async function fetchActiveThreads(status?: ThreadStatus): Promise<ThreadSummary[]> {
  const headers = await authHeaders();
  const params = status ? `?status=${encodeURIComponent(status)}` : '';
  const res = await fetch(`${API_BASE_URL}/api/vault/threads${params}`, { headers });
  if (!res.ok) throw new Error(`GET /vault/threads failed: ${res.status}`);
  const data: ThreadListResponse = await res.json();
  return data.threads;
}

async function fetchThread(slug: string): Promise<ThreadDoc> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/threads/${encodeURIComponent(slug)}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /vault/threads/${slug} failed: ${res.status}`);
  return res.json();
}

async function postChangeStatus(slug: string, status: ThreadStatus): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/threads/${encodeURIComponent(slug)}/status`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    },
  );
  if (!res.ok) throw new Error(`POST /vault/threads/${slug}/status failed: ${res.status}`);
}

// --- Hooks ---

/**
 * Fetch active and watching threads. Optionally filter by status.
 */
export function useActiveThreads(status?: ThreadStatus) {
  return useQuery({
    queryKey: status ? [...THREADS_KEY, status] : THREADS_KEY,
    queryFn: () => fetchActiveThreads(status),
    staleTime: 30_000,
  });
}

/**
 * Fetch a single thread-doc by slug (date-prefixed filename without .md).
 */
export function useThread(slug: string) {
  return useQuery({
    queryKey: THREAD_KEY(slug),
    queryFn: () => fetchThread(slug),
    enabled: !!slug,
  });
}

/**
 * Change a thread's status. Invalidates thread list on success.
 */
export function useChangeThreadStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ slug, status }: { slug: string; status: ThreadStatus }) =>
      postChangeStatus(slug, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: THREADS_KEY });
    },
  });
}
