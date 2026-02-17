-- Configure Orchestrator Agent
-- This agent runs on a schedule to brief users on what happened and what needs attention.
-- It uses read-only tools (AUTO_APPROVE tier) and reports results via notifications.

-- 1. Insert orchestrator agent configuration
INSERT INTO agent_configurations (
    agent_name,
    llm_config,
    system_prompt,
    created_at,
    updated_at
) VALUES (
    'orchestrator',
    '{
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.3,
        "max_tokens": 4096
    }'::jsonb,
    'You are an orchestrator agent. You run on a schedule to keep the user informed.

## Your Job
1. Check what happened since your last run
2. Summarize important information concisely
3. Identify items that need the user''s attention

## Tools
Use your read-only tools to gather information:
- gmail_search / gmail_get_message: Check recent emails
- get_tasks: Review open tasks (when available)

## Output Format
Structure your response as a morning briefing:

**Emails:** [count] new since last check
- [Sender]: [subject] — [one-line summary]
- ...

**Tasks:** [count] open
- [task with approaching deadline or high priority]
- ...

**Needs your attention:**
- [Anything flagged as important or time-sensitive]

Rules:
- Be concise. This is a briefing, not a conversation.
- Focus on what changed and what needs action.
- Do NOT take write actions. Read and report only.
- If a tool fails or returns no data, note it briefly and move on.',
    NOW(),
    NOW()
) ON CONFLICT (agent_name) DO UPDATE SET
    llm_config = EXCLUDED.llm_config,
    system_prompt = EXCLUDED.system_prompt,
    updated_at = NOW();

-- 2. Link existing Gmail read tools to orchestrator agent
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT
    (SELECT id FROM agent_configurations WHERE agent_name = 'orchestrator'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('gmail_search', 'gmail_get_message')
AND NOT EXISTS (
    SELECT 1 FROM agent_tools at
    WHERE at.agent_id = (SELECT id FROM agent_configurations WHERE agent_name = 'orchestrator')
    AND at.tool_id = t.id
    AND at.is_deleted = false
);

-- 3. Create a default orchestrator schedule for users who have Telegram linked
-- This creates a daily 7:00 AM heartbeat schedule
-- Users without Telegram still get web notifications
INSERT INTO agent_schedules (user_id, agent_name, schedule_cron, prompt, active, config)
SELECT
    uc.user_id,
    'orchestrator',
    '0 7 * * *',  -- Daily at 7:00 AM
    'Generate a morning briefing. Check my recent emails from the last 12 hours and summarize what needs my attention today.',
    true,
    jsonb_build_object(
        'schedule_type', 'heartbeat',
        'notify_channels', jsonb_build_array('telegram', 'web'),
        'include_pending_summary', true
    )
FROM user_channels uc
WHERE uc.channel_type = 'telegram'
AND uc.is_active = true
AND NOT EXISTS (
    SELECT 1 FROM agent_schedules
    WHERE user_id = uc.user_id
    AND agent_name = 'orchestrator'
);

-- Add comments
COMMENT ON COLUMN agent_schedules.config IS 'JSON configuration: schedule_type (heartbeat|digest|custom), notify_channels, include_pending_summary, hours_back, etc.';
