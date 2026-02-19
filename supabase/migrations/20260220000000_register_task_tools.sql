-- SPEC-013: Register agent task tools
-- Add tool type enum values, register in tools registry, link to assistant agent

-- 1. Add enum values for task tool types


-- 2. Register task tools in tools registry (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
(
    'get_tasks',
    'GetTasksTool',
    'List the user''s tasks. By default shows top-level pending/in-progress tasks. Use filters to narrow results by status, due date, or to include completed tasks and subtasks.',
    '{}'::jsonb,
    true
),
(
    'get_task',
    'GetTaskTool',
    'Get detailed information about a specific task by its ID, including all subtasks.',
    '{}'::jsonb,
    true
),
(
    'create_task',
    'CreateTaskTool',
    'Create a new task for the user. Set parent_task_id to create a subtask under an existing task. Priority: 1=lowest, 5=highest. Default status is pending.',
    '{}'::jsonb,
    true
),
(
    'update_task',
    'UpdateTaskTool',
    'Update a task''s fields. Only provided fields are changed. To mark a task complete, set status to completed. To clear a due date, pass an empty string for due_date.',
    '{}'::jsonb,
    true
),
(
    'delete_task',
    'DeleteTaskTool',
    'Delete a task and all its subtasks. This is a soft delete (can be undone). Use this when the user explicitly asks to remove a task.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    is_active = true;

-- 3. Link task tools to assistant agent (if not already linked)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('get_tasks', 'get_task', 'create_task', 'update_task', 'delete_task')
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
