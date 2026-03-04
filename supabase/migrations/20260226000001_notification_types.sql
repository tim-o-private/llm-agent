-- SPEC-025: Add notification type system
ALTER TABLE notifications
ADD COLUMN type TEXT NOT NULL DEFAULT 'notify'
  CHECK (type IN ('agent_only', 'silent', 'notify')),
ADD COLUMN requires_approval BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN pending_action_id UUID REFERENCES pending_actions(id);

-- Index for frontend polling (type-filtered)
CREATE INDEX idx_notifications_user_type
ON notifications (user_id, type, created_at DESC)
WHERE type IN ('silent', 'notify');

COMMENT ON COLUMN notifications.type IS 'Delivery tier: agent_only (no store), silent (DB only), notify (DB + Telegram)';
COMMENT ON COLUMN notifications.requires_approval IS 'Whether this notification represents a pending approval request';
COMMENT ON COLUMN notifications.pending_action_id IS 'FK to pending_actions when this notification is an approval request';
