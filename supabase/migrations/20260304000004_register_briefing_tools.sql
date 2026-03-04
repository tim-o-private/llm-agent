-- SPEC-028: Register update_briefing_preferences tool
-- type='system', approval_tier='auto' — no user approval needed

-- 1. Register update_briefing_preferences in tools table (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES (
    'update_briefing_preferences',
    'ManageBriefingPreferencesTool',
    'View or update briefing preferences (morning/evening briefing time, timezone, enabled/disabled). Use ''get'' to view current settings, ''update'' to change them.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    type = EXCLUDED.type,
    description = EXCLUDED.description,
    is_active = true;

-- 2. Link update_briefing_preferences to assistant agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name = 'update_briefing_preferences'
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
