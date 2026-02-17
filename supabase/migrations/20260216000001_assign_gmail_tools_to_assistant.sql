-- Assign Gmail read tools to the assistant agent
-- Gmail search, get_message, and digest tools are read-only (AUTO_APPROVE tier)

-- Ensure Gmail tools exist in tools registry (idempotent)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
(
    'gmail_search',
    'GmailTool',
    'Search Gmail messages using Gmail search syntax. Examples: is:unread, from:example@gmail.com, subject:meeting, newer_than:2d. Returns message IDs, subjects, and basic metadata.',
    '{"tool_class": "GmailSearchTool", "runtime_args_schema": {"query": {"type": "str", "optional": false, "description": "Gmail search query using Gmail search syntax"}, "max_results": {"type": "int", "optional": true, "description": "Maximum number of results (1-50)", "default": 10}}}'::jsonb,
    true
),
(
    'gmail_get_message',
    'GmailTool',
    'Get detailed Gmail message content by ID. Retrieves full message content including body, headers, and attachments info.',
    '{"tool_class": "GmailGetMessageTool", "runtime_args_schema": {"message_id": {"type": "str", "optional": false, "description": "Gmail message ID to retrieve"}}}'::jsonb,
    true
),
(
    'gmail_digest',
    'GmailTool',
    'Generate a digest of recent emails from Gmail. Analyzes email threads and provides a summary of important messages.',
    '{"tool_class": "GmailDigestTool", "runtime_args_schema": {"hours_back": {"type": "int", "optional": false, "description": "Hours to look back (1-168)", "default": 24}, "include_read": {"type": "bool", "optional": true, "default": false}, "max_emails": {"type": "int", "optional": true, "default": 20}}}'::jsonb,
    true
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    is_active = true;

-- Link Gmail tools to assistant agent (if not already linked)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'assistant'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('gmail_search', 'gmail_get_message', 'gmail_digest')
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'assistant')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);

-- Update LLM config for assistant to use Claude
UPDATE agent_configurations
SET llm_config = jsonb_set(
    jsonb_set(
        llm_config,
        '{provider}',
        '"claude"'
    ),
    '{model}',
    '"claude-haiku-4-5-20251001"'
)
WHERE agent_name = 'assistant';

-- Also update email_digest_agent LLM config
UPDATE agent_configurations
SET llm_config = jsonb_set(
    jsonb_set(
        llm_config,
        '{provider}',
        '"claude"'
    ),
    '{model}',
    '"claude-haiku-4-5-20251001"'
)
WHERE agent_name = 'email_digest_agent';
