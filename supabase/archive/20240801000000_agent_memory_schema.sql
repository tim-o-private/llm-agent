-- @docs memory-bank/patterns/data-patterns.md#pattern-2-row-level-security-rls-pattern
-- @rules memory-bank/rules/data-rules.json#data-002
-- @examples memory-bank/patterns/data-patterns.md#pattern-7-timestamp-and-audit-patterns
-- supabase/migrations/YYYYMMDDHHMMSS_agent_memory_schema.sql

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for Agent Sessions
CREATE TABLE IF NOT EXISTS public.agent_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    agent_name TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Table for Agent Chat Messages
CREATE TABLE IF NOT EXISTS public.agent_chat_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.agent_sessions(session_id) ON DELETE CASCADE NOT NULL,
    message_idx INTEGER NOT NULL, -- For ordering messages within a session
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool', 'human', 'ai')), -- 'human'/'ai' for Langchain compatibility
    content TEXT NOT NULL,
    additional_kwargs JSONB, -- For tool calls, name, etc.
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT UQ_session_message_idx UNIQUE (session_id, message_idx) 
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_id ON public.agent_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_chat_messages_session_id ON public.agent_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_chat_messages_timestamp ON public.agent_chat_messages(timestamp);


-- Function to check if the current user owns the record (common RLS helper)
CREATE OR REPLACE FUNCTION public.is_record_owner(record_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN record_user_id = auth.uid();
END;
$$;

-- RLS Policies for agent_sessions
ALTER TABLE public.agent_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can select their own sessions" ON public.agent_sessions;
CREATE POLICY "Users can select their own sessions"
ON public.agent_sessions
FOR SELECT
USING (public.is_record_owner(user_id));

DROP POLICY IF EXISTS "Users can insert their own sessions" ON public.agent_sessions;
CREATE POLICY "Users can insert their own sessions"
ON public.agent_sessions
FOR INSERT
WITH CHECK (public.is_record_owner(user_id));

DROP POLICY IF EXISTS "Users can update their own sessions" ON public.agent_sessions;
CREATE POLICY "Users can update their own sessions"
ON public.agent_sessions
FOR UPDATE
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

DROP POLICY IF EXISTS "Users can delete their own sessions" ON public.agent_sessions;
CREATE POLICY "Users can delete their own sessions"
ON public.agent_sessions
FOR DELETE
USING (public.is_record_owner(user_id));


-- RLS Policies for agent_chat_messages
ALTER TABLE public.agent_chat_messages ENABLE ROW LEVEL SECURITY;

-- Users can manage messages belonging to sessions they own.
DROP POLICY IF EXISTS "Users can select messages for their sessions" ON public.agent_chat_messages;
CREATE POLICY "Users can select messages for their sessions"
ON public.agent_chat_messages
FOR SELECT
USING (
    EXISTS (
        SELECT 1
        FROM public.agent_sessions s
        WHERE s.session_id = agent_chat_messages.session_id
        AND public.is_record_owner(s.user_id)
    )
);

DROP POLICY IF EXISTS "Users can insert messages for their sessions" ON public.agent_chat_messages;
CREATE POLICY "Users can insert messages for their sessions"
ON public.agent_chat_messages
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.agent_sessions s
        WHERE s.session_id = agent_chat_messages.session_id
        AND public.is_record_owner(s.user_id)
    )
);

DROP POLICY IF EXISTS "Users can update messages for their sessions" ON public.agent_chat_messages;
CREATE POLICY "Users can update messages for their sessions"
ON public.agent_chat_messages
FOR UPDATE
USING (
    EXISTS (
        SELECT 1
        FROM public.agent_sessions s
        WHERE s.session_id = agent_chat_messages.session_id
        AND public.is_record_owner(s.user_id)
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.agent_sessions s
        WHERE s.session_id = agent_chat_messages.session_id
        AND public.is_record_owner(s.user_id)
    )
);

DROP POLICY IF EXISTS "Users can delete messages for their sessions" ON public.agent_chat_messages;
CREATE POLICY "Users can delete messages for their sessions"
ON public.agent_chat_messages
FOR DELETE
USING (
    EXISTS (
        SELECT 1
        FROM public.agent_sessions s
        WHERE s.session_id = agent_chat_messages.session_id
        AND public.is_record_owner(s.user_id)
    )
);

-- Grant usage on schema and sequences if necessary (often handled by Supabase defaults)
GRANT USAGE ON SCHEMA public TO supabase_auth_admin; -- Or your specific roles
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_chat_messages TO authenticated;