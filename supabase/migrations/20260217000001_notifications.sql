-- Notifications table for delivering agent results to users
-- Supports web UI (polling) and will support Telegram (Phase 3)

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'info',
    -- categories: 'heartbeat', 'approval_needed', 'agent_result', 'error'
    metadata JSONB DEFAULT '{}',
    -- metadata examples: {schedule_id, agent_name, execution_id, pending_action_ids}
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Fast lookup for unread notifications (most common query)
CREATE INDEX idx_notifications_user_unread
    ON notifications(user_id, created_at DESC)
    WHERE read = false;

-- General user timeline
CREATE INDEX idx_notifications_user_created
    ON notifications(user_id, created_at DESC);

-- RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own notifications"
    ON notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications"
    ON notifications FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all notifications"
    ON notifications FOR ALL
    USING (current_user = 'postgres');

COMMENT ON TABLE notifications IS 'User-facing notifications from agent executions, heartbeats, and system events';
COMMENT ON COLUMN notifications.category IS 'Notification type: heartbeat, approval_needed, agent_result, error, info';
COMMENT ON COLUMN notifications.metadata IS 'Structured context: schedule_id, agent_name, execution_id, pending_action_ids, etc.';
