export type TaskStatus = 'pending' | 'planning' | 'in_progress' | 'completed' | 'skipped' | 'deferred';
export type TaskPriority = 0 | 1 | 2 | 3; // 0: None, 1: Low, 2: Medium, 3: High

export interface Task {
  id: string; // UUID, primary key
  user_id: string; // Foreign key to auth.users.id
  title: string;
  notes?: string | null;
  description?: string | null; // Detailed description of the task
  category?: string | null;
  completed: boolean; // Consider if this is wholly derived from status === 'completed'
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: string | null; // ISO date string
  time_period?: 'Morning' | 'Afternoon' | 'Evening' | null; // Or a more flexible enum/string
  created_at: string; // ISO timestamp string
  updated_at?: string | null; // ISO timestamp string
  position?: number | null; // For task ordering
  parent_task_id?: string | null; // FK to tasks.id, for subtasks
  subtask_position?: number | null; // For ordering subtasks under a parent
  subtasks?: Task[]; // Populated if subtasks are fetched with the parent
  // Add other fields like priority, reminders, etc. as needed
}

// You might also have types for task creation or updates if they differ
export type NewTaskData = Pick<Task, 'title' | 'user_id' | 'status' | 'priority'> & Partial<Omit<Task, 'id' | 'created_at' | 'updated_at' | 'user_id' | 'title' | 'status' | 'priority' | 'subtasks'> >;
export type UpdateTaskData = Partial<Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at' | 'subtasks'>>;

export type FocusSessionMood = 'energized' | 'neutral' | 'drained' | 'focused' | 'distracted' | 'other';
export type FocusSessionOutcome = 'completed_task' | 'made_progress' | 'got_stuck' | 'interrupted' | 'planned_next' | 'other';

export interface FocusSession {
  id: string; // UUID, primary key
  user_id: string; // Foreign key to auth.users.id
  task_id: string; // Foreign key to public.tasks.id
  started_at: string; // ISO timestamp string
  ended_at?: string | null; // ISO timestamp string
  duration_seconds?: number | null;
  notes?: string | null; // User's reflection or notes on the session
  mood?: FocusSessionMood | null;
  outcome?: FocusSessionOutcome | null;
  created_at: string; // ISO timestamp string
}

export type NewFocusSessionData = Pick<FocusSession, 'user_id' | 'task_id'> & Partial<Omit<FocusSession, 'id' | 'created_at' | 'user_id' | 'task_id'> >;
export type UpdateFocusSessionData = Partial<Omit<FocusSession, 'id' | 'user_id' | 'task_id' | 'created_at'>>; 