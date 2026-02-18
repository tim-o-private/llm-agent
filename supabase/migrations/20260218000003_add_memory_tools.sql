-- Add SaveMemoryTool and ReadMemoryTool to agent_tool_type enum
-- and register them on the assistant agent

-- 1. Add new enum values
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SaveMemoryTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'ReadMemoryTool';

-- 2. Register memory tools in tools registry (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
(
    'save_memory',
    'SaveMemoryTool',
    'Save or update your long-term memory notes. Use this to remember important information about the user across sessions, such as preferences, ongoing projects, key dates, or anything the user asks you to remember. Notes are scoped to this user and agent. Maximum 4000 characters.',
    '{}'::jsonb,
    true
),
(
    'read_memory',
    'ReadMemoryTool',
    'Read your long-term memory notes for this user. Returns any previously saved notes about preferences, ongoing projects, key dates, or other information you were asked to remember. Notes are scoped to this user and agent.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    is_active = true;

-- 3. Link memory tools to assistant agent (if not already linked)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('save_memory', 'read_memory')
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
