-- Fix: create_tasks agent_tools link was created with is_active=false.
-- The SPEC-019 canonical migration Step 4 created the link, but Step 2 had
-- already deactivated the old create_task link. The new create_tasks link
-- inherited the deactivated state. This activates it.

UPDATE agent_tools
SET is_active = true, updated_at = now()
WHERE tool_id = (SELECT id FROM tools WHERE name = 'create_tasks')
  AND agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
  AND is_active = false;
