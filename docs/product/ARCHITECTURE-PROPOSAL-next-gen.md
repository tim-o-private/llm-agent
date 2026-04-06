# Architecture Proposal: Clarity Next-Gen

> **Status:** Draft v1 — awaiting Tim's review
> **Author:** Claude (Architecture)
> **Date:** 2026-04-06
> **Input:** PRODUCT-BEHAVIOR-SPEC-next-architecture.md, VISION.md, PRD-003, HQ reference implementation, technology research

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WEB FRONTEND (React)                        │
│                                                                     │
│   Chat UI ←──→ SSE Stream        File Browser ←──→ Config API      │
│                                                                     │
└──────────┬──────────────────────────────┬──────────────────────────┘
           │ WebSocket / HTTP              │ REST
           ▼                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │   Chat       │  │  Workflow        │  │  Config                │ │
│  │   Router     │  │  Engine          │  │  Service               │ │
│  │              │  │  (LangGraph)     │  │  (Supabase Storage)    │ │
│  │  Messages    │  │                  │  │                        │ │
│  │  in/out,     │  │  Graph runner,   │  │  User-scoped FS,      │ │
│  │  streaming   │  │  checkpointing,  │  │  overlay resolution,   │ │
│  │              │  │  human gates     │  │  version tracking      │ │
│  └──────┬───────┘  └────────┬─────────┘  └───────────┬────────────┘ │
│         │                   │                         │              │
│  ┌──────▼───────────────────▼─────────────────────────▼────────────┐ │
│  │                    AGENT LAYER                                   │ │
│  │                                                                  │ │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │ │
│  │  │  Conversation   │  │  Capability      │  │  Sandbox       │ │ │
│  │  │  Handler        │  │  Gateway         │  │  Enforcer      │ │ │
│  │  │  (Anthropic API │  │  (server-side    │  │  (tool allow-  │ │ │
│  │  │   + tools)      │  │   auth, CLI      │  │   list, data   │ │ │
│  │  │                 │  │   tool proxy)    │  │   tagging)     │ │ │
│  │  └─────────────────┘  └──────────────────┘  └────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    DATA LAYER                                    │ │
│  │  PostgreSQL (Supabase) │ Supabase Storage │ Supabase Auth       │ │
│  │  Sessions, messages,   │ User config FS   │ OAuth, tokens       │ │
│  │  audit log, tasks      │ (overlay store)  │ (server-side)       │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**Three key shifts from current architecture:**

1. **Conversation + orchestration split.** The chat handler remains a single LLM agent (Anthropic API direct), but it can now *trigger workflows* that execute as LangGraph graphs server-side. No separate "workflow engine" the user sees — just one agent that sometimes talks and sometimes orchestrates.

2. **Capability Gateway replaces custom tool classes.** Instead of `BaseTool` subclasses with embedded business logic, tools become thin wrappers that delegate to CLI tools or service endpoints. Auth tokens injected server-side, never exposed to the agent context.

3. **User-scoped config in Supabase Storage.** Agent definition, workflows, preferences, and allowlists stored as files in Supabase Storage with RLS isolation. Overlay pattern: system defaults + user customizations.

---

## 2. The Seven Open Questions

### Q1: What Handles User Messages?

**Recommendation: Single conversational agent with workflow dispatch.**

The user always talks to one agent. That agent has two modes of operation, invisible to the user:

**Mode A — Conversation (90% of messages).** Standard LLM tool-loop. User asks a question, agent reasons, maybe calls a tool, responds. This uses the Anthropic Messages API directly with streaming. No LangGraph overhead.

**Mode B — Workflow dispatch (10% of messages).** User says "draft a reply to Mike" or a scheduled trigger fires. The conversational agent recognizes this needs a multi-step workflow, looks up the matching graph template, and dispatches it. The graph runs server-side via the Workflow Engine. Progress streams back to the chat as status updates.

```python
# Simplified dispatch logic inside the conversational agent's tool loop
class DispatchWorkflowTool(BaseTool):
    """Agent calls this when it recognizes a workflow trigger."""
    name = "dispatch_workflow"
    description = "Start a multi-step workflow (email triage, draft reply, etc.)"

    async def _arun(self, workflow_name: str, parameters: dict) -> str:
        graph = workflow_engine.load(workflow_name, user_id=self.user_id)
        run_id = await workflow_engine.start(graph, parameters)
        return f"Workflow '{workflow_name}' started (run_id: {run_id}). Progress will stream to chat."
```

**Why not two separate systems (conversation router + orchestrator)?** Because the user should never perceive a seam. If the agent can both answer "what's on my calendar?" and execute a multi-step email triage — from the same conversation — the product feels like talking to a person, not switching between systems.

**Why not run everything through LangGraph?** Anthropic's own guidance: "use the simplest possible pattern." A basic tool-loop for conversation is faster, cheaper, and easier to debug than routing every message through a graph. LangGraph adds value only when there are multiple steps, dependencies, and human gates.

**What stays from current:** `ChatService.process_chat()` concept (single entry point), session management, message history. What changes: the agent executor switches from LangChain's `AgentExecutor` to a lighter Anthropic API tool-loop, with a `dispatch_workflow` tool for graph triggers.

**Tradeoffs considered:**
- *Full LangGraph for everything:* Too heavy for simple conversation. Adds latency, complexity, and token cost on every message.
- *Separate conversation and orchestration services:* Clean separation but creates a routing problem ("is this message a conversation or a workflow trigger?") that the LLM is better at solving than a deterministic router.
- *Claude Agent SDK as conversation handler:* Requires API keys (no subscription billing), alpha quality, wraps the CLI binary. Not suitable for a multi-tenant web server.

### Q2: How Does Server-Side Auth Expose Capabilities to the Agent?

**Recommendation: Capability Gateway — thin tool wrappers with server-side credential injection.**

The agent sees tools like `email_search`, `email_send`, `calendar_list`. Each tool is a thin function that:
1. Validates the request against the user's trust tier and allowlist
2. Injects the user's OAuth token from the server-side token store
3. Calls the underlying service (CLI tool, API client, or service function)
4. Returns the result with the token stripped

```python
class CapabilityGateway:
    """Resolves tool calls to authenticated capability invocations."""

    async def execute(
        self,
        user_id: str,
        tool_name: str,      # e.g., "email_search"
        parameters: dict,     # tool call parameters from the LLM
    ) -> str:
        # 1. Check allowlist
        if not await self.allowlist.is_permitted(user_id, tool_name):
            return f"Permission denied: {tool_name} is not in your allowlist."

        # 2. Check trust tier
        tier = await self.allowlist.get_tier(user_id, tool_name)
        if tier == "inform" and self._is_action(tool_name):
            return f"I can search emails but can't send yet. Want to enable that?"

        # 3. Get credentials (never exposed to agent)
        creds = await self.token_store.get(user_id, tool_name)

        # 4. Execute
        result = await self.executors[tool_name].run(parameters, creds)

        # 5. Tag external data as untrusted
        return tag_untrusted(result, source=tool_name)
```

**Why not CLI tools directly (like HQ's `gog`)?** HQ runs locally where the CLI can read env vars and config files. Clarity runs server-side where the agent process shouldn't have access to raw tokens. The Capability Gateway is the bridge — it gives the agent the *effect* of a CLI tool without exposing credentials to the LLM context.

**Why not keep the current BaseTool pattern?** Current tools embed too much: auth logic, business logic, database calls, error handling. The new pattern separates these concerns:
- **Tool definition** (what the LLM sees): name, description, parameters — stored in user config
- **Capability implementation** (what runs): thin executor that calls the actual service
- **Auth + enforcement** (gateway): allowlist check, tier check, credential injection, audit logging

**Migration path:** Current tools like `search_emails`, `draft_email_reply` become capability executors. The `CapabilityGateway` replaces `wrap_tools_with_approval()` and `ToolExecutionService`. The LLM sees the same tool names; the plumbing changes underneath.

### Q3: How Is the User-Scoped Filesystem Provisioned and Isolated?

**Recommendation: Supabase Storage + RLS, with application-level overlay resolution.**

```
Supabase Storage
├── /system/                    # Read-only defaults (shared across all users)
│   ├── agent/                  # Default agent identity, personality
│   ├── workflows/              # Built-in graph templates
│   ├── tools/                  # Default tool descriptions
│   └── preferences/            # Sensible defaults
│
└── /users/{user_id}/           # Per-user mutable layer
    ├── agent/                  # User's personality overrides
    ├── workflows/              # Custom or modified workflows
    ├── tools/                  # Tool allowlist, custom descriptions
    ├── preferences/            # Learned preferences, style profiles
    └── memory/                 # Agent's observations about the user
```

**Overlay resolution:** When the agent or file browser reads a path like `agent/identity.md`:
1. Check `/users/{user_id}/agent/identity.md` — if exists, return it
2. Fall back to `/system/agent/identity.md`

Writes always go to the user layer. The system layer is immutable (deployed by us, versioned).

**Provisioning on signup:** Copy nothing. The system layer provides all defaults. User layer starts empty — files appear there only when the agent or user makes a modification. First customization creates the path lazily.

**Isolation:** Supabase Storage RLS policy — each row in `storage.objects` has an `owner` column. Policy: `owner = auth.uid()` for user files. System files are public-read via a separate bucket or policy.

**Version tracking (changelog):** An append-only `file_versions` table in Postgres:
```sql
CREATE TABLE file_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    path TEXT NOT NULL,
    content TEXT,
    change_type TEXT NOT NULL,    -- 'create', 'update', 'delete'
    changed_by TEXT NOT NULL,     -- 'agent', 'user', 'system'
    trigger TEXT,                 -- what caused the change
    created_at TIMESTAMPTZ DEFAULT now()
);
```

This gives us the "changelog view" from the behavior spec without requiring actual git. The file browser shows diff history, "what have you changed recently?" queries this table.

**Why not actual git repos per user?** Git is powerful but operationally heavy at scale. Each user gets a repo, which means: repo provisioning, garbage collection, disk management, SSH key management (or HTTP auth), merge conflicts if the agent and user edit simultaneously. Supabase Storage + a versions table gives us 90% of the value (history, diff, rollback) at 10% of the complexity.

**Why not the filesystem directly?** Server-side processes can't safely share a POSIX filesystem across users at scale. Object storage is the right abstraction for a web service.

**Tradeoffs:**
- We lose `git diff` and `git log` natively. The versions table compensates.
- No branching (agent can't "try a change on a branch"). Acceptable for MVP — the rollback mechanism covers the same use case.
- Power users who want "real" git can export their config. Future: add Gitea integration as an advanced option.

### Q4: What Executes Graph Workflows?

**Recommendation: Port HQ's LangGraph-based engine to the chatServer, adapted for server-side multi-tenant execution.**

HQ's orchestrator already has everything we need:
- **Template parser** (`registry.py`): Markdown → `GraphTemplate` → `StateGraph`
- **Config-driven builder** (`builder.py`): Template + services → compiled LangGraph
- **Node factories** (`factory.py`): Generic closures for work, review, human-gate, complete
- **Checkpointer** (`checkpointer.py`): Postgres-backed state persistence
- **Human gates** (`human_gate.py`): LangGraph `interrupt_before` for approval flows
- **Task board** (`task_board.py`): Supabase CRUD for task tracking

**What changes from HQ:**

| HQ | Clarity |
|----|---------|
| Executes via `claude -p` subprocess | Executes via Anthropic Messages API (server-side LLM calls) |
| Single user (Tim) | Multi-tenant (user-scoped state, checkpoints, task boards) |
| Agents defined as `.claude/agents/*.md` | Agent definitions in user-scoped Supabase Storage |
| Filesystem-local working directory | Supabase Storage paths |
| Telegram notifications | Clarity's NotificationService (web + Telegram) |

**Execution model:**

```python
class WorkflowEngine:
    """Manages graph execution for all users."""

    async def start(self, user_id: str, template_name: str, params: dict) -> str:
        # 1. Load template from system + user overlay
        template = self.registry.get_template(template_name)

        # 2. Build graph with user-scoped services
        graph, interrupts = build_from_template(
            template=template,
            engine=AnthropicEngine(user_id=user_id),  # NOT claude -p
            board=TaskBoard(user_id=user_id),
            notifier=NotificationService(user_id=user_id),
            settings=self.settings,
            registry=self.registry,
        )

        # 3. Compile with checkpointer and human gates
        compiled = graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=interrupts,
        )

        # 4. Run (non-blocking — progress streams to chat)
        thread_id = str(uuid4())
        asyncio.create_task(self._run_graph(compiled, thread_id, params))
        return thread_id
```

**The key adaptation:** HQ's `ClaudePEngine` spawns `claude -p` as a subprocess. Clarity's `AnthropicEngine` makes Anthropic Messages API calls directly. This is the right call for a server-side web product because:
- No subprocess management on a server
- Direct streaming integration with the chat WebSocket
- Token counting and cost tracking built into the API response
- No dependency on the `claude` CLI binary being installed server-side

**LangGraph version:** 1.1.6 (latest stable). We use: `StateGraph`, `interrupt()`, `AsyncPostgresSaver`, conditional edges. We don't need: LangGraph Platform, LangGraph Cloud, or the opinionated LangServe layer.

**Why not something simpler (e.g., a custom DAG executor)?** HQ already proved LangGraph works for this exact pattern. The checkpointer gives us pause/resume for free. The `interrupt_before` mechanism solves human-in-the-loop without custom state management. Reimplementing these from scratch would be higher risk for no benefit.

### Q5: How Are Agents Sandboxed?

**Recommendation: Three-layer enforcement — allowlist, gateway, data tagging.**

The sandbox is not a process-level sandbox (no containers, no chroot). It's an application-level enforcement model appropriate for a web service where the "agent" is a set of LLM API calls, not a running process.

**Layer 1: Tool Allowlist (what the agent can do)**

The agent's available tools are determined by the intersection of:
- System-defined tool registry (what tools exist)
- User's tool allowlist (what tools this user has enabled)
- Trust tier per tool (inform/recommend/act)

Tools not in the allowlist literally don't appear in the LLM's tool definitions. The agent can't call what it can't see.

```python
async def get_tools_for_user(user_id: str) -> list[Tool]:
    """Only return tools the user has enabled at their current trust tier."""
    allowlist = await config_service.get_allowlist(user_id)
    all_tools = tool_registry.get_all()
    return [
        make_tool(t, tier=allowlist[t.name].tier)
        for t in all_tools
        if t.name in allowlist
    ]
```

**Layer 2: Capability Gateway (enforcement at execution)**

Even if the agent has a tool, every execution passes through the Capability Gateway (Q2). The gateway enforces:
- Allowlist re-check (defense in depth — the tool exists but is the user still permitted?)
- Trust tier enforcement (inform tools can't take actions)
- Rate limits (prevent runaway loops)
- Audit logging (every invocation recorded)

**Layer 3: Data Tagging (untrusted content handling)**

Content from external sources is tagged at ingestion:

```python
@dataclass
class TaggedContent:
    content: str
    source: str           # "email", "calendar", "web_search"
    trust_level: str      # "untrusted" (external), "user" (user wrote it), "system"

def tag_untrusted(content: str, source: str) -> TaggedContent:
    return TaggedContent(content=content, source=source, trust_level="untrusted")
```

When the agent proposes a config modification, the system checks the provenance chain. If the modification traces back solely to untrusted content (e.g., an email suggested a prompt change), it's blocked or escalated.

**What about secrets?** OAuth tokens live in the `external_api_connections` table, encrypted at rest. The Capability Gateway reads them at execution time and strips them from the response. The agent's LLM context never contains tokens, API keys, or credentials.

**What about network access?** The agent doesn't make HTTP requests. It calls tools. Tools are the only way to reach the outside world, and every tool goes through the gateway. There's no equivalent of "open a socket" — the architecture prevents it by not providing the capability.

**Tradeoffs:**
- No process-level isolation. If there's a bug in the gateway, the agent could theoretically access something it shouldn't. Mitigation: the gateway is small, auditable code. Defense in depth via the allowlist layer.
- No sandboxed code execution. The agent can't run arbitrary code (unlike Claude Code). This is intentional — Clarity is a personal assistant, not a dev tool. If we add code execution later, that's when we'd need process-level sandboxing.

### Q6: What Role Does LangChain Retain?

**Recommendation: LangChain is phased out. Keep only `ChatMessageHistory` temporarily.**

| Component | Current (LangChain) | Next-Gen | Migration |
|-----------|---------------------|----------|-----------|
| **Agent executor** | `AgentExecutor` via `langchain-anthropic` | Anthropic Messages API tool-loop (direct) | Replace — the tool-loop is ~50 lines of code |
| **Tool definitions** | `BaseTool` subclasses | Anthropic-native tool schemas (JSON) + Capability Gateway | Replace — `BaseTool` wrapping adds no value |
| **Message history** | `PostgresChatMessageHistory` | Keep temporarily, replace with direct Postgres writes | Phase out |
| **Prompt assembly** | `build_agent_prompt()` with `string.Template` | Same pattern, no LangChain dependency | Already framework-agnostic |
| **Streaming** | LangChain callback handlers | Anthropic SDK native streaming | Replace — cleaner, no callback hell |
| **LangGraph** | Not currently used | Used for workflow engine only | New addition |

**Why drop LangChain for conversation?** The Anthropic Messages API is now mature enough that the LangChain wrapper adds complexity without value. The `AgentExecutor` loop is:
1. Send messages + tools to API
2. If response has tool_use blocks, execute them, append results
3. Repeat until stop

That's a `while` loop. LangChain wraps it in abstractions (`RunnableSequence`, `AgentExecutor`, callback managers) that make debugging harder and introduce version-coupling risk. The content block normalization issues we've hit (list-of-dicts vs strings) are LangChain-specific — the raw API is predictable.

**Why keep LangGraph?** LangGraph is genuinely useful for stateful multi-step workflows. Its value proposition — state management, checkpointing, interrupt/resume, conditional routing — is real and would be expensive to reimplement. And LangGraph's dependency on LangChain-core is thin (just type definitions).

**Why keep ChatMessageHistory temporarily?** It works. Replacing it is low-priority grunt work. It should be swapped out within 2-3 sprints of the rearchitecture starting, but it's not a blocker.

**Risk:** LangGraph depends on `langgraph-core` which depends on `langchain-core`. We'd carry `langchain-core` as a transitive dependency. This is fine — it's a type/schema library, not the agent framework.

### Q7: How Does Graph Execution Relate to PRD-003's Daemon Model?

**Recommendation: Complementary. Server-side graphs for the personal assistant. Daemon for dev orchestration. They share the same graph format.**

```
┌─────────────────────────────────────────────────┐
│              SHARED GRAPH FORMAT                 │
│  Templates, gate definitions, interfaces         │
│  (system/graphs/*.md — same format)              │
└─────────┬───────────────────────────┬────────────┘
          │                           │
┌─────────▼──────────┐     ┌─────────▼──────────────┐
│  CLARITY SERVER     │     │  CLARITY DAEMON         │
│  (personal agent)   │     │  (dev orchestrator)     │
│                     │     │                         │
│  AnthropicEngine    │     │  ClaudePEngine          │
│  (API calls)        │     │  (claude -p subprocess) │
│                     │     │                         │
│  User's web chat    │     │  User's local machine   │
│  OAuth tokens       │     │  Claude Code sub        │
│  server-side        │     │  User's API/sub key     │
│                     │     │                         │
│  Workflows:         │     │  Workflows:             │
│  email triage,      │     │  SDLC full cycle,       │
│  briefing, draft    │     │  spec→PR, code review   │
│  reply, scheduling  │     │                         │
└─────────────────────┘     └─────────────────────────┘
```

**The insight:** The graph template format is the abstraction boundary. A workflow like `email-triage.md` defines steps, dependencies, and gates — but says nothing about *how* each step executes. The `ExecutionEngine` protocol from HQ (`runner.py`) already encapsulates this:

```python
@runtime_checkable
class ExecutionEngine(Protocol):
    async def run(self, agent: str, prompt: str, working_dir: str,
                  allowed_tools: list[str], output_format: str) -> RunResult: ...
```

- **`AnthropicEngine`** implements this for server-side execution (API calls)
- **`ClaudePEngine`** implements this for local execution (`claude -p`)
- Same graph template, same builder, same state management — different engine

**PRD-003 daemon model is preserved.** The daemon ships separately, connects to Clarity cloud, receives orchestration instructions. It uses `ClaudePEngine`. Everything in PRD-003 about the daemon protocol, progress monitoring, and decision engine still applies — it's just one execution engine among two.

**Phase 3a from PRD-003 maps to this architecture:** Clarity reads specs, generates plans, produces prompts. In Phase 3a the user copies prompts manually. In Phase 3b the daemon executes them. But the *server-side graph engine* for personal assistant workflows ships first and independently — it doesn't wait for the daemon.

**What this means practically:** A single codebase has both engines. The workflow engine picks which engine to use based on the workflow type:
- Personal assistant workflows (email, calendar, briefing) → `AnthropicEngine` (server-side)
- Dev orchestration workflows (SDLC) → `ClaudePEngine` via daemon (local)

---

## 3. What Stays from the Current System

| Component | Status | Notes |
|-----------|--------|-------|
| **Supabase Auth** | Stays | ES256 JWT, OAuth flows, session management |
| **Chat sessions table** | Stays | Universal session registry across channels |
| **Chat message history** | Stays (temporary) | Swap to direct Postgres writes within 2-3 sprints |
| **NotificationService** | Stays | Web + Telegram routing, notification types |
| **OAuth flow / external_api_connections** | Stays | Token storage, refresh logic, consent screen UX |
| **Frontend (React/TypeScript)** | Stays | Chat UI, settings, add file browser component |
| **Telegram handler** | Stays | Channel adapter pattern works |
| **Jobs table + BackgroundTaskService** | Stays | Scheduled workflows dispatch through this |
| **Pending actions (approval flow)** | Stays (modified) | Integrate with trust tier system |
| **Memory tools** | Stays (modified) | Migrate storage from DB to user-scoped filesystem |
| **User instructions** | Stays (modified) | Become a file in user-scoped config |
| **Audit logs** | Stays (expanded) | Add config change tracking |
| **RLS patterns (SPEC-017)** | Stays | Extended to Storage |
| **Agent personality / soul text (SPEC-022)** | Stays | Becomes default `agent/identity.md` in system config |

## 4. What Goes

| Component | Replacement | Migration Path |
|-----------|-------------|----------------|
| **LangChain AgentExecutor** | Anthropic Messages API tool-loop | Write new conversation handler (~200 LOC), migrate tools |
| **BaseTool subclasses** | Capability Gateway + tool schema JSON | Keep tool logic in services, replace tool wrappers |
| **ToolExecutionService** | Capability Gateway | Gateway subsumes execution, approval, and audit |
| **wrap_tools_with_approval()** | Trust tier enforcement in gateway | Trust tiers are the new approval model |
| **Tool registry in DB (agent_tools)** | Tool definitions in user-scoped filesystem | Migrate to config files, keep DB as index/cache |
| **agent_configurations table** | Agent definition files in user-scoped FS | `/system/agent/` + `/users/{id}/agent/` overlay |
| **TOOL_REGISTRY dict in agent_loader** | Discovery from config files | Tool definitions are data, not code |
| **build_agent_prompt() assembly** | Prompt composed from config files | Agent identity + operating model + tool guidance from FS |
| **approval_tiers.py (hardcoded defaults)** | Trust tier config per user in FS | `/users/{id}/tools/allowlist.yaml` |
| **Content block normalization hacks** | Direct API usage (no LangChain content blocks) | Removed entirely |
| **Email-specific services (digest, processing)** | Workflow templates + capability gateway | `email-triage.md` workflow, `email_search` capability |

## 5. Migration Path

**Principle: Incremental replacement, not big-bang rewrite.** Each phase delivers user-visible value and can be shipped independently.

### Phase 0: Foundation (2-3 SPECs)

**Goal:** Infrastructure that everything else builds on.

1. **Supabase Storage setup + Config Service**
   - Create storage buckets (system, user)
   - Implement overlay resolution logic
   - RLS policies for user isolation
   - File browser API (list, read, write, history)
   - Migrate agent personality from DB to `/system/agent/identity.md`

2. **Anthropic Messages API conversation handler**
   - New `ConversationHandler` class: tool-loop over Messages API
   - SSE streaming to frontend (replace LangChain callback streaming)
   - Wire up alongside existing `ChatService` behind a feature flag
   - Migrate one tool (e.g., `search_emails`) to new Capability Gateway pattern

3. **Audit log expansion**
   - `file_versions` table for config change tracking
   - Audit entries for all capability invocations

### Phase 1: Capability Gateway + Trust Tiers (2-3 SPECs)

**Goal:** New tool model, graduated autonomy.

4. **Capability Gateway**
   - Tool definition schema (JSON in config files)
   - Gateway: allowlist check → tier check → credential injection → execute → audit
   - Migrate remaining tools from BaseTool to capabilities
   - Remove ToolExecutionService, wrap_tools_with_approval

5. **Trust tier system**
   - Per-user, per-tool tier config (stored in user FS)
   - Tier enforcement in gateway
   - UI for trust management (or conversational — agent proposes graduation)

6. **Remove LangChain AgentExecutor**
   - Switch ChatService to ConversationHandler
   - Remove langchain-anthropic dependency
   - Keep langchain-core (LangGraph needs it)

### Phase 2: Workflow Engine (2-3 SPECs)

**Goal:** Graph-based workflows for multi-step operations.

7. **Port HQ's graph engine**
   - Template parser, builder, node factories
   - Implement `AnthropicEngine` (server-side execution)
   - Postgres checkpointer (reuse HQ's)
   - `dispatch_workflow` tool for conversational agent

8. **Initial workflows**
   - `email-triage.md` — scheduled email processing
   - `morning-briefing.md` — compose daily briefing
   - `draft-reply.md` — find thread → compose → present for approval

9. **Human-in-the-loop integration**
   - LangGraph `interrupt_before` → notification to user
   - User approval in chat resumes graph
   - Connect to existing pending_actions/notification infrastructure

### Phase 3: Self-Improvement (2-3 SPECs)

**Goal:** Agent can edit its own config within boundaries.

10. **Immutable security boundary**
    - System files marked immutable in storage metadata
    - Allowlist and tier config in immutable layer
    - Agent's write path restricted to mutable config files

11. **Config modification tools**
    - `edit_config` tool: agent can modify mutable files
    - Diff-based approval: changes produce notification with before/after
    - Auto-rollback: revert if behavior metrics degrade

12. **Introspection loop**
    - Scheduled workflow that reviews agent performance
    - Proposes prompt adjustments, new workflows, capability requests
    - Changelog view in file browser

### Phase 4: File Browser + Power Users (1-2 SPECs)

13. **File browser frontend component**
    - Tree view of user config
    - Read/edit with syntax highlighting
    - Version history (from `file_versions` table)
    - Immutable file indicators (lock icon, "requires unlock to edit")

14. **The Red Button**
    - Settings toggle that unlocks the immutable layer
    - Clear warning UX
    - Agent can self-modify without approval gates when enabled

### Phase 5: Daemon Integration (PRD-003)

15. **Daemon protocol + ClaudePEngine**
    - WebSocket protocol for daemon ↔ server
    - Share graph templates with server-side engine
    - Progress reporting, session management
    - This is PRD-003 Phase 3b

---

## 6. Risks and Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Supabase Storage performance for config reads** | Every agent invocation reads config files. Latency matters. | Cache aggressively (in-memory per user, TTL 60s). Config changes are rare; reads are frequent. |
| **LangGraph version coupling** | LangGraph is at 1.1.6 with frequent releases. Breaking changes possible. | Pin version. Use only stable APIs (StateGraph, interrupt, AsyncPostgresSaver). Avoid LangGraph Platform/Cloud. |
| **Anthropic API as execution engine** | Server-side LLM calls cost per token. Multi-step workflows could be expensive. | Token budgets per workflow. Shorter, focused prompts per step (not the full agent prompt). Model routing (Haiku for simple steps). |
| **Overlay resolution complexity** | Edge cases: user deletes a file that exists in system defaults, partial overrides of structured files, etc. | Keep it simple for MVP: file-level override only (no field-level merge). Delete = restore to system default. |
| **Migration disruption** | Users on the current system during migration. | Feature flags per user. Gradual rollout. Both systems run in parallel until migration is complete. |
| **Self-modification testing** | Hard to test that the agent can't escape its sandbox. | Red-team exercises against the config modification system. Prompt injection test suite (per behavior spec 8.4). |

### Open Questions (Need Prototyping)

1. **Streaming architecture for workflows.** How does a background LangGraph execution stream progress into an active chat SSE connection? Options: (a) workflow writes to a Postgres channel, chat handler subscribes; (b) in-memory event bus; (c) workflow writes status to chat_message_history, frontend polls. Need to prototype for latency/complexity tradeoff.

2. **Token cost of multi-step workflows.** Each workflow step is a separate Anthropic API call. A 5-step email triage workflow costs 5x a single message. Is this acceptable? Need to measure with real prompts and decide if model routing (Haiku for classification steps, Sonnet for generation) is necessary from day one.

3. **Config file format.** YAML? Markdown with frontmatter (like HQ)? JSON? Markdown is most readable for power users in the file browser. YAML is most structured for programmatic access. Recommendation: Markdown with YAML frontmatter (consistent with HQ), but this needs UX validation.

4. **Concurrent config modification.** What if the agent and the user edit the same config file simultaneously via file browser? Supabase Storage doesn't have built-in conflict resolution. Options: last-write-wins (simple, potentially surprising), optimistic locking via ETags, or advisory locks. Recommend last-write-wins for MVP with a notification to the other party.

5. **Daemon auth model.** The daemon needs to authenticate with Clarity's server. Options: long-lived API key, OAuth device flow, magic link. This is a PRD-003 concern, not immediate.

---

## 7. Framework and Library Recommendations

| Library | Version | Purpose | Why This One |
|---------|---------|---------|-------------|
| **anthropic** (Python SDK) | Latest (≥0.49) | Direct Messages API calls, streaming, tool use | First-party SDK. No wrapper needed. |
| **langgraph** | 1.1.6 | Workflow graph execution, checkpointing, human gates | Proven in HQ. Interrupt/resume is uniquely valuable. |
| **langgraph-checkpoint-postgres** | Latest compatible | Postgres-backed graph state persistence | HQ already uses this. Works with Supabase Postgres. |
| **FastAPI** | 0.115+ (current) | HTTP backend | Staying. No change. |
| **supabase-py** | Latest | Storage API, Auth, DB (existing) | Already in use. Add Storage operations. |
| **Pydantic** | v2 (current) | Request/response validation, tool schemas | Already in use. |
| **httpx** | Latest | Async HTTP for capability executors | Replace requests where needed. Already a dependency. |

**What we're NOT adding:**
- LangChain (removing it)
- LangServe / LangGraph Platform (unnecessary for self-hosted)
- Claude Agent SDK (API keys only, alpha, wrong fit for multi-tenant server)
- Redis / Celery (Postgres + jobs table is sufficient for our scale)
- Docker per-user (operational complexity we don't need)

---

## Appendix A: Component Dependency Graph

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
  │              │            │            │            │
  │              │            │            │            └─ File Browser + Red Button
  │              │            │            └─ Self-improvement (needs phases 0-2)
  │              │            └─ Workflow Engine (needs gateway + config service)
  │              └─ Capability Gateway + Trust Tiers (needs config service)
  └─ Storage + Config Service + Conversation Handler (independent foundation)

Phase 5 (Daemon) is independent of Phases 3-4 but needs Phases 0-2.
```

## Appendix B: Mapping to Behavior Spec Sections

| Spec Section | Architecture Components |
|-------------|------------------------|
| 1. Conversational Experience | Q1 (Conversation Handler + Workflow Dispatch) |
| 2. Tool Model | Q2 (Capability Gateway), Q5 (Sandbox) |
| 3. Trust & Permissions | Phase 1 (Trust Tiers), Q5 (Allowlist) |
| 4. Self-Improvement | Phase 3 (Immutable Boundary + Config Modification) |
| 5. Open the Hood | Phase 4 (File Browser), Q3 (User-Scoped FS) |
| 6. Workflows | Q4 (LangGraph Engine), Phase 2 |
| 7. PRD-002 Features | Phase 2 (Initial Workflows) |
| 8. Security | Q5 (Sandbox), Phase 0 (Audit), Phase 3 (Immutable Boundary) |

## Appendix C: What This Means for Current SPECs in Flight

**SPEC-029 (Draft Reply)** and any other in-progress work should complete on the current architecture. The migration path is designed so that existing features continue working while new infrastructure builds alongside.

**SPEC-030 (UX Baseline)** and **SPEC-031 (Playwright)** are compatible — UX and testing infrastructure are frontend concerns that carry forward unchanged.

New SPECs for the rearchitecture should follow the phase ordering above. Phase 0 SPECs can begin immediately.
