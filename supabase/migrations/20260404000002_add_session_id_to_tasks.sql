-- Add session_id to tasks for tracking claude -p sessions
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS session_id TEXT;
CREATE INDEX IF NOT EXISTS idx_tasks_session_id ON tasks(session_id);

-- Add parent_task_id for task hierarchy
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_task_id UUID REFERENCES tasks(id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id);
