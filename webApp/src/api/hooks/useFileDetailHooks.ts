/**
 * SPEC-047 FU-3 + FU-4: React Query hooks for the file detail view.
 *
 * Endpoints consumed:
 *   PUT  /api/vault/file                    (save)
 *   GET  /api/vault/backlinks?path=         (backlinks)
 *   GET  /api/vault/file/context?path=      (file context + suggest cards)
 *   POST /api/vault/file/suggest/{id}/accept
 *   POST /api/vault/file/suggest/{id}/dismiss
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import { toast } from '@/components/ui/toast';
import type {
  SaveFileRequest,
  SaveFileResponse,
  BacklinksResponse,
  FileContextResponse,
} from '@/api/types/fileDetail';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// --- Mutations ---------------------------------------------------------------

async function saveFile(payload: SaveFileRequest): Promise<SaveFileResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/vault/file`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(payload),
  });

  if (res.status === 409) {
    throw Object.assign(new Error('File was modified elsewhere — reload to see changes'), {
      status: 409,
    });
  }
  if (res.status === 413) {
    throw Object.assign(new Error('File exceeds size limit'), { status: 413 });
  }
  if (!res.ok) {
    throw Object.assign(new Error(`PUT /vault/file failed: ${res.status}`), {
      status: res.status,
    });
  }

  return res.json();
}

/**
 * `useSaveFile` — mutation that saves file content via PUT /api/vault/file.
 *
 * On success: invalidates the vault file query so stale data is refreshed.
 * On 409: toasts "File was modified elsewhere".
 * On error: toasts "Save failed".
 */
export function useSaveFile() {
  const queryClient = useQueryClient();

  return useMutation<SaveFileResponse, Error & { status?: number }, SaveFileRequest>({
    mutationFn: saveFile,
    onSuccess: (_data, variables) => {
      // Invalidate the vault file query so content refreshes
      queryClient.invalidateQueries({ queryKey: ['vault', 'file', variables.path] });
    },
    onError: (error) => {
      if ((error as Error & { status?: number }).status === 409) {
        toast.error('File was modified elsewhere — reload to see changes');
      } else if ((error as Error & { status?: number }).status === 413) {
        toast.error('File exceeds size limit');
      } else {
        toast.error('Save failed — try again');
      }
    },
  });
}

// --- Backlinks ---------------------------------------------------------------

const VAULT_BACKLINKS_KEY = ['vault', 'backlinks'] as const;

async function fetchBacklinks(path: string): Promise<BacklinksResponse> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/backlinks?path=${encodeURIComponent(path)}`,
    { headers },
  );
  if (!res.ok) throw new Error(`GET /vault/backlinks failed: ${res.status}`);
  return res.json();
}

/**
 * `useBacklinks` — fetches backlinks (incoming wiki-links) for a file.
 * React Query with 60s stale time.
 */
export function useBacklinks(path: string) {
  return useQuery<BacklinksResponse, Error>({
    queryKey: [...VAULT_BACKLINKS_KEY, path],
    queryFn: () => fetchBacklinks(path),
    enabled: !!path,
    staleTime: 60_000,
  });
}

// --- File Context ------------------------------------------------------------

const VAULT_FILE_CONTEXT_KEY = ['vault', 'file', 'context'] as const;

async function fetchFileContext(path: string): Promise<FileContextResponse> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/file/context?path=${encodeURIComponent(path)}`,
    { headers },
  );
  if (!res.ok)
    throw new Error(`GET /vault/file/context failed: ${res.status}`);
  return res.json();
}

/**
 * `useFileContext` — fetches AI context (summary, suggest cards, activity)
 * for a file. React Query with 30s stale time.
 */
export function useFileContext(path: string) {
  return useQuery<FileContextResponse, Error>({
    queryKey: [...VAULT_FILE_CONTEXT_KEY, path],
    queryFn: () => fetchFileContext(path),
    enabled: !!path,
    staleTime: 30_000,
  });
}

// --- Suggest Card Actions ----------------------------------------------------

interface AcceptResponse {
  text: string;
  target_line: number;
}

async function acceptSuggestCard(id: string): Promise<AcceptResponse> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/file/suggest/${encodeURIComponent(id)}/accept`,
    { method: 'POST', headers },
  );
  if (!res.ok)
    throw new Error(`POST /vault/file/suggest/${id}/accept failed: ${res.status}`);
  return res.json();
}

async function dismissSuggestCard(id: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/vault/file/suggest/${encodeURIComponent(id)}/dismiss`,
    { method: 'POST', headers },
  );
  if (res.status !== 204 && !res.ok)
    throw new Error(`POST /vault/file/suggest/${id}/dismiss failed: ${res.status}`);
}

/**
 * `useSuggestCardAccept` — mutation that accepts a suggest card.
 * Returns the suggested text + target line. Invalidates file context query.
 */
export function useSuggestCardAccept() {
  const queryClient = useQueryClient();

  return useMutation<AcceptResponse, Error, { id: string; filePath: string }>({
    mutationFn: ({ id }) => acceptSuggestCard(id),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...VAULT_FILE_CONTEXT_KEY, variables.filePath],
      });
    },
    onError: () => {
      toast.error('Failed to accept suggestion');
    },
  });
}

/**
 * `useSuggestCardDismiss` — mutation that dismisses a suggest card.
 * Invalidates file context query.
 */
export function useSuggestCardDismiss() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { id: string; filePath: string }>({
    mutationFn: ({ id }) => dismissSuggestCard(id),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...VAULT_FILE_CONTEXT_KEY, variables.filePath],
      });
    },
    onError: () => {
      toast.error('Failed to dismiss suggestion');
    },
  });
}
