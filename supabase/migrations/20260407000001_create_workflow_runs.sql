-- SPEC-036: Workflow runs table
-- Tracks metadata for workflow executions (run_id, status, outputs)
-- LangGraph checkpoint tables are auto-created by AsyncPostgresSaver.setup()

CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    template_name TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'waiting_for_approval', 'completed', 'failed', 'cancelled')),
    parameters JSONB NOT NULL DEFAULT '{}',
    step_outputs JSONB NOT NULL DEFAULT '{}',
    current_step TEXT NOT NULL DEFAULT '',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_status ON workflow_runs(user_id, status);

-- RLS
ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workflow runs"
    ON workflow_runs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own workflow runs"
    ON workflow_runs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own workflow runs"
    ON workflow_runs FOR UPDATE
    USING (auth.uid() = user_id);

-- Service role bypass
CREATE POLICY "Service role full access to workflow_runs"
    ON workflow_runs FOR ALL
    USING (auth.role() = 'service_role');
