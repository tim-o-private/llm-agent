-- SPEC-027: Register calendar tools
-- Add SearchCalendarTool and GetCalendarEventTool types, register in tools table, link to assistant agent

-- 1. Add enum values
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SearchCalendarTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'GetCalendarEventTool';

-- 2. Register search_calendar in tools table (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES (
    'search_calendar',
    'SearchCalendarTool',
    'Search your Google Calendar for events. Returns event titles, times, locations, and attendees. Defaults to today''s events.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    type = EXCLUDED.type,
    description = EXCLUDED.description,
    is_active = true;

-- 3. Register get_calendar_event in tools table (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES (
    'get_calendar_event',
    'GetCalendarEventTool',
    'Get full details for a specific calendar event by ID including description, attendees, and conferencing info.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    type = EXCLUDED.type,
    description = EXCLUDED.description,
    is_active = true;

-- 4. Link search_calendar to assistant agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name = 'search_calendar'
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);

-- 5. Link get_calendar_event to assistant agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name = 'get_calendar_event'
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
