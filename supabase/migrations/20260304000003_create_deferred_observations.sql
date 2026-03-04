-- SPEC-028: Create deferred_observations table for heartbeat deferral
-- Non-urgent heartbeat findings accumulate here until the next briefing consumes them.
-- consumed_at marks when a briefing incorporated the observation.

CREATE TABLE deferred_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'heartbeat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed_at TIMESTAMPTZ
);

ALTER TABLE deferred_observations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on deferred_observations"
ON deferred_observations FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all deferred_observations"
ON deferred_observations TO service_role USING (true) WITH CHECK (true);

CREATE INDEX idx_deferred_observations_unconsumed
ON deferred_observations (user_id, consumed_at)
WHERE consumed_at IS NULL;
