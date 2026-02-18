-- Reminders table for SPEC-006
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT,
    remind_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'dismissed')),
    recurrence TEXT DEFAULT NULL
        CHECK (recurrence IS NULL OR recurrence IN ('daily', 'weekly', 'monthly')),
    created_by TEXT NOT NULL DEFAULT 'user'
        CHECK (created_by IN ('user', 'agent')),
    agent_name TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reminders_due ON reminders (remind_at, status) WHERE status = 'pending';
CREATE INDEX idx_reminders_user_upcoming ON reminders (user_id, remind_at) WHERE status = 'pending';

ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
CREATE POLICY reminders_user_policy ON reminders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY reminders_service_insert ON reminders FOR INSERT TO service_role WITH CHECK (true);
CREATE POLICY reminders_service_update ON reminders FOR UPDATE TO service_role USING (true);
