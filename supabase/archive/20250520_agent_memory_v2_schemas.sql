-- @docs memory-bank/patterns/data-patterns.md#pattern-2-row-level-security-rls-pattern
-- @rules memory-bank/rules/data-rules.json#data-002
-- @examples memory-bank/patterns/data-patterns.md#pattern-3-consistent-table-structure
-- supabase/migrations/{datetime.now().strftime('%Y%m%d%H%M%S')}_agent_memory_v2_schemas.sql
-- Ran on 2025-05-20 14:00:00. Added column to existing public.agent_sessions table.
-- Drop existing tables if they exist (optional, for clean slate during dev)
DROP TABLE IF EXISTS public.agent_long_term_memory;
-- DROP TABLE IF EXISTS public.agent_sessions; -- Keep if V1 used it and it might be adapted

-- Create agent_sessions table (if decided to keep/adapt for V2)
CREATE TABLE IF NOT EXISTS public.agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

ALTER TABLE public.agent_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow full access to own agent_sessions"
ON public.agent_sessions
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE public.agent_sessions IS 'Stores metadata for agent interaction sessions.';
COMMENT ON COLUMN public.agent_sessions.agent_id IS 'Identifier for the agent configuration used in this session (e.g., "test_agent").';
COMMENT ON COLUMN public.agent_sessions.summary IS 'Optional summary of the session (less critical in V2 with LTM notes).';


-- Create agent_long_term_memory table
CREATE TABLE IF NOT EXISTS public.agent_long_term_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT unique_user_agent_ltm UNIQUE (user_id, agent_id) -- Assuming one LTM doc per user/agent pair
);

ALTER TABLE public.agent_long_term_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow full access to own agent_long_term_memory"
ON public.agent_long_term_memory
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE public.agent_long_term_memory IS 'Stores evolving, natural language long-term memory notes curated by agents for specific users.';
COMMENT ON COLUMN public.agent_long_term_memory.agent_id IS 'Identifier for the agent configuration (e.g., "test_agent") to which these notes pertain.';
COMMENT ON COLUMN public.agent_long_term_memory.notes IS 'The curated long-term memory notes in natural language or structured text.';
COMMENT ON CONSTRAINT unique_user_agent_ltm ON public.agent_long_term_memory IS 'Ensures that each user can have only one LTM document per agent_id.';

-- Trigger to update "updated_at" timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_agent_sessions_updated_at
BEFORE UPDATE ON public.agent_sessions
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_agent_long_term_memory_updated_at
BEFORE UPDATE ON public.agent_long_term_memory
FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Remove V1 agent_chat_messages table if it's definitely superseded and not being repurposed.
-- This should be done carefully after confirming no other parts of the system rely on it.
-- For now, we will assume it might be needed or handled in a separate cleanup task.
DROP TABLE IF EXISTS public.agent_chat_messages;

-- Consider if V1 `agent_sessions` table needs data migration or if it's okay to start fresh for V2.
-- If V1 `agent_sessions` used a different schema for `agent_id` or other fields, adjustments might be needed.
-- The provided V2 schema for `agent_sessions` is simple and aligns with typical usage.

-- Note: The `recent_conversation_history` table will be created in Phase 2 of the implementation plan. 