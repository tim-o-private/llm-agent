-- supabase/migrations/{timestamp}_recent_conversation_history_schema.sql

-- 1. Create recent_conversation_history table
CREATE TABLE IF NOT EXISTS public.recent_conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL, -- e.g., 'test_agent', 'clarity_copilot'
    message_batch_jsonb JSONB NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    batch_start_timestamp TIMESTAMPTZ NULL,
    batch_end_timestamp TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_recent_conv_history_session_id ON public.recent_conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_recent_conv_history_user_id ON public.recent_conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_recent_conv_history_agent_id ON public.recent_conversation_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_recent_conv_history_archived_at ON public.recent_conversation_history(archived_at DESC);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.recent_conversation_history ENABLE ROW LEVEL SECURITY;

-- 4. Create RLS policies
-- Users can insert their own conversation history batches
CREATE POLICY "Allow users to insert their own conversation history" 
ON public.recent_conversation_history
FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Users can select their own conversation history batches
CREATE POLICY "Allow users to select their own conversation history"
ON public.recent_conversation_history
FOR SELECT
USING (auth.uid() = user_id);

-- Optional: Prevent users from updating or deleting (updates/deletes should be handled by specific backend processes if needed)
CREATE POLICY "Disallow direct updates by users"
ON public.recent_conversation_history
FOR UPDATE
USING (false); -- Effectively blocks updates for all users via this policy

CREATE POLICY "Disallow direct deletes by users"
ON public.recent_conversation_history
FOR DELETE
USING (false); -- Effectively blocks deletes for all users via this policy

-- 5. Add comments to table and columns for clarity
COMMENT ON TABLE public.recent_conversation_history IS 'Stores batches of recent conversation messages from user sessions for archival and potential rehydration.';
COMMENT ON COLUMN public.recent_conversation_history.id IS 'Unique identifier for the history batch record.';
COMMENT ON COLUMN public.recent_conversation_history.session_id IS 'Identifier for the specific chat session these messages belong to.';
COMMENT ON COLUMN public.recent_conversation_history.user_id IS 'Identifier of the user who owns this conversation history.';
COMMENT ON COLUMN public.recent_conversation_history.agent_id IS 'Identifier of the agent involved in this conversation.';
COMMENT ON COLUMN public.recent_conversation_history.message_batch_jsonb IS 'A JSONB array of serialized LangChain BaseMessage objects representing the conversation turn(s).';
COMMENT ON COLUMN public.recent_conversation_history.archived_at IS 'Timestamp when this batch was archived to the database.';
COMMENT ON COLUMN public.recent_conversation_history.batch_start_timestamp IS 'Timestamp of the first message in this batch (client-provided, optional).';
COMMENT ON COLUMN public.recent_conversation_history.batch_end_timestamp IS 'Timestamp of the last message in this batch (client-provided, optional).';
COMMENT ON COLUMN public.recent_conversation_history.created_at IS 'Timestamp when this record was created.'; 