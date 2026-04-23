/**
 * SPEC-054 Thread-docs — TypeScript types for the thread API.
 *
 * Thread-docs are vault files under `_threads/` with YAML frontmatter.
 * These types match the backend response shapes from `thread_router.py`.
 */

export type ThreadStatus = 'active' | 'watching' | 'paused' | 'completed' | 'archived';

export interface ThreadSummary {
  path: string;
  title: string;
  status: ThreadStatus;
  next_action: string | null;
  blocked_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface ThreadDoc {
  content: string;
  mtime: string;
  size: number;
  path: string;
}

export interface ThreadListResponse {
  threads: ThreadSummary[];
}
