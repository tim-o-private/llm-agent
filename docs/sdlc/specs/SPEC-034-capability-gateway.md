# SPEC-034: Capability Gateway — Replace BaseTool and ToolExecutionService

> **Status:** Draft
> **Author:** Claude (spec-writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06

## Goal

Replace the current BaseTool subclass pattern, ToolExecutionService, and wrap_tools_with_approval with a unified Capability Gateway that handles: allowlist enforcement, trust tier checks, server-side credential injection, execution, audit logging, and untrusted data tagging. This is Phase 1 of the next-gen architecture (per ARCHITECTURE-PROPOSAL-next-gen.md, Section Q2 and Phase 1).

The gateway becomes the single execution path for all tool calls. The agent (via SPEC-033's ConversationHandler) sends tool call requests to the gateway. The gateway enforces permissions, injects credentials, delegates to capability executors (thin functions calling existing services), logs the invocation, and returns tagged results. At no point does the LLM context contain raw OAuth tokens, API keys, or untagged external content.

## Acceptance Criteria

- [ ] **AC-01:** A `CapabilityGateway` class exists that accepts `(user_id, tool_name, parameters)` and returns a result string. All tool calls route through this single entry point. [A1, A12]
- [ ] **AC-02:** The gateway enforces a per-user, per-tool allowlist — tools not in the user's allowlist are rejected before execution. [A12, A13]
- [ ] **AC-03:** Trust tiers (Inform/Recommend/Act) are enforced per tool invocation. If a tool's `required_tier` exceeds the user's `granted_tier`, the gateway returns a denial with an upgrade prompt. [A12]
- [ ] **AC-04:** OAuth credentials (Gmail, Calendar) are injected server-side by the gateway. The executor receives credentials as a parameter; the LLM context never contains raw tokens. [A12]
- [ ] **AC-05:** Every gateway invocation is audit-logged with: tool name, user ID, trust tier, execution status, timestamp, and session context. [A12]
- [ ] **AC-06:** Results from external sources (email, calendar, web search) are wrapped in `TaggedContent` with `trust_level="untrusted"` and `source` metadata. [A12]
- [ ] **AC-07:** Tool definitions are loaded from Markdown files with YAML frontmatter (via SPEC-032 ConfigService) describing name, description, parameters, required_tier, and executor binding. [A2, A13]
- [ ] **AC-08:** Capability executors exist for all 28 canonical tools, each producing equivalent output to the current BaseTool._arun. Regression tests prove equivalence. [S1]
- [ ] **AC-09:** After migration, the following are deleted: `chatServer/tools/` (all BaseTool subclasses), `chatServer/security/tool_wrapper.py`, `chatServer/services/tool_execution.py`, `TOOL_REGISTRY` from `agent_loader_db.py`, `TOOL_APPROVAL_DEFAULTS` from `approval_tiers.py`. [A14]
- [ ] **AC-10:** The gateway exposes a `get_tool_schemas(user_id)` method that returns Anthropic-native tool definitions (name, description, input_schema) for only the tools in the user's allowlist. This is what SPEC-033's ConversationHandler passes to the Anthropic Messages API. [A12]
- [ ] **AC-11:** Unknown tool names produce a clear error, not a crash. The gateway's default for unrecognized tools is denial. [A12]
- [ ] **AC-12:** Memory tools receive the MCP client handle via the gateway's dependency injection, not via constructor args on a BaseTool subclass. [A1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/capabilities/__init__.py` | Package init |
| `chatServer/capabilities/gateway.py` | `CapabilityGateway` class — the single execution entry point |
| `chatServer/capabilities/schemas.py` | `TrustTier` enum, `ToolDefinition` model, `TaggedContent` dataclass, `CapabilityResult` |
| `chatServer/capabilities/allowlist.py` | `AllowlistResolver` — reads per-user allowlist from ConfigService, resolves granted tiers |
| `chatServer/capabilities/executors/__init__.py` | Executor registry |
| `chatServer/capabilities/executors/tasks.py` | Executors for get_tasks, create_tasks, update_tasks, delete_tasks |
| `chatServer/capabilities/executors/reminders.py` | Executors for get_reminders, create_reminders, delete_reminders |
| `chatServer/capabilities/executors/schedules.py` | Executors for get_schedules, create_schedules, delete_schedules |
| `chatServer/capabilities/executors/gmail.py` | Executors for search_gmail, get_gmail |
| `chatServer/capabilities/executors/gmail_compose.py` | Executors for draft_email_reply, send_email_reply |
| `chatServer/capabilities/executors/calendar.py` | Executors for search_calendar, get_calendar_event |
| `chatServer/capabilities/executors/memory.py` | Executors for all 10 memory tools (delegate to MCP client) |
| `chatServer/capabilities/executors/web_search.py` | Executor for search_web |
| `chatServer/capabilities/executors/config.py` | Executor for update_instructions |
| `chatServer/capabilities/executors/briefing.py` | Executor for update_briefing_preferences |
| `tests/chatServer/capabilities/test_gateway.py` | Gateway unit tests |
| `tests/chatServer/capabilities/test_allowlist.py` | Allowlist resolution tests |
| `tests/chatServer/capabilities/test_schemas.py` | Schema/tagging tests |
| `tests/chatServer/capabilities/test_executors.py` | Executor regression tests |
| `tests/chatServer/capabilities/test_security.py` | Security-focused tests (credential isolation, tier enforcement) |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/audit_service.py` | Add `trust_tier` and `data_source` fields to audit log entries |
| `supabase/migrations/NNNN_audit_trust_tier.sql` | Add `trust_tier` TEXT column to `audit_logs` |
| `src/core/agent_loader_db.py` | Remove `TOOL_REGISTRY` dict and `load_tools_from_db` after executor migration |
| `chatServer/services/pending_actions.py` | Wire approval flow to gateway's Recommend tier (tools at Recommend queue for approval) |

### Files to Delete (after all executors pass regression tests)

| File | Replaced By |
|------|-------------|
| `chatServer/tools/task_tools.py` | `capabilities/executors/tasks.py` |
| `chatServer/tools/reminder_tools.py` | `capabilities/executors/reminders.py` |
| `chatServer/tools/schedule_tools.py` | `capabilities/executors/schedules.py` |
| `chatServer/tools/gmail_tools.py` | `capabilities/executors/gmail.py` |
| `chatServer/tools/gmail_compose_tools.py` | `capabilities/executors/gmail_compose.py` |
| `chatServer/tools/calendar_tools.py` | `capabilities/executors/calendar.py` |
| `chatServer/tools/memory_tools.py` | `capabilities/executors/memory.py` |
| `chatServer/tools/web_search_tool.py` | `capabilities/executors/web_search.py` |
| `chatServer/tools/update_instructions_tool.py` | `capabilities/executors/config.py` |
| `chatServer/tools/briefing_tools.py` | `capabilities/executors/briefing.py` |
| `chatServer/tools/gmail_rate_limiter.py` | Moved into `capabilities/executors/gmail.py` |
| `chatServer/security/tool_wrapper.py` | `capabilities/gateway.py` (tier enforcement) |
| `chatServer/security/approval_tiers.py` | `capabilities/schemas.py` (TrustTier) + `capabilities/allowlist.py` |
| `chatServer/services/tool_execution.py` | `capabilities/gateway.py` |
| `tests/chatServer/services/test_tool_execution.py` | `tests/chatServer/capabilities/test_gateway.py` |
| `tests/chatServer/security/test_approval_tiers.py` | `tests/chatServer/capabilities/test_allowlist.py` |
| `tests/chatServer/security/test_tool_wrapper.py` | `tests/chatServer/capabilities/test_gateway.py` |
| `tests/chatServer/services/test_tool_registry_validator.py` | `tests/chatServer/capabilities/test_executors.py` (registry validation moves here) |

### Out of Scope

- **Config storage layer** — SPEC-032 provides `ConfigService` for reading tool definitions and allowlists
- **Conversation handler** — SPEC-033 provides the Anthropic API tool-loop that calls the gateway
- **Self-modification approval flow** — SPEC-038 adds the flow for agent-initiated config changes
- **Workflow dispatch tool** — Phase 2 adds `dispatch_workflow`; this spec covers only direct tool execution
- **Trust tier UI** — frontend for managing per-tool tiers is a separate spec
- **Rate limiting** — per-tool rate limits are a future enhancement; the gateway has an extension point but no implementation

## Technical Approach

### 1. Trust Tier Model (replaces approval_tiers.py)

Three tiers with clear semantic meaning:

```python
class TrustTier(str, Enum):
    INFORM = "inform"       # Read-only — search, list, get
    RECOMMEND = "recommend"  # Propose actions — create drafts, queue for approval
    ACT = "act"             # Execute directly — send, delete, modify
```

Each tool has a `required_tier` (minimum tier needed to call it). Each user has a `granted_tier` per tool (what they've authorized). Execution is allowed when `granted_tier >= required_tier`.

**Tier ordering:** `inform < recommend < act`.

**Mapping from current system:**

| Current Tier | Current Tools | New required_tier | Default granted_tier |
|-------------|---------------|-------------------|---------------------|
| AUTO_APPROVE (reads) | get_tasks, search_gmail, get_gmail, search_calendar, get_calendar_event, get_reminders, get_schedules, search_memories, get_memories, get_entities, search_entities, get_context, search_web | `inform` | `act` |
| AUTO_APPROVE (writes) | create_memories, update_memories, delete_memories, set_project, link_memories, draft_email_reply, update_briefing_preferences | `recommend` | `act` |
| USER_CONFIGURABLE (default auto) | create_tasks, update_tasks, create_reminders, create_schedules | `recommend` | `act` |
| USER_CONFIGURABLE (default approval) | delete_tasks, delete_reminders, delete_schedules, update_instructions | `act` | `recommend` |
| REQUIRES_APPROVAL | send_email_reply | `act` | `recommend` |

**Key invariant:** `send_email_reply` has `min_grantable_tier = "recommend"` — it can never be set below Recommend (always requires at least an approval gate). This replaces the old "REQUIRES_APPROVAL cannot be overridden" behavior.

### 2. Tool Definition Schema (replaces BaseTool class registration)

Tool definitions are Markdown files with YAML frontmatter stored in config (via SPEC-032's ConfigService). This format is consistent with HQ conventions, agent definitions, and the file browser UX. Each definition describes what the LLM sees and how the gateway executes it.

**Example tool definition file** (`system/tools/search_gmail.md`):

```markdown
---
name: search_gmail
description: >
  Search Gmail for emails matching a query. Returns message metadata
  (subject, sender, date, snippet) without full email bodies.
required_tier: inform
min_grantable_tier: inform
default_granted_tier: act
executor: gmail.search_gmail
credential_type: oauth_gmail
data_source: email
parameters:
  type: object
  properties:
    query:
      type: string
      description: Gmail search query (supports Gmail search operators)
    max_results:
      type: integer
      description: Maximum number of results (1-20)
      default: 10
  required: [query]
prompt_section:
  web: >
    Gmail: Use search_gmail to find emails. Supports Gmail search operators
    like from:, subject:, newer_than:. Use get_gmail to read full email content.
  telegram: >
    Gmail: Use search_gmail to find emails. Use get_gmail to read full content.
  heartbeat: >
    Gmail: Check search_gmail for important unread emails that need attention.
---

Search the user's Gmail accounts for messages matching a query.
Returns metadata only — use get_gmail with a message ID for full content.

## Multi-account behavior

Searches across all connected Gmail accounts. Results are prefixed with
the account email address for disambiguation.
```

**Parsed into Python model:**

```python
class ToolDefinition(BaseModel):
    """Schema for a tool definition loaded from Markdown+YAML frontmatter."""
    name: str                        # e.g., "search_gmail"
    description: str                 # LLM-facing description (from frontmatter)
    parameters: dict                 # JSON Schema for input parameters
    required_tier: TrustTier         # Minimum tier to call this tool
    min_grantable_tier: TrustTier    # Floor — user can't grant below this
    default_granted_tier: TrustTier  # Default for new users
    executor: str                    # Dotted path: "gmail.search_gmail"
    credential_type: str | None      # "oauth_gmail", "oauth_calendar", "mcp_memory", None
    data_source: str | None          # "email", "calendar", "web_search", None (for tagging)
    prompt_section: dict[str, str | None] | None  # Channel → guidance text (optional)
    body: str | None                 # Markdown body (extended docs, not sent to LLM)
```

**Why Markdown with YAML frontmatter, not JSON?** Consistent with HQ conventions — agent definitions, skills, and config files all use this format. Power users will read these in the Phase 4 file browser; Markdown is more readable than JSON. The YAML frontmatter carries structured data for the gateway; the Markdown body carries extended documentation for humans and the agent's own reference. Per A2 (DB config, code behavior): tool definitions are data — name, description, parameters, tier. Tool behavior is code — the executor functions. Separating these means tools can be reconfigured without code changes. When bwrap lands (Phase 3), the agent can edit tool definitions directly as files.

**Migration from TOOL_REGISTRY + TOOL_APPROVAL_DEFAULTS:** A migration script generates Markdown tool definition files from the current BaseTool classes (extracting `args_schema`, `description`, `name`) and approval_tiers.py entries. These become the initial system-level tool definition files in `system/tools/`.

### 3. Capability Gateway (replaces ToolExecutionService + wrap_tools_with_approval)

```python
class CapabilityGateway:
    """Single execution path for all tool calls."""

    def __init__(
        self,
        config_service,       # SPEC-032: reads tool definitions + allowlists
        allowlist_resolver,   # Resolves per-user granted tiers
        credential_provider,  # Reads OAuth tokens from external_api_connections
        audit_service,        # Logs invocations
        pending_actions_service,  # Queues actions at Recommend tier
        notification_service,     # Notifies user of queued actions
        mcp_client=None,      # Memory MCP client (injected per session)
    ):
        self._executors: dict[str, Callable] = {}  # Loaded from executor registry
        # ... store deps

    async def execute(
        self,
        user_id: str,
        tool_name: str,
        parameters: dict,
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> CapabilityResult:
        """
        Execute a tool call through the gateway pipeline:
        1. Load tool definition
        2. Check allowlist (is this tool enabled for this user?)
        3. Check trust tier (does the user's granted tier meet the required tier?)
        4. Resolve credentials (if needed)
        5. Execute via capability executor
        6. Tag result (if external data source)
        7. Audit log
        8. Return result
        """

    async def get_tool_schemas(self, user_id: str) -> list[dict]:
        """
        Return Anthropic-native tool definitions for the user's allowed tools.
        Only tools in the user's allowlist are returned.
        Format: [{"name": ..., "description": ..., "input_schema": {...}}, ...]
        """

    async def get_prompt_sections(self, user_id: str, channel: str) -> str:
        """
        Return assembled tool guidance text for the system prompt.
        Replaces the per-tool prompt_section() class methods.
        """
```

**`CapabilityResult` model:**

```python
@dataclass
class CapabilityResult:
    content: str                 # The result text (same format as current BaseTool returns)
    tagged: TaggedContent | None # Non-None for external data sources
    status: str                  # "success", "denied", "queued", "error"
    tool_name: str
    trust_tier: str              # The tier this was executed at
```

**Pipeline detail:**

Step 1 — **Load definition.** `config_service.get_tool_definition(tool_name)`. Cached in-memory with TTL (same 60s pattern as current tool cache). Unknown tool → `CapabilityResult(status="denied", content="Unknown tool: {name}")`.

Step 2 — **Allowlist check.** `allowlist_resolver.is_permitted(user_id, tool_name)`. If the tool isn't in the user's allowlist, return denial. Defense in depth: even if the tool was included in the LLM's tool definitions (shouldn't happen via `get_tool_schemas` filtering), execution is blocked.

Step 3 — **Tier check.** `allowlist_resolver.get_granted_tier(user_id, tool_name)` vs `definition.required_tier`. Three outcomes:
- `granted >= required` → proceed to step 4
- `granted == recommend` and `required == act` → queue for approval via PendingActionsService, return `CapabilityResult(status="queued", content="I've requested approval for '{tool_name}'...")`
- `granted < required` and gap > 1 tier → return `CapabilityResult(status="denied", content="I can view your emails but can't send yet. Want to enable that?")`

Step 4 — **Credential injection.** Based on `definition.credential_type`:
- `oauth_gmail` / `oauth_calendar` → `credential_provider.get_oauth_tokens(user_id, service_type)` returns OAuth credentials. Multiple accounts supported (same pattern as current gmail_tools.py/calendar_tools.py).
- `mcp_memory` → pass `self.mcp_client`
- `None` → no credentials needed (service-backed tools use user-scoped DB client)

Step 5 — **Execute.** Look up executor function from `self._executors[definition.executor]`. Call with `(parameters, credentials, user_id)`. Executors are thin async functions — see section 4.

Step 6 — **Tag result.** If `definition.data_source` is set, wrap result in `TaggedContent(content=result, source=data_source, trust_level="untrusted")`.

Step 7 — **Audit log.** Call `audit_service.log_action(...)` with trust tier, execution status, and session context. Non-blocking (fire and forget, same as current).

Step 8 — **Return.** `CapabilityResult` with the content string (for backward compatibility with SPEC-033's tool result handling) and optional tagged metadata.

### 4. Capability Executors (replace BaseTool._arun methods)

Executors are thin async functions that call existing services. They do NOT contain business logic, auth logic, or error handling beyond basic try/except. Each executor receives a standardized `ExecutionContext`:

```python
@dataclass
class ExecutionContext:
    user_id: str
    agent_name: str | None
    credentials: Any | None      # OAuth creds, MCP client, etc.
    db_client: Any               # User-scoped Supabase client
    settings: Any                # App settings (URLs, keys)
```

**Example: search_gmail executor**

```python
async def search_gmail(params: dict, ctx: ExecutionContext) -> str:
    """Search Gmail — delegates to Google API with injected OAuth credentials."""
    # ctx.credentials contains OAuth tokens (injected by gateway)
    # Build Gmail API client from credentials (same logic as current SearchGmailTool)
    # Execute search
    # Return formatted result string (same format as current)
```

**Executor categories by credential pattern:**

| Category | Tools | Credential Type | Service Dependency |
|----------|-------|----------------|--------------------|
| Service-backed | get_tasks, create_tasks, update_tasks, delete_tasks, get_reminders, create_reminders, delete_reminders, get_schedules, create_schedules, delete_schedules, update_briefing_preferences | None (uses ctx.db_client) | TaskService, ReminderService, ScheduleService, BriefingService |
| OAuth (Gmail) | search_gmail, get_gmail | `oauth_gmail` | Google Gmail API (direct) |
| OAuth (Gmail Compose) | draft_email_reply, send_email_reply | `oauth_gmail` | GmailComposeService |
| OAuth (Calendar) | search_calendar, get_calendar_event | `oauth_calendar` | CalendarService |
| MCP | create_memories, search_memories, get_memories, update_memories, delete_memories, set_project, link_memories, get_entities, search_entities, get_context | `mcp_memory` | min-memory MCP client |
| External API | search_web | None (API key from settings) | WebSearchService |
| Config | update_instructions | None (uses ctx.db_client) | PromptCustomizationService (or SPEC-032 ConfigService) |

**Migration strategy for each executor:** Extract the body of `_arun()` from the current BaseTool subclass. Remove constructor boilerplate, Pydantic field declarations, and LangChain imports. The business logic (service calls, result formatting) is preserved verbatim. Regression tests compare old and new output for the same inputs.

### 5. Allowlist Resolution (replaces hardcoded TOOL_APPROVAL_DEFAULTS)

```python
class AllowlistResolver:
    """Resolves which tools a user has enabled and at what tier."""

    def __init__(self, config_service):
        self._config = config_service

    async def is_permitted(self, user_id: str, tool_name: str) -> bool:
        """Check if a tool is in the user's allowlist."""

    async def get_granted_tier(self, user_id: str, tool_name: str) -> TrustTier:
        """Get the user's granted tier for a tool."""

    async def get_allowlist(self, user_id: str) -> dict[str, TrustTier]:
        """Get the full allowlist for a user (tool_name → granted_tier)."""
```

**Resolution logic:**

1. Load system-level tool definitions (all tools that exist)
2. Load user-level allowlist from config (SPEC-032: `tools/allowlist.yaml`)
3. If user has no allowlist → use default granted tiers from tool definitions (all current 29 tools enabled at their existing behavior)
4. If user has an allowlist → merge: user overrides take precedence, but `granted_tier` can never drop below `min_grantable_tier`

**Allowlist file format** (stored in user config via SPEC-032, Markdown+YAML frontmatter):

```markdown
---
# User tool allowlist — overrides system defaults
tools:
  search_gmail:
    granted_tier: act
  send_email_reply:
    granted_tier: recommend
  delete_tasks:
    granted_tier: act
---
```

Tools not listed in the user's file use the `default_granted_tier` from the system tool definition.

**Migration behavior:** All 29 current tools are enabled for existing users at their existing tier (preserving current AUTO_APPROVE/USER_CONFIGURABLE/REQUIRES_APPROVAL behavior via the tier mapping table above). New tools added post-migration start disabled by default — they must be explicitly added to the user's allowlist or have `default_granted_tier` set in their system definition.

### 6. Data Tagging (new)

```python
@dataclass
class TaggedContent:
    """Wraps content with provenance metadata."""
    content: str
    source: str           # "email", "calendar", "web_search"
    trust_level: str      # "untrusted" (external), "user" (user-generated), "system"
```

Applied by the gateway when `definition.data_source` is set. The ConversationHandler (SPEC-033) uses this metadata when the agent proposes config modifications (SPEC-038) — if a modification traces back solely to untrusted content, it's blocked.

For this spec, tagging is applied but not yet consumed for blocking. The consuming logic belongs in SPEC-038.

### 7. Credential Provider (extracts pattern from current tool constructors)

```python
class CredentialProvider:
    """Server-side credential resolution. Tokens never reach LLM context."""

    async def get_oauth_tokens(
        self, user_id: str, service_type: str
    ) -> list[OAuthCredentials]:
        """
        Fetch OAuth tokens for a user+service from external_api_connections.
        Returns list (multi-account support for Gmail/Calendar).
        Handles token refresh transparently.
        """

    async def get_mcp_client(self) -> Any:
        """Return the session's MCP client for memory tools."""
```

This extracts the credential-fetching logic currently embedded in `GmailToolProvider`, `CalendarToolProvider`, and `_get_task_service()`. The gateway calls this once per execution and passes credentials to the executor.

**Security invariant:** The executor receives credentials as a function parameter. The gateway strips credentials from the result before returning to the ConversationHandler. The audit log records that credentials were used but not the credential values.

### Dependencies

- **SPEC-032 (Config Service):** Provides `ConfigService` for reading tool definitions and user allowlists from Supabase Storage. The gateway calls `config_service.get_tool_definition(name)` and `config_service.get_user_config(user_id, "tools/allowlist.json")`.
- **SPEC-033 (Conversation Handler):** The ConversationHandler calls `gateway.execute()` for each tool call and `gateway.get_tool_schemas()` to build the Anthropic API tool definitions. SPEC-033 and SPEC-034 must agree on the `CapabilityResult` interface.
- **Existing services:** TaskService, ReminderService, ScheduleService, GmailComposeService, CalendarService, WebSearchService, BriefingService, AuditService, PendingActionsService, NotificationService — all remain unchanged. Executors call them.

## Blast Radius

### Complete Tool Migration Map

| # | Tool Name | Current Class | Current File | Service | New Executor | Credential |
|---|-----------|--------------|--------------|---------|-------------|------------|
| 1 | get_tasks | GetTasksTool | tools/task_tools.py | TaskService | executors/tasks.py | None |
| 2 | create_tasks | CreateTasksTool | tools/task_tools.py | TaskService | executors/tasks.py | None |
| 3 | update_tasks | UpdateTasksTool | tools/task_tools.py | TaskService | executors/tasks.py | None |
| 4 | delete_tasks | DeleteTasksTool | tools/task_tools.py | TaskService | executors/tasks.py | None |
| 5 | get_reminders | GetRemindersTool | tools/reminder_tools.py | ReminderService | executors/reminders.py | None |
| 6 | create_reminders | CreateRemindersTool | tools/reminder_tools.py | ReminderService | executors/reminders.py | None |
| 7 | delete_reminders | DeleteRemindersTool | tools/reminder_tools.py | ReminderService | executors/reminders.py | None |
| 8 | get_schedules | GetSchedulesTool | tools/schedule_tools.py | ScheduleService | executors/schedules.py | None |
| 9 | create_schedules | CreateSchedulesTool | tools/schedule_tools.py | ScheduleService | executors/schedules.py | None |
| 10 | delete_schedules | DeleteSchedulesTool | tools/schedule_tools.py | ScheduleService | executors/schedules.py | None |
| 11 | search_gmail | SearchGmailTool | tools/gmail_tools.py | Gmail API | executors/gmail.py | oauth_gmail |
| 12 | get_gmail | GetGmailTool | tools/gmail_tools.py | Gmail API | executors/gmail.py | oauth_gmail |
| 13 | draft_email_reply | DraftEmailReplyTool | tools/gmail_compose_tools.py | GmailComposeService | executors/gmail_compose.py | oauth_gmail |
| 14 | send_email_reply | SendEmailReplyTool | tools/gmail_compose_tools.py | GmailComposeService | executors/gmail_compose.py | oauth_gmail |
| 15 | search_calendar | SearchCalendarTool | tools/calendar_tools.py | CalendarService | executors/calendar.py | oauth_calendar |
| 16 | get_calendar_event | GetCalendarEventTool | tools/calendar_tools.py | CalendarService | executors/calendar.py | oauth_calendar |
| 17 | create_memories | CreateMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 18 | search_memories | SearchMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 19 | get_memories | GetMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 20 | update_memories | UpdateMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 21 | delete_memories | DeleteMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 22 | set_project | SetProjectTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 23 | link_memories | LinkMemoriesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 24 | get_entities | GetEntitiesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 25 | search_entities | SearchEntitiesTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 26 | get_context | GetContextTool | tools/memory_tools.py | MCP (min-memory) | executors/memory.py | mcp_memory |
| 27 | search_web | SearchWebTool | tools/web_search_tool.py | WebSearchService | executors/web_search.py | None |
| 28 | update_instructions | UpdateInstructionsTool | tools/update_instructions_tool.py | Supabase (direct) | executors/config.py | None |
| 29 | update_briefing_preferences | ManageBriefingPreferencesTool | tools/briefing_tools.py | BriefingService | executors/briefing.py | None |

### Components Deleted After Migration

| Component | File(s) | Reason |
|-----------|---------|--------|
| TOOL_REGISTRY dict | `src/core/agent_loader_db.py` (lines 44-86) | Replaced by executor registry + JSON definitions |
| GMAIL_TOOL_CLASSES dict | `src/core/agent_loader_db.py` (lines 89-92) | Gmail executors are directly registered |
| load_tools_from_db() | `src/core/agent_loader_db.py` | Replaced by `gateway.get_tool_schemas()` |
| TOOL_APPROVAL_DEFAULTS dict | `chatServer/security/approval_tiers.py` | Replaced by `required_tier` in tool definitions |
| ApprovalTier enum | `chatServer/security/approval_tiers.py` | Replaced by `TrustTier` enum |
| get_effective_tier() | `chatServer/security/approval_tiers.py` | Replaced by `AllowlistResolver.get_granted_tier()` |
| wrap_tools_with_approval() | `chatServer/security/tool_wrapper.py` | Replaced by gateway pipeline |
| ApprovalContext class | `chatServer/security/tool_wrapper.py` | Gateway holds these deps directly |
| ToolExecutionService | `chatServer/services/tool_execution.py` | Replaced by gateway.execute() |
| CANONICAL_TOOL_NAMES set | `tests/.../test_tool_registry_validator.py` | Replaced by registry completeness tests in test_executors.py |
| All BaseTool subclasses | `chatServer/tools/*.py` (11 files) | Replaced by capability executors |
| CRUDTool + CRUDToolInput | `core/tools/crud_tool.py` | Deprecated since SPEC-019, now removed |

### Components That Stay (modified)

| Component | Modification |
|-----------|-------------|
| `AuditService` | Add `trust_tier` field to log entries |
| `PendingActionsService` | Called by gateway for Recommend-tier queuing (interface unchanged) |
| `NotificationService` | Called by gateway for approval notifications (interface unchanged) |
| All service classes (TaskService, etc.) | No changes — executors call them exactly as BaseTool._arun does today |
| `external_api_connections` table | No schema change — CredentialProvider reads from it |
| `audit_logs` table | Add `trust_tier` column |

## Testing Requirements

### Unit Tests (required)

**Gateway tests (test_gateway.py):**
- `test_execute_allowed_tool` — happy path, tool in allowlist, tier sufficient
- `test_execute_unknown_tool` — unknown tool returns denial
- `test_execute_not_in_allowlist` — tool exists but not permitted for user
- `test_execute_tier_insufficient` — granted tier < required tier → denial
- `test_execute_tier_recommend_queues` — granted=recommend, required=act → queues for approval
- `test_execute_injects_credentials` — OAuth tools receive credentials from provider
- `test_execute_audit_logged` — every execution produces an audit log entry
- `test_execute_audit_on_error` — errors are also audit logged
- `test_get_tool_schemas_filters_by_allowlist` — only permitted tools returned
- `test_get_tool_schemas_anthropic_format` — output matches Anthropic tool definition format

**Allowlist tests (test_allowlist.py):**
- `test_default_allowlist_uses_definition_defaults` — no user config → defaults apply
- `test_user_override_respected` — user config overrides default tier
- `test_min_grantable_tier_enforced` — user can't grant below minimum
- `test_is_permitted_true_for_listed_tools`
- `test_is_permitted_false_for_unlisted_tools`

**Schema tests (test_schemas.py):**
- `test_trust_tier_ordering` — inform < recommend < act
- `test_tagged_content_creation`
- `test_tool_definition_validation`

**Security tests (test_security.py):**
- `test_credential_not_in_result` — gateway strips credentials from executor output
- `test_credential_not_in_audit_log` — audit log contains no raw tokens
- `test_mcp_client_not_leaked` — MCP client handle not in result content
- `test_external_data_tagged_untrusted` — email/calendar/web results carry untrusted tag

### Integration Tests (required)

- `test_gateway_with_mocked_service` — full pipeline: gateway → executor → mocked service → result
- `test_gateway_approval_flow` — tier=recommend → PendingActionsService.queue_action called
- `test_gateway_oauth_credential_injection` — mock VaultTokenService, verify executor receives creds

### Regression Tests (required for AC-08)

For each of the 28 tools, a regression test that:
1. Calls the current BaseTool._arun with a set of test inputs
2. Calls the new capability executor with the same inputs
3. Asserts the outputs are equivalent (or documents intentional differences)

These tests ensure the migration is behaviorally transparent.

### AC-to-Test Mapping

| AC | Flow Test | Notes |
|----|-----------|-------|
| AC-01 | `test_execute_allowed_tool` | Gateway exists and processes calls |
| AC-02 | `test_execute_not_in_allowlist` | Allowlist enforcement |
| AC-03 | `test_execute_tier_insufficient`, `test_execute_tier_recommend_queues` | Tier enforcement |
| AC-04 | `test_credential_not_in_result`, `test_gateway_oauth_credential_injection` | Credential isolation |
| AC-05 | `test_execute_audit_logged`, `test_execute_audit_on_error` | Audit logging |
| AC-06 | `test_external_data_tagged_untrusted` | Data tagging |
| AC-07 | `test_tool_definition_validation` | Tool definition loading |
| AC-08 | Regression test suite (28 tools) | Output equivalence |
| AC-09 | Verify files deleted + tests pass | Post-migration cleanup |
| AC-10 | `test_get_tool_schemas_filters_by_allowlist`, `test_get_tool_schemas_anthropic_format` | Schema generation |
| AC-11 | `test_execute_unknown_tool` | Unknown tool handling |
| AC-12 | `test_gateway_with_mocked_service` (memory variant) | MCP client injection |

### Manual Verification (UAT)

- [ ] Start chatServer with new gateway wired in
- [ ] Send a message that triggers a tool call (e.g., "what are my tasks?")
- [ ] Verify tool executes and returns results in the same format as before
- [ ] Check `audit_logs` table for the new `trust_tier` column
- [ ] Verify a Recommend-tier tool queues for approval correctly
- [ ] Verify `chatServer/tools/` directory is empty (all files deleted)

## Edge Cases

- **User has no allowlist config yet:** Fall back to system defaults. All 29 current tools available at their `default_granted_tier` (preserving existing behavior). First-time users get a working agent without configuration. New tools added post-migration are disabled by default until the user or system enables them.
- **Tool definition missing from config service:** Log warning, return denial. The gateway never crashes on missing definitions — it degrades to "tool not available."
- **OAuth token expired during execution:** CredentialProvider handles refresh transparently (same pattern as current `_refresh_access_token` in gmail_tools.py). If refresh fails, executor returns an error message, not a crash.
- **MCP client not provided:** Memory tool executors return "Memory service unavailable" (same as current ToolExecutionService's memory tool rejection, but as a runtime check rather than a hardcoded blocklist).
- **Concurrent tool execution:** The gateway is stateless per call. Multiple tool calls in a single turn (parallel tool use in Anthropic API) each get their own gateway.execute() call. No shared mutable state.
- **Tool definition changes while agent is active:** In-memory cache with TTL (60s). Worst case, a stale definition is used for one request. Acceptable for the config change frequency.
- **Approval flow for Recommend-tier tools:** The gateway queues the action via PendingActionsService (same as current wrap_tools_with_approval). The ConversationHandler (SPEC-033) handles the approval response and calls gateway.execute() again with an approval token. Detail of the re-execution flow is in SPEC-033.

## Functional Units (for PR Breakdown)

Single branch `feat/SPEC-034-capability-gateway`, single PR. Sequential execution:

1. **FU-1: Gateway core + schemas + allowlist** (database-dev + backend-dev)
   - Migration: add `trust_tier` column to `audit_logs`
   - `chatServer/capabilities/schemas.py` — TrustTier, ToolDefinition, TaggedContent, CapabilityResult, ExecutionContext
   - `chatServer/capabilities/allowlist.py` — AllowlistResolver
   - `chatServer/capabilities/gateway.py` — CapabilityGateway class (full pipeline)
   - `chatServer/capabilities/__init__.py`
   - Unit tests for gateway, allowlist, schemas, security
   - **ACs covered:** AC-01, AC-02, AC-03, AC-05, AC-06, AC-07, AC-10, AC-11

2. **FU-2: Capability executors — service-backed tools** (backend-dev)
   - `chatServer/capabilities/executors/tasks.py` — 4 executors
   - `chatServer/capabilities/executors/reminders.py` — 3 executors
   - `chatServer/capabilities/executors/schedules.py` — 3 executors
   - `chatServer/capabilities/executors/briefing.py` — 1 executor
   - `chatServer/capabilities/executors/config.py` — 1 executor (update_instructions)
   - `chatServer/capabilities/executors/__init__.py` — executor registry
   - Regression tests for all 12 service-backed tools
   - **ACs covered:** AC-08 (partial)

3. **FU-3: Capability executors — OAuth + MCP + external** (backend-dev)
   - `chatServer/capabilities/executors/gmail.py` — 2 executors + credential handling
   - `chatServer/capabilities/executors/gmail_compose.py` — 2 executors
   - `chatServer/capabilities/executors/calendar.py` — 2 executors
   - `chatServer/capabilities/executors/memory.py` — 10 executors (MCP delegation)
   - `chatServer/capabilities/executors/web_search.py` — 1 executor
   - `chatServer/capabilities/gateway.py` — CredentialProvider class
   - Regression tests for all 17 OAuth/MCP/external tools
   - Security tests for credential isolation
   - **ACs covered:** AC-04, AC-08 (complete), AC-12

4. **FU-4: Cleanup — delete old system** (backend-dev)
   - Delete `chatServer/tools/*.py` (11 files)
   - Delete `chatServer/security/tool_wrapper.py`
   - Delete `chatServer/security/approval_tiers.py`
   - Delete `chatServer/services/tool_execution.py`
   - Remove `TOOL_REGISTRY`, `GMAIL_TOOL_CLASSES`, `load_tools_from_db` from `agent_loader_db.py`
   - Delete old test files, replace with new registry completeness tests
   - Update any imports in chat.py, session_open_service.py, etc. that reference deleted modules
   - **ACs covered:** AC-09

**Merge order:** FU-1 → FU-2 → FU-3 → FU-4 (strictly sequential, same branch)

**Note:** FU-4 can only execute after SPEC-033 (ConversationHandler) is wired to use the gateway. If SPEC-033 is not yet complete when FU-1–3 finish, FU-4 waits. The old and new systems can coexist temporarily — the gateway is additive until the old system is removed.

## Decisions (Resolved)

1. **Allowlist default:** All 29 current tools enabled at their existing tier for existing users. Migration preserves current behavior exactly. New tools added post-migration start disabled by default — must be explicitly enabled.

2. **Tool definition format:** Markdown with YAML frontmatter. Consistent with HQ conventions, agent definitions, and SPEC-032 config files. Power users will read these in the Phase 4 file browser.

3. **Executor location:** `chatServer/capabilities/executors/` — self-contained package under the gateway. Executors are gateway-internal and should not be imported directly by other modules.

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-12)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (gateway ↔ SPEC-033, gateway ↔ SPEC-032)
- [x] Technical decisions reference principles (A1, A2, A12, A13, A14, S1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3 → FU-4)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Blast radius mapped (29 tools, 18 files deleted, 3 components modified)
