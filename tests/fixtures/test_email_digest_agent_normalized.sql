-- Test Agent Configuration for Gmail Tools Integration Testing
-- This creates a test agent with Gmail tools using the new normalized schema
-- Pattern: agents -> agent_tools -> tools

-- 1. Insert test agent configuration
INSERT INTO agent_configurations (
    agent_name,
    system_prompt,
    llm_config
) VALUES (
    'test_email_digest_agent',
    'You are a helpful assistant that can access Gmail to help users manage their email. Use the available Gmail tools to search emails and generate digests when requested.',
    '{"provider": "openai", "model": "gpt-4", "temperature": 0.1}'
) ON CONFLICT (agent_name) DO UPDATE SET
    system_prompt = EXCLUDED.system_prompt,
    llm_config = EXCLUDED.llm_config,
    updated_at = NOW();

-- 2. Insert Gmail tools into tools registry (if they don't exist)
INSERT INTO tools (name, type, description, config)
VALUES 
(
    'gmail_digest',
    'GmailTool',
    'Generate a digest of recent emails from Gmail. Analyzes email threads and provides a summary of important messages.',
    '{"tool_class": "GmailDigestTool", "runtime_args_schema": {"hours_back": {"type": "int", "optional": false, "description": "Hours to look back for emails (1-168)", "default": 24}, "max_threads": {"type": "int", "optional": true, "description": "Maximum number of email threads to analyze", "default": 20}, "include_read": {"type": "bool", "optional": true, "description": "Whether to include read emails in the digest", "default": false}}}'
),
(
    'gmail_search',
    'GmailTool',
    'Search Gmail messages using Gmail search syntax. Examples: is:unread, from:example@gmail.com, subject:meeting, newer_than:2d.',
    '{"tool_class": "GmailSearchTool", "runtime_args_schema": {"query": {"type": "str", "optional": false, "description": "Gmail search query using Gmail search syntax"}, "max_results": {"type": "int", "optional": true, "description": "Maximum number of search results to return", "default": 20}}}'
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    config = EXCLUDED.config,
    updated_at = NOW();

-- 3. Delete existing tool assignments for this agent (for clean test setup)
DELETE FROM agent_tools 
WHERE agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent');

-- 4. Assign Gmail tools to test agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT 
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('gmail_digest', 'gmail_search')
AND t.is_deleted = FALSE; 