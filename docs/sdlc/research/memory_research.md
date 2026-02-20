# llm-agent: Architecture Coherence & Feature Proposal

## Executive Summary

Your platform already has the hard parts working: multi-tenant isolation via RLS, tiered approval enforcement at the application layer, multi-channel delivery (web + Telegram + scheduled), and database-driven agent configuration. What it lacks is architectural coherence—the pieces were built incrementally and don't yet compose into a system that feels unified to either developers or end users.

This proposal identifies the structural issues, draws specific lessons from OpenClaw's success patterns, and recommends a phased implementation plan that transforms the current hodgepodge into a coherent platform where agents are autonomous within enforceable bounds, and users don't need to understand the machinery.

---

## Part 1: Current State Assessment

### What Works Well

**The approval system is genuinely good.** The three-tier model (AUTO_APPROVE / REQUIRES_APPROVAL / USER_CONFIGURABLE) with application-layer enforcement is the right architecture. OpenClaw has nothing equivalent—they rely on sandboxing and user trust. Your approach scales to multi-tenant because the enforcement happens in `tool_wrapper.py` after the LLM output, not in the prompt.

**Database-driven agent configuration.** Agent definitions, tool registrations, and schedules in PostgreSQL rather than YAML files is the right call for a multi-tenant system. Config changes don't require redeployment.

**RLS-first data model.** Every table has Row Level Security. The Python code never manually filters by `user_id`. This is a genuine security property most agent frameworks don't have.

**The heartbeat/HEARTBEAT_OK pattern.** You already implemented the proactive-but-quiet pattern that's one of OpenClaw's signature features. Scheduled agents that suppress notifications when nothing needs attention.

### What's Incoherent

**1. Two agent loading paths that don't agree.**

`load_agent_executor_db` (sync) and `load_agent_executor_db_async` exist as separate implementations with different caching strategies, different fallback paths, and different error handling. The sync version calls `asyncio.run()` inside an async context (which will fail in production). The async version uses three separate cache services (`agent_config_cache_service`, `tool_cache_service`, `user_instructions_cache_service`) while the sync version uses none or falls back to raw SQL.

This isn't just code duplication—it's a source of bugs where behavior diverges silently between interactive (async, web/Telegram) and scheduled (sync) paths.

**2. Memory is a single blob, and a better system already exists.**

`agent_long_term_memory` stores a single `notes` TEXT field per user+agent, capped at 4000 characters. The agent must read the entire blob to recall anything and must rewrite the entire blob to save anything. This is fundamentally at odds with the "progressive learning" goal described in the README.

Meanwhile, the min-memory MCP server — already running in production on GCP, already used by Claude Desktop and Claude Code — supports semantic search via Qdrant vector embeddings, entity relationships, hierarchical scoping (global/project/task), typed memories (core_identity/project_context/task_instruction/episodic), and multi-user isolation. The in-app memory is a regression from infrastructure that already exists and is proven.

**3. The prompt assembly is rigidly sectioned.**

`prompt_builder.py` hard-codes a specific section order (Identity → Soul → Channel → Time → Memory → User Instructions → Tools → Onboarding). There's no way to:
- Add context-specific sections (e.g., "Today's calendar" for morning briefings)
- Let tools contribute prompt context (Gmail tool could inject "3 unread from VIPs")
- Weight sections by relevance to the current query
- Inject per-schedule custom context

OpenClaw solves this with their skills system—skills inject context sections conditionally based on what the agent is doing. Your prompt builder is closer to a template than a composable system.

**4. Sessions don't have clear lifecycle semantics.**

`chat_sessions` tracks sessions but doesn't distinguish between:
- An interactive conversation the user is having right now
- A background scheduled run
- A heartbeat check
- A follow-up from an approval action

The `channel` column helps but sessions lack a `purpose` or `isolation_level` concept. OpenClaw's explicit session model (main session with continuity vs. isolated cron sessions that don't pollute the main context) is more principled.

**5. Tool registration is over-engineered for what it does.**

The CRUDTool dynamic schema system with `_create_dynamic_crud_tool_class` is architecturally sophisticated but practically only serves the legacy memory CRUD tools (which are being deprecated). Meanwhile, the actual tools people use (Gmail, tasks, reminders) are purpose-built Python classes. The generic system adds complexity without current payoff.

**6. The frontend is feature-complete but navigation-confused.**

Five nav items (Today, Today Mockup, Focus, Coach, Settings) where "Today Mockup" is still in navigation, two separate ChatPanel implementations (V1 and V2), and the core interaction model isn't clear: Is this a task manager? A chat interface? A dashboard? Users shouldn't have to figure this out.

---

## Part 2: What OpenClaw Gets Right (Specifically)

Drawing from both the codebase research and community documentation, these are the patterns that have generated the most user value:

### Pattern 1: The Agent Initiates, Not Just Responds

OpenClaw's most revolutionary UX insight: the agent reaches out to you. Heartbeats, cron jobs, and proactive notifications mean users open their phone to find their agent has already done useful work. You have the infrastructure for this (scheduled execution, notification service, Telegram push) but it's not the primary UX—it's a feature buried behind schedule creation.

**What to steal:** Make proactive behavior the default experience. When a user signs up, the first thing that happens shouldn't be an empty chat window—it should be the agent reaching out with "I checked your email and here's what needs attention."

### Pattern 2: Memory Flush Before Context Loss

OpenClaw prompts the agent to write durable notes before a session compacts. This prevents the common failure mode where a long conversation builds up important context that's lost when the window slides.

**What to steal:** Before a chat session is marked stale (`deactivate_stale_chat_session_instances`), inject a "write anything important to memory" prompt. This transforms your memory from something the agent occasionally remembers to do into a systematic context preservation mechanism.

### Pattern 3: Isolated Sessions Prevent Context Pollution

A morning briefing shouldn't inherit yesterday's debugging conversation. OpenClaw makes this explicit: cron jobs get fresh sessions, the main session maintains continuity.

**What you already have (partially):** Your scheduled execution service creates isolated sessions with `f"scheduled_{agent_name}_{timestamp}"`. But there's no concept of a "main session" that persists across interactive conversations. Each web chat appears to create a new session, losing continuity.

### Pattern 4: Skills as Composable Context

Rather than a monolithic system prompt, OpenClaw lets skills inject relevant sections. A "Gmail skill" adds Gmail-specific instructions only when Gmail tools are loaded. A "calendar skill" adds scheduling awareness only when calendar tools are present.

**What to steal:** Transform your prompt builder from a rigid template into a composable system where each registered tool can contribute prompt context. When the agent has Gmail tools, the prompt should include Gmail-specific guidance. When running a heartbeat, the prompt should include the heartbeat checklist. This replaces the current "soul" megaprompt with modular, testable sections.

### Pattern 5: The User's Mental Model Is Simple

Despite enormous internal complexity, OpenClaw users think in simple terms: "My agent checks my stuff and tells me what matters." The complexity (sessions, tools, skills, sandboxes) is invisible. Your current architecture surfaces too much of its own complexity: separate Coach and Today views, visible agent names, explicit session management.

---

## Part 3: Proposed Features

### Feature Set A: Coherent Agent Runtime (Developer Experience)

#### A1. Unified Async Agent Loader

**Problem:** Two divergent loading paths.
**Solution:** Delete the sync path. Make `load_agent_executor_db_async` the single source of truth. The scheduled execution service already runs in an async context—there's no reason for the sync version to exist.

```python
# What changes:
# 1. Delete load_agent_executor_db (sync)
# 2. Rename load_agent_executor_db_async → load_agent_executor
# 3. ScheduledExecutionService calls the async version directly
# 4. Remove all asyncio.run() calls from agent loading
```

**Effort:** Small. Mostly deletion and rewiring.

#### A2. Composable Prompt System

**Problem:** Rigid prompt template.
**Solution:** Replace `build_agent_prompt` with a section-based builder where tools and features register their own prompt contributions.

```python
class PromptSection:
    key: str           # "gmail_guidance", "heartbeat_checklist", etc.
    content: str       # The actual text
    priority: int      # Ordering (lower = earlier in prompt)
    condition: Callable # When to include (e.g., lambda ctx: "gmail" in ctx.tool_names)

class PromptBuilder:
    sections: list[PromptSection]
    
    def register(self, section: PromptSection): ...
    def build(self, context: PromptContext) -> str: ...
```

Each tool registers its prompt section at tool-load time. The prompt builder evaluates conditions and assembles only the relevant sections. This eliminates the monolithic soul prompt and makes the system testable—you can verify that loading Gmail tools adds Gmail guidance.

**Effort:** Medium. Requires refactoring prompt_builder.py and updating tool registration.

#### A3. Session Lifecycle Model

**Problem:** Sessions lack clear semantics.
**Solution:** Add explicit session types with defined behaviors.

| Session Type | Context Source | Memory Behavior | Delivery |
|---|---|---|---|
| `interactive` | Chat history window (k=50) | Flush on deactivation | Direct to channel |
| `scheduled` | Fresh (no history) | Write-only (report results) | Via notification |
| `heartbeat` | Fresh + heartbeat checklist | Suppress if HEARTBEAT_OK | Via notification |
| `continuation` | Loads summary from parent session | Append to parent memory | Via notification |

The `continuation` type is new and important: when a scheduled job finds something that needs follow-up, it can spawn a continuation session that carries summarized context forward.

**Schema change:**
```sql
ALTER TABLE chat_sessions ADD COLUMN session_type TEXT 
  NOT NULL DEFAULT 'interactive'
  CHECK (session_type IN ('interactive', 'scheduled', 'heartbeat', 'continuation'));
ALTER TABLE chat_sessions ADD COLUMN parent_session_id UUID REFERENCES chat_sessions(id);
```

**Effort:** Medium. Schema change + updates to session creation in chat service and scheduled execution.

#### A4. Migrate Memory to min-memory MCP Server

**Problem:** The in-app memory (`agent_long_term_memory`, `SaveMemoryTool`, `ReadMemoryTool`) is a 4000-char blob with no search, no structure, and no continuity with other tools. A production-grade memory server (min-memory) already exists with semantic search, entity relationships, hierarchical scoping, and cross-tool continuity.

**Solution:** Replace the in-app memory tools with thin HTTP clients that call the min-memory server. This gives agents access to the same memory that Claude Desktop, Claude Code, and any MCP-compatible client can read and write.

**Architecture:**

```
┌─────────────────────┐     ┌──────────────────────────┐
│   llm-agent         │     │   min-memory (GCP)       │
│   chatServer        │     │                          │
│                     │     │   Starlette + MCP        │
│  ┌───────────────┐  │     │   Qdrant vector store    │
│  │ MemoryTools   │──┼─────┤   fastembed (bge-small)  │
│  │ (HTTP client) │  │     │   OAuth2 (Auth0) for     │
│  └───────────────┘  │ HTTP│     MCP clients          │
│                     │     │   Trusted backend key for │
│  Auth: Supabase JWT │     │     server-to-server     │
└─────────────────────┘     └──────────────────────────┘
        │                              │
        │                              │
   Users via web/                 Claude Desktop /
   Telegram/scheduled             Claude Code /
                                  ChatGPT + MCP
```

**The cross-tool continuity is the key value proposition.** A user tells Claude Desktop about a project; the next morning when llm-agent's heartbeat fires, it has that context. No other agent platform offers this — memory is always siloed to a single product.

**Implementation steps:**

**Step 1: Add trusted backend auth to min-memory (~30 lines)**

```python
# In min-memory src/auth.py — add alongside existing OAuth
def get_current_user() -> str | None:
    # Check for trusted backend header first (server-to-server)
    request = _get_current_request()  # from Starlette request context
    backend_key = request.headers.get("X-Backend-Key")
    if backend_key and backend_key == os.getenv("TRUSTED_BACKEND_KEY"):
        user_id = request.headers.get("X-User-Id")
        if user_id:
            return user_id
    
    # Fall back to OAuth (MCP clients: Claude Desktop, etc.)
    if not mcp_auth:
        return None
    auth_info = mcp_auth.auth_info
    return auth_info.subject if auth_info else None
```

This preserves OAuth for MCP clients while giving the chatServer a simple authenticated path. The trusted backend key is a shared secret stored in both services' environment variables.

**Step 2: User identity mapping**

The chatServer authenticates users via Supabase (user ID is a UUID). The memory server identifies users by Auth0 subject (`google-oauth2|{google_id}`). These need to resolve to the same person.

Options (pick one):
- **Simplest:** Store the Auth0 subject (or Google ID) in Supabase `auth.users` raw_user_meta_data (Supabase already captures the Google provider ID during OAuth sign-in). The chatServer reads this and passes it as `X-User-Id`.
- **Alternative:** Create a `user_identity_map` table in Supabase that maps `supabase_uid → memory_server_user_id`. Populated during onboarding.

Either way, the mapping is resolved once at agent load time and passed to the memory tools.

**Step 3: New LangChain tools in chatServer (~200 lines)**

```python
# chatServer/tools/memory_tools.py — replace existing tools

class MemoryClient:
    """Async HTTP client for the min-memory MCP server."""
    
    def __init__(self, base_url: str, backend_key: str, user_id: str):
        self.base_url = base_url
        self.headers = {
            "X-Backend-Key": backend_key,
            "X-User-Id": user_id,
            "Content-Type": "application/json",
        }
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/mcp",
                headers=self.headers,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                    "id": 1,
                },
            )
            resp.raise_for_status()
            return resp.json()


class StoreMemoryTool(BaseTool):
    """Store a memory via the min-memory server."""
    name: str = "store_memory"
    description: str = (
        "Save information to long-term memory. Use for facts about the user, "
        "decisions made, project context, preferences, or anything the user "
        "asks you to remember. Memories persist across all sessions and are "
        "searchable. Specify a memory_type and entity for organization."
    )
    # ... args_schema maps to min-memory's store_memory params
    
    async def _arun(self, text: str, memory_type: str, entity: str, 
                     scope: str = "global", **kwargs) -> str:
        result = await self.memory_client.call_tool("store_memory", {
            "text": text,
            "memory_type": memory_type,
            "scope": scope,
            "entity": entity,
            **kwargs,
        })
        return json.dumps(result.get("result", {}).get("content", [{}])[0].get("text", ""))


class RecallMemoryTool(BaseTool):
    """Semantic search over memory via the min-memory server."""
    name: str = "recall"
    description: str = (
        "Search your memory for relevant information. Use before answering "
        "questions about the user, their preferences, past decisions, or "
        "ongoing projects. Returns the most semantically relevant memories."
    )
    
    async def _arun(self, query: str, limit: int = 5, **kwargs) -> str:
        result = await self.memory_client.call_tool("retrieve_context", {
            "query": query,
            "limit": limit,
            "include_related": True,
            **kwargs,
        })
        return json.dumps(result.get("result", {}).get("content", [{}])[0].get("text", ""))


class SearchMemoryTool(BaseTool):
    """Quick keyword search over memory."""
    name: str = "search_memory"
    description: str = "Search for specific memories by keyword."
    
    async def _arun(self, query: str) -> str:
        result = await self.memory_client.call_tool("search", {"query": query})
        return json.dumps(result.get("result", {}).get("content", [{}])[0].get("text", ""))
```

**Step 4: Wire into agent loading**

In `agent_loader_db.py`, when instantiating memory tools, create a `MemoryClient` with the user's memory server identity and pass it to the tools:

```python
# In load_tools_from_db or the async loader
memory_client = MemoryClient(
    base_url=os.getenv("MEMORY_SERVER_URL"),
    backend_key=os.getenv("MEMORY_SERVER_BACKEND_KEY"),
    user_id=resolve_memory_user_id(user_id),  # Supabase UUID → memory server ID
)

# Pass to memory tool constructors
tool_constructor_kwargs["memory_client"] = memory_client
```

**Step 5: Update prompt builder for semantic context injection**

Instead of loading the entire memory blob into the prompt, the prompt builder calls `retrieve_context` at prompt assembly time to inject the most relevant memories:

```python
# In prompt_builder.py
async def build_agent_prompt_async(self, ..., memory_client=None):
    # ... existing sections ...
    
    # Memory context: retrieve top facts and preferences
    if memory_client:
        context = await memory_client.call_tool("retrieve_context", {
            "query": "user preferences and key facts",
            "memory_type": ["core_identity", "project_context"],
            "scope": "global",
            "limit": 10,
        })
        memory_context = format_memory_context(context)
        sections.append(f"## What You Know About This User\n{memory_context}")
```

**Step 6: Deprecation and cleanup**

- Mark `agent_long_term_memory` table as deprecated
- Remove `SaveMemoryTool` / `ReadMemoryTool` (old blob tools)
- Remove `_fetch_memory_notes` / `_fetch_memory_notes_async` from agent loader
- Update onboarding detection to check min-memory instead (call `search` for user-related memories; if empty → onboarding)
- Update tool registry in DB: deactivate old memory tools, register new ones

**What NOT to migrate:** The existing blob data in `agent_long_term_memory` is small enough to re-enter naturally. Don't build a bulk migration — let the agent accumulate fresh structured memories through normal use.

**Effort:** Small-Medium (~3-4 days total).
- 0.5 days: Trusted backend auth in min-memory
- 0.5 days: User identity mapping (read Google ID from Supabase user metadata)
- 1 day: New LangChain tools + MemoryClient
- 0.5 days: Prompt builder update for semantic context injection
- 0.5 days: Wire into agent loader + update tool registrations in DB
- 0.5 days: Testing round-trip (store from llm-agent, verify visible in Claude Desktop)

### Feature Set B: Proactive Agent Behavior (User Experience)

#### B1. Default Heartbeat on Sign-Up

**Problem:** New users see an empty chat window.
**Solution:** When a user completes onboarding, automatically create a heartbeat schedule with sensible defaults.

```python
# On first successful onboarding interaction:
default_heartbeat = {
    "schedule_cron": "0 8 * * 1-5",  # 8am weekdays
    "prompt": "Morning check-in. Review what needs attention today.",
    "config": {
        "schedule_type": "heartbeat",
        "heartbeat_checklist": [
            "Check for any pending approvals",
            "Review tasks due today or overdue",
            "Check for unread notifications"
        ],
        "notify_channels": ["web", "telegram"]
    }
}
```

If Gmail is connected, the checklist expands to include email triage. If tasks exist, it includes task review. The heartbeat grows with the user's integrations.

**Effort:** Small. Just wiring up schedule creation to the onboarding flow.

#### B2. Session-End Memory Flush

**Problem:** Important context lost when sessions deactivate.
**Solution:** Before marking a session stale, trigger a lightweight agent turn that reviews the conversation and saves anything important to the min-memory server.

```python
async def flush_session_memory(session_id: str, user_id: str, agent_name: str):
    """Prompt the agent to save important context before session deactivation."""
    flush_prompt = (
        "This conversation session is ending. Review the conversation above "
        "and save any important information to memory using store_memory. "
        "Focus on: facts you learned about the user, decisions made, "
        "commitments or follow-ups, and preference changes. "
        "Use appropriate memory_type values: 'core_identity' for user facts, "
        "'episodic' for events and decisions, 'task_instruction' for commitments."
    )
    # Run in isolated continuation session with conversation history loaded
    # Uses Haiku for cost efficiency
    # ...
```

This runs with a cheaper model (Haiku) and only fires for sessions with >5 message exchanges (no point flushing a "hello" session). Because it writes to min-memory, the flushed context is immediately available to Claude Desktop, Claude Code, and any other MCP-connected tool.

**Effort:** Medium. Requires loading conversation history into a fresh agent turn. Depends on A4 (min-memory integration).

#### B3. Integration-Aware Tool Guidance

**Problem:** The soul prompt includes generic tool guidance regardless of what's connected.
**Solution:** Tools self-describe their prompt contributions. When Gmail is connected, the agent gets Gmail-specific guidance. When it's not, the agent knows to suggest connecting it.

```python
class GmailSearchTool(BaseTool):
    @staticmethod
    def prompt_contribution(context: PromptContext) -> Optional[str]:
        if context.channel == "heartbeat":
            return (
                "Gmail is connected. During heartbeat checks, scan for:\n"
                "- Emails from VIP senders (check user preferences)\n"
                "- Emails older than 24h without response\n"
                "- Calendar invitations requiring action"
            )
        return "Gmail is connected. Use gmail_search to check email when relevant."
```

Tools that aren't connected can also contribute:
```python
class CalendarTool(BaseTool):
    @staticmethod
    def prompt_contribution_when_missing() -> str:
        return (
            "Calendar is not connected. If the user asks about scheduling, "
            "suggest connecting Google Calendar in Settings > Integrations."
        )
```

**Effort:** Medium. Requires the composable prompt system (A2) as a prerequisite.

#### B4. Approval UX Streamlining

**Problem:** Pending approvals require navigating to a separate view.
**Solution:** Three improvements:

1. **Inline approval in Telegram.** When the agent queues an action, the Telegram notification includes approve/reject buttons (Telegram inline keyboards). No need to open the web app.

2. **Batch approval.** Heartbeat runs that queue multiple actions (e.g., "create 3 tasks from your email") present them as a batch with "approve all" / "review individually" options.

3. **Smart defaults for USER_CONFIGURABLE tools.** After a user approves the same tool type 5 times without rejection, surface a suggestion: "You've approved every create_task action. Want to auto-approve task creation going forward?"

**Effort:** Medium-Large. Telegram inline keyboards require webhook changes. Batch approval needs a new UI component. Smart defaults need a simple counter in user_tool_preferences.

### Feature Set C: Simplified User Experience

#### C1. Single-View Dashboard

**Problem:** Five nav items, two of which are development artifacts.
**Solution:** Collapse to three views:

1. **Home** — The unified dashboard. Shows: latest agent activity (heartbeat results, scheduled run summaries), pending approvals (inline), and active tasks. This replaces Today, Today Mockup, and Focus.

2. **Chat** — The interactive conversation. Replaces Coach/CoachV2. Clean chat interface with the agent. Message input at bottom, conversation history above.

3. **Settings** — Account, integrations, agent preferences, approval preferences, schedule management.

The Home view is what OpenClaw users describe as the "magic": you open the app and your agent has already done work for you. The pending approvals are right there, tasks are visible, and the agent's latest summary is front and center.

**Effort:** Medium. Mostly frontend consolidation, not new backend work.

#### C2. Guided Onboarding Flow

**Problem:** The current onboarding is a chat conversation where the agent asks questions. This works for power users but is awkward for most people.
**Solution:** A structured 3-step onboarding:

**Step 1: "What should I watch?"**
- Connect Gmail (OAuth flow, already built)
- Connect calendar (new, but same OAuth pattern)
- Toggle which integrations to monitor

**Step 2: "How should I reach you?"**
- Link Telegram (already built)
- Set preferred notification times (morning briefing, end-of-day summary)
- Choose notification density (minimal / balanced / proactive)

**Step 3: "Let me learn about you"**
- Short chat conversation where the agent asks 3-4 key questions
- Agent saves facts and preferences to structured memory
- Creates default heartbeat schedule based on connected integrations

After onboarding, the user lands on the Home dashboard, which should already show the first heartbeat result (or a "your first check-in is scheduled for tomorrow at 8am" message).

**Effort:** Medium-Large. Step 1 and 2 are UI work. Step 3 leverages existing onboarding prompts.

#### C3. Transparent Memory View

**Problem:** Users can't see what the agent remembers about them. This erodes trust.
**Solution:** A "What I Know" section in Settings that shows memory entries from the min-memory server, grouped by entity and type (facts, preferences, events, instructions), with the ability to delete any entry.

The chatServer exposes a read-only API that proxies to min-memory's `list_entities` and `retrieve_context` tools. Deletion proxies to `delete_memory` (soft delete). This is critical for the target audience — people who want an AI assistant but are justifiably cautious about what it stores. OpenClaw's memory is transparent (markdown files on your machine). Your hosted service needs an equivalent.

**Effort:** Small-Medium. Backend proxy routes (~50 lines) + frontend view. Depends on A4 (min-memory integration).

---

## Part 4: Prioritized Implementation Plan

### Phase 1: Runtime Coherence (Weeks 1-2)
*Foundation work that makes everything else easier.*

1. **A1: Unified async agent loader** — Delete sync path, single loading implementation
2. **A3: Session lifecycle model** — Schema change + session type enforcement
3. **C1: Single-view dashboard** — Collapse nav to Home/Chat/Settings (frontend only)

**Why this order:** A1 removes a class of bugs. A3 gives you the vocabulary for B2 (memory flush). C1 removes user confusion immediately.

### Phase 2: Memory Migration (Weeks 3-4)
*Replace the blob with the min-memory server. Unlock cross-tool continuity.*

4. **A4: Migrate memory to min-memory** — Trusted backend auth, new LangChain tools, wire into agent loader
5. **B2: Session-end memory flush** — Automatic context preservation via min-memory
6. **C3: Transparent memory view** — User-facing memory browser backed by min-memory

**Why this order:** A4 is the prerequisite for everything memory-related. B2 makes memory useful without user effort. C3 builds trust. Total new code in llm-agent is ~300 lines (HTTP client + tools + proxy routes), not a database migration.

### Phase 3: Proactive UX (Weeks 5-6)
*The features that make users say "this actually helps me."*

7. **A2: Composable prompt system** — Refactor prompt builder
8. **B3: Integration-aware tool guidance** — Tools contribute to prompts
9. **B1: Default heartbeat on sign-up** — Proactive from day one

### Phase 4: Polish & Streamline (Weeks 7-8)
*Reduce friction, increase accessibility.*

10. **C2: Guided onboarding flow** — Structured setup instead of raw chat
11. **B4: Approval UX streamlining** — Inline Telegram approvals, batch approval, smart defaults

---

## Part 5: What NOT to Build

**Don't build a skills marketplace.** OpenClaw has ClawHub but its value comes from the open-source community. A hosted multi-tenant platform benefits more from first-party integrations that work reliably than from a plugin ecosystem.

**Don't build calendar write access yet.** Read-only calendar monitoring is 80% of the value with 10% of the risk. Reading someone's calendar and surfacing "you have a conflict at 2pm" is useful. Autonomously rescheduling meetings is terrifying and one mistake destroys trust.

**Don't build sub-agent spawning.** OpenClaw's `sessions_spawn` is powerful for power users but adds complexity without proportional value for the target audience. One agent per user, with different behaviors in different session types, is sufficient.

**Don't over-invest in the CRUDTool dynamic schema system.** The purpose-built tools (Gmail, tasks, reminders) work well. The generic system isn't earning its complexity. If new tool types are needed, build them as purpose-built classes.

---

## Part 6: Architecture After Implementation

```
User signs up
  → Guided onboarding (connect integrations, set preferences)
  → Initial memories stored in min-memory via store_memory tool
  → Default heartbeat schedule created

Daily flow:
  Morning heartbeat fires
    → Isolated session, checks integrations via tools
    → Each tool contributes relevant prompt context
    → Agent decides what needs attention
    → HEARTBEAT_OK (suppressed) or summary notification
    → Notification delivered to web + Telegram

User opens app:
  Home dashboard shows:
    → Latest agent activity summary
    → Pending approvals (inline approve/reject)
    → Task overview
    → "Chat with your agent" entry point

User chats:
  Interactive session with full memory context
    → Relevant facts and preferences loaded from min-memory into prompt
    → Deeper recall available via recall/search_memory tools
    → Tools wrapped with approval enforcement
    → Session-end memory flush writes to min-memory

Cross-tool continuity:
  User tells Claude Desktop about a new project
    → Claude Desktop writes to min-memory via MCP
    → Next llm-agent heartbeat retrieves that context
    → Agent references the project without being told twice

Agent takes action:
  AUTO_APPROVE → executes immediately
  REQUIRES_APPROVAL → queued, notification sent
  USER_CONFIGURABLE → checks user preference, suggests auto-approve after pattern
```

The coherence comes from: one agent loader, one prompt builder with composable sections, one session model with clear types, one external memory system shared across all tools (min-memory), and one approval system that never lets the LLM bypass it.

---

## Appendix: Key Files Affected

| Feature | Files Modified | Files Created |
|---|---|---|
| A1: Unified loader | `src/core/agent_loader_db.py`, `chatServer/services/scheduled_execution_service.py` | — |
| A2: Composable prompts | `chatServer/services/prompt_builder.py`, all tools | `chatServer/services/prompt_sections.py` |
| A3: Session lifecycle | `chatServer/services/chat.py`, `chatServer/services/background_tasks.py` | Migration |
| A4: min-memory integration | `chatServer/tools/memory_tools.py`, `src/core/agent_loader_db.py`, `chatServer/services/prompt_builder.py` | `chatServer/services/memory_client.py` |
| A4 (min-memory side) | `min-memory/src/auth.py` | — |
| B1: Default heartbeat | `chatServer/services/prompt_builder.py` (onboarding section) | — |
| B2: Memory flush | `chatServer/services/background_tasks.py` | `chatServer/services/memory_flush_service.py` |
| B3: Tool guidance | All tool files in `chatServer/tools/` | — |
| B4: Approval streamlining | `chatServer/channels/telegram_bot.py`, `chatServer/routers/actions.py` | Migration (approval counter) |
| C1: Dashboard | `webApp/src/pages/`, `webApp/src/navigation/` | `webApp/src/pages/HomeDashboard.tsx` |
| C2: Onboarding | `webApp/src/pages/` | `webApp/src/pages/Onboarding/` |
| C3: Memory view | `chatServer/routers/` (new proxy route) | `webApp/src/pages/Settings/Memory.tsx`, API hooks |