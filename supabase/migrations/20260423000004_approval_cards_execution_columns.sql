-- SPEC-052: Add execution tracking columns to approval_cards.
-- After a card is approved, the executor records when execution was attempted,
-- the structured result, and any error message.

ALTER TABLE approval_cards
    ADD COLUMN IF NOT EXISTS executed_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS execution_result JSONB,
    ADD COLUMN IF NOT EXISTS execution_error  TEXT;

COMMENT ON COLUMN approval_cards.executed_at IS
    'UTC timestamp of when execution was attempted. NULL = not yet executed. '
    'Set exactly once per card — idempotency guard.';

COMMENT ON COLUMN approval_cards.execution_result IS
    'Structured result from the executor. Shape varies by card_type. '
    'Examples: {"message_id": "...", "thread_id": "..."} for email_draft, '
    '{"event_id": "..."} for calendar_hold, {"path": "..."} for vault writes.';

COMMENT ON COLUMN approval_cards.execution_error IS
    'Human-readable error message if execution failed. NULL = success or not yet attempted. '
    'A card with executed_at set and execution_error set is a recorded failure.';
