/**
 * SPEC-047 FU-3: React Query hooks for the file detail view.
 *
 * Endpoints consumed:
 *   PUT /api/vault/file      (save)
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import { toast } from '@/components/ui/toast';
import type { SaveFileRequest, SaveFileResponse } from '@/api/types/fileDetail';

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
