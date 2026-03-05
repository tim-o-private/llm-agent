-- SPEC-029: Register draft_email_reply and send_email_reply tools

-- Register tools in the tools table (post-SPEC-019 schema: tools.type is TEXT)
INSERT INTO tools (name, type, description, config)
VALUES
  ('draft_email_reply', 'DraftEmailReplyTool',
   'Draft a reply to an email in the user''s writing style', '{}')
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = true,
  updated_at = now();

INSERT INTO tools (name, type, description, config)
VALUES
  ('send_email_reply', 'SendEmailReplyTool',
   'Send an approved email reply via Gmail', '{}')
ON CONFLICT (name) DO UPDATE SET
  type = EXCLUDED.type,
  description = EXCLUDED.description,
  is_active = true,
  updated_at = now();

-- Link tools to assistant agent via agent_tools
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT ac.id, t.id, true
FROM agent_configurations ac, tools t
WHERE ac.agent_name = 'assistant' AND t.name = 'draft_email_reply'
ON CONFLICT DO NOTHING;

INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT ac.id, t.id, true
FROM agent_configurations ac, tools t
WHERE ac.agent_name = 'assistant' AND t.name = 'send_email_reply'
ON CONFLICT DO NOTHING;
