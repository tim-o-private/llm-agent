/**
 * SPEC-053 AC-07: React Query hooks for the entity index and search APIs.
 *
 * Endpoints consumed:
 *   GET /api/vault/entities/index
 *   GET /api/vault/entities/search?q=<query>
 */

import { useQuery } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import type {
  EntityIndex,
  EntityIndexResponse,
  EntitySearchResponse,
} from '@/api/types/entity';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const ENTITY_INDEX_KEY = ['vault', 'entities', 'index'] as const;
const ENTITY_SEARCH_KEY = ['vault', 'entities', 'search'] as const;

async function fetchEntityIndex(): Promise<EntityIndex> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/entities/index`, { headers });
  if (!res.ok) throw new Error(`GET /vault/entities/index failed: ${res.status}`);
  const data: EntityIndexResponse = await res.json();
  return data.entities;
}

async function fetchEntitySearch(query: string): Promise<EntitySearchResponse> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/entities/search?q=${encodeURIComponent(query)}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /vault/entities/search failed: ${res.status}`);
  return res.json();
}

// --- Queries ----------------------------------------------------------------

/**
 * Fetch and cache the entity index. 5-minute stale time per AC-07.
 */
export function useEntityIndex() {
  return useQuery<EntityIndex, Error>({
    queryKey: [...ENTITY_INDEX_KEY],
    queryFn: fetchEntityIndex,
    staleTime: 5 * 60_000, // 5 minutes
  });
}

/**
 * Search entities by substring match. Query is debounced by the caller.
 */
export function useEntitySearch(query: string, enabled = true) {
  return useQuery<EntitySearchResponse, Error>({
    queryKey: [...ENTITY_SEARCH_KEY, query],
    queryFn: () => fetchEntitySearch(query),
    enabled: enabled && query.length > 0,
    staleTime: 30_000,
  });
}
