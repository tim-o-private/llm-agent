/**
 * React Query hooks for the SPEC-051 Capture API.
 *
 * Endpoints consumed:
 *   POST /api/capture
 *   GET  /api/capture/{id}
 *   POST /api/capture/{id}/redirect
 */

import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authHeaders } from '@/lib/apiClient';
import { toast } from '@/components/ui/toast';
import type { CaptureRequest, CaptureResponse, RedirectRequest } from '@/api/types/capture';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const CAPTURE_KEY = ['capture'] as const;
const TODAY_KEY = ['today'] as const;

async function postCapture(req: CaptureRequest): Promise<CaptureResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/capture`, {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`POST /capture failed: ${res.status}`);
  return res.json();
}

async function fetchCapture(captureId: string): Promise<CaptureResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/capture/${captureId}`, { headers });
  if (!res.ok) throw new Error(`GET /capture/${captureId} failed: ${res.status}`);
  return res.json();
}

async function postRedirect(captureId: string, req: RedirectRequest): Promise<CaptureResponse> {
  const headers = await authHeaders();
  const res = await fetch(`${API_BASE_URL}/api/capture/${captureId}/redirect`, {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`POST /capture/${captureId}/redirect failed: ${res.status}`);
  return res.json();
}

// --- Mutations -------------------------------------------------------------

export function useCreateCapture() {
  const qc = useQueryClient();
  return useMutation<CaptureResponse, Error, CaptureRequest>({
    mutationFn: postCapture,
    onSuccess: () => {
      // Invalidate today query since capture may have modified today.md
      qc.invalidateQueries({ queryKey: TODAY_KEY });
    },
    onError: (err) => {
      toast.error("Couldn't capture. Try again.", err.message);
    },
  });
}

export function useRedirectCapture() {
  const qc = useQueryClient();
  return useMutation<CaptureResponse, Error, { captureId: string; targetHint: string }>({
    mutationFn: ({ captureId, targetHint }) =>
      postRedirect(captureId, { target_hint: targetHint }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TODAY_KEY });
    },
    onError: (err) => {
      toast.error("Couldn't redirect. Try again.", err.message);
    },
  });
}

/**
 * Poll the capture status at 1-second intervals for up to 10 seconds
 * while the capture is still routing. After 10 seconds of routing,
 * stops polling automatically.
 */
export function useCaptureStatus(captureId: string | null) {
  const startTimeRef = useRef<number>(Date.now());

  // Reset the start time when captureId changes
  useEffect(() => {
    startTimeRef.current = Date.now();
  }, [captureId]);

  return useQuery<CaptureResponse, Error>({
    queryKey: [...CAPTURE_KEY, captureId],
    queryFn: () => fetchCapture(captureId!),
    enabled: !!captureId,
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data || data.status !== 'routing') return false;
      // Stop polling after 10 seconds
      const elapsed = Date.now() - startTimeRef.current;
      if (elapsed > 10_000) return false;
      return 1_000;
    },
    refetchIntervalInBackground: false,
  });
}
