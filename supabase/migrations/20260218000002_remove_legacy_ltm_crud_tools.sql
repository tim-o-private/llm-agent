-- Remove legacy CRUDTool-based LTM tools, replaced by SaveMemoryTool/ReadMemoryTool.
-- save_memory (upsert) and read_memory supersede these with proper tool classes,
-- correct agent_name column handling, and cleaner agent UX (one tool per operation).

-- 1. Unlink from all agents
DELETE FROM agent_tools
WHERE tool_id IN (
    SELECT id FROM tools
    WHERE name IN ('create_agent_long_term_memory', 'update_agent_long_term_memory')
);

-- 2. Remove from tools registry
DELETE FROM tools
WHERE name IN ('create_agent_long_term_memory', 'update_agent_long_term_memory');
