-- SPEC-025: Add session_id to notifications for per-chat timeline filtering
ALTER TABLE notifications ADD COLUMN session_id TEXT;

CREATE INDEX idx_notifications_session
ON notifications (session_id, created_at DESC)
WHERE session_id IS NOT NULL;

COMMENT ON COLUMN notifications.session_id IS 'Chat session (chat_id) this notification belongs to, for timeline filtering';
