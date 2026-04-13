-- Add last_run_at to agent_schedules so the scheduler can persist execution
-- history across server restarts and avoid silently dropping missed jobs.
ALTER TABLE agent_schedules
  ADD COLUMN IF NOT EXISTS last_run_at timestamptz;
