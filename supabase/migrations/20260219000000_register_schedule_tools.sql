-- Register schedule tools (CreateScheduleTool, DeleteScheduleTool, ListSchedulesTool)
-- and link them to the assistant agent

-- 1. Add new enum values
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'CreateScheduleTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'DeleteScheduleTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'ListSchedulesTool';

-- 2. Register schedule tools in tools registry (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
(
    'create_schedule',
    'CreateScheduleTool',
    'Create a recurring schedule that runs an agent with a given prompt on a cron schedule. Use this when the user wants something done periodically (e.g. daily summaries, weekly reports). The schedule_cron must be a valid 5-field cron expression.',
    '{}'::jsonb,
    true
),
(
    'delete_schedule',
    'DeleteScheduleTool',
    'Delete a recurring schedule by its ID. Use this when the user wants to stop a scheduled task.',
    '{}'::jsonb,
    true
),
(
    'list_schedules',
    'ListSchedulesTool',
    'List the user''s recurring agent schedules. Shows each schedule''s prompt, cron expression, agent, and next run time. Use this when the user asks about their scheduled tasks.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    is_active = true;

-- 3. Link schedule tools to assistant agent (if not already linked)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('create_schedule', 'delete_schedule', 'list_schedules')
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
