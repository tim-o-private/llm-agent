-- Add approval_tier to tools table
ALTER TABLE tools ADD COLUMN IF NOT EXISTS approval_tier VARCHAR(50);

-- Add status to agent_tools table
ALTER TABLE agent_tools ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'granted';

-- Backfill existing agent_tools rows
UPDATE agent_tools SET status = 'granted' WHERE status IS NULL;

-- Change tools.type from enum to text to support extensible tool types (e.g. WebhookTool)
ALTER TABLE tools ALTER COLUMN type TYPE TEXT;

-- Seed approval_tier for canonical tools from TOOL_APPROVAL_DEFAULTS
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_tasks';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'create_tasks';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'update_tasks';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'delete_tasks';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_reminders';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'create_reminders';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'delete_reminders';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_schedules';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'create_schedules';
UPDATE tools SET approval_tier = 'user_configurable' WHERE name = 'delete_schedules';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_gmail';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_gmail';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_calendar';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_calendar_event';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'create_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'update_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'delete_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'set_project';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'link_memories';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_entities';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_entities';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'get_context';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'search_web';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'draft_email_reply';
UPDATE tools SET approval_tier = 'requires_approval' WHERE name = 'send_email_reply';
UPDATE tools SET approval_tier = 'auto' WHERE name = 'update_briefing_preferences';
