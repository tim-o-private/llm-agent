CREATE TABLE email_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES external_api_connections(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    result_summary JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE email_processing_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on email_processing_jobs"
ON email_processing_jobs FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE INDEX idx_email_processing_jobs_user ON email_processing_jobs(user_id);
CREATE INDEX idx_email_processing_jobs_status ON email_processing_jobs(status) WHERE status = 'pending';

CREATE UNIQUE INDEX idx_email_processing_jobs_pending_connection
ON email_processing_jobs(connection_id) WHERE status = 'pending';

CREATE TRIGGER update_email_processing_jobs_updated_at
BEFORE UPDATE ON email_processing_jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE email_processing_jobs IS 'Tracks email onboarding processing jobs triggered by Gmail OAuth connections';
