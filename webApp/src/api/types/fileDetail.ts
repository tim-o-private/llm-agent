/**
 * SPEC-047 File Detail View types.
 *
 * Covers save endpoint, backlinks, AI context, and suggest cards.
 */

export interface SaveFileRequest {
  path: string;
  content: string;
  mtime: number;
}

export interface SaveFileResponse {
  mtime: number;
}

export interface BacklinksResponse {
  backlinks: Array<{ path: string; name: string }>;
}

export interface SuggestCard {
  id: string;
  file_path: string;
  target_line: number;
  label: string;
  body: string;
  suggested_text: string | null;
  status: 'pending' | 'accepted' | 'dismissed';
  created_at: string;
}

export interface ActivityEntry {
  id: string;
  actor: string;
  action: string;
  status: string;
  created_at: string;
}

export interface FileContextResponse {
  summary: string | null;
  suggest_cards: SuggestCard[];
  activity: ActivityEntry[];
}
