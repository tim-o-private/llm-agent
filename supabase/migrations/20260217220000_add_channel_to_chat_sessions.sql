-- SPEC-005: Add channel and session_id columns to chat_sessions
-- Makes chat_sessions the universal session registry for web, Telegram, and scheduled channels.

-- Add channel column with CHECK constraint
ALTER TABLE chat_sessions
  ADD COLUMN channel TEXT NOT NULL DEFAULT 'web'
  CHECK (channel IN ('web', 'telegram', 'scheduled'));

-- Add session_id column (links to chat_message_history)
ALTER TABLE chat_sessions
  ADD COLUMN session_id TEXT;

-- Unique index on session_id (where not null)
CREATE UNIQUE INDEX idx_chat_sessions_session_id
  ON chat_sessions (session_id) WHERE session_id IS NOT NULL;

-- Composite index for session listing by user + channel
CREATE INDEX idx_chat_sessions_user_channel_created
  ON chat_sessions (user_id, channel, created_at DESC);

-- Backfill existing rows: only assign session_id to the most recent row per chat_id
-- to avoid unique constraint violations when multiple session instances share a chat_id.
UPDATE chat_sessions cs
  SET session_id = cs.chat_id::text, channel = 'web'
  WHERE cs.session_id IS NULL
    AND cs.id = (
      SELECT id FROM chat_sessions sub
      WHERE sub.chat_id = cs.chat_id
      ORDER BY sub.created_at DESC
      LIMIT 1
    );
