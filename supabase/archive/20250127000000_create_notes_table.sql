-- Create notes table for user notes with RLS
-- Follows established patterns from existing tables

CREATE TABLE public.notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Add indexes for efficient querying
CREATE INDEX idx_notes_user_id ON public.notes(user_id);
CREATE INDEX idx_notes_deleted ON public.notes(deleted);
CREATE INDEX idx_notes_updated_at ON public.notes(updated_at DESC);

-- Add trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_notes_updated_at 
    BEFORE UPDATE ON public.notes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Users can only access their own notes
CREATE POLICY "Users can view their own notes" ON public.notes
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own notes" ON public.notes
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own notes" ON public.notes
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own notes" ON public.notes
    FOR DELETE USING (auth.uid() = user_id);

-- Add comments for documentation
COMMENT ON TABLE public.notes IS 'User notes with soft delete support and RLS';
COMMENT ON COLUMN public.notes.id IS 'Primary key UUID';
COMMENT ON COLUMN public.notes.user_id IS 'Reference to auth.users - owner of the note';
COMMENT ON COLUMN public.notes.title IS 'Optional title for the note';
COMMENT ON COLUMN public.notes.content IS 'Main content of the note';
COMMENT ON COLUMN public.notes.created_at IS 'Timestamp when note was created';
COMMENT ON COLUMN public.notes.updated_at IS 'Timestamp when note was last updated (auto-updated)';
COMMENT ON COLUMN public.notes.deleted IS 'Soft delete flag - when true, note is considered deleted'; 