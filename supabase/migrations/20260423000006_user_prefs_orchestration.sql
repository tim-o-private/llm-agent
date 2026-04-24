-- SPEC-054: user_preferences columns for orchestration proposals
-- `orchestration_check_enabled` gates the orchestration-check workflow
-- (default FALSE — user must opt in per AC-19).
-- `orchestration_check_time` is a user-local time-of-day (TEXT HH:MM).
-- `orchestration_limits` is nullable JSONB for per-user rate-limit overrides.

ALTER TABLE user_preferences
    ADD COLUMN orchestration_check_enabled BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN orchestration_check_time TEXT NOT NULL DEFAULT '07:00',
    ADD COLUMN orchestration_limits JSONB;
