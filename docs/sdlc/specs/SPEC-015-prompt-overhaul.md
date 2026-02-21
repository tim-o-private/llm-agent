# SPEC-015: Prompt Overhaul — Tool Guidance, Pre-loaded Memory, Channel-Aware Assembly

> **Status:** Ready
> **Author:** spec-writer
> **Created:** 2026-02-20
> **Updated:** 2026-02-20

## Goal

Transform the rigid, template-style prompt builder into a composable system where tools contribute contextual guidance, memory is pre-loaded instead of fetched on first turn, and channel context is rich enough to drive meaningfully different agent behavior across web, Telegram, scheduled, and heartbeat channels. This directly addresses the agent's failure to proactively use its tools — the prompt currently lists tool names but never explains *how* or *when* to use them well.

## Acceptance Criteria

- [ ] **AC-01:** Every tool class in `chatServer/tools/` has a `prompt_section(channel: str) -> str | None` classmethod that returns channel-appropriate behavioral guidance or `None`. [A6, A14]
- [ ] **AC-02:** `build_agent_prompt()` collects prompt sections from instantiated tool objects and assembles them into a `## Tool Guidance` section, replacing the current flat tool-name listing. [A6, F1]
- [ ] **AC-03:** `build_agent_prompt()` accepts `tools` (list of instantiated tool objects) instead of `tool_names` (list of strings). Both sync and async agent loader paths pass instantiated tools. [A6]
- [ ] **AC-04:** When `memory_notes` is non-empty, `build_agent_prompt()` injects the notes into a `## What You Know` section so the agent starts conversations already informed. [A14]
- [ ] **AC-05:** The static `MEMORY_SECTION` constant is removed. Memory tool behavioral guidance moves to `SaveMemoryTool.prompt_section()` and `ReadMemoryTool.prompt_section()`. [A6]
- [ ] **AC-06:** `CHANNEL_GUIDANCE` for `heartbeat` and `scheduled` channels includes rich behavioral context: what to check, when to suppress, how to report. [A7]
- [ ] **AC-07:** Tool `prompt_section()` returns channel-specific guidance (e.g., Gmail guidance differs between `web` and `heartbeat`). [A7]
- [ ] **AC-08:** Onboarding detection still works: when both `memory_notes` and `user_instructions` are empty on interactive channels, the onboarding section is injected. [A14]
- [ ] **AC-09:** All changes have unit tests with at least one test per AC. [S1]
- [ ] **AC-10:** The assembled prompt does not exceed reasonable size — tool guidance sections are concise (under 200 chars each for non-heartbeat channels). [A14]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `tests/chatServer/services/test_prompt_builder.py` | Unit tests for prompt builder changes (AC-02, AC-04, AC-05, AC-06, AC-08, AC-10) |
| `tests/chatServer/tools/test_tool_prompt_sections.py` | Unit tests for each tool's `prompt_section()` (AC-01, AC-07) |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/prompt_builder.py` | Replace `tool_names` param with `tools` list; collect `prompt_section()` into `## Tool Guidance`; inject `## What You Know` from memory_notes; remove `MEMORY_SECTION` constant; expand `CHANNEL_GUIDANCE`; keep `ONBOARDING_SECTION` |
| `chatServer/tools/task_tools.py` | Add `prompt_section(channel)` classmethod to one representative tool class (e.g., `GetTasksTool`) |
| `chatServer/tools/memory_tools.py` | Add `prompt_section(channel)` classmethods to `SaveMemoryTool` and `ReadMemoryTool`; absorb the behavioral guidance from the removed `MEMORY_SECTION` |
| `chatServer/tools/gmail_tools.py` | Add `prompt_section(channel)` classmethod to one representative Gmail tool (e.g., `BaseGmailTool`) |
| `chatServer/tools/reminder_tools.py` | Add `prompt_section(channel)` classmethod to `CreateReminderTool` |
| `chatServer/tools/schedule_tools.py` | Add `prompt_section(channel)` classmethod to `CreateScheduleTool` |
| `chatServer/tools/update_instructions_tool.py` | Add `prompt_section(channel)` classmethod to `UpdateInstructionsTool` |
| `chatServer/tools/email_digest_tool.py` | Add `prompt_section(channel)` classmethod to `EmailDigestTool` |
| `src/core/agent_loader_db.py` | In both `load_agent_executor_db()` and `load_agent_executor_db_async()`, pass `tools=instantiated_tools` to `build_agent_prompt()` instead of `tool_names` |

### Out of Scope

- **min-memory migration** — Replacing the blob with semantic retrieval is a separate spec. This spec uses the existing `agent_long_term_memory.notes` field as-is.
- **Soul content changes** — The soul has already been rewritten as a DB-only update. This spec does not modify soul text.
- **Frontend changes** — No UI modifications.
- **Session lifecycle model** — No changes to how sessions are created, scoped, or deactivated.
- **New tools or API endpoints** — No new capabilities; only new `prompt_section()` classmethods on existing tools.
- **CRUDTool prompt sections** — CRUDTool is legacy/deprecated; no `prompt_section()` added. If a CRUDTool is loaded, it simply contributes nothing to Tool Guidance.

## Technical Approach

### Part 1: Tool-Contributed Prompt Sections (FU-1)

Per A6 (tools = capability units), each tool should own its own prompt guidance rather than relying on a centralized prompt template that tries to describe all tools generically.

**1a. Add `prompt_section()` classmethod to tool classes.**

Each tool class gets a classmethod with this signature:

```python
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    """Return behavioral guidance for the agent prompt, or None to omit."""
```

The method returns a short string describing *when and how* to use this tool well, scoped to the current channel. Returns `None` when the tool has no channel-specific guidance worth including.

Only one tool per "capability group" needs a `prompt_section()`. For example, `GetTasksTool` provides guidance for all five task tools — there's no need for `CreateTaskTool`, `UpdateTaskTool`, etc. to each repeat similar guidance. The prompt section describes the *capability*, not the individual tool.

**Concrete examples of `prompt_section()` return values:**

`GetTasksTool.prompt_section("web")`:
```
"Tasks: Check get_tasks at conversation start to know what the user is working on. When they mention something actionable, create_task without asking. Update task status as work progresses."
```

`GetTasksTool.prompt_section("heartbeat")`:
```
"Tasks: Call get_tasks to check for overdue or stale tasks. Report any that need attention."
```

`SaveMemoryTool.prompt_section("web")`:
```
"Memory: Call read_memory before answering questions about the user's preferences, projects, or anything previously discussed. When the user shares something worth remembering, call save_memory immediately — don't wait to be asked."
```

`SaveMemoryTool.prompt_section("heartbeat")`:
```
None  # No memory guidance needed on heartbeat
```

`GmailSearchTool.prompt_section("web")`:
```
"Gmail: Available for email search, reading, and digests. When the user asks about email, use gmail_search or gmail_digest. Don't proactively check email unless asked."
```

`GmailSearchTool.prompt_section("heartbeat")`:
```
"Gmail: Check for important unread emails using gmail_search with 'is:unread newer_than:4h'. Report subjects and senders of anything that looks urgent. Skip newsletters and automated notifications."
```

`CreateReminderTool.prompt_section("web")`:
```
"Reminders: When the user mentions a deadline or wants to be reminded, use create_reminder with an ISO datetime. Check list_reminders if they ask about upcoming reminders."
```

`CreateScheduleTool.prompt_section("web")`:
```
"Schedules: When the user wants recurring work (daily summaries, weekly reports), use create_schedule with a cron expression. Use list_schedules to show existing schedules."
```

`UpdateInstructionsTool.prompt_section("web")`:
```
"Instructions: When the user says 'always do X' or 'never do Y', use update_instructions to persist the preference. This is a full replace — include existing instructions you want to keep."
```

`EmailDigestTool.prompt_section("web")`:
```
"Email Digest: Use email_digest for comprehensive email summaries. Prefer this over manual gmail_search when the user wants an overview of recent email activity."
```

`EmailDigestTool.prompt_section("scheduled")`:
```
"Email Digest: Generate the digest using email_digest. Include the full summary in your response for notification delivery."
```

For `telegram` channel, most tools return the same guidance as `web` (or `None` if not relevant). For `scheduled` and `heartbeat`, guidance shifts to proactive/autonomous behavior.

**1b. Update `build_agent_prompt()` to collect tool guidance.**

Replace the current `tool_names: list[str] | None` parameter with `tools: list | None` (list of instantiated `BaseTool` objects). Iterate over the tools, call `prompt_section(channel)` on each, deduplicate (since multiple tools from the same class may exist), and assemble into a `## Tool Guidance` section.

```python
# In build_agent_prompt():
if tools:
    seen_classes = set()
    guidance_lines = []
    for tool in tools:
        tool_cls = type(tool)
        if tool_cls in seen_classes:
            continue
        seen_classes.add(tool_cls)
        if hasattr(tool_cls, "prompt_section"):
            section = tool_cls.prompt_section(channel)
            if section:
                guidance_lines.append(section)
    if guidance_lines:
        sections.append("## Tool Guidance\n" + "\n".join(guidance_lines))
```

This replaces the current `## Tools` section that just lists names.

**1c. Update agent loaders to pass tool objects.**

In `src/core/agent_loader_db.py`, both `load_agent_executor_db()` and `load_agent_executor_db_async()` already have `instantiated_tools`. Change the `build_agent_prompt()` call from:

```python
tool_names = [getattr(t, "name", None) for t in instantiated_tools if getattr(t, "name", None)]
assembled_prompt = build_agent_prompt(..., tool_names=tool_names, ...)
```

to:

```python
assembled_prompt = build_agent_prompt(..., tools=instantiated_tools, ...)
```

### Part 2: Pre-loaded Memory Context (FU-2)

Per A14 (pragmatic progressivism), inject available memory into the prompt at build time rather than requiring the agent to call `read_memory` as its first action every conversation.

**2a. Add `## What You Know` section.**

When `memory_notes` is non-empty, inject it as a prompt section:

```python
if memory_notes:
    # Truncate to prevent prompt bloat (same 4000 char limit as storage)
    truncated_notes = memory_notes[:4000]
    sections.append(
        f"## What You Know\n"
        f"These are your accumulated notes about this user:\n{truncated_notes}"
    )
```

This section appears *after* Soul and *before* Tool Guidance, so the agent has context before it sees what tools are available.

**2b. Remove `MEMORY_SECTION` constant.**

The static `MEMORY_SECTION` text ("You have long-term memory via read_memory and save_memory tools...") is deleted. Its behavioral guidance ("call read_memory FIRST", "call save_memory immediately") moves into `SaveMemoryTool.prompt_section()` and `ReadMemoryTool.prompt_section()` (done in Part 1).

The `## Memory` section in the prompt is replaced by:
- `## What You Know` (pre-loaded notes, from Part 2)
- Memory tool guidance inside `## Tool Guidance` (from Part 1)

**2c. Preserve onboarding detection.**

Onboarding logic stays unchanged: when `memory_notes` is falsy AND `user_instructions` is falsy on interactive channels, inject the `ONBOARDING_SECTION`. The `## What You Know` section simply doesn't appear when there are no notes.

### Part 3: Channel-Aware Prompt Assembly (FU-3)

Per A7 (cross-channel default), expand `CHANNEL_GUIDANCE` so heartbeat and scheduled channels get rich behavioral context beyond the current one-liners.

**3a. Expand `CHANNEL_GUIDANCE`.**

```python
CHANNEL_GUIDANCE = {
    "web": (
        "User is on the web app. Markdown formatting is supported. "
        "This is an interactive conversation — respond to what the user says, "
        "ask clarifying questions when needed."
    ),
    "telegram": (
        "User is on Telegram. Keep responses concise — under 4096 characters. "
        "Use simple markdown (bold, italic, code). No tables or complex formatting. "
        "This is an interactive conversation."
    ),
    "scheduled": (
        "This is an automated scheduled run. No one is waiting for a response.\n"
        "- Do the work described in the prompt thoroughly.\n"
        "- Use all available tools to gather information before composing your response.\n"
        "- Don't ask follow-up questions — make reasonable assumptions.\n"
        "- Your response will be delivered as a notification, so make it self-contained."
    ),
    "heartbeat": (
        "This is an automated heartbeat check. No one is waiting for a response.\n"
        "Your job: check each area using your tools, then decide if anything needs the user's attention.\n"
        "- Use tools to actively check state (tasks, emails, reminders) — don't guess.\n"
        "- If everything is fine, respond with exactly: HEARTBEAT_OK\n"
        "- If something needs attention, report ONLY what needs action — no filler.\n"
        "- Never fabricate information. If a tool fails, skip that check and note the failure."
    ),
}
```

**3b. Tool `prompt_section()` is already channel-aware.**

From Part 1, each tool's `prompt_section(channel)` already receives the channel and can return different guidance. No additional work needed here — the composability is built in.

### Dependencies

- No database migrations required.
- No new tables or columns.
- No external service dependencies.
- The soul rewrite (already applied as DB update) works independently of these changes.

## Contracts

### `build_agent_prompt()` signature change

```python
# Before (current):
def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tool_names: list[str] | None = None,
    memory_notes: str | None = None,
) -> str:

# After:
def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tools: list | None = None,
    memory_notes: str | None = None,
) -> str:
```

### `prompt_section()` classmethod contract

```python
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    """Return behavioral guidance for the prompt, or None.

    Args:
        channel: One of "web", "telegram", "scheduled", "heartbeat"

    Returns:
        A concise string (under 200 chars for interactive channels)
        describing when/how to use this tool capability, or None
        if no guidance is relevant for this channel.
    """
```

### Prompt section ordering

The assembled prompt follows this section order:

1. `## Identity` (if identity provided)
2. `## Soul` (behavioral philosophy)
3. `## Channel` (channel context from expanded `CHANNEL_GUIDANCE`)
4. `## Current Time`
5. `## What You Know` (pre-loaded memory notes, if any — new)
6. `## User Instructions`
7. `## Tool Guidance` (collected from tool `prompt_section()` calls — replaces `## Tools`)
8. `## Onboarding` (only for new users on interactive channels)

## Testing Requirements

### Unit Tests (required)

Every change is testable in isolation since `prompt_builder.py` is a pure function (no I/O, no DB calls) and `prompt_section()` is a classmethod (no instance state needed).

### What to Test

**prompt_builder tests (`test_prompt_builder.py`):**
- `build_agent_prompt()` with `tools=[]` produces no `## Tool Guidance` section
- `build_agent_prompt()` with tools that have `prompt_section()` produces `## Tool Guidance` with their output
- `build_agent_prompt()` deduplicates tools of the same class (only one `prompt_section()` call per class)
- `build_agent_prompt()` with tools that return `None` from `prompt_section()` omits them from guidance
- `build_agent_prompt()` with `memory_notes="some notes"` produces `## What You Know` section containing those notes
- `build_agent_prompt()` with `memory_notes=None` produces no `## What You Know` section
- `build_agent_prompt()` with `memory_notes=None` and `user_instructions=None` on `channel="web"` still produces `## Onboarding`
- `build_agent_prompt()` with `memory_notes="notes"` and `user_instructions=None` on `channel="web"` does NOT produce `## Onboarding`
- The string `MEMORY_SECTION` no longer exists in the module
- `CHANNEL_GUIDANCE["heartbeat"]` contains "HEARTBEAT_OK"
- `CHANNEL_GUIDANCE["scheduled"]` contains "notification"
- Assembled prompt section order is correct (Identity before Soul before Channel, etc.)
- Tool guidance from memory tools contains "read_memory" and "save_memory" behavioral text

**tool prompt_section tests (`test_tool_prompt_sections.py`):**
- Each tool class that defines `prompt_section()` returns `str | None` for each known channel
- `GetTasksTool.prompt_section("web")` returns non-None string mentioning tasks
- `GetTasksTool.prompt_section("heartbeat")` returns non-None string mentioning overdue/stale
- `SaveMemoryTool.prompt_section("web")` returns non-None string mentioning "read_memory" and "save_memory"
- `SaveMemoryTool.prompt_section("heartbeat")` returns `None`
- `GmailSearchTool.prompt_section("web")` returns non-None string
- `GmailSearchTool.prompt_section("heartbeat")` returns non-None string mentioning unread
- `CreateReminderTool.prompt_section("web")` returns non-None string
- `UpdateInstructionsTool.prompt_section("web")` returns non-None string mentioning "always" or "never"
- `EmailDigestTool.prompt_section("scheduled")` returns non-None string
- No `prompt_section()` return value exceeds 300 characters (prevents prompt bloat)
- Tools without `prompt_section()` (e.g., CRUDTool subclasses) don't break the collector

### AC-to-Test Mapping

| AC | Test Type | Test Function(s) |
|----|-----------|-------------------|
| AC-01 | Unit | `test_tool_prompt_sections.py::test_*_prompt_section_*` (one per tool class per channel) |
| AC-02 | Unit | `test_prompt_builder.py::test_tool_guidance_section_assembled`, `test_no_tools_no_guidance_section` |
| AC-03 | Unit | `test_prompt_builder.py::test_tools_param_accepts_tool_objects` |
| AC-04 | Unit | `test_prompt_builder.py::test_what_you_know_section_with_notes`, `test_no_what_you_know_without_notes` |
| AC-05 | Unit | `test_prompt_builder.py::test_memory_section_constant_removed`, `test_memory_guidance_in_tool_section` |
| AC-06 | Unit | `test_prompt_builder.py::test_heartbeat_channel_guidance_rich`, `test_scheduled_channel_guidance_rich` |
| AC-07 | Unit | `test_tool_prompt_sections.py::test_gmail_heartbeat_vs_web_differs` |
| AC-08 | Unit | `test_prompt_builder.py::test_onboarding_still_works_no_memory_no_instructions` |
| AC-09 | — | Meta: all tests above exist and pass |
| AC-10 | Unit | `test_tool_prompt_sections.py::test_prompt_section_length_limits` |

### Manual Verification (UAT)

- [ ] Deploy to staging, start a web conversation. Verify the agent references task/memory context naturally without being asked.
- [ ] Trigger a heartbeat run. Verify the agent uses tools to check state rather than guessing.
- [ ] Start a conversation with a user who has memory notes. Verify the agent demonstrates awareness of stored facts without calling `read_memory` first.
- [ ] Start a conversation with a brand-new user (no memory, no instructions). Verify onboarding flow still triggers.
- [ ] Check an agent that does NOT have Gmail tools configured. Verify no Gmail guidance appears in the prompt.

## Edge Cases

- **Tool class without `prompt_section()`**: The collector uses `hasattr()` to check. Tools without the method (e.g., CRUDTool, third-party LangChain tools) are silently skipped. No error, no guidance — expected behavior.
- **Duplicate tool classes in tools list**: Multiple instances of the same class (e.g., two `GmailSearchTool` instances for different accounts in the future) should produce only one prompt section. The collector deduplicates by class identity.
- **Empty memory_notes string `""`**: Treated as falsy — no `## What You Know` section injected. Same behavior as `None`.
- **Very long memory_notes**: Truncated to 4000 characters (matching the storage limit in `memory_tools.py`). No error.
- **Unknown channel string**: Falls back to `web` guidance (existing behavior preserved). Tool `prompt_section()` receives the raw channel string — tools should return reasonable defaults or `None` for unrecognized channels.
- **`prompt_section()` raises an exception**: The collector catches exceptions per-tool and logs a warning. The prompt assembles without that tool's guidance. Never fails the entire prompt build.
- **No tools loaded at all**: `tools=None` or `tools=[]` results in no `## Tool Guidance` section — same as current behavior when `tool_names` is empty.

## Functional Units (for PR Breakdown)

All FUs are **backend-dev** scope. No database migrations, no frontend changes.

---

### FU-1: Add `prompt_section()` to Tool Classes (`feat/SPEC-015-tool-sections`)

**Domain:** backend-dev
**Delivers:** AC-01, AC-07, AC-10
**Depends on:** nothing

Add a `prompt_section(channel: str) -> str | None` classmethod to one representative tool per capability group. The method returns a short behavioral guidance string or `None`.

**Files to modify (add classmethod only — no other changes):**

| File | Class | Add `prompt_section()` |
|------|-------|----------------------|
| `chatServer/tools/task_tools.py` | `GetTasksTool` | Yes — represents all 5 task tools |
| `chatServer/tools/memory_tools.py` | `SaveMemoryTool` | Yes — represents both memory tools |
| `chatServer/tools/gmail_tools.py` | `GmailSearchTool` | Yes — represents all 3 Gmail tools |
| `chatServer/tools/reminder_tools.py` | `CreateReminderTool` | Yes |
| `chatServer/tools/schedule_tools.py` | `CreateScheduleTool` | Yes |
| `chatServer/tools/update_instructions_tool.py` | `UpdateInstructionsTool` | Yes |
| `chatServer/tools/email_digest_tool.py` | `EmailDigestTool` | Yes |

**Files to create:**

| File | Purpose |
|------|---------|
| `tests/chatServer/tools/test_tool_prompt_sections.py` | Tests for every `prompt_section()` |

#### Contract: Exact `prompt_section()` return values

Each classmethod MUST follow this signature exactly:

```python
@classmethod
def prompt_section(cls, channel: str) -> str | None:
    """Return behavioral guidance for the agent prompt, or None to omit."""
```

**Return values by class and channel:**

**`GetTasksTool`:**
- `"web"` / `"telegram"`: `"Tasks: Check get_tasks at conversation start to see what the user is working on. When they mention something actionable, use create_task. Update status as work progresses."`
- `"heartbeat"`: `"Tasks: Call get_tasks to check for overdue or stale tasks. Report any that need attention."`
- `"scheduled"`: `None`

**`SaveMemoryTool`:**
- `"web"` / `"telegram"`: `"Memory: Before answering questions about the user's preferences, past conversations, or projects, call read_memory first. When the user shares something worth remembering, call save_memory immediately."`
- `"heartbeat"` / `"scheduled"`: `None`

**`GmailSearchTool`:**
- `"web"` / `"telegram"`: `"Gmail: Use gmail_search, gmail_get_message, and gmail_digest for email tasks. When the user asks about email, use the tools — don't ask clarifying questions first."`
- `"heartbeat"`: `"Gmail: Check for important unread emails using gmail_search with 'is:unread newer_than:4h'. Report subjects and senders of anything urgent. Skip newsletters and automated notifications."`
- `"scheduled"`: `None`

**`CreateReminderTool`:**
- `"web"` / `"telegram"`: `"Reminders: When the user mentions a deadline or wants to be reminded, use create_reminder with an ISO datetime. Use list_reminders to show upcoming reminders."`
- `"heartbeat"` / `"scheduled"`: `None`

**`CreateScheduleTool`:**
- `"web"` / `"telegram"`: `"Schedules: When the user wants recurring work (daily summaries, weekly reports), use create_schedule with a cron expression. Use list_schedules to show existing schedules."`
- `"heartbeat"` / `"scheduled"`: `None`

**`UpdateInstructionsTool`:**
- `"web"` / `"telegram"`: `"Instructions: When the user says 'always do X' or 'never do Y', use update_instructions to persist the preference. This is a full replace — include existing instructions you want to keep."`
- `"heartbeat"` / `"scheduled"`: `None`

**`EmailDigestTool`:**
- `"web"` / `"telegram"`: `"Email Digest: Use email_digest for comprehensive email summaries. Prefer this over manual gmail_search when the user wants an overview of recent email activity."`
- `"scheduled"`: `"Email Digest: Generate the digest using email_digest. Include the full summary in your response for notification delivery."`
- `"heartbeat"`: `None`

For any unrecognized channel string, return the same as `"web"`.

#### Contract: Test requirements

`tests/chatServer/tools/test_tool_prompt_sections.py` must test:
- Each tool class that has `prompt_section()` returns `str` or `None` for each of the 4 channels
- `GmailSearchTool.prompt_section("web")` differs from `GmailSearchTool.prompt_section("heartbeat")` (AC-07)
- No `prompt_section()` return value exceeds 300 characters (AC-10)
- `SaveMemoryTool.prompt_section("heartbeat")` returns `None`
- `GetTasksTool.prompt_section("heartbeat")` returns non-None mentioning "overdue" or "stale"

**Verification command:** `pytest tests/chatServer/tools/test_tool_prompt_sections.py -x -q && ruff check chatServer/tools/`

---

### FU-2: Prompt Builder — Tool Guidance Collector (`feat/SPEC-015-tool-guidance-collector`)

**Domain:** backend-dev
**Delivers:** AC-02, AC-03
**Depends on:** FU-1

Replace the flat tool-name listing in `build_agent_prompt()` with a collector that calls `prompt_section()` on each tool object.

**Files to modify:**

| File | Change |
|------|--------|
| `chatServer/services/prompt_builder.py` | Replace `tool_names: list[str] \| None` param with `tools: list \| None`; replace `## Tools` section with `## Tool Guidance` collector |
| `src/core/agent_loader_db.py` | Both `load_agent_executor_db()` (line ~649-659) and `load_agent_executor_db_async()` (line ~767-778): pass `tools=instantiated_tools` instead of `tool_names=tool_names`; delete the `tool_names` list comprehension |

**Files to create:**

| File | Purpose |
|------|---------|
| `tests/chatServer/services/test_prompt_builder.py` | Tests for tool guidance assembly |

#### Contract: Exact changes to `prompt_builder.py`

**Remove** (lines 108-114):
```python
# 7. Tools
if tool_names:
    tools_list = ", ".join(tool_names)
    sections.append(
        f"## Tools\nAvailable tools: {tools_list}\n"
        "Use tools when they help. Don't narrate routine tool calls."
    )
```

**Replace with:**
```python
# 7. Tool Guidance
if tools:
    seen_classes = set()
    guidance_lines = []
    for tool in tools:
        tool_cls = type(tool)
        if tool_cls in seen_classes:
            continue
        seen_classes.add(tool_cls)
        try:
            if hasattr(tool_cls, "prompt_section"):
                section = tool_cls.prompt_section(channel)
                if section:
                    guidance_lines.append(section)
        except Exception:
            pass  # Never fail the prompt build for a single tool
    if guidance_lines:
        sections.append("## Tool Guidance\n" + "\n".join(guidance_lines))
```

**Change function signature** from:
```python
def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tool_names: list[str] | None = None,
    memory_notes: str | None = None,
) -> str:
```
to:
```python
def build_agent_prompt(
    soul: str,
    identity: dict | None,
    channel: str,
    user_instructions: str | None,
    timezone: str | None = None,
    tools: list | None = None,
    memory_notes: str | None = None,
) -> str:
```

#### Contract: Exact changes to `agent_loader_db.py`

**In `load_agent_executor_db()` (sync path, around line 649-659):**

Delete:
```python
tool_names = [getattr(t, "name", None) for t in instantiated_tools if getattr(t, "name", None)]
```

Change:
```python
assembled_prompt = build_agent_prompt(
    soul=soul,
    identity=identity,
    channel=channel,
    user_instructions=user_instructions,
    tool_names=tool_names,
    memory_notes=memory_notes,
)
```
to:
```python
assembled_prompt = build_agent_prompt(
    soul=soul,
    identity=identity,
    channel=channel,
    user_instructions=user_instructions,
    tools=instantiated_tools,
    memory_notes=memory_notes,
)
```

**In `load_agent_executor_db_async()` (async path, around line 767-778):** Same change — delete `tool_names` comprehension, pass `tools=instantiated_tools`.

#### Contract: Test requirements

`tests/chatServer/services/test_prompt_builder.py` must test:
- `build_agent_prompt(tools=[])` produces no `## Tool Guidance` section
- `build_agent_prompt(tools=None)` produces no `## Tool Guidance` section
- `build_agent_prompt()` with mock tools that have `prompt_section()` produces `## Tool Guidance` containing their output
- Deduplication: two instances of the same class produce only one guidance line
- Tools that return `None` from `prompt_section()` are omitted
- Tools without `prompt_section()` (e.g., plain `BaseTool`) don't crash the builder
- The old string `"Available tools:"` does NOT appear in any output

**Verification command:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py src/core/agent_loader_db.py`

---

### FU-3: Pre-loaded Memory Context (`feat/SPEC-015-preloaded-memory`)

**Domain:** backend-dev
**Delivers:** AC-04, AC-05, AC-08
**Depends on:** FU-2

Remove the static `MEMORY_SECTION` constant and `## Memory` section. Add `## What You Know` section that injects pre-loaded memory notes.

**Files to modify:**

| File | Change |
|------|--------|
| `chatServer/services/prompt_builder.py` | Remove `MEMORY_SECTION` constant; remove `## Memory` section; add `## What You Know` section |

#### Contract: Exact changes to `prompt_builder.py`

**Delete** the `MEMORY_SECTION` constant (lines 34-40):
```python
MEMORY_SECTION = (
    "You have long-term memory via the read_memory and save_memory tools.\n"
    "IMPORTANT: Before answering any question about the user's preferences, past conversations, "
    "ongoing projects, or anything you were previously told to remember — call read_memory FIRST. "
    "Do not guess from the conversation. Check your memory.\n"
    "When the user tells you something to remember, call save_memory immediately."
)
```

**Delete** from `build_agent_prompt()` (line 91):
```python
# 5. Memory
sections.append(f"## Memory\n{MEMORY_SECTION}")
```

**Add** in its place (same position — after Current Time, before User Instructions):
```python
# 5. What You Know (pre-loaded memory)
if memory_notes:
    truncated_notes = memory_notes[:4000]
    sections.append(
        f"## What You Know\n"
        f"These are your accumulated notes about this user:\n{truncated_notes}"
    )
```

**Important:** The `ONBOARDING_SECTION` constant and its detection logic (lines 116-120) must NOT be changed. Onboarding still triggers when `memory_notes` is falsy AND `user_instructions` is falsy on interactive channels.

#### Contract: Test requirements

Add to `tests/chatServer/services/test_prompt_builder.py`:
- `build_agent_prompt(memory_notes="user likes cats")` produces `## What You Know` section containing "user likes cats"
- `build_agent_prompt(memory_notes=None)` does NOT produce `## What You Know` section
- `build_agent_prompt(memory_notes="")` does NOT produce `## What You Know` section
- `build_agent_prompt(memory_notes=None, user_instructions=None, channel="web")` still produces `## Onboarding`
- `build_agent_prompt(memory_notes="notes", user_instructions=None, channel="web")` does NOT produce `## Onboarding`
- The string `MEMORY_SECTION` no longer exists as an attribute of the module
- Memory tool behavioral guidance ("read_memory", "save_memory") now comes from `## Tool Guidance` section (via `SaveMemoryTool.prompt_section()` from FU-1), not from a hardcoded constant

**Verification command:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py`

---

### FU-4: Channel-Aware Prompt Assembly (`feat/SPEC-015-channel-guidance`)

**Domain:** backend-dev
**Delivers:** AC-06
**Depends on:** FU-2 (so all prompt sections are in their final positions)

Expand the `CHANNEL_GUIDANCE` dict with richer behavioral context for all four channels.

**Files to modify:**

| File | Change |
|------|--------|
| `chatServer/services/prompt_builder.py` | Replace `CHANNEL_GUIDANCE` dict values |

#### Contract: Exact replacement for `CHANNEL_GUIDANCE`

Replace lines 6-18 with:

```python
CHANNEL_GUIDANCE = {
    "web": (
        "User is on the web app. Markdown formatting is supported. "
        "This is an interactive conversation — respond to what the user says, "
        "ask clarifying questions when needed."
    ),
    "telegram": (
        "User is on Telegram. Keep responses concise — under 4096 characters. "
        "Use simple markdown (bold, italic, code). No tables or complex formatting. "
        "This is an interactive conversation."
    ),
    "scheduled": (
        "This is an automated scheduled run. No one is waiting for a response.\n"
        "- Do the work described in the prompt thoroughly.\n"
        "- Use all available tools to gather information before composing your response.\n"
        "- Don't ask follow-up questions — make reasonable assumptions.\n"
        "- Your response will be delivered as a notification, so make it self-contained."
    ),
    "heartbeat": (
        "This is an automated heartbeat check. No one is waiting for a response.\n"
        "Your job: check each area using your tools, then decide if anything needs the user's attention.\n"
        "- Use tools to actively check state (tasks, emails, reminders) — don't guess.\n"
        "- If everything is fine, respond with exactly: HEARTBEAT_OK\n"
        "- If something needs attention, report ONLY what needs action — no filler.\n"
        "- Never fabricate information. If a tool fails, skip that check and note the failure."
    ),
}
```

#### Contract: Test requirements

Add to `tests/chatServer/services/test_prompt_builder.py`:
- `CHANNEL_GUIDANCE["heartbeat"]` contains "HEARTBEAT_OK"
- `CHANNEL_GUIDANCE["heartbeat"]` contains "Use tools"
- `CHANNEL_GUIDANCE["scheduled"]` contains "notification"
- `CHANNEL_GUIDANCE["scheduled"]` contains "Don't ask follow-up questions"
- `CHANNEL_GUIDANCE["web"]` contains "interactive"
- `CHANNEL_GUIDANCE["telegram"]` contains "4096"

**Verification command:** `pytest tests/chatServer/services/test_prompt_builder.py -x -q && ruff check chatServer/services/prompt_builder.py`

---

### Merge Order

```
FU-1 (tool prompt_section methods) → FU-2 (prompt builder collector) → FU-3 (pre-loaded memory) → FU-4 (channel guidance)
```

**Why this order:**
- FU-1 creates the `prompt_section()` classmethods that FU-2's collector calls
- FU-2 changes the `build_agent_prompt()` signature that FU-3 modifies further
- FU-3 removes `MEMORY_SECTION` — safe only after FU-1 moved that guidance into `SaveMemoryTool.prompt_section()`
- FU-4 is independent of FU-3 but both modify `prompt_builder.py` — sequential merge avoids conflicts

**Note:** FU-3 and FU-4 are small enough that they could be done in parallel by the same agent as separate commits on the same branch, if the orchestrator prefers. They touch different parts of `prompt_builder.py` (FU-3: memory section logic; FU-4: CHANNEL_GUIDANCE constant at the top).

### AC-to-FU Mapping

| AC | FU | What it covers |
|----|-----|---------------|
| AC-01 | FU-1 | `prompt_section()` exists on all tool classes |
| AC-02 | FU-2 | `## Tool Guidance` assembled from tool objects |
| AC-03 | FU-2 | `tools` param replaces `tool_names` in builder + both loader paths |
| AC-04 | FU-3 | `## What You Know` injected from `memory_notes` |
| AC-05 | FU-3 | `MEMORY_SECTION` removed; guidance in tool prompt sections |
| AC-06 | FU-4 | `CHANNEL_GUIDANCE` expanded for all channels |
| AC-07 | FU-1 | `prompt_section()` returns different values per channel |
| AC-08 | FU-3 | Onboarding detection preserved |
| AC-09 | FU-1, FU-2, FU-3, FU-4 | All FUs include tests |
| AC-10 | FU-1 | No `prompt_section()` exceeds 300 chars |

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-10)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (`build_agent_prompt()` signature, `prompt_section()` classmethod signature, prompt section ordering)
- [x] Technical decisions reference principles (A6, A7, A14, F1, S1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3 → FU-4)
- [x] Out of scope is explicit (min-memory, soul, frontend, sessions, new tools)
- [x] Edge cases documented with expected behavior (7 cases)
- [x] Testing requirements map to ACs (all 10 ACs have test mappings)
- [x] Every FU has exact code snippets and verification commands (haiku-ready)
- [x] All `prompt_section()` return values are specified verbatim (no ambiguity for less capable models)
