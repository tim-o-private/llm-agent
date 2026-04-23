/**
 * SPEC-050 Activity Log — TypeScript types matching the backend
 * response shapes from activity_router.py.
 */

export interface ActivityEntry {
  id: string;
  user_id: string;
  actor: string;
  action: string;
  subject_path: string | null;
  workflow_run_id: string | null;
  status: 'done' | 'failed' | 'awaiting_approval';
  reasoning: string | null;
  created_at: string;
}

export interface ActivityListResponse {
  items: ActivityEntry[];
  total: number;
  has_more: boolean;
}

export interface ActivityCountResponse {
  total: number;
  since_last_viewed: number;
}

export interface ActivityFilters {
  q?: string;
  status?: string;
  workflow_run_id?: string;
}
