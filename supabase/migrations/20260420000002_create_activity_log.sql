-- SPEC-045: Activity log table (Today surface, Stage 1)
-- Append-only audit trail written by the service role on every approval
-- transition (approve/reject/edit) and — via later specs — workflow
-- completions. Stage 1 emits; S7 adds the reader endpoint + UI.

CREATE TABLE activity_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    actor           TEXT NOT NULL,
    action          TEXT NOT NULL,
    subject_path    TEXT,
    workflow_run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    status          TEXT NOT NULL CHECK (status IN ('done', 'failed', 'awaiting_approval')),
    reasoning       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_log_user_created
    ON activity_log(user_id, created_at DESC);

ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Users read their own entries.
CREATE POLICY "Users can view own activity log"
    ON activity_log FOR SELECT
    USING (auth.uid() = user_id);

-- Append is service-role only: agent writes are authoritative, clients never
-- author audit rows.
CREATE POLICY "Service role full access to activity_log"
    ON activity_log FOR ALL
    USING (auth.role() = 'service_role');
