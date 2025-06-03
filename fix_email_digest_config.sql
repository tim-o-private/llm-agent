-- Fix EmailDigestAgent configuration issues
-- Run this script to fix the Gemini model name and missing tool configuration

-- 1. Fix Gemini model name from 'gemini-pro' to 'gemini-1.5-pro'
UPDATE agent_configurations 
SET llm_config = jsonb_set(llm_config, '{model}', '"gemini-1.5-pro"')
WHERE agent_name = 'email_digest_agent';

-- 2. Fix missing tool_class for gmail_get_message tool (if it exists)
-- First, let's check if this tool exists and add the missing tool_class
UPDATE tools 
SET config = jsonb_set(
    COALESCE(config, '{}'), 
    '{tool_class}', 
    '"GmailGetMessageTool"'
)
WHERE name = 'gmail_get_message' 
AND type = 'GmailTool' 
AND (config->>'tool_class') IS NULL;

-- 3. Verify the changes
SELECT 
    agent_name,
    llm_config->>'model' as model_name,
    llm_config->>'provider' as provider
FROM agent_configurations 
WHERE agent_name = 'email_digest_agent';

-- 4. Show Gmail tools configuration
SELECT 
    t.name,
    t.type,
    t.config->>'tool_class' as tool_class,
    t.is_active
FROM tools t
JOIN agent_tools at ON t.id = at.tool_id
JOIN agent_configurations ac ON at.agent_id = ac.id
WHERE ac.agent_name = 'email_digest_agent'
AND t.type = 'GmailTool'
ORDER BY t.name; 