-- Add deleted column to tasks table for soft deletes
-- This prevents foreign key constraint violations when deleting tasks

ALTER TABLE public.tasks 
ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- Add index for efficient filtering of non-deleted tasks
CREATE INDEX idx_tasks_deleted ON public.tasks(deleted);

-- Add comment to explain the column
COMMENT ON COLUMN public.tasks.deleted IS 'Soft delete flag - when true, task is considered deleted but preserved for referential integrity'; 