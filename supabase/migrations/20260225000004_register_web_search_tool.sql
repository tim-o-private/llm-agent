-- SPEC-016: Register web search tool
-- Add SearchWebTool type, register in tools table, link to assistant agent

-- 1. Add enum value
-- ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SearchWebTool';

-- 2. Register in tools table (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES (
    'search_web',
    'SearchWebTool',
    'Search the web for current information. Returns titles, URLs, and snippets for up-to-date web results.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    type = EXCLUDED.type,
    description = EXCLUDED.description,
    is_active = true;

-- 3. Link to assistant agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name = 'search_web'
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
