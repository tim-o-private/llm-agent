-- SPEC-018: Convert agent_tool_type enum to VARCHAR(100), register min-memory tools

-- Step 1: Convert tools.type from enum to VARCHAR(100)
ALTER TABLE tools ALTER COLUMN type TYPE VARCHAR(100) USING type::VARCHAR(100);

-- Also convert any backup tables that reference the same enum
ALTER TABLE IF EXISTS agent_tools_backup ALTER COLUMN type TYPE VARCHAR(100) USING type::VARCHAR(100);

-- Drop the enum type — no longer needed
DROP TYPE IF EXISTS agent_tool_type;

-- Step 2: Deactivate old memory tools
UPDATE tools SET is_active = false, updated_at = now()
WHERE name IN ('save_memory', 'read_memory');

-- Step 3: Register all min-memory tools (upsert to handle re-runs)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
  ('store_memory', 'StoreMemoryTool',
   'Store a memory. Use proactively when you learn something — preferences, habits, projects, decisions.',
   '{}', true),
  ('recall', 'RecallMemoryTool',
   'Recall memories relevant to a query. Returns semantically similar memories with hierarchical context.',
   '{}', true),
  ('search_memory', 'SearchMemoryTool',
   'Search for memories matching a query. Returns matching memories ranked by relevance.',
   '{}', true),
  ('fetch_memory', 'FetchMemoryTool',
   'Fetch a specific memory by its ID. Use after search to get full details.',
   '{}', true),
  ('delete_memory', 'DeleteMemoryTool',
   'Delete a memory. Use when the user asks you to forget something or when information is outdated.',
   '{}', true),
  ('update_memory', 'UpdateMemoryTool',
   'Update an existing memory''s text and/or metadata fields. Only provided fields are changed.',
   '{}', true),
  ('set_project', 'SetProjectTool',
   'Validate a project exists in memory or create it. Returns project summary with memory counts.',
   '{}', true),
  ('link_memories', 'LinkMemoriesTool',
   'Link two memories with a relationship (supports, contradicts, supersedes, refines, depends_on, implements, example_of).',
   '{}', true),
  ('list_entities', 'ListEntitiesTool',
   'List all entities in memory with optional filtering by scope, project, or memory type.',
   '{}', true),
  ('search_entities', 'SearchEntitiesTool',
   'Search for entities by name. Use before storing to avoid creating duplicate entities.',
   '{}', true),
  ('get_context_info', 'GetContextInfoTool',
   'Get environment context: current user identity, active project, and metadata.',
   '{}', true)
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active,
  updated_at = now();

-- Step 4: Link new tools to agents that had old memory tools
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('save_memory', 'read_memory')
  AND new_t.name IN ('store_memory', 'recall', 'search_memory', 'fetch_memory',
                      'delete_memory', 'update_memory', 'set_project', 'link_memories',
                      'list_entities', 'search_entities', 'get_context_info')
  AND at.is_active = true
ON CONFLICT DO NOTHING;

-- Step 5: Deactivate old agent_tools assignments
UPDATE agent_tools SET is_active = false, updated_at = now()
WHERE tool_id IN (SELECT id FROM tools WHERE name IN ('save_memory', 'read_memory'));
