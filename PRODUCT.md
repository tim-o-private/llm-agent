# Clarity — Product Source of Truth

> **Last updated:** 2026-04-13
>
> This is the single canonical reference for what Clarity is, what exists, what's being built, and what's next. Agents start here. Humans start here. If this document conflicts with a spec, roadmap, or skill — this document wins (and the other one needs updating).

---

## 1. What This Is

Clarity is a personal agent that exercises executive function on behalf of individuals. It manages information across services (email, calendar, tasks), applies judgment about what matters, and acts on your behalf — safely, through a tiered approval system enforced at the application layer.

The core insight: the value of AI is under-realized because managing context is manual and every service optimizes for itself, not for the user. Clarity is the first product that works for the individual across everything.

**Core metric:** User time in the product goes *down* over time. The agent handles more; the user approves less.

**Target user:** Regular humans with overloaded brains — not developers, not power users. 90% will never open a terminal.

See `docs/product/VISION.md` for the full product vision.

---

## 2. What Exists Today

Shipped capabilities, grouped by domain. Each was built via one or more specs (see `docs/sdlc/specs/completed/` for historical detail).

### Agent Runtime

| Capability | What it does |
|-----------|-------------|
| Deep Agents runtime | LangChain Deep Agents (`create_deep_agent()`) builds a LangGraph `CompiledStateGraph`. All agent execution goes through this. |
| Filesystem-based agent config | Agent definitions in YAML + soul.md files at `/data/config/system/agents/{name}/`. Loaded by `AgentConfigLoader` with mtime-based cache invalidation. Hydrated from Supabase Storage on startup. |
| bwrap sandbox | Per-user OS-level isolation via bubblewrap. `/system/` (read-only config, skills) and `/user/` (read-write preferences, memory). Falls back to `FilesystemBackend` if bwrap unavailable. |
| Workflow engine | LangGraph `StateGraph` workflows built from Markdown templates with YAML frontmatter. Human-required gates via `interrupt_before`. Templates at `/system/workflows/` and `/user/workflows/`. |
| Agent memory & skills | Agents read/write working memory at `/user/memory/AGENTS.md`. Skills loaded from filesystem paths. Both synced to Supabase Storage post-invocation. |
| Tool system | `BaseTool` subclasses instantiated per agent config. Tool *definitions* (which tools an agent has) are filesystem YAML; tool *implementations* are Python classes in `chatServer/tools/`. |
| Tool approval | Three-tier system (AUTO_APPROVE, REQUIRES_APPROVAL, USER_CONFIGURABLE) enforced at the application layer via `ApprovalContext` wrapping. Not bypassable via prompt. |
| PostgreSQL checkpointing | `AsyncPostgresSaver` persists conversation state across invocations, keyed by `thread_id`. |
| SSE streaming | `deep_agent_stream.py` adapts Deep Agent `astream()` to SSE for the web frontend. |
| Prompt architecture | Soul text + identity + channel context built dynamically per invocation. |

### Channels

| Capability | What it does |
|-----------|-------------|
| Web chat | React frontend (Vite, Radix UI, Tailwind). SSE streaming. Conversation list sidebar for session switching. Inline notifications and approval messages in chat stream. |
| Telegram | Full conversational channel with tool approval, LTM injection, session tracking. Bidirectional linking. |
| Scheduled execution | Background agent runs via job queue. Heartbeat monitoring with `HEARTBEAT_OK` suppression. Model tiering (Haiku for cost control). |

### Agent Capabilities (Tools)

| Capability | What it does |
|-----------|-------------|
| Gmail | Search, read, draft replies, send (with approval gate). Multi-account OAuth. |
| Email digests | Context-aware digests generated with Haiku, delivered via Telegram/web. |
| Draft-reply workflow | Graph workflow: fetch context → compose draft → present for approval → send. Writing style matched from memory. Email preview card in chat UI. |
| Google Calendar | Read access — events and scheduling context. |
| Morning/evening briefings | Consolidated daily summaries via scheduled workflow. Self-scheduling job handler. |
| Web search | External search for current information. |
| Long-term memory | CRUD tools for cross-session memory. Semantic search via min-memory MCP. Entity tracking. Project-scoped memory. |
| Tasks | Full CRUD. Drag-and-drop UI with quick-add and focus mode. |
| Reminders | Create/list/delete with background delivery loop. |
| Notifications | Multi-channel routing (web DB + Telegram). Inline in chat stream with category-based styling. Useful/not-useful feedback. |

### Platform

| Capability | What it does |
|-----------|-------------|
| Unified sessions | All channels share `chat_sessions` registry with channel tag. Cross-channel state. |
| Universal job queue | Single `jobs` table + handler registry. Handlers: email processing, agent invocation, workflow dispatch, morning briefing, reminders. |
| Conversation history | Users browse and switch between past sessions. Filtered by agent. |
| User-scoped DB | RLS + `UserScopedClient` (routers) / `SystemClient` (background jobs). |
| Proactive bootstrap | First-session onboarding detection, memory-gated. Agent introduces itself and learns about user. |
| Audit trail | All tool executions logged with approval status. |
| OAuth integrations | Gmail, Google Calendar. Settings page with connect/disconnect. Telegram linking. |
| Storage sync | Config and user files synced between Supabase Storage and local filesystem. |

### Frontend (webApp)

| Route | What it does |
|-------|-------------|
| `/today` | Main interface — task management with drag-and-drop, quick add, focus mode |
| `/coach` | Chat interface with agent |
| `/settings` | Integration management (Gmail, Calendar, Telegram, Slack placeholder) |
| Sidebar | Conversation list — past sessions, new conversation, agent filter |
| Chat stream | Inline notifications, approval messages with approve/reject, email preview cards |

---

## 3. What's Being Built

### Current: SPEC-044 implementation branch

Completing the bwrap sandbox backend — `BackendProtocol` implementation for Deep Agents, OS-level per-user isolation.

### Specs 029–044 status

All specs through 044 have been implemented. The rearchitecture wave (033–044) replaced LangChain AgentExecutor with Deep Agents, added the workflow engine, and wired up bwrap sandboxing.

| Spec | Title | Status |
|------|-------|--------|
| 029 | Draft-Reply Workflow | **Complete** — implemented as graph workflow |
| 030 | UX Baseline | **Complete** |
| 031 | UI Test Infrastructure | **Complete** |
| 032 | Assistant-UI Alignment | **Complete** |
| 033 | Conversation Handler | **Complete** — replaced by Deep Agents runtime (043) |
| 034 | Capability Gateway | **Skipped** — tool system stays, tools become CLI commands in sandbox |
| 035 | Config Service | **Complete** — filesystem YAML + Supabase Storage sync |
| 036 | Workflow Engine | **Complete** — LangGraph StateGraph + template registry |
| 037 | Initial Workflows | **Complete** — draft-reply, email-triage, briefings |
| 038 | bwrap Sandbox Provisioning | **Complete** — per-user POSIX namespace |
| 039 | Security Boundary | **Complete** — self-improvement guardrails |
| 040 | Introspection Loop | **Complete** — agent self-optimization |
| 041 | Sandbox Wiring | **Complete** — end-to-end integration |
| 042 | Sandbox Config Authority | **Superseded** by 043 |
| 043 | Deep Agents Runtime | **Complete** — `create_deep_agent()` as sole runtime |
| 044 | bwrap Sandbox Backend | **In Progress** — implementation branch active |

---

## 4. Architecture (Current State)

```
webApp/ (React, Vite, :5173)
  └── api/hooks/ → chatServer API

chatServer/ (FastAPI, Python, :3001)
  ├── routers/ → services/ → database/        (thin routers, fat services)
  ├── dependencies/auth.py                     (ES256 JWT from Supabase)
  ├── tools/                                   (BaseTool subclasses — tool implementations)
  ├── services/deep_agent_builder.py           (builds CompiledStateGraph via create_deep_agent())
  ├── services/agent_config_loader.py          (filesystem YAML config)
  ├── sandbox/bwrap_backend.py                 (per-user OS isolation)
  ├── workflows/                               (LangGraph engine, builder, templates)
  └── config/settings.py

src/core/                                      (agent_loader_db.py — tool instantiation)

supabase/migrations/                           (RLS-first, all tables user-scoped)

/data/config/
  ├── system/agents/{name}/agent.yaml          (agent definitions)
  ├── system/agents/{name}/soul.md             (personality/values)
  ├── system/skills/                           (skill templates)
  └── system/workflows/                        (workflow templates)
```

**Execution flow:**
```
User message → FastAPI endpoint
  → build_deep_agent(user_id, agent_name, session_id, channel)
    → AgentConfigLoader reads YAML + soul.md
    → Tools instantiated from config (BaseTool subclasses)
    → Backend created (BwrapBackend or FilesystemBackend fallback)
    → create_deep_agent(model, tools, system_prompt, backend, skills, memory, checkpointer)
    → Returns CompiledStateGraph
  → agent.ainvoke() or agent.astream()
  → Response → SSE stream or direct return
  → sync_user_files_after_invocation()
```

**Key patterns:**
- All channels converge on `build_deep_agent()` → `create_deep_agent()` → `CompiledStateGraph`
- Background work through `jobs` table + handler registry — never a new table
- User isolation: RLS + `UserScopedClient` (routers) / `SystemClient` (background jobs) + bwrap namespace
- Agent config on filesystem (YAML + soul.md), synced from Supabase Storage
- Workflows are Markdown templates parsed into LangGraph `StateGraph` with optional human gates

**Architecture skills** (for implementation detail):
- `.claude/skills/backend-patterns/` — FastAPI, services, tools
- `.claude/skills/frontend-patterns/` — React, TypeScript, Radix
- `.claude/skills/database-patterns/` — PostgreSQL, Supabase, migrations
- `.claude/skills/product-architecture/` — domain model, primitives, recipes
- `.claude/skills/deep-agents/` — Deep Agents SDK patterns
- `.claude/skills/agent-sdk/` — Claude Agent SDK patterns

---

## 5. What's Next (Unspecced)

Decided work that doesn't have specs yet. Ordered by likely priority, not commitment.

| Item | Notes |
|------|-------|
| Trust tier graduation | Agent proposes Inform→Recommend→Act per domain based on demonstrated judgment. Static tiers exist; dynamic graduation does not. |
| Dynamic tool creation | Agent writes tool config into sandbox filesystem — self-extending without code deployment. |
| Signal processing abstraction | Generic ingest/normalize/enrich/judge pipeline across all signal sources (email is hardwired today). |
| Calendar write access | Agent can schedule/reschedule, not just read. Needs trust tier system. |
| Notification preferences UI | Per-category channel routing settings page. |
| Execution results dashboard | Dedicated view for past scheduled run output (data exists, no UI). |
| Slack integration | New channel, follows Telegram pattern. |

---

## 6. Maintenance Rules

**When a spec completes:** Move its row from section 3 to section 2. Update section 4 if architecture changed.

**When a new spec is written:** Add it to section 3 with accurate status and dependencies.

**When priorities shift:** Update section 5. Remove items that are no longer planned.

**When architecture changes:** Update section 4 to reflect *current* state, not aspirational. Point to design docs for the target.

**When in doubt:** Read the code, not the docs. Then fix the docs.

---

## Document Map

| Document | Purpose | Status |
|----------|---------|--------|
| **PRODUCT.md** (this file) | Single source of truth: what exists, what's building, what's next | Maintained — update at every spec completion |
| `docs/product/VISION.md` | North star product vision, design principles, competitive position | Stable |
| `docs/product/PRODUCT-BEHAVIOR-SPEC-next-architecture.md` | Product behavior constraints for the rearchitecture | Review needed — rearchitecture is mostly complete |
| `docs/product/ARCHITECTURE-DESIGN-v0.1.md` | Technical design for the rearchitecture (v0.1, Apr 2026) | Historical — describes what was built in SPEC-033–044 |
| `docs/sdlc/specs/` | Individual feature specifications | Per-spec lifecycle |
| `docs/sdlc/specs/completed/` | Shipped specs (historical reference) | Frozen |
| `IMPLEMENTATION_PLAN.md` | Rearchitecture sprint coordination | Review needed — wave is nearly complete |
| `.claude/skills/*/` | Domain implementation patterns | Update when patterns change |
| `CLAUDE.md` | Agent operating instructions, gotchas | Update when gotchas discovered |
| `README.md` | External-facing setup + overview | Needs update to reflect Deep Agents architecture |
| `docs/archive/ROADMAP.md` | Milestone tracker (Feb 2026) | Archived — replaced by this file |
| `docs/archive/BACKLOG.md` | Priority queue (Feb 2026) | Archived — replaced by this file |
| `docs/archive/*` | Pre-rearchitecture docs (decomposition plans, message flow, Feb review) | Archived |
