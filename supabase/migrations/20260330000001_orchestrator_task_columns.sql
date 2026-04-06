-- SPEC-004: Add orchestrator columns to tasks table and 'review' status

-- Add 'review' to the task_status enum
ALTER TYPE public.task_status ADD VALUE IF NOT EXISTS 'review' AFTER 'in_progress';
-- Add 'blocked' status for graph interrupts
ALTER TYPE public.task_status ADD VALUE IF NOT EXISTS 'blocked' AFTER 'review';

-- Add orchestrator columns
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS graph_id text;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS node_id text;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS project text;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS assigned_to text;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS output jsonb;

-- Index for querying tasks by graph
CREATE INDEX IF NOT EXISTS idx_tasks_graph_id ON public.tasks (graph_id) WHERE graph_id IS NOT NULL;

-- Index for querying tasks by project
CREATE INDEX IF NOT EXISTS idx_tasks_project ON public.tasks (project) WHERE project IS NOT NULL;

-- Update the status check constraint to include new values
-- (The enum alteration above handles this; the existing CHECK constraint
-- references the enum type, so new enum values are automatically valid.)
-- However, the CHECK constraint explicitly lists enum values, so we need to update it:
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_status_check CHECK (
  status = ANY (ARRAY[
    'pending'::public.task_status,
    'planning'::public.task_status,
    'in_progress'::public.task_status,
    'review'::public.task_status,
    'blocked'::public.task_status,
    'completed'::public.task_status,
    'skipped'::public.task_status,
    'deferred'::public.task_status
  ])
);
