-- Migrate existing email_processing_jobs rows to jobs table
INSERT INTO jobs (id, user_id, job_type, status, input, error, created_at, started_at, completed_at, updated_at)
SELECT
    id,
    user_id,
    'email_processing',
    CASE status
        WHEN 'processing' THEN 'running'
        ELSE status
    END,
    jsonb_build_object('connection_id', connection_id::text)
        || COALESCE(result_summary, '{}'::jsonb),
    error_message,
    created_at,
    started_at,
    completed_at,
    updated_at
FROM email_processing_jobs;

-- Drop orphaned table (AC-04)
DROP TABLE IF EXISTS email_digest_batches;

-- Drop migrated table (AC-05)
DROP TABLE IF EXISTS email_processing_jobs;
