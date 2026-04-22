-- SPEC-045: user_preferences columns for Today morning regeneration
-- `today_regeneration_enabled` gates the scheduled regenerate-today workflow
-- (reuses SPEC-037 job-creation pattern). `today_regeneration_time` is a
-- user-local time-of-day (TEXT HH:MM per spec — intentionally not TIME to
-- keep parsing in application code where user tz is known).

ALTER TABLE user_preferences
    ADD COLUMN today_regeneration_enabled BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN today_regeneration_time TEXT NOT NULL DEFAULT '06:30';
