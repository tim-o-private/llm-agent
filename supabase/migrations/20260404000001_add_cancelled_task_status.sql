-- Add 'cancelled' to task_status enum for rejected graph tasks
ALTER TYPE public.task_status ADD VALUE IF NOT EXISTS 'cancelled' AFTER 'blocked';

-- Update check constraint to include cancelled
ALTER TABLE public.tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE public.tasks ADD CONSTRAINT tasks_status_check CHECK (
  status = ANY (ARRAY[
    'pending'::public.task_status,
    'planning'::public.task_status,
    'in_progress'::public.task_status,
    'review'::public.task_status,
    'blocked'::public.task_status,
    'cancelled'::public.task_status,
    'completed'::public.task_status,
    'skipped'::public.task_status,
    'deferred'::public.task_status
  ])
);
