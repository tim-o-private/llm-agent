-- Test Agent Configuration for Gmail Tools Integration Testing
-- This creates a test agent with Gmail tools for integration testing

-- Insert test agent configuration
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

-- Insert Gmail tools for test agent
INSERT INTO agent_tools (
    agent_id,
    name,
    type,
    config,
    is_active,
    "order"
) VALUES (
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent'),
    'gmail_digest',
    'GmailTool',
    '{"tool_class": "GmailDigestTool"}',
    true,
    1
),
(
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_email_digest_agent'),
    'gmail_search',
    'GmailTool', 
    '{"tool_class": "GmailSearchTool"}',
    true,
    2
) ON CONFLICT (agent_id, name) DO UPDATE SET
    type = EXCLUDED.type,
    config = EXCLUDED.config,
    is_active = EXCLUDED.is_active,
    "order" = EXCLUDED."order",
    updated_at = NOW(); 