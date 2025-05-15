CREATE TABLE public.tasks (
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      user_id UUID REFERENCES auth.users(id) NOT NULL,
      title TEXT NOT NULL,
      notes TEXT, -- General notes about the task
      description TEXT, -- Detailed description of the task
      category TEXT,
      completed BOOLEAN DEFAULT FALSE NOT NULL, -- May become redundant or derived from status
      status TEXT CHECK (status IN ('pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred')) DEFAULT 'pending' NOT NULL,
      priority INTEGER DEFAULT 0 NOT NULL, -- e.g., 0=None, 1=Low, 2=Medium, 3=High
      motivation TEXT, -- User's "Why this matters" for the task
      completion_note TEXT, -- User's final reflection upon task completion
      due_date DATE,
      time_period TEXT CHECK (time_period IN ('Morning', 'Afternoon', 'Evening')), -- Or your specific enum values
      created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
      updated_at TIMESTAMPTZ,
      position INTEGER,
      parent_task_id UUID NULL REFERENCES public.tasks(id),
      subtask_position INTEGER NULL
    );

-- Optional: Add comments for clarity
COMMENT ON COLUMN public.tasks.time_period IS 'Can be Morning, Afternoon, or Evening';
COMMENT ON COLUMN public.tasks.parent_task_id IS 'Reference to the parent task if this is a subtask';
COMMENT ON COLUMN public.tasks.subtask_position IS 'Order of this subtask within its parent task';

-- Enable Row Level Security (RLS) for the table
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

-- Policies for RLS:
-- Allow authenticated users to select their own tasks
CREATE POLICY "Allow individual read access"
ON public.tasks
FOR SELECT
USING (auth.uid() = user_id);

-- Allow authenticated users to insert tasks for themselves
CREATE POLICY "Allow individual insert access"
ON public.tasks
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Allow authenticated users to update their own tasks
CREATE POLICY "Allow individual update access"
ON public.tasks
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Allow authenticated users to delete their own tasks
CREATE POLICY "Allow individual delete access"
ON public.tasks
FOR DELETE
USING (auth.uid() = user_id);

-- Optional: Create indexes for better query performance
CREATE INDEX idx_tasks_user_id ON public.tasks(user_id);
CREATE INDEX idx_tasks_due_date ON public.tasks(due_date);
CREATE INDEX idx_tasks_completed ON public.tasks(completed);
CREATE INDEX idx_tasks_position ON public.tasks(position);
CREATE INDEX idx_tasks_status ON public.tasks(status);
CREATE INDEX idx_tasks_priority ON public.tasks(priority);

-- Table for Focus Sessions / Reflections
CREATE TABLE public.focus_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    task_id UUID REFERENCES public.tasks(id) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER, -- Duration of the focus session in seconds
    notes TEXT, -- User's reflection or notes on the session
    mood TEXT CHECK (mood IN ('energized', 'neutral', 'drained', 'focused', 'distracted', 'other')),
    outcome TEXT CHECK (outcome IN ('completed_task', 'made_progress', 'got_stuck', 'interrupted', 'planned_next', 'other')),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

COMMENT ON COLUMN public.focus_sessions.notes IS 'User reflection or summary of what was done during the session.';
COMMENT ON COLUMN public.focus_sessions.mood IS 'User-reported mood after the session.';
COMMENT ON COLUMN public.focus_sessions.outcome IS 'User-reported outcome of the session.';

ALTER TABLE public.focus_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow individual read access for focus_sessions"
ON public.focus_sessions
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Allow individual insert access for focus_sessions"
ON public.focus_sessions
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow individual update access for focus_sessions"
ON public.focus_sessions
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow individual delete access for focus_sessions"
ON public.focus_sessions
FOR DELETE
USING (auth.uid() = user_id);

CREATE INDEX idx_focus_sessions_user_id ON public.focus_sessions(user_id);
CREATE INDEX idx_focus_sessions_task_id ON public.focus_sessions(task_id);
CREATE INDEX idx_focus_sessions_created_at ON public.focus_sessions(created_at);

-- Table for Scratch Pad Entries
CREATE TABLE public.scratch_pad_entries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ,
    archived BOOLEAN DEFAULT FALSE NOT NULL,
    task_id UUID REFERENCES public.tasks(id) NULL, -- Optional: if converted to/linked from a task
    session_id UUID REFERENCES public.focus_sessions(id) NULL -- Optional: if captured during a specific session
);

COMMENT ON TABLE public.scratch_pad_entries IS 'For quick capture of thoughts, ideas, or distractions.';
COMMENT ON COLUMN public.scratch_pad_entries.task_id IS 'Reference to a task if this entry was converted or is related.';
COMMENT ON COLUMN public.scratch_pad_entries.session_id IS 'Reference to a focus session if captured during one.';

ALTER TABLE public.scratch_pad_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow individual read access for scratch_pad_entries"
ON public.scratch_pad_entries
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Allow individual insert access for scratch_pad_entries"
ON public.scratch_pad_entries
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow individual update access for scratch_pad_entries"
ON public.scratch_pad_entries
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow individual delete access for scratch_pad_entries"
ON public.scratch_pad_entries
FOR DELETE
USING (auth.uid() = user_id);

CREATE INDEX idx_scratch_pad_entries_user_id ON public.scratch_pad_entries(user_id);
CREATE INDEX idx_scratch_pad_entries_created_at ON public.scratch_pad_entries(created_at);
CREATE INDEX idx_scratch_pad_entries_task_id ON public.scratch_pad_entries(task_id);
CREATE INDEX idx_scratch_pad_entries_session_id ON public.scratch_pad_entries(session_id); 