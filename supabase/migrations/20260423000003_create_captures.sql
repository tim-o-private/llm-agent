-- SPEC-051: Capture — text routing into the vault.
-- Creates the `captures` table for the capture audit trail.

CREATE TABLE captures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    source          TEXT NOT NULL,  -- 'today', 'cmdk', 'chat'
    context         JSONB,          -- source-specific metadata
    status          TEXT NOT NULL DEFAULT 'routing'
                    CHECK (status IN ('routing', 'placed', 'failed')),
    target_path     TEXT,
    target_section  TEXT,
    method          TEXT CHECK (method IN ('append', 'create')),
    reasoning       TEXT,
    fallback        BOOLEAN NOT NULL DEFAULT FALSE,
    error_detail    TEXT,
    redirect        JSONB,          -- { target_hint, new_target_path, new_target_section, redirected_at }
    confirmation    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    placed_at       TIMESTAMPTZ,
    CONSTRAINT text_not_empty CHECK (char_length(trim(text)) > 0)
);

CREATE INDEX idx_captures_user_created ON captures(user_id, created_at DESC);
CREATE INDEX idx_captures_user_routing ON captures(user_id, status) WHERE status = 'routing';

-- RLS policies: user SELECT/UPDATE own rows; INSERT via service role (backend creates on behalf of user).
ALTER TABLE captures ENABLE ROW LEVEL SECURITY;

CREATE POLICY captures_select_own ON captures
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY captures_update_own ON captures
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY captures_insert_service ON captures
    FOR INSERT WITH CHECK (
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role') = 'service_role'
        OR auth.uid() = user_id
    );

-- Allow service role full access for backend operations
CREATE POLICY captures_service_all ON captures
    FOR ALL USING (
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role') = 'service_role'
    );
