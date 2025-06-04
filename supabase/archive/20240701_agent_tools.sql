-- Migration: Agent and Tool Configuration Tables

CREATE TABLE IF NOT EXISTS agent_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    llm_config JSONB NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agent_configurations(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    tool_config JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    "order" INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Optional: Tool type registry for validation (not required for MVP)
-- CREATE TABLE IF NOT EXISTS tool_types (
--     type_name TEXT PRIMARY KEY,
--     description TEXT,
--     config_schema JSONB
-- );

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_agent_tools_agent_id ON agent_tools(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_tools_active_order ON agent_tools(agent_id, is_active, "order");

-- Enable RLS
ALTER TABLE agent_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY;

-- Service role only policy for agent_configurations
CREATE POLICY "Allow service_role to manage all agent configs"
  ON agent_configurations
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Service role only policy for agent_tools
CREATE POLICY "Allow service_role to manage all agent tools"
  ON agent_tools
  TO service_role
  USING (true)
  WITH CHECK (true);
