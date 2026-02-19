-- SPEC-010: Agent Prompt Architecture — schema changes
-- Renames system_prompt → soul, adds identity JSONB, simplifies prompt customizations

-- 1. Rename agent_configurations.system_prompt → soul
ALTER TABLE agent_configurations RENAME COLUMN system_prompt TO soul;
COMMENT ON COLUMN agent_configurations.soul IS 'Behavioral philosophy and core instructions. Admin-editable only.';

-- 2. Add agent_configurations.identity JSONB
ALTER TABLE agent_configurations ADD COLUMN identity JSONB;
COMMENT ON COLUMN agent_configurations.identity IS 'Structured identity: {name, vibe, description}. Used by prompt builder.';

-- 3. Backfill identity for existing agents
UPDATE agent_configurations
SET identity = '{"name": "Clarity", "vibe": "direct and helpful", "description": "a personal assistant for email, tasks, and reminders"}'::jsonb
WHERE agent_name = 'assistant';

UPDATE agent_configurations
SET identity = '{"name": "Digest", "vibe": "concise and thorough", "description": "an email digest specialist"}'::jsonb
WHERE agent_name = 'email_digest_agent';

UPDATE agent_configurations
SET identity = '{"name": "Orchestrator", "vibe": "efficient briefer", "description": "a scheduled briefing agent"}'::jsonb
WHERE agent_name = 'orchestrator';

-- 4. Simplify user_agent_prompt_customizations
-- Add new instructions TEXT column
ALTER TABLE user_agent_prompt_customizations ADD COLUMN instructions TEXT NOT NULL DEFAULT '';

-- Migrate existing JSONB content to TEXT (best-effort)
UPDATE user_agent_prompt_customizations
SET instructions = COALESCE(content::text, '')
WHERE instructions = '';

-- Drop old columns
ALTER TABLE user_agent_prompt_customizations DROP COLUMN content;
ALTER TABLE user_agent_prompt_customizations DROP COLUMN customization_type;
ALTER TABLE user_agent_prompt_customizations DROP COLUMN priority;

-- Replace unique constraint: old one included customization_type, new one is just user+agent
ALTER TABLE user_agent_prompt_customizations
  DROP CONSTRAINT IF EXISTS "UQ_user_agent_customization_type";
ALTER TABLE user_agent_prompt_customizations
  ADD CONSTRAINT uq_user_agent_instructions UNIQUE (user_id, agent_name);
