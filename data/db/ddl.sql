CREATE TABLE public.tasks (
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      user_id UUID REFERENCES auth.users(id) NOT NULL,
      title TEXT NOT NULL,
      notes TEXT,
      category TEXT,
      completed BOOLEAN DEFAULT FALSE NOT NULL,
      due_date DATE,
      time_period TEXT CHECK (time_period IN ('Morning', 'Afternoon', 'Evening')), -- Or your specific enum values
      created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
      updated_at TIMESTAMPTZ
    );

    -- Optional: Add comments for clarity
    COMMENT ON COLUMN public.tasks.time_period IS 'Can be Morning, Afternoon, or Evening';

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