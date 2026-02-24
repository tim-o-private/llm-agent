-- Fix: Ensure create_task tool row in tools table is active and has correct type.
-- Previous migrations may have left is_deleted=true or is_active=false on this row.
-- Also ensures the agent_tools link is active.

-- Step 1: Repair the tools table row for create_task
UPDATE tools
SET
    type = 'CreateTaskTool',
    is_active = true,
    is_deleted = false
WHERE name = 'create_task';

-- Step 2: Repair the agent_tools link for create_task
UPDATE agent_tools
SET
    is_active = true,
    is_deleted = false
WHERE agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
  AND tool_id = (SELECT id FROM tools WHERE name = 'create_task');
