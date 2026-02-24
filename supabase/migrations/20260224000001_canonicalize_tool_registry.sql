-- SPEC-019: Canonicalize tool registry, update soul, add prompt_template
-- One migration to establish the canonical state for all tool registrations.

-- ============================================================
-- Step 1: Deactivate ALL old/ghost/replaced tools
-- ============================================================
UPDATE tools SET is_active = false, updated_at = now()
WHERE name IN (
  -- Ghost tools (CRUDTool era)
  'delete_agent_long_term_memory',
  'fetch_agent_long_term_memory',
  'fetch_tasks',
  -- Already deactivated in SPEC-018 but ensure they stay off
  'save_memory',
  'read_memory',
  -- Digest tools (replaced by search_gmail + agent reasoning)
  'email_digest',
  'gmail_digest',
  -- Old Gmail names (verb_resource reorder)
  'gmail_search',
  'gmail_get_message',
  -- Old singular task tools (consolidated to plural)
  'get_task',
  'delete_task',
  'create_task',
  'update_task',
  -- Old reminder tools (renamed to plural verb_resource)
  'list_reminders',
  'create_reminder',
  -- Old schedule tools (renamed to plural verb_resource)
  'list_schedules',
  'create_schedule',
  'delete_schedule',
  -- Old memory tools (renamed to plural verb_resource)
  'store_memory',
  'recall',
  'search_memory',
  'fetch_memory',
  'delete_memory',
  'update_memory',
  -- Old memory utility tools (renamed)
  'list_entities',
  'get_context_info'
);

-- ============================================================
-- Step 2: Deactivate agent_tools links for all deactivated tools
-- ============================================================
UPDATE agent_tools SET is_active = false, updated_at = now()
WHERE tool_id IN (
  SELECT id FROM tools WHERE name IN (
    'delete_agent_long_term_memory', 'fetch_agent_long_term_memory', 'fetch_tasks',
    'save_memory', 'read_memory',
    'email_digest', 'gmail_digest',
    'gmail_search', 'gmail_get_message',
    'get_task', 'delete_task', 'create_task', 'update_task',
    'list_reminders', 'create_reminder',
    'list_schedules', 'create_schedule', 'delete_schedule',
    'store_memory', 'recall', 'search_memory', 'fetch_memory',
    'delete_memory', 'update_memory',
    'list_entities', 'get_context_info'
  )
);

-- ============================================================
-- Step 3: Upsert 23 canonical tools
-- ============================================================
-- Note: get_tasks already exists but may have stale type/description.
-- update_instructions already exists. set_project, link_memories, search_entities
-- were registered in SPEC-018 and keep their names.

INSERT INTO tools (name, type, description, config, is_active)
VALUES
  -- Task tools (4)
  ('get_tasks', 'GetTasksTool',
   'Get tasks. Optionally filter by id for a single task, or by status/priority.',
   '{}', true),
  ('create_tasks', 'CreateTasksTool',
   'Create one or more tasks. Accepts a list of task objects with title, description, priority, due date.',
   '{}', true),
  ('update_tasks', 'UpdateTasksTool',
   'Update one or more tasks. Accepts a list of {id, ...fields} objects. Use for status changes, edits, completions.',
   '{}', true),
  ('delete_tasks', 'DeleteTasksTool',
   'Delete one or more tasks by ID. Accepts a list of task IDs.',
   '{}', true),

  -- Reminder tools (3)
  ('get_reminders', 'GetRemindersTool',
   'Get reminders. Returns active reminders with their trigger times and messages.',
   '{}', true),
  ('create_reminders', 'CreateRemindersTool',
   'Create one or more reminders. Each needs a message and trigger time.',
   '{}', true),
  ('delete_reminders', 'DeleteRemindersTool',
   'Delete one or more reminders by ID. Accepts a list of reminder IDs.',
   '{}', true),

  -- Schedule tools (3)
  ('get_schedules', 'GetSchedulesTool',
   'Get schedules. Returns active scheduled automations with their cron expressions and prompts.',
   '{}', true),
  ('create_schedules', 'CreateSchedulesTool',
   'Create a scheduled automation. Needs a cron expression, prompt, and optional channel.',
   '{}', true),
  ('delete_schedules', 'DeleteSchedulesTool',
   'Delete one or more schedules by ID. Accepts a list of schedule IDs.',
   '{}', true),

  -- Update instructions (1) — name unchanged
  ('update_instructions', 'UpdateInstructionsTool',
   'Update the user''s persistent instructions. Use when they say "always do X" or "never do Y".',
   '{}', true),

  -- Gmail tools (2)
  ('search_gmail', 'SearchGmailTool',
   'Search Gmail messages. Supports Gmail search syntax (from:, subject:, after:, label:, etc).',
   '{}', true),
  ('get_gmail', 'GetGmailTool',
   'Get the full content of a specific Gmail message by ID.',
   '{}', true),

  -- Memory tools (5)
  ('create_memories', 'CreateMemoriesTool',
   'Store a memory. Use proactively when you learn something — preferences, habits, projects, decisions.',
   '{}', true),
  ('search_memories', 'SearchMemoriesTool',
   'Search and recall memories relevant to a query. Returns semantically similar memories with hierarchical context.',
   '{}', true),
  ('get_memories', 'GetMemoriesTool',
   'Fetch a specific memory by its ID. Use after search to get full details.',
   '{}', true),
  ('update_memories', 'UpdateMemoriesTool',
   'Update an existing memory''s text and/or metadata fields. Only provided fields are changed.',
   '{}', true),
  ('delete_memories', 'DeleteMemoriesTool',
   'Delete a memory. Use when the user asks you to forget something or when information is outdated.',
   '{}', true),

  -- Memory utility tools (5) — set_project, link_memories, search_entities keep names
  ('set_project', 'SetProjectTool',
   'Validate a project exists in memory or create it. Returns project summary with memory counts.',
   '{}', true),
  ('link_memories', 'LinkMemoriesTool',
   'Link two memories with a relationship (supports, contradicts, supersedes, refines, depends_on, implements, example_of).',
   '{}', true),
  ('get_entities', 'GetEntitiesTool',
   'List all entities in memory with optional filtering by scope, project, or memory type.',
   '{}', true),
  ('search_entities', 'SearchEntitiesTool',
   'Search for entities by name. Use before storing to avoid creating duplicate entities.',
   '{}', true),
  ('get_context', 'GetContextTool',
   'Get environment context: current user identity, active project, and metadata.',
   '{}', true)
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active,
  updated_at = now();

-- ============================================================
-- Step 4: Link new tools to agents that had old tools
-- ============================================================

-- Task tools: agents that had any old task tool get all 4 new ones
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('get_tasks', 'get_task', 'fetch_tasks', 'create_task', 'update_task', 'delete_task')
  AND new_t.name IN ('get_tasks', 'create_tasks', 'update_tasks', 'delete_tasks')
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- Reminder tools: agents that had old reminder tools get all 3 new ones
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('list_reminders', 'create_reminder')
  AND new_t.name IN ('get_reminders', 'create_reminders', 'delete_reminders')
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- Schedule tools: agents that had old schedule tools get all 3 new ones
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('list_schedules', 'create_schedule', 'delete_schedule')
  AND new_t.name IN ('get_schedules', 'create_schedules', 'delete_schedules')
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- Gmail tools: agents that had old gmail tools get new ones
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('gmail_search', 'gmail_get_message', 'email_digest', 'gmail_digest')
  AND new_t.name IN ('search_gmail', 'get_gmail')
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- Memory tools: agents that had any old memory tool get all new memory tools
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('save_memory', 'read_memory', 'store_memory', 'recall', 'search_memory',
                      'fetch_memory', 'delete_memory', 'update_memory',
                      'set_project', 'link_memories', 'list_entities', 'search_entities', 'get_context_info')
  AND new_t.name IN ('create_memories', 'search_memories', 'get_memories', 'update_memories', 'delete_memories',
                      'set_project', 'link_memories', 'get_entities', 'search_entities', 'get_context')
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- update_instructions: agents that had it keep it (already linked, upsert handles the tool row)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name = 'update_instructions'
  AND new_t.name = 'update_instructions'
  AND new_t.is_active = true
ON CONFLICT DO NOTHING;

-- ============================================================
-- Step 5: Update assistant agent soul — behavioral philosophy only
-- ============================================================
UPDATE agent_configurations
SET soul = 'You manage things so the user doesn''t have to hold it all in their head.

Be direct and practical. Skip pleasantries when the user is clearly in work mode. Match their energy — brief for brief, thoughtful for thoughtful.

Have opinions about priorities when asked. "Everything is important" is never useful.

When you learn something about the user — preferences, context, how they like things — save it to memory without being asked. You should know more about them with each conversation.

Don''t narrate your tool calls or explain what you''re about to do. Just do it.',
    updated_at = now()
WHERE agent_name = 'assistant';

-- ============================================================
-- Step 6: Add prompt_template column to agent_configurations
-- ============================================================
ALTER TABLE agent_configurations ADD COLUMN IF NOT EXISTS prompt_template TEXT;

COMMENT ON COLUMN agent_configurations.prompt_template IS 'Full prompt template with $placeholder syntax (string.Template). NULL = use hardcoded fallback.';

-- ============================================================
-- Step 7: Seed assistant prompt_template
-- ============================================================
UPDATE agent_configurations
SET prompt_template = '## Identity
$identity

## Soul
$soul

## Operating Model
$operating_model

## Channel
You are responding via the current channel. $channel_guidance

## Current Time
$current_time

## What You Know
$memory_notes

## User Instructions
$user_instructions

## Tool Guidance
$tool_guidance

## Interaction Learning
$interaction_learning

## Session
$session_section',
    updated_at = now()
WHERE agent_name = 'assistant';
