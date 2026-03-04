-- SPEC-028: Create user_preferences table for briefing scheduling
-- Stores timezone, morning/evening briefing configuration per user.
-- Lazy-init pattern: rows created on first access, not signup.

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    morning_briefing_enabled BOOLEAN NOT NULL DEFAULT true,
    morning_briefing_time TIME NOT NULL DEFAULT '07:30:00',
    evening_briefing_enabled BOOLEAN NOT NULL DEFAULT false,
    evening_briefing_time TIME NOT NULL DEFAULT '20:00:00',
    briefing_sections JSONB NOT NULL DEFAULT '{"calendar": true, "tasks": true, "email": true, "observations": true}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on user_preferences"
ON user_preferences FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all user_preferences"
ON user_preferences TO service_role USING (true) WITH CHECK (true);

CREATE INDEX idx_user_preferences_user ON user_preferences (user_id);

CREATE TRIGGER update_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
