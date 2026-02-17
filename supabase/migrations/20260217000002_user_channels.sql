-- User notification channels (Telegram, etc.)
-- Stores per-user channel configuration for push notifications

CREATE TABLE user_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    channel_type TEXT NOT NULL,  -- 'telegram'
    channel_id TEXT NOT NULL,    -- Telegram chat_id
    config JSONB DEFAULT '{}',   -- per-channel settings (e.g., quiet hours)
    is_active BOOLEAN DEFAULT true,
    linked_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, channel_type)
);

-- RLS
ALTER TABLE user_channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own channels"
    ON user_channels FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own channels"
    ON user_channels FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all channels"
    ON user_channels FOR ALL
    USING (current_user = 'postgres');

-- Telegram linking tokens (temporary, expire after 10 minutes)
CREATE TABLE channel_linking_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    channel_type TEXT NOT NULL DEFAULT 'telegram',
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '10 minutes'),
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_linking_tokens_token ON channel_linking_tokens(token) WHERE used = false;

ALTER TABLE channel_linking_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own linking tokens"
    ON channel_linking_tokens FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own linking tokens"
    ON channel_linking_tokens FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role can manage all linking tokens"
    ON channel_linking_tokens FOR ALL
    USING (current_user = 'postgres');

COMMENT ON TABLE user_channels IS 'Per-user notification channel configuration (Telegram chat_id, etc.)';
COMMENT ON TABLE channel_linking_tokens IS 'Temporary tokens for linking external channels (Telegram /start flow)';
