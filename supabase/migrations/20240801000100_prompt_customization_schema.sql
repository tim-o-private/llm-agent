-- supabase/migrations/YYYYMMDDHHMMSS_prompt_customization_schema.sql

-- Table for User-Specific Agent Prompt Customizations
CREATE TABLE IF NOT EXISTS public.user_agent_prompt_customizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    agent_name TEXT NOT NULL, -- Identifier for the agent this customization applies to
    customization_type TEXT NOT NULL DEFAULT 'instruction_set', -- e.g., 'instruction_set', 'personality_trait', 'tone'
    content JSONB NOT NULL, -- Flexible structure for various customization types. Could be a list of instructions, key-value pairs for traits, etc.
    is_active BOOLEAN DEFAULT TRUE NOT NULL, -- To allow disabling a customization without deleting
    priority INTEGER DEFAULT 0 NOT NULL, -- For ordering if multiple customizations of the same type apply
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT UQ_user_agent_customization_type UNIQUE (user_id, agent_name, customization_type) -- Assuming one active customization of a given type per user/agent for simplicity. Could be removed if multiple are needed, then rely on priority.
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_agent_prompt_customizations_user_agent ON public.user_agent_prompt_customizations(user_id, agent_name);

-- RLS Policies for user_agent_prompt_customizations
ALTER TABLE public.user_agent_prompt_customizations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own prompt customizations" ON public.user_agent_prompt_customizations;
CREATE POLICY "Users can manage their own prompt customizations"
ON public.user_agent_prompt_customizations
FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

-- Grant authenticated users access
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_agent_prompt_customizations TO authenticated; 