---
name: prompt-engineering
description: Prompt architecture patterns for the llm-agent platform. Use when writing or modifying agent prompts, soul text, identity configs, tool descriptions, tool guidance (prompt_section), channel guidance constants, or prompt templates. Covers the DB-driven prompt assembly pipeline, $placeholder template system, and testing via clarity-dev MCP.
---

# Prompt Engineering — Quick Reference

This skill covers how production agent prompts are structured, stored, and assembled in llm-agent.

## Architecture Overview

```
agent_configurations (Supabase)
  ├── soul           TEXT    — behavioral philosophy ("who you are")
  ├── identity       JSONB   — {name, vibe, description}
  ├── prompt_template TEXT   — $placeholder layout (section order + framing)
  └── llm_config     JSONB   — {provider, model, temperature}
                ↓
         prompt_builder.py
  ├── _compute_section_values()  — resolves all placeholders
  └── build_agent_prompt()       — template path OR hardcoded fallback
                ↓
         Assembled system prompt
  ├── ## Identity       ← from identity JSONB
  ├── ## Soul           ← from soul TEXT
  ├── ## Operating Model← OPERATING_MODEL constant (interactive only)
  ├── ## Channel        ← CHANNEL_GUIDANCE[channel]
  ├── ## Current Time   ← computed at render
  ├── ## What You Know  ← pre-fetched memory notes
  ├── ## User Instructions ← user_agent_prompt_customizations.instructions
  ├── ## Tool Guidance  ← tool.prompt_section(channel) per class
  ├── ## Interaction Learning ← static (interactive only)
  └── ## Session        ← onboarding / session_open (conditional)
                ↓
    ChatPromptTemplate([system, chat_history, human, agent_scratchpad])
```

**Prompts live in Supabase, not local files.** The codebase contains:
- Assembly logic (`chatServer/services/prompt_builder.py`)
- Constants for channel/session behavior (same file)
- Tool guidance methods (each tool class's `prompt_section()`)
- Migration-seeded defaults (for reference, not source of truth)

## Prompt Layers

| Layer | Where it lives | Who changes it | Cached? |
|-------|---------------|----------------|---------|
| **Soul** | `agent_configurations.soul` | Developer (migration/SQL) | 600s TTL |
| **Identity** | `agent_configurations.identity` | Developer (migration/SQL) | 600s TTL |
| **Template** | `agent_configurations.prompt_template` | Developer (migration/SQL) | 600s TTL |
| **Channel guidance** | `CHANNEL_GUIDANCE` dict in prompt_builder.py | Developer (code) | Deploy |
| **Operating model** | `OPERATING_MODEL` constant in prompt_builder.py | Developer (code) | Deploy |
| **Session/onboarding** | Constants in prompt_builder.py | Developer (code) | Deploy |
| **Tool descriptions** | `tools.description` column | Developer (migration/SQL) | 300s TTL |
| **Tool guidance** | `ToolClass.prompt_section()` methods | Developer (code) | Deploy |
| **User instructions** | `user_agent_prompt_customizations.instructions` | Agent (via UpdateInstructionsTool) | 120s TTL |
| **Memory notes** | min-memory MCP (pre-fetched) | Agent (via CreateMemoriesTool) | Per-request |

## Template System

Uses Python `string.Template` with `$placeholder` syntax. NOT Jinja — chosen to avoid `{}` conflicts.

Available placeholders: `$identity`, `$soul`, `$operating_model`, `$channel_guidance`, `$current_time`, `$memory_notes`, `$user_instructions`, `$tool_guidance`, `$interaction_learning`, `$session_section`

Empty sections are auto-stripped: `## Header\n\n` with no content is removed. Triple+ newlines collapse to double.

## Quick Checklist

Before modifying any prompt:

- [ ] **Read the current production value** — check Supabase directly or read the migration that last seeded it
- [ ] **Identify which layer** you're changing (soul vs template vs tool guidance vs constant)
- [ ] **Check channel behavior** — does this apply to all channels or only some? (Operating model and interaction learning are interactive-only)
- [ ] **Check conditional logic** — onboarding and session_open sections have branching based on `is_new_user` and `last_message_at`
- [ ] **Consider cache TTL** — soul/identity/template changes won't take effect for up to 600s without server restart
- [ ] **Test via clarity-dev MCP** — `chat_with_clarity(message, agent_name)` hits the live assembled prompt

## Recipes

### 1. Edit Soul Text

1. Read current value: check latest migration or query `agent_configurations` in Supabase
2. Write new soul text — keep it behavioral, not procedural (see principles below)
3. Deploy via SQL migration: `UPDATE agent_configurations SET soul = '...' WHERE agent_name = '...';`
4. Test: restart server or wait 600s, then use clarity-dev MCP

### 2. Add/Edit Tool Guidance

Two surfaces for tool behavior in the prompt:

- **`tools.description`** — the LangChain tool description (shown alongside the tool schema). Keep factual and concise. Change via SQL on `tools` table.
- **`ToolClass.prompt_section(channel)`** — behavioral guidance injected into the system prompt. Change in the tool's Python class. Can be channel-aware (return different text for `scheduled` vs `web`).

### 3. Modify Channel Guidance

Edit `CHANNEL_GUIDANCE` dict in `chatServer/services/prompt_builder.py`. Key: channel name string. Value: guidance text. Requires code deploy.

### 4. Add a New Placeholder

1. Add computation in `_compute_section_values()` in prompt_builder.py
2. Add `$new_placeholder` to the DB template via migration
3. Add fallback rendering in the hardcoded assembly path
4. Keep both paths in sync

### 5. Test a Prompt Change

```bash
# If chatServer is running:
# Use clarity-dev MCP tool
chat_with_clarity(message="hello", agent_name="assistant")

# To see the assembled prompt, add logging in prompt_builder.py
# or inspect via debugger at build_agent_prompt() return
```

## Prompt Writing Principles

1. **Soul = philosophy, not procedure.** Soul describes *who* the agent is and *how* it thinks. Procedural instructions go in operating model, tool guidance, or channel guidance.
2. **Show, don't tell.** "Don't narrate your tool calls" > "You should avoid narrating your tool calls to the user."
3. **Behavioral over declarative.** "Match their energy — brief for brief, thoughtful for thoughtful" > "Adapt response length to user input."
4. **Negative space matters.** What you tell the agent NOT to do shapes behavior as much as what you tell it to do. "Don't ask about preferences — learn from behavior."
5. **Channel separation.** Interactive channels get operating model + learning. Automated channels don't. Don't bleed interactive patterns into scheduled/heartbeat.
6. **Tool guidance is behavioral context.** `prompt_section()` explains *when and why* to use a tool, not *how* (the tool schema handles that).
7. **Conditional sections should be rare.** Every `if` in prompt assembly is a source of bugs. Prefer channel-based gating over complex conditionals.
8. **Test with the full pipeline.** Prompt text in isolation means nothing — test the assembled prompt with real tools, real memory, real channel.

## Key Gotchas

1. **Two assembly paths must stay in sync.** Template path (DB) and hardcoded path (code fallback) produce the same prompt. If you add a section to one, add it to both.
2. **Cache TTL is real.** Agent config is cached 600s. You won't see soul/template changes instantly after a DB update — restart the server or wait.
3. **`safe_substitute` swallows missing placeholders.** `string.Template.safe_substitute()` leaves `$unknown` as literal text instead of erroring. Typos in placeholder names silently fail.
4. **Empty section stripping is regex-based.** The regex `## \w[\w ]*\n\s*\n` only strips sections where the header is followed by whitespace then a blank line. Content that's just whitespace won't be stripped.
5. **Tool guidance deduplicates by class, not instance.** If two tools share a base class, only one `prompt_section()` is called. This is intentional (e.g., Gmail tools share guidance).
6. **User instructions are truncated at 2000 chars.** The agent can write unlimited instructions via UpdateInstructionsTool, but only the first 2000 chars appear in the prompt.
7. **Memory notes are truncated at 4000 chars.** Pre-fetched memory is capped. The agent should keep high-signal memories concise.

For full patterns with code examples and anti-patterns, see [reference.md](reference.md).
