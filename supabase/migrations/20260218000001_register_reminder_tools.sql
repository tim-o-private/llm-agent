-- Register reminder tools on the assistant agent
INSERT INTO agent_tools (agent_id, tool_name, tool_type, tool_config, is_active, "order")
SELECT id, 'create_reminder', 'CreateReminderTool', '{}', true, 12
FROM agent_configurations WHERE agent_name = 'assistant';

INSERT INTO agent_tools (agent_id, tool_name, tool_type, tool_config, is_active, "order")
SELECT id, 'list_reminders', 'ListRemindersTool', '{}', true, 13
FROM agent_configurations WHERE agent_name = 'assistant';
