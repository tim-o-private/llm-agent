-- Fix: Ensure all task tools are active in agent_tools for the assistant agent.
-- The original migration (20260220000000) used NOT EXISTS which could miss
-- rows that were soft-deleted (is_deleted=true) or inactive (is_active=false).
-- This migration uses an upsert approach to guarantee correctness.

-- Step 1: Reactivate any soft-deleted or inactive agent_tools rows
UPDATE agent_tools
SET is_active = true,
    is_deleted = false,
    updated_at = now()
WHERE agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
  AND tool_id IN (SELECT id FROM tools WHERE name IN ('create_task', 'get_task', 'get_tasks', 'update_task', 'delete_task'))
  AND (is_active = false OR is_deleted = true);

-- Step 2: Insert any completely missing rows
INSERT INTO agent_tools (agent_id, tool_id, is_active, is_deleted)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true,
    false
FROM tools t
WHERE t.name IN ('create_task', 'get_task', 'get_tasks', 'update_task', 'delete_task')
  AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
      AND at.tool_id = t.id
      AND at.is_deleted = false
  );
