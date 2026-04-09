-- SPEC-039: Security Boundary + Self-Improvement
-- Tracks agent-proposed configuration changes for approval/rollback.

CREATE TABLE IF NOT EXISTS config_change_proposals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sandbox_id  TEXT,
    file_path   TEXT NOT NULL,
    change_description TEXT NOT NULL,
    git_commit_hash TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected', 'reverted')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for user lookups
CREATE INDEX idx_config_change_proposals_user_id
    ON config_change_proposals(user_id);

-- Index for status filtering
CREATE INDEX idx_config_change_proposals_status
    ON config_change_proposals(user_id, status);

-- RLS
ALTER TABLE config_change_proposals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own proposals"
    ON config_change_proposals FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own proposals"
    ON config_change_proposals FOR UPDATE
    USING (auth.uid() = user_id);

-- Server-side insert (service role only)
CREATE POLICY "Service role can insert proposals"
    ON config_change_proposals FOR INSERT
    WITH CHECK (true);
