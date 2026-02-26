-- Add SearchWebTool to agent_tool_type enum
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SearchWebTool';

-- Register search_web tool on assistant agent
INSERT INTO agent_tools (agent_id, tool_name, type, tool_config, is_active, "order")
SELECT
    ac.id,
    'search_web',
    'SearchWebTool'::agent_tool_type,
    '{}'::jsonb,
    true,
    (SELECT COALESCE(MAX("order"), 0) + 1 FROM agent_tools WHERE agent_id = ac.id)
FROM agent_configurations ac
WHERE ac.agent_name = 'assistant';
