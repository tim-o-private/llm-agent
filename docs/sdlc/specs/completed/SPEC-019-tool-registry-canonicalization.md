# SPEC-019: Tool Registry Canonicalization & Prompt Simplification

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-24
> **Branch:** `feat/spec-019-tool-registry`

## Goal

Establish a single canonical state for all tool registrations, enforce a standard verb vocabulary (`get_`, `create_`, `update_`, `delete_`, `search_`), remove dead tools, move the full prompt template into `agent_configurations` for no-deploy iteration, and add a CI test that blocks deployment when code and DB are out of sync.

## Background

Over months of incremental work, the agent's tool descriptions (DB), prompt sections (Python), and DB registrations have drifted apart:

- **Ghost tools** from deprecated CRUDTool patterns still exist in the `tools` table (`delete_agent_long_term_memory`, `fetch_agent_long_term_memory`, `fetch_tasks`, `save_memory`, `read_memory`)
- **Two email digest tools** (`email_digest`, `gmail_digest`) both do the wrong thing — the agent should use `search_gmail` and reason about results instead of getting pre-formatted summaries
- **The soul column** references a tool (`read_memory`) that no longer exists
- **No validation** that code-defined tools have DB registrations — new tools can ship without descriptions and silently default to `REQUIRES_APPROVAL`
- **Tool verb explosion** — `get_tasks` vs `get_task` vs `list_reminders` vs `list_schedules` vs `gmail_search` — inconsistent verbs and `verb_resource` order for the same operations
- **Prompt is assembled in Python** — changing section order, wording, or structure requires a code deploy. The soul is already in DB; the full template should be too.

## Acceptance Criteria

### Tool Verb Consolidation

- [ ] **AC-01:** Tasks consolidated from 5 tools to 4: `get_tasks` (replaces `get_tasks` + `get_task` — filter by `id` for single), `create_tasks` (accepts a list), `update_tasks` (accepts a list), `delete_tasks` (accepts a list of IDs — backend enforces soft-delete). [A10, A14]
- [ ] **AC-02:** Reminders consolidated from 2 tools to 3: `get_reminders` (replaces `list_reminders`), `create_reminders`, `delete_reminders`. [A10]
- [ ] **AC-03:** Schedules consolidated from 3 tools to 3: `get_schedules` (replaces `list_schedules`), `create_schedules`, `delete_schedules`. [A10]
- [ ] **AC-04:** Memory tools renamed to standard vocab: `create_memories` (was `store_memory`), `search_memories` (merges `recall` + `search_memory`), `get_memories` (was `fetch_memory`), `update_memories` (was `update_memory`), `delete_memories` (was `delete_memory`). Plural names, single-item I/O (min-memory API is single-item). [A10]
- [ ] **AC-05:** Memory utility tools renamed: `get_entities` (was `list_entities`), `search_entities` (unchanged), `get_context` (was `get_context_info`), `set_project` (unchanged), `link_memories` (unchanged). [A10]
- [ ] **AC-06:** Gmail tools renamed to `verb_resource` order: `search_gmail` (was `gmail_search`), `get_gmail` (was `gmail_get_message`). [A10]
- [ ] **AC-07:** `update_instructions` keeps current name — singular resource, not a collection. [A14]
- [ ] **AC-08:** All delete operations are soft-deletes enforced by the backend. The agent never sees `is_deleted`. [A12]

### Ghost Tool Cleanup

- [ ] **AC-09:** Ghost tools deactivated in `tools` table: `delete_agent_long_term_memory`, `fetch_agent_long_term_memory`, `fetch_tasks`, `save_memory`, `read_memory`. Their `agent_tools` links also deactivated. [A6]
- [ ] **AC-10:** Both digest tools deactivated: `email_digest`, `gmail_digest`. Their `agent_tools` links also deactivated. [A6]
- [ ] **AC-11:** `EmailDigestTool` Python class deleted. `GmailDigestTool` Python class deleted. Imports removed from `agent_loader_db.py`. [A6]
- [ ] **AC-12:** `email_digest` and `gmail_digest` entries removed from `approval_tiers.py`. Legacy entries (`save_memory`, `read_memory`, `memory_store`, `memory_search`, `memory_delete`) also removed. [A12]

### Email Digest Scheduler Flag

- [ ] **AC-13:** The `is_email_digest` code path in `background_tasks.py` is flagged with a `# TODO: SPEC-020` comment and a log warning. Not removed in this spec (needs its own investigation). [A14]

### Soul & Prompt Template

- [ ] **AC-14:** `agent_configurations.soul` for the assistant agent updated to behavioral philosophy only — no `##` headers, no tool references, no operational instructions. [A2]
- [ ] **AC-15:** New `prompt_template` TEXT column added to `agent_configurations`. Contains the full prompt template with `{placeholder}` format strings. One agent = one prompt template. No separate table. [A2]
- [ ] **AC-16:** `build_agent_prompt()` reads the template from the agent config (already loaded by agent_loader_db) and performs string substitution. Falls back to current hardcoded assembly if template is NULL/empty. [A2, A14]
- [ ] **AC-17:** An `operating_model` placeholder replaces the operational instructions currently jammed into soul. Only rendered for interactive channels (`web`, `telegram`) and `session_open`. Scheduled/heartbeat get empty string for this placeholder. [A2]

### CI Validation

- [ ] **AC-18:** `tests/chatServer/test_tool_registry_sync.py` — a pytest that imports `TOOL_REGISTRY` and checks against a hardcoded fixture of expected active tools to verify: (a) every expected tool has a matching TOOL_REGISTRY entry, (b) every TOOL_REGISTRY entry has a matching expected tool, (c) every active tool has an explicit approval tier (not falling through to `DEFAULT_UNKNOWN_TIER`). [S1, S3]

### Tests

- [ ] **AC-19:** Unit tests for consolidated tool classes (`get_tasks` with id filter, `create_tasks` with list input, `update_tasks` with list input, `delete_tasks` with list of IDs). [S1]
- [ ] **AC-20:** Unit tests for `build_agent_prompt()` using DB template path — template from agent config, placeholders substituted, fallback works when no template exists. [S1]
- [ ] **AC-21:** Existing prompt builder tests updated to pass with new soul content and operating model section. [S1]

## Verb Vocabulary

Standard verbs for all tools (per A10). Format is always `verb_resource`:

| Verb | Semantics | Example |
|------|-----------|---------|
| `get_` | Read one or many. Filter by `id` for single. | `get_tasks`, `get_reminders`, `get_gmail` |
| `create_` | Create one or many. Input is always a list. | `create_tasks`, `create_memories` |
| `update_` | Update one or many. Input is always a list of `{id, ...fields}`. | `update_tasks`, `update_memories` |
| `delete_` | Soft-delete one or many. Input is a list of IDs. Backend sets `is_deleted`. | `delete_tasks`, `delete_memories` |
| `search_` | Search/query with flexible criteria. | `search_gmail`, `search_memories`, `search_entities` |
| `set_` | Set a configuration value. | `set_project` |
| `link_` | Create a relationship between entities. | `link_memories` |

## Active Tools After Migration

| # | Tool name | Python class | Verb |
|---|-----------|-------------|------|
| 1 | `get_tasks` | GetTasksTool | get |
| 2 | `create_tasks` | CreateTasksTool | create |
| 3 | `update_tasks` | UpdateTasksTool | update |
| 4 | `delete_tasks` | DeleteTasksTool | delete |
| 5 | `get_reminders` | GetRemindersTool | get |
| 6 | `create_reminders` | CreateRemindersTool | create |
| 7 | `delete_reminders` | DeleteRemindersTool | delete |
| 8 | `get_schedules` | GetSchedulesTool | get |
| 9 | `create_schedules` | CreateSchedulesTool | create |
| 10 | `delete_schedules` | DeleteSchedulesTool | delete |
| 11 | `update_instructions` | UpdateInstructionsTool | update |
| 12 | `search_gmail` | SearchGmailTool | search |
| 13 | `get_gmail` | GetGmailTool | get |
| 14 | `create_memories` | CreateMemoriesTool | create |
| 15 | `search_memories` | SearchMemoriesTool | search |
| 16 | `get_memories` | GetMemoriesTool | get |
| 17 | `update_memories` | UpdateMemoriesTool | update |
| 18 | `delete_memories` | DeleteMemoriesTool | delete |
| 19 | `set_project` | SetProjectTool | set |
| 20 | `link_memories` | LinkMemoriesTool | link |
| 21 | `get_entities` | GetEntitiesTool | get |
| 22 | `search_entities` | SearchEntitiesTool | search |
| 23 | `get_context` | GetContextTool | get |

**Deactivated:** `email_digest`, `gmail_digest`, `gmail_search`, `gmail_get_message`, `delete_agent_long_term_memory`, `fetch_agent_long_term_memory`, `fetch_tasks`, `save_memory`, `read_memory`, `get_task`, `delete_task`, `create_task`, `update_task`, `list_reminders`, `create_reminder`, `list_schedules`, `create_schedule`, `delete_schedule`, `store_memory`, `recall`, `search_memory`, `fetch_memory`, `delete_memory`, `update_memory`, `list_entities`, `get_context_info`

## Soul (New Content)

```
You manage things so the user doesn't have to hold it all in their head.

Be direct and practical. Skip pleasantries when the user is clearly in work mode. Match their energy — brief for brief, thoughtful for thoughtful.

Have opinions about priorities when asked. "Everything is important" is never useful.

When you learn something about the user — preferences, context, how they like things — save it to memory without being asked. You should know more about them with each conversation.

Don't narrate your tool calls or explain what you're about to do. Just do it.
```

## Operating Model (New — rendered into `{operating_model}` placeholder)

```
Every conversation starts with awareness. Before responding:
1. Check tasks (get_tasks) for what's active, overdue, or due today.
2. Search your memories about this person (search_memories).
3. Respond informed by what you found — don't announce that you did this.

When the user mentions something they need to do — create a task. Don't ask permission. If they don't want it, they'll say so. Break vague goals into concrete next steps.

When you have Gmail access, scan for actionable items — things that need replies, deadlines mentioned, commitments made. Turn these into tasks when appropriate.

When the user says they finished something, mark it complete. The task list should always reflect reality.
```

## Prompt Template Design

### Column: `agent_configurations.prompt_template`

New TEXT column on the existing `agent_configurations` table. One agent = one prompt. No separate table needed.

```sql
ALTER TABLE agent_configurations ADD COLUMN prompt_template TEXT;
```

The template contains the full prompt with `{placeholder}` format strings. The `build_agent_prompt()` function reads it from the agent config dict (already loaded) and substitutes values.

### Placeholders

| Placeholder | Source | Always present |
|-------------|--------|----------------|
| `{identity}` | `agent_configurations.identity` → formatted string | Yes (fallback: empty) |
| `{soul}` | `agent_configurations.soul` | Yes |
| `{channel_guidance}` | `CHANNEL_GUIDANCE[channel]` constant | Yes |
| `{current_time}` | Computed at render time | Yes |
| `{memory_notes}` | Pre-fetched from min-memory | No (empty if none) |
| `{user_instructions}` | `user_agent_prompt_customizations` | Yes (fallback text if none) |
| `{tool_guidance}` | Aggregated from `tool.prompt_section()` | No (empty if none) |
| `{interaction_learning}` | Static guidance text | Channel-dependent |
| `{operating_model}` | Static guidance text | Channel-dependent |
| `{session_section}` | Session open / onboarding logic | Channel-dependent |

### Rendering Logic

```python
def build_agent_prompt(prompt_template: str | None = None, ...) -> str:
    if not prompt_template:
        return _build_hardcoded_prompt(...)  # existing logic, unchanged

    values = {
        "identity": _format_identity(identity),
        "soul": soul or "You are a helpful assistant.",
        "channel_guidance": CHANNEL_GUIDANCE.get(channel, CHANNEL_GUIDANCE["web"]),
        "current_time": _get_current_time(timezone),
        "memory_notes": _format_memory_notes(memory_notes),
        "user_instructions": _format_instructions(user_instructions),
        "tool_guidance": _format_tool_guidance(tools, channel),
        "interaction_learning": INTERACTION_LEARNING if channel in ("web", "telegram") else "",
        "operating_model": OPERATING_MODEL if channel in ("web", "telegram", "session_open") else "",
        "session_section": _format_session_section(channel, memory_notes, user_instructions, last_message_at),
    }
    return string.Template(prompt_template).safe_substitute(values)
```

Note: Uses `string.Template` with `$placeholder` syntax (not `str.format`) to avoid conflicts with `{` and `}` in template content. Template uses `$identity`, `$soul`, etc.

## Functional Units

### FU-1: Consolidate task tools (Python)

**Files:**
- `chatServer/tools/task_tools.py` — rewrite to 4 classes: `GetTasksTool`, `CreateTasksTool`, `UpdateTasksTool`, `DeleteTasksTool`
- `chatServer/services/task_service.py` — update service methods for list inputs; add soft-delete method
- `src/core/agent_loader_db.py` — update `TOOL_REGISTRY` (remove old, add new)
- `chatServer/security/approval_tiers.py` — update entries

**Key changes:**
- `GetTasksTool`: add optional `id` filter param. When `id` provided, return single task detail (what `get_task` did). Remove `GetTaskTool` class.
- `CreateTasksTool`: accept `tasks: list[dict]` input. Each dict has title, description, priority, etc. Return list of created task confirmations. Single task = list with one item.
- `UpdateTasksTool`: accept `tasks: list[dict]` input. Each dict has `id` + fields to update. Does NOT handle deletes.
- `DeleteTasksTool`: accept `ids: list[str]` input. Backend sets `is_deleted = true`. Agent never sees `is_deleted` field.

### FU-2: Consolidate reminder tools (Python)

**Files:**
- `chatServer/tools/reminder_tools.py` — rewrite to 3 classes: `GetRemindersTool`, `CreateRemindersTool`, `DeleteRemindersTool`
- `chatServer/services/reminder_service.py` — add delete method (soft-delete)
- `src/core/agent_loader_db.py` — update `TOOL_REGISTRY`
- `chatServer/security/approval_tiers.py` — update entries

### FU-3: Consolidate schedule tools (Python)

**Files:**
- `chatServer/tools/schedule_tools.py` — rewrite to 3 classes: `GetSchedulesTool`, `CreateSchedulesTool`, `DeleteSchedulesTool`
- `src/core/agent_loader_db.py` — update `TOOL_REGISTRY`
- `chatServer/security/approval_tiers.py` — update entries

### FU-4: Rename memory tools (Python)

**Files:**
- `chatServer/tools/memory_tools.py` — rename classes and tool names:
  - `StoreMemoryTool` → `CreateMemoriesTool` (name: `create_memories`)
  - `RecallMemoryTool` + `SearchMemoryTool` → `SearchMemoriesTool` (name: `search_memories`, merges both)
  - `FetchMemoryTool` → `GetMemoriesTool` (name: `get_memories`)
  - `UpdateMemoryTool` → `UpdateMemoriesTool` (name: `update_memories`)
  - `DeleteMemoryTool` → `DeleteMemoriesTool` (name: `delete_memories`)
  - `ListEntitiesTool` → `GetEntitiesTool` (name: `get_entities`)
  - `GetContextInfoTool` → `GetContextTool` (name: `get_context`)
  - `SetProjectTool`, `LinkMemoriesTool`, `SearchEntitiesTool` — name unchanged
- `src/core/agent_loader_db.py` — update `TOOL_REGISTRY`
- `chatServer/security/approval_tiers.py` — update entries

### FU-5: Rename Gmail tools (Python)

**Files:**
- `chatServer/tools/gmail_tools.py` — rename:
  - `GmailSearchTool` → `SearchGmailTool` (name: `search_gmail`)
  - `GmailGetMessageTool` → `GetGmailTool` (name: `get_gmail`)
  - Remove `GmailDigestTool` class and `GmailDigestInput`
- `src/core/agent_loader_db.py` — update registries, remove `GmailDigestTool`
- `chatServer/security/approval_tiers.py` — update entries

### FU-6: Remove digest tools + cleanup

**Files:**
- `chatServer/tools/email_digest_tool.py` — **DELETE**
- `src/core/agent_loader_db.py` — remove `EmailDigestTool` from imports and registries
- `chatServer/security/approval_tiers.py` — remove digest + legacy entries
- `chatServer/services/background_tasks.py` — add `# TODO: SPEC-020` and log warning on `is_email_digest` path

**Keep:** `chatServer/services/email_digest_service.py` — used by scheduler independently.

### FU-7: Canonical migration

**File:** `supabase/migrations/20260224000001_canonicalize_tool_registry.sql`

One migration that:
1. Deactivates ghost tools and digest tools (tools + agent_tools)
2. Deactivates old tool names being replaced by renamed/consolidated versions
3. Upserts new tool names with correct types and descriptions
4. Links new tools to agents that had corresponding old tools
5. Updates assistant soul to behavioral philosophy only
6. Adds `prompt_template` column to `agent_configurations`
7. Seeds the assistant agent's `prompt_template` with the default template

### FU-8: Prompt template rendering

**Files:**
- `chatServer/services/prompt_builder.py` — add template rendering path using `string.Template`. Existing hardcoded logic becomes the fallback when `prompt_template` is NULL.
- `src/core/agent_loader_db.py` — pass `prompt_template` from agent config to `build_agent_prompt()`

### FU-9: CI validation test

**File:** `tests/chatServer/test_tool_registry_sync.py`

Pytest that:
- Imports `TOOL_REGISTRY` from `agent_loader_db.py`
- Checks against a hardcoded fixture of the 23 expected active tools
- Checks bidirectional sync: fixture → code and code → fixture
- Checks approval tier coverage for every tool in the fixture

### FU-10: Update tests

**Files:**
- `tests/chatServer/services/test_prompt_builder.py` — update for template system + new soul
- `tests/core/test_agent_loader_db.py` — update for removed/renamed tools
- New test files for consolidated tool classes

## Files Changed (Summary)

| File | Change |
|------|--------|
| `supabase/migrations/20260224000001_canonicalize_tool_registry.sql` | **NEW** — tool consolidation, ghost cleanup, soul update, prompt_template column + seed |
| `chatServer/tools/task_tools.py` | Consolidate to 4 tools (get, create, update, delete) |
| `chatServer/tools/reminder_tools.py` | Consolidate to 3 tools (get, create, delete) |
| `chatServer/tools/schedule_tools.py` | Consolidate to 3 tools (get, create, delete) |
| `chatServer/tools/memory_tools.py` | Rename all tools to standard vocab |
| `chatServer/tools/gmail_tools.py` | Rename to verb_resource order, remove GmailDigestTool |
| `chatServer/tools/email_digest_tool.py` | **DELETE** |
| `chatServer/services/prompt_builder.py` | Add template rendering path |
| `chatServer/services/task_service.py` | Update for list inputs + soft-delete |
| `chatServer/services/reminder_service.py` | Add delete method |
| `chatServer/services/background_tasks.py` | Flag digest scheduler |
| `chatServer/main.py` | No changes (template comes from agent config, already cached) |
| `src/core/agent_loader_db.py` | Update all registries, pass prompt_template |
| `chatServer/security/approval_tiers.py` | Update all entries |
| `tests/chatServer/test_tool_registry_sync.py` | **NEW** — CI validation |
| `tests/chatServer/services/test_prompt_builder.py` | Update for template system |
| `tests/core/test_agent_loader_db.py` | Update for removed/renamed tools |

## UAT Plan

### Pre-requisites
1. Apply migration to local Supabase
2. Restart chatServer (`pnpm dev`) to clear executor cache

### Test 1: Tool list is clean
**Method:** Send any message via clarity-dev MCP, check LangSmith trace.
**Expected:**
- Tool list contains exactly the 23 tools from the "Active Tools After Migration" table
- No ghost tools, no old names
- All tool names follow `verb_resource` pattern

### Test 2: Consolidated task tools work
**Method:** Via clarity-dev MCP:
- "Create a task to buy groceries and another to call the dentist" → agent calls `create_tasks` with a list of 2
- "Show me my tasks" → agent calls `get_tasks`
- "Show me details on task {id}" → agent calls `get_tasks` with `id` filter
- "Mark the groceries task as done" → agent calls `update_tasks`
- "Delete the dentist task" → agent calls `delete_tasks`

### Test 3: Consolidated reminder tools work
**Method:** Via clarity-dev MCP:
- "Remind me to take medicine at 3pm tomorrow" → agent calls `create_reminders`
- "Show my reminders" → agent calls `get_reminders`
- "Cancel that reminder" → agent calls `delete_reminders`

### Test 4: Consolidated schedule tools work
**Method:** Via clarity-dev MCP:
- "Set up a daily 9am email summary" → agent calls `create_schedules`
- "Show my schedules" → agent calls `get_schedules`
- "Delete that schedule" → agent calls `delete_schedules`

### Test 5: Memory tools work with new names
**Method:** Via clarity-dev MCP:
- "Remember that I prefer dark roast coffee" → agent calls `create_memories`
- "What do you know about my coffee preferences?" → agent calls `search_memories`
- "Forget the coffee preference" → agent calls `delete_memories`

### Test 6: Gmail tools work with new names
**Method:** Via clarity-dev MCP:
- "Check my email" → agent calls `search_gmail`

### Test 7: Soul is slim
**Method:** Check LangSmith trace system prompt.
**Expected:**
- Soul section has no `##` headers
- Soul section does not mention `read_memory` or any specific tool name
- Soul is ~5 sentences of behavioral philosophy

### Test 8: Operating model present on interactive channels
**Method:** Compare LangSmith traces for web vs scheduled.
**Expected:**
- Web/telegram: operating model section present with "Check tasks" / "Search memories" instructions
- Scheduled/heartbeat: no operating model section

### Test 9: Prompt template from DB
**Method:** Update `agent_configurations.prompt_template` in Supabase dashboard (e.g., swap section order). Restart server (to clear config cache). Check prompt in trace.
**Expected:** Prompt reflects the DB template, not hardcoded Python.

### Test 10: CI test passes
**Method:** `pytest tests/chatServer/test_tool_registry_sync.py -v`
**Expected:** All checks pass — every tool in sync, every tier covered.

## Dependencies

- SPEC-018 (Proactive Memory) — completed, provides min-memory tools
- SPEC-017 (User-Scoped DB) — completed, provides scoped client pattern

## Out of Scope

- Dropping `agent_long_term_memory` table
- Removing `email_digest_service.py` or the scheduler code path (SPEC-020)
- Frontend changes (task UI still works — it calls REST API, not tools)
- CRUDTool pattern removal (no active CRUDTools remain, but the code stays)
- Adding new tools (e.g., `gmail_send_message`)
- List-based I/O for memory tools (min-memory API is single-item; we use plural names for consistency but accept single items)

## Risks

1. **Agent behavior change**: every tool name changes. Existing conversation history has different tool names. Agent executor cache must be cleared (server restart). No impact on stored chat history — LangChain doesn't replay tool names from history.
2. **Scheduled executions**: the `is_email_digest` path in background_tasks.py still references `EmailDigestService`. We're flagging it, not removing it.
3. **Prompt template rendering**: `string.Template` uses `$placeholder` syntax which avoids `{`/`}` conflicts in template content. Template content can freely use curly braces.
4. **Memory tool merge**: `recall` (hierarchical context) and `search_memory` (vector search) merge into `search_memories`. The merged tool should expose the superset of parameters from both, defaulting to the richer `recall` behavior (hierarchical scoping).
