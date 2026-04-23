/**
 * SPEC-051 Capture types matching the backend capture_router.py
 * response/request models.
 */

export interface CaptureRequest {
  text: string;
  source: 'today' | 'cmdk' | 'chat';
  context?: {
    current_path?: string;
    [key: string]: unknown;
  };
}

export interface CaptureResponse {
  capture_id: string;
  status: 'routing' | 'placed' | 'failed';
  target_path?: string | null;
  target_section?: string | null;
  method?: 'append' | 'create' | null;
  confirmation?: string | null;
  fallback: boolean;
  redirect?: CaptureRedirect | null;
  created_at?: string | null;
  placed_at?: string | null;
  reasoning?: string | null;
  error_detail?: string | null;
}

export type CaptureStatus = CaptureResponse['status'];

export interface CaptureRedirect {
  from_path: string;
  from_section?: string | null;
  target_hint: string;
  new_target_path: string;
  new_target_section?: string | null;
  redirected_at: string;
}

export interface RedirectRequest {
  target_hint: string;
}
