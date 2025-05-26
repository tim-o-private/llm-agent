create table public.agent_long_term_memory (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  agent_id text not null,
  notes text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint agent_long_term_memory_pkey primary key (id),
  constraint unique_user_agent_ltm unique (user_id, agent_id),
  constraint agent_long_term_memory_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create trigger update_agent_long_term_memory_updated_at BEFORE
update on agent_long_term_memory for EACH row
execute FUNCTION update_updated_at_column ();

create table public.agent_sessions (
  session_id uuid not null default extensions.uuid_generate_v4 (),
  user_id uuid not null,
  agent_name text not null,
  summary text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  agent_id text not null default ''::text,
  constraint agent_sessions_pkey primary key (session_id),
  constraint agent_sessions_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_agent_sessions_user_id on public.agent_sessions using btree (user_id) TABLESPACE pg_default;

create trigger update_agent_sessions_updated_at BEFORE
update on agent_sessions for EACH row
execute FUNCTION update_updated_at_column ();

create table public.focus_sessions (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  task_id uuid not null,
  started_at timestamp with time zone not null default now(),
  ended_at timestamp with time zone null,
  duration_seconds integer null,
  notes text null,
  mood text null,
  outcome text null,
  created_at timestamp with time zone not null default now(),
  constraint focus_sessions_pkey primary key (id),
  constraint focus_sessions_task_id_fkey foreign KEY (task_id) references tasks (id),
  constraint focus_sessions_user_id_fkey foreign KEY (user_id) references auth.users (id),
  constraint focus_sessions_mood_check check (
    (
      mood = any (
        array[
          'energized'::text,
          'neutral'::text,
          'drained'::text,
          'focused'::text,
          'distracted'::text,
          'other'::text
        ]
      )
    )
  ),
  constraint focus_sessions_outcome_check check (
    (
      outcome = any (
        array[
          'completed_task'::text,
          'made_progress'::text,
          'got_stuck'::text,
          'interrupted'::text,
          'planned_next'::text,
          'other'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_focus_sessions_user_id on public.focus_sessions using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_focus_sessions_task_id on public.focus_sessions using btree (task_id) TABLESPACE pg_default;

create index IF not exists idx_focus_sessions_created_at on public.focus_sessions using btree (created_at) TABLESPACE pg_default;

create table public.scratch_pad_entries (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  content text not null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone null,
  archived boolean not null default false,
  task_id uuid null,
  session_id uuid null,
  constraint scratch_pad_entries_pkey primary key (id),
  constraint scratch_pad_entries_session_id_fkey foreign KEY (session_id) references focus_sessions (id),
  constraint scratch_pad_entries_task_id_fkey foreign KEY (task_id) references tasks (id),
  constraint scratch_pad_entries_user_id_fkey foreign KEY (user_id) references auth.users (id)
) TABLESPACE pg_default;

create index IF not exists idx_scratch_pad_entries_user_id on public.scratch_pad_entries using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_scratch_pad_entries_created_at on public.scratch_pad_entries using btree (created_at) TABLESPACE pg_default;

create index IF not exists idx_scratch_pad_entries_task_id on public.scratch_pad_entries using btree (task_id) TABLESPACE pg_default;

create index IF not exists idx_scratch_pad_entries_session_id on public.scratch_pad_entries using btree (session_id) TABLESPACE pg_default;

create table public.tasks (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  title text not null,
  notes text null,
  category text null,
  completed boolean not null default false,
  due_date date null,
  time_period text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone null,
  position integer null,
  priority integer null,
  status public.task_status null,
  motivation text null,
  description text null,
  completion_note text null,
  parent_task_id uuid null,
  subtask_position integer null,
  constraint tasks_pkey primary key (id),
  constraint tasks_parent_task_id_fkey foreign KEY (parent_task_id) references tasks (id),
  constraint tasks_user_id_fkey foreign KEY (user_id) references auth.users (id),
  constraint tasks_status_check check (
    (
      status = any (
        array[
          'pending'::task_status,
          'planning'::task_status,
          'in_progress'::task_status,
          'completed'::task_status,
          'skipped'::task_status,
          'deferred'::task_status
        ]
      )
    )
  ),
  constraint tasks_time_period_check check (
    (
      time_period = any (
        array[
          'Morning'::text,
          'Afternoon'::text,
          'Evening'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_tasks_user_id on public.tasks using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_tasks_due_date on public.tasks using btree (due_date) TABLESPACE pg_default;

create index IF not exists idx_tasks_completed on public.tasks using btree (completed) TABLESPACE pg_default;

create index IF not exists idx_tasks_position on public.tasks using btree ("position") TABLESPACE pg_default;

create index IF not exists idx_tasks_status on public.tasks using btree (status) TABLESPACE pg_default;

create index IF not exists idx_tasks_priority on public.tasks using btree (priority) TABLESPACE pg_default;

create table public.user_agent_prompt_customizations (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id uuid not null,
  agent_name text not null,
  customization_type text not null default 'instruction_set'::text,
  content jsonb not null,
  is_active boolean not null default true,
  priority integer not null default 0,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint user_agent_prompt_customizations_pkey primary key (id),
  constraint uq_user_agent_customization_type unique (user_id, agent_name, customization_type),
  constraint user_agent_prompt_customizations_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_user_agent_prompt_customizations_user_agent on public.user_agent_prompt_customizations using btree (user_id, agent_name) TABLESPACE pg_default;

CREATE TABLE public.user_agent_active_sessions (
    user_id uuid NOT NULL,
    agent_name TEXT NOT NULL,
    active_session_id TEXT NOT NULL,
    last_active_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT user_agent_active_sessions_pkey PRIMARY KEY (user_id, agent_name),
    CONSTRAINT user_agent_active_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);

-- Enable RLS
ALTER TABLE public.user_agent_active_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own active session records
CREATE POLICY "Allow users to manage their own active sessions"
ON public.user_agent_active_sessions
FOR ALL
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Trigger to update last_active_at
-- Note: We are reusing 'update_updated_at_column' which typically updates a column named 'updated_at'.
-- This assumes it will correctly update 'last_active_at' if that's the only timestamp being changed on update.
-- If this is not the case, a more specific trigger function like 'update_last_active_at_column' would be needed.
CREATE TRIGGER update_user_agent_active_sessions_last_active_at
BEFORE UPDATE ON public.user_agent_active_sessions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Placeholder for chat_message_history DDL (to be added next)
-- DDL for chat_message_history table compatible with langchain-postgres
CREATE TABLE public.chat_message_history (
    id SERIAL PRIMARY KEY, -- Or UUID: id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    session_id TEXT NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster session_id lookups
CREATE INDEX idx_chat_message_history_session_id ON public.chat_message_history(session_id);

-- Enable RLS
ALTER TABLE public.chat_message_history ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service_role full access.
CREATE POLICY "Allow service_role full access" ON public.chat_message_history FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Grant access to authenticated users (example, adjust as needed)
-- This might not be necessary if all access is through the service_role key from the backend.
-- CREATE POLICY "Allow individual user access" ON public.chat_message_history
-- FOR SELECT USING (auth.uid() = user_id); -- Assuming you add a user_id column linked to auth.users
-- CREATE POLICY "Allow individual user insert" ON public.chat_message_history
-- FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Remove DDL for recent_conversation_history table as it's now redundant
/* -- Removing the following table definition:
CREATE TABLE IF NOT EXISTS public.recent_conversation_history (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id text NOT NULL,
    user_id uuid,
    agent_id text,
    message_batch_jsonb jsonb NOT NULL,
    batch_start_timestamp timestamp with time zone,
    batch_end_timestamp timestamp with time zone,
    archived_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT recent_conversation_history_pkey PRIMARY KEY (id),
    CONSTRAINT recent_conversation_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);

ALTER TABLE IF EXISTS public.recent_conversation_history ENABLE ROW LEVEL SECURITY;

-- Policies for recent_conversation_history (these will also be removed)
DROP POLICY IF EXISTS "Allow authenticated user read access to their history" ON public.recent_conversation_history;
CREATE POLICY "Allow authenticated user read access to their history" ON public.recent_conversation_history FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow authenticated user insert access to their history" ON public.recent_conversation_history;
CREATE POLICY "Allow authenticated user insert access to their history" ON public.recent_conversation_history FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Allow service_role full access on recent_conversation_history" ON public.recent_conversation_history;
CREATE POLICY "Allow service_role full access on recent_conversation_history" ON public.recent_conversation_history FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Indexes for recent_conversation_history (these will also be removed)
DROP INDEX IF EXISTS idx_recent_conversation_history_session_user_agent;
CREATE INDEX IF NOT EXISTS idx_recent_conversation_history_session_user_agent ON public.recent_conversation_history USING btree (session_id, user_id, agent_id) TABLESPACE pg_default;
DROP INDEX IF EXISTS idx_recent_conversation_history_user_id;
CREATE INDEX IF NOT EXISTS idx_recent_conversation_history_user_id ON public.recent_conversation_history USING btree (user_id) TABLESPACE pg_default;
*/

-- Ensure the update_updated_at_column function is created (if not already from previous DDL sections)