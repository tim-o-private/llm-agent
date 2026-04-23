-- SPEC-047 FU-1: suggest_cards table for inline AI suggestions in file detail view.
-- RLS: users SELECT/UPDATE their own cards; only service_role can INSERT (agent-side).

CREATE TYPE suggest_card_status AS ENUM ('pending', 'accepted', 'dismissed');

CREATE TABLE suggest_cards (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path    TEXT NOT NULL,
    target_line  INT NOT NULL DEFAULT 0,
    label        TEXT NOT NULL DEFAULT 'Clarity suggests',
    body         TEXT NOT NULL,
    suggested_text TEXT,
    status       suggest_card_status NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at   TIMESTAMPTZ
);
CREATE INDEX ON suggest_cards(user_id, file_path, status);
ALTER TABLE suggest_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY suggest_cards_select ON suggest_cards
    FOR SELECT USING (public.is_record_owner(user_id));
CREATE POLICY suggest_cards_update ON suggest_cards
    FOR UPDATE USING (public.is_record_owner(user_id))
    WITH CHECK (public.is_record_owner(user_id));
CREATE POLICY suggest_cards_insert ON suggest_cards
    FOR INSERT WITH CHECK (auth.role() = 'service_role');
