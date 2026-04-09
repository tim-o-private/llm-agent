-- SPEC-037: Add email triage preference columns to user_preferences
-- Enables scheduled email triage workflows

ALTER TABLE user_preferences
ADD COLUMN IF NOT EXISTS email_triage_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS email_triage_interval_hours INTEGER DEFAULT 6;

COMMENT ON COLUMN user_preferences.email_triage_enabled IS 'Whether scheduled email triage is active';
COMMENT ON COLUMN user_preferences.email_triage_interval_hours IS 'Hours between triage runs (default 6)';
