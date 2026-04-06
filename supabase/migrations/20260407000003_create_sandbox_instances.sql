-- Sandbox instance tracking
-- Tracks provisioned per-user bwrap sandboxes for lifecycle management.

CREATE TABLE IF NOT EXISTS sandbox_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    disk_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'destroying', 'destroyed', 'error')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- RLS
ALTER TABLE sandbox_instances ENABLE ROW LEVEL SECURITY;

CREATE POLICY sandbox_instances_user_read ON sandbox_instances
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can do everything (provisioner runs as service role)
CREATE POLICY sandbox_instances_service_all ON sandbox_instances
    FOR ALL USING (auth.role() = 'service_role');

-- Index for lookups by user
CREATE INDEX IF NOT EXISTS idx_sandbox_instances_user_id ON sandbox_instances(user_id);
