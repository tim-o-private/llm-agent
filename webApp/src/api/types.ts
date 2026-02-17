export type TaskStatus = 'pending' | 'planning' | 'in_progress' | 'completed' | 'skipped' | 'deferred';
export type TaskPriority = 0 | 1 | 2 | 3; // 0: None, 1: Low, 2: Medium, 3: High

export interface Task {
  id: string;
  user_id: string;
  parent_task_id?: string | null;
  title: string;
  description?: string | null;
  notes?: string | null;
  motivation?: string | null;
  completion_note?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null;
  category?: string | null;
  subtask_position?: number | null;
  position?: number | null;
  created_at: string;
  updated_at: string;
  completed: boolean; // Derived from status for easier filtering, ensure it's kept in sync
  completed_at?: string | null;
  deleted: boolean; // Soft delete flag
  subtasks?: Task[]; // Added for client-side handling of subtasks
}

export interface UserPreferences {
  id: string;
  user_id: string;
  dark_mode_enabled?: boolean;
  default_view?: string;
  show_completed_tasks_in_today_view?: boolean;
  // other preferences
}

export type FocusSessionOutcome = 'completed' | 'incomplete' | 'skipped';

export interface FocusSession {
  id: string;
  user_id: string;
  task_id: string; // FK to tasks.id
  start_time: string; // ISO timestamp string
  end_time?: string | null; // ISO timestamp string
  planned_duration_minutes: number;
  actual_duration_minutes?: number | null;
  interruptions?: number | null;
  notes?: string | null; // Notes taken during/after the session
  outcome?: FocusSessionOutcome | null;
  created_at: string; // ISO timestamp string
  motivation?: string | null;
  completion_note?: string | null;
}

export type NewTaskData = Omit<Task, 'id' | 'created_at' | 'updated_at' | 'completed' | 'deleted' | 'subtasks'> & {
  user_id: string;
};
export type UpdateTaskData = Partial<Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at' | 'subtasks'>>;

export type TaskCreatePayload = NewTaskData;
export type TaskUpdatePayload = UpdateTaskData;

export type NewFocusSessionData = Pick<FocusSession, 'user_id' | 'task_id' | 'planned_duration_minutes'> &
  Partial<Omit<FocusSession, 'id' | 'created_at' | 'user_id' | 'task_id' | 'start_time' | 'planned_duration_minutes'>>;
export type UpdateFocusSessionData = Partial<Omit<FocusSession, 'id' | 'user_id' | 'task_id' | 'created_at'>>;

export interface Streak {
  id: string;
  user_id: string;
  start_date: string;
  end_date?: string | null;
  current_length_days: number;
  longest_length_days: number;
}

export interface Reflection {
  id: string;
  user_id: string;
  date: string;
  content: string;
  created_at: string;
}

export interface ScratchPadEntry {
  id: string;
  user_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: string;
  user_id: string;
  title?: string | null;
  content: string;
  created_at: string;
  updated_at: string;
  deleted: boolean; // Soft delete flag
}

export type NewNoteData = Omit<Note, 'id' | 'created_at' | 'updated_at' | 'deleted'> & { user_id: string };
export type UpdateNoteData = Partial<Omit<Note, 'id' | 'user_id' | 'created_at' | 'updated_at'>>;

export type NoteCreatePayload = NewNoteData;
export type NoteUpdatePayload = UpdateNoteData;

// Generic type for API responses with pagination (if needed)
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
