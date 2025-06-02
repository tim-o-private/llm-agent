-- Configure Gmail Tools for Email Digest Agent
-- This migration adds Gmail digest and search tools to the email digest agent
-- Following the established tool configuration patterns

-- Configure Gmail digest tool
INSERT INTO agent_tools (
    agent_id,
    name,
    description,
    type,
    config,
    "order",
    created_at,
    updated_at
) VALUES (
    (SELECT id FROM agent_configurations WHERE agent_name = 'email_digest_agent'),
    'gmail_digest',
    'Generate a digest of recent emails from Gmail. Analyzes email threads and provides a summary of important messages.',
    'GmailTool',
    '{
        "tool_class": "GmailDigestTool",
        "runtime_args_schema": {
            "hours_back": {
                "type": "int",
                "optional": false,
                "description": "Hours to look back for emails (1-168)",
                "default": 24,
                "minimum": 1,
                "maximum": 168
            },
            "max_threads": {
                "type": "int", 
                "optional": true,
                "description": "Maximum number of email threads to analyze",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            },
            "include_read": {
                "type": "bool",
                "optional": true,
                "description": "Whether to include read emails in the digest",
                "default": false
            }
        }
    }'::jsonb,
    1,
    NOW(),
    NOW()
) ON CONFLICT (agent_id, name) DO UPDATE SET
    description = EXCLUDED.description,
    type = EXCLUDED.type,
    config = EXCLUDED.config,
    "order" = EXCLUDED."order",
    updated_at = NOW();

-- Configure Gmail search tool
INSERT INTO agent_tools (
    agent_id,
    name,
    description,
    type,
    config,
    "order",
    created_at,
    updated_at
) VALUES (
    (SELECT id FROM agent_configurations WHERE agent_name = 'email_digest_agent'),
    'gmail_search',
    'Search Gmail messages using Gmail search syntax. Examples: is:unread, from:example@gmail.com, subject:meeting, newer_than:2d.',
    'GmailTool',
    '{
        "tool_class": "GmailSearchTool",
        "runtime_args_schema": {
            "query": {
                "type": "str",
                "optional": false,
                "description": "Gmail search query using Gmail search syntax (e.g., is:unread, from:example@gmail.com)"
            },
            "max_results": {
                "type": "int",
                "optional": true,
                "description": "Maximum number of search results to return",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            }
        }
    }'::jsonb,
    2,
    NOW(),
    NOW()
) ON CONFLICT (agent_id, name) DO UPDATE SET
    description = EXCLUDED.description,
    type = EXCLUDED.type,
    config = EXCLUDED.config,
    "order" = EXCLUDED."order",
    updated_at = NOW(); 