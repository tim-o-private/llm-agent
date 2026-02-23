-- SPEC-018: Register new min-memory-backed tools, deactivate old blob tools

-- Deactivate old memory tools
UPDATE tools SET is_active = false, updated_at = now()
WHERE name IN ('save_memory', 'read_memory');

-- Register new tools (upsert to handle re-runs)
INSERT INTO tools (name, type, description, config, is_active)
VALUES
  ('store_memory', 'StoreMemoryTool',
   'Store a memory about the user or their context. Use this to remember preferences, decisions, and observations.',
   '{}', true),
  ('recall', 'RecallMemoryTool',
   'Recall memories relevant to a query. Returns semantically similar memories ranked by relevance.',
   '{}', true),
  ('search_memory', 'SearchMemoryTool',
   'Search for specific memories by keyword.',
   '{}', true)
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active,
  updated_at = now();

-- Link new tools to agents that had old memory tools
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT DISTINCT at.agent_id, new_t.id, true
FROM agent_tools at
JOIN tools old_t ON at.tool_id = old_t.id
CROSS JOIN tools new_t
WHERE old_t.name IN ('save_memory', 'read_memory')
  AND new_t.name IN ('store_memory', 'recall', 'search_memory')
  AND at.is_active = true
ON CONFLICT DO NOTHING;

-- Deactivate old agent_tools assignments
UPDATE agent_tools SET is_active = false, updated_at = now()
WHERE tool_id IN (SELECT id FROM tools WHERE name IN ('save_memory', 'read_memory'));
