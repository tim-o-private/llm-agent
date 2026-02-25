ALTER TABLE notifications
ADD COLUMN feedback TEXT CHECK (feedback IN ('useful', 'not_useful')),
ADD COLUMN feedback_at TIMESTAMPTZ;

CREATE INDEX idx_notifications_user_feedback
ON notifications (user_id, feedback, created_at DESC)
WHERE feedback IS NOT NULL;
