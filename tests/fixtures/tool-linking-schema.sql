-- Migration: Normalized Tool Schema with Linking Table
-- This replaces the current agent_tools table with a proper many-to-many design

-- 1. Tools registry table (reusable tool definitions)
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

-- 2. Agent-tool linking table (many-to-many with agent-specific overrides)
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

-- Partial unique index to handle soft deletes properly
-- Only enforce uniqueness for non-deleted assignments
CREATE UNIQUE INDEX idx_agent_tool_assignments_unique_active 
ON agent_tool_assignments(agent_id, tool_id) 
WHERE is_deleted = FALSE;

-- Performance indexes
CREATE INDEX idx_tools_name ON tools(name) WHERE is_deleted = FALSE;
CREATE INDEX idx_tools_type ON tools(type) WHERE is_deleted = FALSE;
CREATE INDEX idx_agent_tool_assignments_agent_id ON agent_tool_assignments(agent_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_agent_tool_assignments_tool_id ON agent_tool_assignments(tool_id) WHERE is_deleted = FALSE;

-- Enable RLS on both tables
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tool_assignments ENABLE ROW LEVEL SECURITY;

-- Service role only policies for tools
CREATE POLICY "Allow service_role to manage all tools"
  ON tools
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Service role only policies for agent_tool_assignments  
CREATE POLICY "Allow service_role to manage all agent tool assignments"
  ON agent_tool_assignments
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Updated_at triggers
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

CREATE TRIGGER update_agent_tool_assignments_updated_at
BEFORE UPDATE ON agent_tool_assignments
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();