-- SPEC-045: Approval cards table (Today surface, Stage 1)
-- Six card shapes (email_draft, calendar_hold, outreach, workflow_proposal,
-- config_change, file_operation) render in the Today page's Approvals lane.
-- Stage 1 contract: approve/reject flip status and emit activity_log rows;
-- no outbound effects execute from this table.

CREATE TYPE approval_card_type AS ENUM (
    'email_draft',
    'calendar_hold',
    'outreach',
    'workflow_proposal',
    'config_change',
    'file_operation'
);

CREATE TYPE approval_card_status AS ENUM (
    'pending',
    'approved',
    'rejected'
);

CREATE TABLE approval_cards (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    card_type     approval_card_type NOT NULL,
    title         TEXT NOT NULL,
    payload       JSONB NOT NULL,
    status        approval_card_status NOT NULL DEFAULT 'pending',
    rationale     TEXT,
    source_ref    TEXT,
    decided_at    TIMESTAMPTZ,
    decided_by    UUID REFERENCES auth.users(id),
    decision_note TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_cards_user_status_created
    ON approval_cards(user_id, status, created_at DESC);

ALTER TABLE approval_cards ENABLE ROW LEVEL SECURITY;

-- Users can read their own cards.
CREATE POLICY "Users can view own approval cards"
    ON approval_cards FOR SELECT
    USING (auth.uid() = user_id);

-- Users can update their own cards (approve/reject/edit transitions).
CREATE POLICY "Users can update own approval cards"
    ON approval_cards FOR UPDATE
    USING (auth.uid() = user_id);

-- INSERT is service-role only: cards originate agent-side, not from the client.
CREATE POLICY "Service role full access to approval_cards"
    ON approval_cards FOR ALL
    USING (auth.role() = 'service_role');
