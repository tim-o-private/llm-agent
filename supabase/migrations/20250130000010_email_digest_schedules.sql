-- Create agent schedules table for scheduled email digest execution
-- This table stores configuration for scheduled agent execution

CREATE TABLE agent_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    schedule_cron TEXT NOT NULL,
    prompt TEXT NOT NULL,
    active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient lookups
CREATE INDEX idx_agent_schedules_user_active ON agent_schedules(user_id, active);
CREATE INDEX idx_agent_schedules_active ON agent_schedules(active) WHERE active = true;

-- Enable RLS
ALTER TABLE agent_schedules ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY "Users can view their own schedules" ON agent_schedules
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own schedules" ON agent_schedules
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own schedules" ON agent_schedules
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own schedules" ON agent_schedules
    FOR DELETE USING (auth.uid() = user_id);

-- Allow service role (postgres) to access all schedules for background processing
CREATE POLICY "Service role can access all schedules" ON agent_schedules
    FOR ALL USING (current_user = 'postgres');

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_agent_schedules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
CREATE TRIGGER trigger_agent_schedules_updated_at
    BEFORE UPDATE ON agent_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_schedules_updated_at();

-- Add context column to existing email_digests table to track execution context
ALTER TABLE email_digests ADD COLUMN IF NOT EXISTS context TEXT DEFAULT 'on-demand';
ALTER TABLE email_digests ADD COLUMN IF NOT EXISTS email_count INTEGER DEFAULT 0;

-- Create index for context-based queries
CREATE INDEX IF NOT EXISTS idx_email_digests_context ON email_digests(context, generated_at DESC);

-- Add RLS policies for email_digests if not already present
ALTER TABLE email_digests ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist and recreate them
DROP POLICY IF EXISTS "Users can view their own digests" ON email_digests;
DROP POLICY IF EXISTS "Users can insert their own digests" ON email_digests;
DROP POLICY IF EXISTS "Service role can insert digests" ON email_digests;

CREATE POLICY "Users can view their own digests" ON email_digests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own digests" ON email_digests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Allow service role (postgres) to insert digest results for scheduled execution
CREATE POLICY "Service role can insert digests" ON email_digests
    FOR INSERT WITH CHECK (current_user = 'postgres');

-- Insert default email digest schedule for existing users (optional)
-- This creates a daily 7:30 AM email digest schedule for users who have Gmail connected
INSERT INTO agent_schedules (user_id, agent_name, schedule_cron, prompt, config)
SELECT 
    eac.user_id,
    'assistant',
    '30 7 * * *', -- Daily at 7:30 AM
    'Generate a daily email digest of my recent emails from the last 24 hours. Focus on important messages and provide a clear summary.',
    jsonb_build_object(
        'hours_back', 24,
        'include_read', false,
        'context', 'scheduled'
    )
FROM external_api_connections eac
WHERE eac.service_name = 'gmail' 
AND eac.is_active = true
AND NOT EXISTS (
    SELECT 1 FROM agent_schedules 
    WHERE user_id = eac.user_id 
    AND agent_name = 'assistant'
    AND prompt LIKE '%email digest%'
);

-- Add comments for documentation
COMMENT ON TABLE agent_schedules IS 'Stores configuration for scheduled agent execution, including email digest schedules';
COMMENT ON COLUMN agent_schedules.schedule_cron IS 'Cron expression for schedule timing (e.g., "30 7 * * *" for daily at 7:30 AM)';
COMMENT ON COLUMN agent_schedules.config IS 'JSON configuration for the scheduled execution (e.g., hours_back, include_read)';

COMMENT ON COLUMN email_digests.context IS 'Execution context: "scheduled" for background tasks, "on-demand" for user requests';
COMMENT ON COLUMN email_digests.email_count IS 'Number of emails found in the digest'; 