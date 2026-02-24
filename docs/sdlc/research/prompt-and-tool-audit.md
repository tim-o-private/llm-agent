# Prompt & Tool Audit

> **Date:** 2026-02-24
> **Purpose:** Map every prompt component and tool description source to enable systematic iteration.

## Part 1: Prompt Components

The system prompt is assembled in `chatServer/services/prompt_builder.py:build_agent_prompt()` from 9 sections, in order:

### 1. Identity (`## Identity`)

**Source:** `agent_configurations.identity` JSONB column in Supabase
**Set by:** Migration `20260219000001_agent_prompt_architecture.sql` (backfill only)
**Current value (assistant):**
```json
{"name": "Clarity", "vibe": "direct and helpful", "description": "a personal assistant for email, tasks, and reminders"}
```
**Rendered as:** `"You are Clarity — a personal assistant for email, tasks, and reminders. direct and helpful"`

**Problems:**
- "direct and helpful" is appended as-is after a period, reads awkwardly
- Description is generic — doesn't differentiate from any other assistant
- No mention of proactive behavior, memory, or the "chief of staff" vision

---

### 2. Soul (`## Soul`)

**Source:** `agent_configurations.soul` TEXT column in Supabase
**Set by:** Manually edited in DB (no migration sets the current value)
**Current value (assistant):**
```
You manage things so the user doesn't have to hold it all in their head.

## How you operate

Every conversation starts with awareness. Before responding to the user,
silently orient yourself:
1. Call get_tasks to see what's active — overdue items, things due today, priorities.
2. Call read_memory to recall what you know about this person.
3. Only then respond, informed by what you found.

Don't announce that you're doing this. Just do it and weave what you learn into your response.

## Tasks are your primary tool
[... long section about task creation behavior ...]

## When you have Gmail access
[... email scanning guidance ...]

## Memory
[... save preferences guidance ...]

## Personality
[... direct and practical ...]
```

**Problems:**
- References `read_memory` which no longer exists (old tool, replaced by `recall` in SPEC-018)
- Contains H2 headers (`## How you operate`, `## Tasks`, etc.) which conflict with the prompt builder's own H2 section headers — the LLM sees a flat list of `##` headers with no hierarchy
- Duplicates behavior that the bootstrap/session_open section also specifies (both say "use tools before greeting")
- The "soul" concept was supposed to be behavioral philosophy, but this is actually operational instructions — it's doing double duty
- No versioning — was hand-edited in the DB, no audit trail

---

### 3. Channel (`## Channel`)

**Source:** `CHANNEL_GUIDANCE` dict in `prompt_builder.py:6-36`
**Values:**
| Channel | Guidance |
|---------|----------|
| `web` | "Markdown formatting supported. Interactive conversation." |
| `telegram` | "Keep under 4096 chars. Simple markdown." |
| `scheduled` | "Automated run. Use tools. Don't ask follow-ups." |
| `heartbeat` | "Check state with tools. HEARTBEAT_OK if fine." |
| `session_open` | "User just returned. Deciding whether to initiate." |

**Problems:** None major. These are appropriate and concise.

---

### 4. Current Time (`## Current Time`)

**Source:** `_get_current_time()` in `prompt_builder.py:219-229`
**Value:** Formatted datetime with optional user timezone, falls back to UTC.

**Problems:** Timezone comes from `agent_loader_db.py` but there's no mechanism to detect or store user timezone. Always shows UTC unless manually configured.

---

### 5. What You Know (`## What You Know`)

**Source:** `_prefetch_memory_notes()` in `agent_loader_db.py:474-495`
**Populated by:** min-memory `retrieve_context` call with `query="user context and preferences"`, `memory_type=["core_identity", "project_context"]`, `limit=10`
**Truncated to:** 4000 chars

**Problems:**
- The query "user context and preferences" is hardcoded — doesn't adapt to channel or context
- For session_open bootstrap (new user), this will be empty, which is correct
- For returning users, this is the only memory the agent sees in the prompt — tool-based recall is separate and requires the agent to decide to call it

---

### 6. User Instructions (`## User Instructions`)

**Source:** `user_agent_prompt_customizations.instructions` TEXT column
**Fetched by:** `_fetch_user_instructions()` in `agent_loader_db.py:430-449` (sync) or `get_cached_user_instructions()` (async)
**Truncated to:** 2000 chars
**Default:** `"(No custom instructions set.)"` + boilerplate about using `update_instructions` tool

**Problems:** None. Clean design.

---

### 7. Tool Guidance (`## Tool Guidance`)

**Source:** Each tool class's `prompt_section(channel)` classmethod
**Assembled by:** `build_agent_prompt()` lines 182-198

**Current tool guidance (for channel=session_open or web):**

| Tool Class | `prompt_section()` output |
|---|---|
| `GmailSearchTool` | "Gmail: Use gmail_search, gmail_get_message, and gmail_digest for email tasks. When the user asks about email, use the tools — don't ask clarifying questions first." |
| `GetTasksTool` | "Tasks: Check get_tasks at conversation start to see what the user is working on. When they mention something actionable, use create_task. Update status as work progresses." |
| `CreateReminderTool` | "Reminders: When the user mentions a deadline or wants to be reminded, use create_reminder with an ISO datetime. Use list_reminders to show upcoming reminders." |
| `CreateScheduleTool` | "Schedules: When the user wants recurring work (daily summaries, weekly reports), use create_schedule with a cron expression." |
| `UpdateInstructionsTool` | "Instructions: When the user says 'always do X' or 'never do Y', use update_instructions to persist the preference." |
| `StoreMemoryTool` | "Memory: Proactively observe and record. When you learn something about the user — from their messages, email patterns, task habits, or tone — call store_memory. Don't wait to be asked. Use recall before answering questions about the user's preferences, past decisions, or projects." |
| `EmailDigestTool` | "Email Digest: Use email_digest for comprehensive email summaries. Prefer this over manual gmail_search when the user wants an overview." |
| All other tools | Return `None` — no guidance |

**Problems:**
- Only 7 of 30+ tools provide guidance. The other 23 are invisible in the prompt.
- Gmail guidance says "use gmail_digest" but the session_open bootstrap doesn't mention digest specifically — agent has to figure out which email tool to use
- Task guidance says "check get_tasks at conversation start" which duplicates the Soul section's step 1
- Memory guidance says "use recall before answering" but Soul section says "call read_memory" (wrong tool name)

---

### 8. Interaction Learning (`## Interaction Learning`)

**Source:** `INTERACTION_LEARNING_GUIDANCE` constant in `prompt_builder.py:82-89`
**Shown:** Only on `web` and `telegram` channels
**Value:**
```
Learn from every interaction:
- Notice communication patterns (terse replies = wants concise responses).
- Infer preferences from behavior, don't wait to be told.
- After every few exchanges, call store_memory to record observations.
  Use memory_type 'core_identity' for user facts, 'episodic' for events/decisions.
- Use recall before answering questions about the user's preferences or history.
```

**Problems:** None major. Good guidance, appropriately scoped.

---

### 9. Session Open / Onboarding (`## Session Open` or `## Onboarding`)

**Source:** Constants in `prompt_builder.py:38-80`
**Logic:** `is_new_user = not memory_notes and not user_instructions`

**Bootstrap (new user, channel=session_open):**
```
This is the very first time you are meeting this user.
No one typed anything yet — you are initiating.

Your job is to SHOW usefulness, not ASK about it.

Steps:
1. Use your tools to learn what you can — check emails, tasks, reminders.
   Do this BEFORE writing your greeting.
2. Introduce yourself in one sentence.
3. Share what you found: 'You have X emails, Y tasks, Z reminders.'
   If tools are empty or not connected, say so plainly.
4. Based on what you found, suggest ONE concrete next step.
5. Call store_memory to record initial observations about their setup.

Do NOT ask about communication preferences or priorities.
Learn those from how they respond to you.
```

**Returning user (channel=session_open):**
```
The user just returned to the app. {time_context}
No one typed anything yet — you are deciding whether to initiate.

Decision rules:
- If the user was here less than 5 minutes ago AND nothing new is in flight: respond with exactly: WAKEUP_SILENT
- Otherwise: check your tools (tasks, reminders, optionally emails), then greet with a brief summary of what needs attention.

If you greet: 2-4 sentences max. State facts, don't ask questions.
```

**Onboarding (new user, channel=web/telegram — not session_open):**
```
[Same as bootstrap but slightly different wording]
```

**Problems:**
- Bootstrap tells agent to "check emails, tasks, reminders" but doesn't say WHICH tools. Agent has `email_digest`, `gmail_search`, `gmail_digest`, `gmail_get_message` for email alone — has to guess.
- Bootstrap says "suggest ONE concrete next step" but for a new user with no tasks/emails connected, the only sensible step is onboarding setup (connect Gmail, set preferences) — which the agent has no guidance on how to facilitate.
- The bootstrap is purely about showing tool results — there's no structured onboarding flow. No attempt to understand what kind of user this is, what their needs are, or what workflow they want.
- `ONBOARDING_SECTION` is nearly identical to `SESSION_OPEN_BOOTSTRAP_GUIDANCE` — redundant.

---

## Part 2: Tool Sources & Descriptions

Tools have **THREE** description sources that may conflict:

### Source A: Python class `description` attribute
Set in `chatServer/tools/*.py` as a class field on each `BaseTool` subclass.

### Source B: Database `tools.description` column
Set by SQL migrations in `supabase/migrations/`.

### Source C: Database `tools.config` JSONB (for CRUDTool/GmailTool types)
Contains `runtime_args_schema` with field-level descriptions.

**The agent sees Source B** (from DB), because `load_tools_from_db()` passes `description=db_tool_description` to the tool constructor, which overrides Source A.

### Complete Tool Inventory

| # | Tool Name | Python Class | DB Type | Source A (Python) | Source B (DB migration) | Match? | Active? |
|---|-----------|-------------|---------|-------------------|------------------------|--------|---------|
| 1 | `get_tasks` | `GetTasksTool` | `GetTasksTool` | "List the user's tasks. By default shows top-level pending/in-progress tasks." | Set in `20260220000000` | ✅ Same | ✅ |
| 2 | `get_task` | `GetTaskTool` | `GetTaskTool` | "Get detailed information about a specific task by its ID, including all subtasks." | Set in `20260220000000` | ✅ Same | ✅ |
| 3 | `create_task` | `CreateTaskTool` | `CreateTaskTool` | "Create a new task for the user. Set parent_task_id to create a subtask." | Set in `20260220000000` | ✅ Same | ✅ |
| 4 | `update_task` | `UpdateTaskTool` | `UpdateTaskTool` | "Update a task's fields. Only provided fields are changed." | Set in `20260220000000` | ✅ Same | ✅ |
| 5 | `delete_task` | `DeleteTaskTool` | `DeleteTaskTool` | "Delete a task and all its subtasks." | Set in `20260220000000` | ✅ Same | ✅ |
| 6 | `create_reminder` | `CreateReminderTool` | `CreateReminderTool` | "Create a reminder that will notify the user at a specified time." | Set in `20260218000001` | ✅ Same | ✅ |
| 7 | `list_reminders` | `ListRemindersTool` | `ListRemindersTool` | "List the user's upcoming reminders." | Set in `20260218000001` | ✅ Same | ✅ |
| 8 | `create_schedule` | `CreateScheduleTool` | `CreateScheduleTool` | "Create a recurring schedule that runs an agent with a given prompt." | Set in `20260219000000` | ✅ Same | ✅ |
| 9 | `delete_schedule` | `DeleteScheduleTool` | `DeleteScheduleTool` | "Delete a recurring schedule by its ID." | Set in `20260219000000` | ✅ Same | ✅ |
| 10 | `list_schedules` | `ListSchedulesTool` | `ListSchedulesTool` | "List the user's recurring agent schedules." | Set in `20260219000000` | ✅ Same | ✅ |
| 11 | `update_instructions` | `UpdateInstructionsTool` | `UpdateInstructionsTool` | "Update your standing instructions for this user." | Set in `20260219000002` | ✅ Same | ✅ |
| 12 | `gmail_search` | `GmailSearchTool` | `GmailTool` | "Search Gmail messages using Gmail search syntax." | Set in `20260216000001` | ⚠️ DB has shorter version | ✅ |
| 13 | `gmail_get_message` | `GmailGetMessageTool` | `GmailTool` | "Get detailed Gmail message content by ID." | Set in `20260216000001` | ⚠️ DB lacks `account` param mention | ✅ |
| 14 | `gmail_digest` | `GmailDigestTool` | `GmailTool` | "Generate a digest of recent emails from Gmail." | Set in `20260216000001` | ⚠️ DB version shorter | ✅ |
| 15 | `email_digest` | `EmailDigestTool` | `EmailDigestTool` | "Generate a digest of recent emails from Gmail." | **Unknown** — no migration registers this tool! | ❓ | ✅ (in trace) |
| 16 | `store_memory` | `StoreMemoryTool` | `StoreMemoryTool` | "Store a memory. Use proactively..." | Set in `20260223000002` | ✅ Same | ✅ |
| 17 | `recall` | `RecallMemoryTool` | `RecallMemoryTool` | "Recall memories relevant to a query." | Set in `20260223000002` | ✅ Same | ✅ |
| 18 | `search_memory` | `SearchMemoryTool` | `SearchMemoryTool` | "Search for memories matching a query." | Set in `20260223000002` | ✅ Same | ✅ |
| 19 | `fetch_memory` | `FetchMemoryTool` | `FetchMemoryTool` | "Fetch a specific memory by its ID." | Set in `20260223000002` | ✅ Same | ✅ |
| 20 | `delete_memory` | `DeleteMemoryTool` | `DeleteMemoryTool` | "Delete a memory." | Set in `20260223000002` | ✅ Same | ✅ |
| 21 | `update_memory` | `UpdateMemoryTool` | `UpdateMemoryTool` | "Update an existing memory's text and/or metadata." | Set in `20260223000002` | ✅ Same | ✅ |
| 22 | `set_project` | `SetProjectTool` | `SetProjectTool` | "Validate a project exists in memory or create it." | Set in `20260223000002` | ✅ Same | ✅ |
| 23 | `link_memories` | `LinkMemoriesTool` | `LinkMemoriesTool` | "Link two memories with a relationship." | Set in `20260223000002` | ✅ Same | ✅ |
| 24 | `list_entities` | `ListEntitiesTool` | `ListEntitiesTool` | "List all entities in memory." | Set in `20260223000002` | ✅ Same | ✅ |
| 25 | `search_entities` | `SearchEntitiesTool` | `SearchEntitiesTool` | "Search for entities by name." | Set in `20260223000002` | ✅ Same | ✅ |
| 26 | `get_context_info` | `GetContextInfoTool` | `GetContextInfoTool` | "Get environment context." | Set in `20260223000002` | ✅ Same | ✅ |

### Ghost Tools (visible in trace but shouldn't be)

These appeared in the LangSmith trace tool list but are **legacy CRUDTool entries** from the original schema:

| Tool Name | Origin | Status | Problem |
|-----------|--------|--------|---------|
| `delete_agent_long_term_memory` | Original CRUDTool migration | **Still active in DB** | Never deactivated. SPEC-018 only deactivated `save_memory`/`read_memory`. |
| `fetch_agent_long_term_memory` | Original CRUDTool migration | **Still active in DB** | Same. |
| `fetch_tasks` | Original CRUDTool migration | **Still active in DB** | Redundant with `get_tasks` (GetTasksTool). |

These are loaded because the `tools` table still has them as `is_active=true` and they're linked to the assistant agent via `agent_tools`.

### Tool Description Conflict Points

1. **`email_digest` vs `gmail_digest`**: Two separate tools that do similar things. `email_digest` uses `EmailDigestService` (a higher-level wrapper), `gmail_digest` is a direct Gmail API tool. Both show up in the agent's tool list. Agent must choose between them with no clear guidance on when to use which (aside from the `prompt_section` hint).

2. **Gmail tool descriptions diverge**: Python classes have richer descriptions (mention `account` parameter for multi-account) but DB descriptions from `20260216000001` are older and less detailed. Since DB wins, the agent sees the older, less helpful descriptions.

3. **Memory tool descriptions are consistent**: Python and DB match because SPEC-018 registered them with the Python descriptions.

4. **`read_memory` (old) referenced in Soul but tool doesn't exist**: Soul text says "Call read_memory" but the tool is `recall`. Agent will fail to find it or hallucinate the call.

---

## Part 3: Key Issues Summary

### Critical
1. **Soul references non-existent `read_memory` tool** — agent gets confused
2. **Ghost tools still active** (`delete_agent_long_term_memory`, `fetch_agent_long_term_memory`, `fetch_tasks`) — pollute tool list
3. **Soul contains `##` headers** that conflict with prompt builder's section headers — flat hierarchy confusion

### Important
4. **`email_digest` tool has no DB registration migration** — may have been manually inserted
5. **`email_digest` vs `gmail_digest` overlap** — two tools for the same job, no clear delineation
6. **Gmail DB descriptions are stale** — don't mention multi-account `account` parameter
7. **Bootstrap has no structured onboarding flow** — just "show tool results" with no way to understand the user
8. **Soul does double duty** — philosophical identity AND operational instructions in one field
9. **No prompt versioning** — soul was hand-edited in DB, no migration trail

### Nice to Fix
10. **Identity vibe rendering is awkward** — "direct and helpful" appended after period
11. **Timezone always UTC** — no detection mechanism
12. **23 of 30 tools have no prompt guidance** — only 7 implement `prompt_section()`
13. **Duplicate guidance** — Soul's "call get_tasks first" duplicates Tool Guidance's "check get_tasks at conversation start"

---

## Part 4: Architecture Observations

### The Description Priority Chain
```
DB tools.description → load_tools_from_db() passes as kwarg → tool.__init__ sets self.description
                       ↓
                       This is what the LLM sees in tool binding
```

Python class `description` is a default that gets overwritten if DB provides one. This means:
- To change what the LLM sees, you MUST update the DB (migration or direct edit)
- Python class changes alone won't take effect for DB-registered tools
- This is intentional (DB is source of truth) but creates a maintenance trap when devs update Python and forget the DB

### The prompt_section() Pattern
Tool guidance is assembled from `tool_cls.prompt_section(channel)`. This is purely code-driven (not DB). To add guidance for a tool, you edit the Python class. This is separate from the tool description and is a good pattern — but only 7/30 tools use it.

### The Soul vs. Prompt Builder Tension
The `soul` column was designed as behavioral philosophy, but in practice it contains operational instructions ("Call get_tasks", "Call read_memory"). These overlap with:
- Tool Guidance section (which also says "check get_tasks")
- Session Open section (which also says "use tools before greeting")
- Interaction Learning section (which also says "store_memory")

The result: the same instruction appears 2-3 times in different sections, sometimes with conflicting tool names.
