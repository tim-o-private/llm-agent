-- How to edit agent tools in Supabase (Postgres)
-- This file documents how to update or add tools for an agent in the agent_tools table.
-- You can edit the tool_config JSONB to change tool parameters.

-- Example: Update an existing tool's config for an agent
UPDATE agent_tools
SET tool_config = jsonb_set(tool_config, '{param_name}', '"new_value"', true),
    updated_at = now()
WHERE agent_id = '<agent-uuid>'
  AND tool_name = 'MyToolName';

-- Example: Add a new tool for an agent
INSERT INTO agent_tools (
    id, agent_id, tool_name, tool_type, tool_config, is_active, "order", created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '<agent-uuid>',
    'NewToolName',
    'FileManagementToolkit',
    '{"root_dir": "/app/data", "selected_tools": ["read_file", "write_file"]}',
    true,
    2,
    now(),
    now()
);

-- Note: Replace <agent-uuid> with the actual agent_configurations.id value.
-- You can use SELECT id FROM agent_configurations WHERE agent_name = 'your_agent_name'; 