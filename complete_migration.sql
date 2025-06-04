-- Complete the data migration from agent_tools_backup to tools
INSERT INTO tools (name, type, description, config, is_active, created_at, updated_at)
SELECT DISTINCT 
    name,
    type,
    COALESCE(description, ''),
    COALESCE(config, '{}'),
    true,
    MIN(created_at),
    MAX(updated_at)
FROM agent_tools_backup 
WHERE is_deleted = FALSE
GROUP BY name, type, COALESCE(description, ''), COALESCE(config, '{}')
ON CONFLICT (name) DO NOTHING;

-- Populate new agent_tools linking table from backup
INSERT INTO agent_tools (agent_id, tool_id, config_override, is_active, created_at, updated_at)
SELECT 
    atb.agent_id,
    t.id as tool_id,
    CASE 
        WHEN atb.config != t.config THEN atb.config 
        ELSE '{}'::jsonb 
    END as config_override,
    atb.is_active,
    atb.created_at,
    atb.updated_at
FROM agent_tools_backup atb
JOIN tools t ON t.name = atb.name AND t.type = atb.type
WHERE atb.is_deleted = FALSE
ON CONFLICT DO NOTHING; 