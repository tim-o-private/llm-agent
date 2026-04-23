/**
 * React Query hooks for the SPEC-050 Activity Log API.
 *
 * Endpoints:
 *   GET  /api/activity          (paginated, filtered)
 *   GET  /api/activity/count    (total + since_last_viewed)
 *   POST /api/activity/mark-viewed
 */

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import type {
  ActivityCountResponse,
  ActivityFilters,
  ActivityListResponse,
} from '@/api/types/activity';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const ACTIVITY_KEY = ['activity'] as const;
const ACTIVITY_COUNT_KEY = ['activity', 'count'] as const;

// --- Fetch helpers -----------------------------------------------------------

async function fetchActivityPage(
  filters: ActivityFilters,
  before?: string,
): Promise<ActivityListResponse> {
  const headers = await authHeaders();
  const params = new URLSearchParams();
  params.set('limit', '50');
  if (before) params.set('before', before);
  if (filters.q) params.set('q', filters.q);
  if (filters.status) params.set('status', filters.status);
  if (filters.workflow_run_id)
    params.set('workflow_run_id', filters.workflow_run_id);

  const res = await fetch(
    `${API_BASE_URL}/api/activity?${params.toString()}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /api/activity failed: ${res.status}`);
  return res.json();
}

async function fetchActivityCount(): Promise<ActivityCountResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/activity/count`, { headers });
  if (!res.ok)
    throw new Error(`GET /api/activity/count failed: ${res.status}`);
  return res.json();
}

async function postMarkViewed(): Promise<{ marked_at: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/activity/mark-viewed`, {
    method: 'POST',
    headers,
  });
  if (!res.ok)
    throw new Error(`POST /api/activity/mark-viewed failed: ${res.status}`);
  return res.json();
}

// --- Queries -----------------------------------------------------------------

export function useActivityLog(filters: ActivityFilters = {}) {
  return useInfiniteQuery<ActivityListResponse, Error>({
    queryKey: [...ACTIVITY_KEY, 'list', filters],
    queryFn: ({ pageParam }) =>
      fetchActivityPage(filters, pageParam as string | undefined),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      if (!lastPage.has_more || lastPage.items.length === 0) return undefined;
      // Use created_at of the last item as the cursor
      return lastPage.items[lastPage.items.length - 1].created_at;
    },
    staleTime: 30_000,
  });
}

export function useActivityCount() {
  return useQuery<ActivityCountResponse, Error>({
    queryKey: ACTIVITY_COUNT_KEY,
    queryFn: fetchActivityCount,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    placeholderData: { total: 0, since_last_viewed: 0 },
  });
}

// --- Mutations ---------------------------------------------------------------

export function useMarkActivityViewed() {
  const qc = useQueryClient();
  return useMutation<{ marked_at: string }, Error>({
    mutationFn: postMarkViewed,
    onSuccess: () => {
      // Optimistically set since_last_viewed to 0
      qc.setQueryData<ActivityCountResponse>(
        ACTIVITY_COUNT_KEY,
        (old) => old && { ...old, since_last_viewed: 0 },
      );
      // Then refetch to get the real value
      qc.invalidateQueries({ queryKey: ACTIVITY_COUNT_KEY });
    },
  });
}
