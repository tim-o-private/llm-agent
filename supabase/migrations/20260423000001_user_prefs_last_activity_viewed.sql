ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS last_activity_viewed_at TIMESTAMPTZ;

COMMENT ON COLUMN user_preferences.last_activity_viewed_at IS
    'UTC timestamp of when the user last opened the activity log panel. '
    'NULL = never viewed. Used by GET /api/activity/count to compute '
    'since_last_viewed.';
