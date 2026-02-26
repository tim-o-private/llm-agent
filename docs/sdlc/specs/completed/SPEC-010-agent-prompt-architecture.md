# SPEC-010: Agent Prompt Architecture

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-18
> **Updated:** 2026-02-18

## Goal

Transform the agent system prompt from a static DB text blob into a programmatically assembled prompt with layered context, behavioral philosophy, channel awareness, and mandatory memory search. The agent should know who it is, what channel it's on, what time it is, and should proactively search memory before answering memory-dependent questions — rather than having the entire LTM injected into every request's context window.

Inspired by OpenClaw's prompt architecture: identity files + programmatic assembly + memory-on-demand.

## Acceptance Criteria

- [ ] AC-1: System prompt is assembled programmatically from sections (identity/soul, tools, safety, channel, time) — not a monolithic DB string
- [ ] AC-2: `agent_configurations.system_prompt` replaced by `agent_configurations.soul` (TEXT) containing the agent's behavioral philosophy, and `agent_configurations.identity` (JSONB) containing name/vibe/description metadata
- [ ] AC-3: Agent system prompt includes current date/time and timezone at assembly time
- [ ] AC-4: Agent system prompt includes channel context (web, telegram, scheduled) so the agent can adapt its response format
- [ ] AC-5: LTM notes are NOT injected into the system prompt. Instead, the system prompt instructs the agent to use `read_memory` before answering memory-dependent questions
- [ ] AC-6: `user_agent_prompt_customizations` table simplified to a single TEXT column `instructions` per user+agent (replacing JSONB `content`, `customization_type`, `priority`)
- [ ] AC-7: New tool `update_instructions` allows the agent to write to the user's prompt customizations (so the agent can self-modify its own instructions when the user says "always do X")
- [ ] AC-8: User instructions from `user_agent_prompt_customizations` are injected into the assembled prompt as a dedicated section
- [ ] AC-9: `CustomizableAgentExecutor._build_system_message()` replaced by a `build_agent_prompt()` function that assembles all sections
- [ ] AC-10: All three entry points (web chat, Telegram, scheduled execution) pass channel context to the prompt builder
- [ ] AC-11: Tests verify prompt assembly with various combinations of soul/identity/instructions/channel/LTM

## Scope

### Schema Changes

**Simplify `agent_configurations`:**
- Rename `system_prompt` → `soul` (TEXT). Contains the behavioral philosophy — who the agent is, how it operates, what it prioritizes. Written by admin, not user-editable.
- Add `identity` (JSONB, nullable). Contains structured metadata: `{name, vibe, description}`. Optional — used by prompt builder for the identity line.

**Simplify `user_agent_prompt_customizations`:**
- Drop `customization_type`, `content` (JSONB), `priority` columns
- Add `instructions` (TEXT) — a single free-text block of user instructions
- Drop the unique constraint on `(user_id, agent_name, customization_type)`, replace with `UNIQUE (user_id, agent_name)` — one instructions block per user+agent
- The agent writes this via NLP. No need for structured JSONB — the LLM can read and write plain text.

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/prompt_builder.py` | Assembles system prompt from sections |
| `chatServer/tools/update_instructions_tool.py` | Tool for agent to update user instructions |
| `tests/chatServer/services/test_prompt_builder.py` | Tests for prompt assembly |
| `tests/chatServer/tools/test_update_instructions_tool.py` | Tests for instructions tool |

### Files to Modify

| File | Change |
|------|--------|
| `src/core/agents/customizable_agent.py` | Remove `_build_system_message`, accept assembled prompt string |
| `src/core/agent_loader_db.py` | Use `build_agent_prompt()`, pass channel, fetch user instructions, stop injecting LTM into prompt |
| `chatServer/services/chat.py` | Pass `channel="web"` to agent loading, stop calling `update_ltm_context()` |
| `chatServer/channels/telegram_bot.py` | Pass `channel="telegram"` to agent loading, stop calling `update_ltm_context()` |
| `chatServer/services/scheduled_execution_service.py` | Pass `channel="scheduled"` to agent loading, stop prepending LTM to prompt |
| `chatServer/services/prompt_customization.py` | Simplify to work with TEXT `instructions` column |
| `chatServer/models/prompt_customization.py` | Simplify Pydantic models |
| `supabase/migrations/` | Schema changes for both tables |

### Out of Scope

- Frontend UI for editing instructions (future spec — SPEC-007 or separate)
- Renaming legacy tools (already in backlog as P2)
- Memory search improvements (vector search, semantic indexing) — this spec just mandates the tool-based pattern over injection
- Heartbeat/silent-reply pattern (future consideration)
- Sub-agent prompt modes (minimal vs full) — only one agent type for now

## Technical Approach

### 1. Prompt Builder Service

New `chatServer/services/prompt_builder.py` with a single function:

```python
def build_agent_prompt(
    soul: str,                          # from agent_configurations.soul
    identity: dict | None,              # from agent_configurations.identity
    channel: str,                       # "web" | "telegram" | "scheduled"
    user_instructions: str | None,      # from user_agent_prompt_customizations.instructions
    timezone: str | None = None,        # from user preferences (future) or server default
    tool_names: list[str] | None = None, # names of available tools for reference
) -> str:
```

Assembled sections (in order):

```
## Identity
You are {identity.name or "an AI assistant"} — {identity.description or "a personal assistant"}.
{identity.vibe or ""}

## Soul
{soul}

## Channel
You are responding via {channel}.
- web: User is on the web app. Markdown formatting is supported.
- telegram: User is on Telegram. Keep responses concise. No complex markdown.
- scheduled: This is an automated scheduled run. No one is waiting for a response.
  Be thorough but don't ask follow-up questions — just do the work and report results.

## Current Time
{formatted datetime} ({timezone})

## Memory
You have long-term memory via the read_memory and save_memory tools.
IMPORTANT: Before answering any question about the user's preferences, past conversations,
ongoing projects, or anything you were previously told to remember — call read_memory FIRST.
Do not guess from the conversation. Check your memory.
When the user tells you something to remember, call save_memory immediately.

## User Instructions
{user_instructions or "(No custom instructions set.)"}
The user can change these by telling you things like "always do X" or "never do Y".
When they do, use the update_instructions tool to persist the change.

## Tools
Available tools: {comma-separated tool_names}
Use tools when they help. Don't narrate routine tool calls.
```

The soul section is the big one — it replaces the old monolithic `system_prompt`. Example soul for the assistant agent:

```
Be genuinely helpful, not performatively helpful. Skip the "Great question!"
and "I'd be happy to help!" — just help.

Be resourceful before asking. Check your memory. Use your tools. Search for it.
Then ask if you're stuck. Come back with answers, not questions.

Earn trust through competence. Be careful with external actions (sending emails,
creating reminders that trigger notifications). Be bold with internal ones
(reading emails, searching, organizing information).

When you don't know something, say so. Don't fabricate information.

Key responsibilities:
- Email management: search, summarize, and draft responses
- Task tracking: help the user stay on top of what matters
- Reminders: set them when asked, or proactively suggest them
- Memory: remember what the user tells you across sessions

Be concise. Be direct. Be useful.
```

### 2. Schema Migration

```sql
-- Rename system_prompt → soul
ALTER TABLE agent_configurations RENAME COLUMN system_prompt TO soul;
COMMENT ON COLUMN agent_configurations.soul IS
  'Behavioral philosophy and core instructions for this agent. Admin-editable only.';

-- Add identity JSONB
ALTER TABLE agent_configurations ADD COLUMN identity JSONB;
COMMENT ON COLUMN agent_configurations.identity IS
  'Structured identity metadata: {name, vibe, description}. Used by prompt builder.';

-- Simplify user_agent_prompt_customizations
ALTER TABLE user_agent_prompt_customizations
  ADD COLUMN instructions TEXT NOT NULL DEFAULT '';

-- Migrate existing JSONB content to TEXT (best-effort)
UPDATE user_agent_prompt_customizations
SET instructions = COALESCE(content::text, '')
WHERE instructions = '';

-- Drop old columns
ALTER TABLE user_agent_prompt_customizations
  DROP COLUMN content,
  DROP COLUMN customization_type,
  DROP COLUMN priority;

-- Replace unique constraint
ALTER TABLE user_agent_prompt_customizations
  DROP CONSTRAINT IF EXISTS UQ_user_agent_customization_type;
ALTER TABLE user_agent_prompt_customizations
  ADD CONSTRAINT uq_user_agent_instructions UNIQUE (user_id, agent_name);
```

### 3. Update Instructions Tool

```python
class UpdateInstructionsInput(BaseModel):
    instructions: str = Field(
        ...,
        description="The complete updated instructions text. This REPLACES all existing instructions."
    )

class UpdateInstructionsTool(BaseTool):
    name: str = "update_instructions"
    description: str = (
        "Update your standing instructions for this user. "
        "Use this when the user says things like 'always summarize emails in bullet points' "
        "or 'never send emails without asking me first'. "
        "Call read_memory first to see existing instructions, then write the full updated text. "
        "This is a REPLACE operation — include all existing instructions you want to keep."
    )
```

The tool does an upsert into `user_agent_prompt_customizations` with the full text. The agent is responsible for merging old instructions with new ones using NLP — no need for structured JSONB or priority ordering.

### 4. Wire Into Entry Points

**Web chat (`chat.py`):**
```python
# Before: inject LTM into executor
# After: pass channel to loader, LTM stays tool-accessible
agent_executor = get_or_load_agent_executor(
    ..., channel="web"
)
# Remove: update_ltm_context() call
```

**Telegram (`telegram_bot.py`):**
```python
agent_executor = load_agent_executor_db(
    ..., channel="telegram"
)
# Remove: fetch_ltm_notes + update_ltm_context
```

**Scheduled (`scheduled_execution_service.py`):**
```python
agent_executor = load_agent_executor_db(
    ..., channel="scheduled"
)
# Remove: LTM prepending to prompt
```

### 5. Agent Loader Changes

`load_agent_executor_db` gains a `channel` parameter. It:
1. Fetches `soul` and `identity` from `agent_configurations` (was `system_prompt`)
2. Fetches `instructions` from `user_agent_prompt_customizations` for this user+agent
3. Calls `build_agent_prompt(soul, identity, channel, instructions, ...)`
4. Passes the assembled string to `CustomizableAgentExecutor.from_agent_config()`
5. Does NOT fetch or inject LTM — the agent uses `read_memory` tool on-demand

### Dependencies

- SPEC-006 PRs #30-34 must be merged first (they wire LTM into loading — this spec removes that wiring and replaces it with the tool-based approach)
- Memory tools (`save_memory`, `read_memory`) must exist (they do, from SPEC-006 PR #32)

## Testing Requirements

### Unit Tests (required)

- `test_prompt_builder.py`: Test `build_agent_prompt()` with all combinations:
  - Soul only (no identity, no instructions, no channel)
  - All sections populated
  - Missing identity (graceful fallback)
  - Each channel type produces correct guidance
  - Current time is included and formatted
  - Tool names are listed
- `test_update_instructions_tool.py`: Test the upsert behavior:
  - First write creates row
  - Second write replaces
  - Empty string clears instructions
  - Scoped to user+agent (can't write other user's instructions)

### Integration Tests (required for API/DB changes)

- Agent executor loads with new soul/identity columns
- Agent executor includes channel in assembled prompt
- `update_instructions` tool persists and is readable by prompt builder on next request
- Scheduled execution passes `channel="scheduled"` correctly

### What to Test

- Happy path for all ACs
- Backward compatibility: agent with old `system_prompt` column still loads (migration renames column)
- Agent with no user instructions works fine
- Agent with no identity JSONB works fine

### Manual Verification (UAT)

- [ ] Chat with assistant on web — verify prompt includes `channel: web` and current time
- [ ] Chat with assistant on Telegram — verify prompt includes `channel: telegram`
- [ ] Tell the agent "always respond in bullet points" — verify it calls `update_instructions`
- [ ] Start a new session — verify the instruction persists (agent reads it from DB)
- [ ] Ask "what do you remember about me?" — verify agent calls `read_memory` (not answered from injected LTM)
- [ ] Run a scheduled execution — verify it runs with `channel: scheduled` context
- [ ] Check that existing agent functionality (email digest, reminders) still works

## Edge Cases

- **No soul set**: Prompt builder uses a minimal default ("You are a helpful assistant.")
- **No identity set**: Identity section omitted entirely
- **No user instructions**: Section says "(No custom instructions set.)"
- **Very long user instructions**: Truncate at 2000 chars with warning (agent can read_memory for overflow)
- **Agent updates instructions to empty**: Allowed — effectively clears custom instructions
- **Multiple agents per user**: Each agent has independent instructions (unique on user_id + agent_name)
- **LTM migration**: Existing LTM notes stay in `agent_long_term_memory` table, still accessible via `read_memory`/`save_memory` tools. The only change is we stop injecting them into the system prompt.
- **Cached executors**: The `AGENT_EXECUTOR_CACHE` currently caches executors by `(user_id, agent_name)`. Since the prompt now includes channel, we either need to cache by `(user_id, agent_name, channel)` or rebuild the prompt on each request (preferred — prompt assembly is cheap, and it ensures fresh instructions + time).

## Functional Units (for PR Breakdown)

1. **Unit 1: Schema migration** (`feat/SPEC-010-migration`)
   - Rename `system_prompt` → `soul`, add `identity` JSONB
   - Simplify `user_agent_prompt_customizations`
   - Backfill existing data
   - Merge order: **1st** (no prerequisites)

2. **Unit 2: Prompt builder + update_instructions tool** (`feat/SPEC-010-prompt-builder`)
   - `chatServer/services/prompt_builder.py`
   - `chatServer/tools/update_instructions_tool.py`
   - Register tool in DB, link to assistant agent
   - Tests for both
   - Merge order: **2nd** (requires migration)

3. **Unit 3: Wire entry points** (`feat/SPEC-010-wire-entry-points`)
   - Update `agent_loader_db.py` to use prompt builder
   - Update `chat.py`, `telegram_bot.py`, `scheduled_execution_service.py` to pass channel
   - Remove LTM injection from all entry points
   - Update `customizable_agent.py` to remove `_build_system_message`
   - Simplify `prompt_customization.py` models
   - Tests for integration
   - Merge order: **3rd** (requires prompt builder + migration)
