-- SPEC-053: Entity refresh scheduling preferences.
-- entity_refresh_enabled: user opt-in for daily entity-refresher runs
-- entity_refresh_time: preferred time for daily refresh (HH:MM, user-local)

ALTER TABLE user_preferences
  ADD COLUMN IF NOT EXISTS entity_refresh_enabled BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS entity_refresh_time TEXT DEFAULT '07:00';
