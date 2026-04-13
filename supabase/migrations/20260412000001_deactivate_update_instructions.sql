-- Deactivate update_instructions tool.
-- Replaced by Deep Agents' built-in edit_file tool writing to AGENTS.md.

-- Deactivate all agent_tools links for this tool
UPDATE agent_tools
SET is_active = false
WHERE tool_id IN (
    SELECT id FROM tools WHERE name = 'update_instructions'
);

-- Deactivate the tool itself
UPDATE tools
SET is_active = false
WHERE name = 'update_instructions';
