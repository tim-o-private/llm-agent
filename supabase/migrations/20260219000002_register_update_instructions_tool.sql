-- Register update_instructions tool and assign to assistant agent

-- 1. Add new enum value
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'UpdateInstructionsTool';

-- 2. Register tool in tools registry (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
(
    'update_instructions',
    'UpdateInstructionsTool',
    'Update your standing instructions for this user. Use this when the user says things like ''always summarize emails in bullet points'' or ''never send emails without asking me first''. This is a REPLACE operation — include all existing instructions you want to keep.',
    '{}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    is_active = true;

-- 3. Link tool to assistant agent (if not already linked)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name = 'update_instructions'
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);
