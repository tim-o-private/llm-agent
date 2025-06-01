-- Create email digest tables for storing digest results and batch execution summaries
-- Migration: 20250128000002_create_email_digest_tables.sql

-- Create email_digests table for storing individual digest results
CREATE TABLE IF NOT EXISTS public.email_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ NOT NULL,
    hours_back INTEGER NOT NULL DEFAULT 24,
    include_read BOOLEAN NOT NULL DEFAULT false,
    digest_content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one digest per user per timestamp
    UNIQUE(user_id, generated_at)
);

-- Create email_digest_batches table for storing batch execution summaries
CREATE TABLE IF NOT EXISTS public.email_digest_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds NUMERIC(10,2) NOT NULL,
    total_users INTEGER NOT NULL DEFAULT 0,
    successful INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create agent_logs table for general agent activity logging
CREATE TABLE IF NOT EXISTS public.agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_digests_user_id ON public.email_digests(user_id);
CREATE INDEX IF NOT EXISTS idx_email_digests_generated_at ON public.email_digests(generated_at);
CREATE INDEX IF NOT EXISTS idx_email_digests_status ON public.email_digests(status);

CREATE INDEX IF NOT EXISTS idx_email_digest_batches_start_time ON public.email_digest_batches(start_time);
CREATE INDEX IF NOT EXISTS idx_email_digest_batches_status ON public.email_digest_batches(successful, failed);

CREATE INDEX IF NOT EXISTS idx_agent_logs_user_id ON public.agent_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_name ON public.agent_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON public.agent_logs(created_at);

-- Enable Row Level Security (RLS) on email_digests
ALTER TABLE public.email_digests ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for email_digests
CREATE POLICY "Users can view their own email digests" ON public.email_digests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own email digests" ON public.email_digests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own email digests" ON public.email_digests
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own email digests" ON public.email_digests
    FOR DELETE USING (auth.uid() = user_id);

-- Enable Row Level Security (RLS) on agent_logs
ALTER TABLE public.agent_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for agent_logs
CREATE POLICY "Users can view their own agent logs" ON public.agent_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own agent logs" ON public.agent_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Email digest batches are admin-only (no RLS policies for regular users)
-- Only service accounts should access this table

-- Create updated_at trigger for email_digests
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_email_digests_updated_at 
    BEFORE UPDATE ON public.email_digests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON public.email_digests TO authenticated;
GRANT SELECT, INSERT ON public.agent_logs TO authenticated;
GRANT SELECT ON public.email_digest_batches TO authenticated;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Add helpful comments
COMMENT ON TABLE public.email_digests IS 'Stores individual email digest results for users';
COMMENT ON TABLE public.email_digest_batches IS 'Stores batch execution summaries for daily digest runs';
COMMENT ON TABLE public.agent_logs IS 'General logging table for agent activities';

COMMENT ON COLUMN public.email_digests.digest_content IS 'The generated email digest content';
COMMENT ON COLUMN public.email_digests.hours_back IS 'Number of hours looked back for emails';
COMMENT ON COLUMN public.email_digests.include_read IS 'Whether read emails were included';
COMMENT ON COLUMN public.email_digests.status IS 'Generation status: success, error, etc.';

COMMENT ON COLUMN public.email_digest_batches.summary IS 'Detailed JSON summary of batch execution';
COMMENT ON COLUMN public.agent_logs.result IS 'JSON result data from agent execution'; 