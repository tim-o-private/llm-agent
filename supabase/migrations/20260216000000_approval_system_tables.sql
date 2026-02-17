-- Approval system tables: audit_logs, pending_actions, user_tool_preferences
-- Part of the safety layer for the AI secretary

-- Audit log for all tool executions (auto-approved and manually approved)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_args_hash TEXT NOT NULL,
    approval_tier TEXT NOT NULL CHECK (approval_tier IN ('auto', 'requires_approval', 'user_configurable')),
    approval_status TEXT NOT NULL CHECK (approval_status IN ('auto_approved', 'user_approved', 'user_rejected', 'expired')),
    pending_action_id UUID,
    execution_status TEXT CHECK (execution_status IN ('success', 'error', 'skipped')),
    execution_result JSONB,
    error_message TEXT,
    session_id TEXT,
    agent_name TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tool_name ON audit_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_approval_status ON audit_logs(approval_status);

-- RLS: Users can only see their own audit logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can insert (from backend)
CREATE POLICY "Service role can insert audit logs" ON audit_logs
    FOR INSERT WITH CHECK (true);


-- Pending actions queue for actions awaiting user approval
CREATE TABLE IF NOT EXISTS pending_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_args JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'executed')),
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
    resolved_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pending_actions_user_id ON pending_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_pending_actions_status ON pending_actions(status);
CREATE INDEX IF NOT EXISTS idx_pending_actions_expires_at ON pending_actions(expires_at);
CREATE INDEX IF NOT EXISTS idx_pending_actions_created_at ON pending_actions(created_at DESC);

-- RLS: Users can only see and manage their own pending actions
ALTER TABLE pending_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own pending actions" ON pending_actions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage pending actions" ON pending_actions
    FOR ALL WITH CHECK (true);


-- User tool preferences for configurable approval tiers
CREATE TABLE IF NOT EXISTS user_tool_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    approval_tier TEXT NOT NULL CHECK (approval_tier IN ('auto', 'requires_approval')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, tool_name)
);

-- RLS
ALTER TABLE user_tool_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tool preferences" ON user_tool_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own tool preferences" ON user_tool_preferences
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage tool preferences" ON user_tool_preferences
    FOR ALL WITH CHECK (true);


-- Function to expire stale pending actions (called by background job or manually)
CREATE OR REPLACE FUNCTION expire_pending_actions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE pending_actions
    SET status = 'expired',
        updated_at = now(),
        resolved_at = now()
    WHERE status = 'pending'
      AND expires_at < now();

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$;
