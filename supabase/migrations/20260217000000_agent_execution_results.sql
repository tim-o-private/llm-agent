-- Generalized agent execution results table
-- Stores output from any scheduled agent run (not just email digests)

CREATE TABLE agent_execution_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    schedule_id UUID REFERENCES agent_schedules(id) ON DELETE SET NULL,
    agent_name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    result_content TEXT,
    status TEXT NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'error', 'partial')),
    pending_actions_created INTEGER DEFAULT 0,
    execution_duration_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_agent_exec_results_user ON agent_execution_results(user_id, created_at DESC);
CREATE INDEX idx_agent_exec_results_schedule ON agent_execution_results(schedule_id);

-- RLS
ALTER TABLE agent_execution_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own execution results"
    ON agent_execution_results FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all execution results"
    ON agent_execution_results FOR ALL
    USING (current_user = 'postgres');

COMMENT ON TABLE agent_execution_results IS 'Stores results from scheduled agent executions (heartbeats, digests, orchestrator runs, etc.)';
COMMENT ON COLUMN agent_execution_results.schedule_id IS 'References the agent_schedules row that triggered this execution, NULL if ad-hoc';
COMMENT ON COLUMN agent_execution_results.pending_actions_created IS 'Number of pending actions queued during this execution';
COMMENT ON COLUMN agent_execution_results.execution_duration_ms IS 'Wall-clock execution time in milliseconds';
