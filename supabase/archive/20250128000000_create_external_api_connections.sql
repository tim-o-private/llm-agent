-- Create external_api_connections table for storing OAuth tokens
-- Follows established patterns from existing tables

CREATE TABLE public.external_api_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL CHECK (service_name IN ('gmail', 'google_calendar', 'slack')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    service_user_id TEXT, -- External service's user ID (e.g., Google user ID)
    service_user_email TEXT, -- External service's user email
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Ensure one connection per user per service
    UNIQUE(user_id, service_name)
);

-- Add indexes for efficient querying
CREATE INDEX idx_external_api_connections_user_id ON public.external_api_connections(user_id);
CREATE INDEX idx_external_api_connections_service_name ON public.external_api_connections(service_name);
CREATE INDEX idx_external_api_connections_active ON public.external_api_connections(is_active);
CREATE INDEX idx_external_api_connections_expires_at ON public.external_api_connections(token_expires_at);

-- Add trigger to automatically update updated_at
CREATE TRIGGER update_external_api_connections_updated_at 
    BEFORE UPDATE ON public.external_api_connections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE public.external_api_connections ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Users can only access their own API connections
CREATE POLICY "Users can view their own API connections" ON public.external_api_connections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own API connections" ON public.external_api_connections
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own API connections" ON public.external_api_connections
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own API connections" ON public.external_api_connections
    FOR DELETE USING (auth.uid() = user_id);

-- Add comments for documentation
COMMENT ON TABLE public.external_api_connections IS 'OAuth connections to external APIs with encrypted token storage';
COMMENT ON COLUMN public.external_api_connections.id IS 'Primary key UUID';
COMMENT ON COLUMN public.external_api_connections.user_id IS 'Reference to auth.users - owner of the connection';
COMMENT ON COLUMN public.external_api_connections.service_name IS 'Name of the external service (gmail, google_calendar, slack)';
COMMENT ON COLUMN public.external_api_connections.access_token IS 'OAuth access token (should be encrypted at application level)';
COMMENT ON COLUMN public.external_api_connections.refresh_token IS 'OAuth refresh token (should be encrypted at application level)';
COMMENT ON COLUMN public.external_api_connections.token_expires_at IS 'When the access token expires';
COMMENT ON COLUMN public.external_api_connections.scopes IS 'Array of OAuth scopes granted';
COMMENT ON COLUMN public.external_api_connections.service_user_id IS 'User ID from the external service';
COMMENT ON COLUMN public.external_api_connections.service_user_email IS 'User email from the external service';
COMMENT ON COLUMN public.external_api_connections.created_at IS 'Timestamp when connection was created';
COMMENT ON COLUMN public.external_api_connections.updated_at IS 'Timestamp when connection was last updated';
COMMENT ON COLUMN public.external_api_connections.is_active IS 'Whether the connection is currently active'; 