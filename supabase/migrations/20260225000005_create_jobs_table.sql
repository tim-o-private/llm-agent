CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'running', 'complete', 'failed')),
    input JSONB NOT NULL DEFAULT '{}',
    output JSONB,
    error TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    scheduled_for TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    claimed_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on jobs"
ON jobs FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all jobs"
ON jobs TO service_role USING (true) WITH CHECK (true);

CREATE INDEX idx_jobs_poll ON jobs (status, scheduled_for, priority DESC)
    WHERE status = 'pending';
CREATE INDEX idx_jobs_user ON jobs (user_id);
CREATE INDEX idx_jobs_type_status ON jobs (job_type, status);

CREATE TRIGGER update_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION expire_stale_jobs() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE jobs
    SET status = 'failed',
        error = 'Job timed out (stale claim)',
        completed_at = now(),
        updated_at = now()
    WHERE status IN ('claimed', 'running')
      AND claimed_at < now() - interval '30 minutes';
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$;

COMMENT ON TABLE jobs IS 'Universal job queue for all background work types (email processing, agent invocation, reminder delivery, etc.)';
COMMENT ON COLUMN jobs.job_type IS 'Discriminator for handler dispatch (e.g., email_processing, agent_invocation, reminder_delivery)';
COMMENT ON COLUMN jobs.priority IS 'Higher priority jobs are claimed first. Default 0.';
COMMENT ON COLUMN jobs.scheduled_for IS 'Job is not eligible for claiming until this time. Supports delayed/scheduled execution.';
COMMENT ON COLUMN jobs.expires_at IS 'Optional hard expiry. Jobs past this time should not be executed.';
