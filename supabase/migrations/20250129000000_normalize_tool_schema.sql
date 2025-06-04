-- Migration: Normalize Tool Schema with Linking Table
-- This replaces the current agent_tools table with a proper many-to-many design
-- Date: 2025-01-29
-- Pattern: agents -> agent_tools -> tools (parent_children pattern)

-- 1. Create tools registry table (reusable tool definitions)
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,  -- e.g., 'gmail_digest', 'gmail_search'
    type agent_tool_type NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Migrate existing agent_tools data to tools registry
-- Extract unique tools from current agent_tools table
INSERT INTO tools (name, type, description, config, is_active, created_at, updated_at)
SELECT DISTINCT 
    name,
    type,
    COALESCE(description, ''),
    COALESCE(config, '{}'),
    true,  -- Default to active
    MIN(created_at),
    MAX(updated_at)
FROM agent_tools 
WHERE is_deleted = FALSE
GROUP BY name, type, COALESCE(description, ''), COALESCE(config, '{}');

-- 3. Rename current agent_tools to agent_tools_backup for safety
ALTER TABLE agent_tools RENAME TO agent_tools_backup;

-- 4. Create new agent_tools as linking table (many-to-many)
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    config_override JSONB DEFAULT '{}',  -- Agent-specific config overrides
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create partial unique index to handle soft deletes properly
-- Only enforce uniqueness for non-deleted assignments
CREATE UNIQUE INDEX idx_agent_tools_unique_active 
ON agent_tools(agent_id, tool_id) 
WHERE is_deleted = FALSE;

-- 6. Create performance indexes
CREATE INDEX idx_tools_name ON tools(name) WHERE is_deleted = FALSE;
CREATE INDEX idx_tools_type ON tools(type) WHERE is_deleted = FALSE;
CREATE INDEX idx_agent_tools_agent_id ON agent_tools(agent_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_agent_tools_tool_id ON agent_tools(tool_id) WHERE is_deleted = FALSE;

-- 7. Enable RLS on both tables
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY;

-- 8. Create service role only policies
CREATE POLICY "Allow service_role to manage all tools"
  ON tools
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow service_role to manage all agent tools"
  ON agent_tools
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 9. Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tools_updated_at
BEFORE UPDATE ON tools
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_tools_updated_at
BEFORE UPDATE ON agent_tools
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 10. Populate new agent_tools linking table from backup
INSERT INTO agent_tools (agent_id, tool_id, config_override, is_active, created_at, updated_at)
SELECT 
    atb.agent_id,
    t.id as tool_id,
    CASE 
        WHEN atb.config != t.config THEN atb.config 
        ELSE '{}'::jsonb 
    END as config_override,
    atb.is_active,
    atb.created_at,
    atb.updated_at
FROM agent_tools_backup atb
JOIN tools t ON t.name = atb.name AND t.type = atb.type
WHERE atb.is_deleted = FALSE;

-- 11. Drop backup table after confirming migration success
-- Uncomment the following line after verifying the migration worked correctly:
-- DROP TABLE agent_tools_backup;

-- 12. Add helpful comments
COMMENT ON TABLE tools IS 'Registry of reusable tool definitions';
COMMENT ON TABLE agent_tools IS 'Many-to-many linking table between agents and tools with optional config overrides';
COMMENT ON COLUMN tools.config IS 'Default configuration for this tool type';
COMMENT ON COLUMN agent_tools.config_override IS 'Agent-specific configuration overrides (merged with tool default config)';
COMMENT ON INDEX idx_agent_tools_unique_active IS 'Ensures one active assignment per agent-tool pair (allows soft deletes)'; 