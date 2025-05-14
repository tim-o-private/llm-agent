export interface Task {
  id: string; // UUID, primary key
  user_id: string; // Foreign key to auth.users.id
  title: string;
  notes?: string | null;
  category?: string | null;
  completed: boolean;
  due_date?: string | null; // ISO date string
  time_period?: 'Morning' | 'Afternoon' | 'Evening' | null; // Or a more flexible enum/string
  created_at: string; // ISO timestamp string
  updated_at?: string | null; // ISO timestamp string
  // Add other fields like priority, reminders, etc. as needed
}

// You might also have types for task creation or updates if they differ
export type NewTaskData = Pick<Task, 'title' | 'user_id'> & Partial<Omit<Task, 'id' | 'created_at' | 'updated_at' | 'user_id' | 'title'>>;
export type UpdateTaskData = Partial<Omit<Task, 'id' | 'user_id' | 'created_at' | 'updated_at'>>; 