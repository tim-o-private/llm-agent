-- Fix Gmail Tools Consistency Issues
-- This script removes the inconsistent gmail_get_message tool and ensures 
-- all remaining Gmail tools use the correct tool_class configuration format

-- 1. Show current state before changes
SELECT 
    'BEFORE CHANGES' as status,
    t.name,
    t.type,
    t.config->>'tool_class' as tool_class,
    t.config->>'operation' as operation,
    t.is_active
FROM tools t
WHERE t.type = 'GmailTool'
ORDER BY t.name;

-- 2. Remove the inconsistent gmail_get_message tool
-- First, remove it from agent_tools assignments
DELETE FROM agent_tools 
WHERE tool_id IN (
    SELECT id FROM tools 
    WHERE name = 'gmail_get_message' 
    AND type = 'GmailTool'
);

-- Then remove the tool itself
DELETE FROM tools 
WHERE name = 'gmail_get_message' 
AND type = 'GmailTool';

-- 3. Verify that remaining tools have correct tool_class configuration
-- gmail_digest should have tool_class = "GmailDigestTool"
UPDATE tools 
SET config = jsonb_set(
    COALESCE(config, '{}'), 
    '{tool_class}', 
    '"GmailDigestTool"'
)
WHERE name = 'gmail_digest' 
AND type = 'GmailTool'
AND (config->>'tool_class') != 'GmailDigestTool';

-- gmail_search should have tool_class = "GmailSearchTool"  
UPDATE tools 
SET config = jsonb_set(
    COALESCE(config, '{}'), 
    '{tool_class}', 
    '"GmailSearchTool"'
)
WHERE name = 'gmail_search' 
AND type = 'GmailTool'
AND (config->>'tool_class') != 'GmailSearchTool';

-- 4. Show final state after changes
SELECT 
    'AFTER CHANGES' as status,
    t.name,
    t.type,
    t.config->>'tool_class' as tool_class,
    t.config->>'operation' as operation,
    t.is_active
FROM tools t
WHERE t.type = 'GmailTool'
ORDER BY t.name;

-- 5. Verify agent_tools assignments are correct
SELECT 
    'AGENT TOOL ASSIGNMENTS' as status,
    ac.agent_name,
    t.name as tool_name,
    t.config->>'tool_class' as tool_class,
    at.is_active
FROM agent_tools at
JOIN tools t ON at.tool_id = t.id
JOIN agent_configurations ac ON at.agent_id = ac.id
WHERE t.type = 'GmailTool'
AND ac.agent_name = 'email_digest_agent'
ORDER BY t.name; 