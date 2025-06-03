-- Fix foreign key constraints for proper soft delete strategy
-- Remove CASCADE from tool_id constraint since deleting a tool shouldn't cascade delete assignments

-- Drop the incorrect constraint
ALTER TABLE agent_tools DROP CONSTRAINT IF EXISTS agent_tools_tool_id_fkey;

-- Add correct constraint without CASCADE
ALTER TABLE agent_tools ADD CONSTRAINT agent_tools_tool_id_fkey 
    FOREIGN KEY (tool_id) REFERENCES tools(id);

-- Verify agent_id constraint (this one should keep CASCADE since deleting an agent should remove its assignments)
-- But let's check if it needs fixing too
SELECT 
    conname as constraint_name,
    confdeltype as delete_action
FROM pg_constraint 
WHERE conrelid = 'agent_tools'::regclass 
AND confrelid IN ('agent_configurations'::regclass, 'tools'::regclass);

-- Comment: 
-- - agent_id -> agent_configurations: SHOULD have CASCADE (deleting agent removes its tool assignments)
-- - tool_id -> tools: SHOULD NOT have CASCADE (deleting tool should not auto-delete assignments, use soft delete) 