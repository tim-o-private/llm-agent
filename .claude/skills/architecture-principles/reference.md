# Architecture Principles — llm-agent

This document is the project's decision-making framework. It defines what "correct" means for every change — from database migrations to React components. When you face an ambiguous choice, the answer should be derivable from these principles.

Principles are organized in three tiers:

1. **SDLC Principles (S1-S7)** — How work gets done and verified.
2. **Foundation Principles (F1-F2)** — How architecture and process reinforce each other.
3. **Architectural Principles (A1-A14)** — How code is structured and connected.

## How to Use This Document

- **Before starting work:** Read the full document. Internalize the rationale, not just the rules.
- **When making a decision:** Find the most specific applicable principle. If two principles conflict, the more specific one wins (A-level over F-level over S-level).
- **When something isn't covered:** Apply the rationale of the closest principle to derive the correct behavior. If you cannot derive an answer, flag it — that is an architecture gap (see F1).
- **When you violate a principle:** Document the deviation in `docs/sdlc/DEVIATIONS.md` with the root cause and correction.

---

## SDLC Principles

### S1: "Done" Means Verified, Not Just Built

**Statement:** A feature is not done when the code compiles. It is done when it passes unit tests, lint, integration checks, and works end-to-end.

**Rationale:** Building something that appears to work but fails in production wastes more time than building it right the first time. Unit tests prove individual functions work; end-to-end verification proves the feature works as a user experiences it.

**Enforcement:**
- `task-completed-gate.sh` hook blocks task completion if pytest fails, vitest fails, ruff check fails, or pnpm lint fails.
- New service files without corresponding test files are blocked.
- Reviewer agent checks for test presence before approving.

**Correct:**
```
# New service chatServer/services/reminder_service.py
# Corresponding test: tests/chatServer/services/test_reminder_service.py
# pytest passes, ruff passes, feature tested via API
```

**Incorrect:**
```
# New service chatServer/services/reminder_service.py
# No test file created
# "It works when I call the endpoint manually"
```

---

### S2: Human Attention on Decisions, Not Verification

**Statement:** The human operator acts as CPO/CTO — approving specs, priorities, and design trade-offs. Machines handle verification: linting, testing, pattern enforcement, and review.

**Rationale:** Human attention is the scarcest resource. Spending it on "did the import order change?" or "are tests passing?" is waste. Automated gates free humans to focus on product direction, UX judgment, and architectural trade-offs that require context machines lack.

**Enforcement:**
- `validate-patterns.sh` hook catches anti-patterns on every file write.
- `task-completed-gate.sh` runs full test/lint suite before task completion.
- Reviewer agent checks scope boundaries, contract compliance, and pattern adherence.
- Human reviews specs and PRs for product correctness, not mechanical checks.

**Correct:**
```
Human: Reviews spec for "add email digest scheduling" — approves UX and data model.
Machines: Validate migrations have RLS, services have tests, hooks use getSession().
```

**Incorrect:**
```
Human: Manually checks that every file uses correct imports and naming conventions.
```

---

### S3: Principles Are Executable, Not Advisory

**Statement:** If a principle has no enforcement mechanism (hook, lint rule, test, or gate), it is a suggestion, not a standard. Every principle in this document has at least one enforcement mechanism.

**Rationale:** Agents and developers will drift from unenforced guidelines over time. The only reliable standards are the ones the system physically prevents you from violating. Advisory guidelines create false confidence — people believe they are followed when they are not.

**Enforcement:**
- This document lists enforcement for every principle.
- Missing enforcement is itself a gap that must be filed and addressed.
- `validate-patterns.sh` and `task-completed-gate.sh` are the primary enforcement hooks.

**Correct:**
```
Principle: "Agent references use UUID FK, not agent_name TEXT"
Enforcement: validate-patterns.sh blocks `agent_name TEXT` in migration files.
```

**Incorrect:**
```
Principle: "Try to use semantic color tokens when possible"
Enforcement: None. Developers use whatever colors they want.
```

---

### S4: Agents Understand WHY, Not Just WHAT

**Statement:** Every rule includes its rationale so agents can generalize to novel situations they have never encountered before.

**Rationale:** Rules without rationale produce brittle compliance. An agent told "use UUID FKs" will follow the rule for tables it has seen, but invent a TEXT reference for a new entity. An agent told "UUID FKs exist because name-based references break when entities are renamed, create ambiguous joins, and cannot enforce referential integrity" will apply the principle to any new table.

**Enforcement:**
- This document pairs every principle with a rationale section.
- Reviewer agent checks that new patterns include rationale in skill docs.
- `docs/sdlc/DEVIATIONS.md` captures cases where an agent failed to generalize.

**Correct:**
```
Rule: Use `Depends(get_supabase_client)` for database access.
Why: Dependency injection enables testing with mocks, enforces single
     connection management, and makes the dependency graph explicit.
```

**Incorrect:**
```
Rule: Use `Depends(get_supabase_client)` for database access.
Why: (not provided — agent creates a global client in a new file)
```

---

### S5: Spec = Contract with User

**Statement:** Once a spec is approved by the human operator, the system delivers the complete feature without further human intervention. The spec is a contract, not a conversation starter.

**Rationale:** Specs that require ongoing clarification during implementation are incomplete specs. Every ambiguity resolved during coding is a spec gap that should have been caught during review. Complete specs enable parallel work: multiple agents can execute against well-defined contracts simultaneously.

**Enforcement:**
- Orchestrator agent decomposes specs into cross-team contracts with explicit schema, API, and config details.
- Reviewer agent checks that implementation matches the spec contract.
- Deviations from spec require explicit re-approval, not silent drift.

**Correct:**
```markdown
## Contract: database-dev -> backend-dev
### Schema provided:
- Table: reminders (id UUID PK, user_id UUID FK, agent_id UUID FK, ...)
- RLS: SELECT/INSERT/UPDATE/DELETE with is_record_owner(user_id)
### What backend must implement:
- ReminderService with CRUD operations
- reminder_router.py with GET/POST/PATCH/DELETE endpoints
```

**Incorrect:**
```
"Build a reminders feature. Ask me if you have questions."
```

---

### S6: Fail Fast, Fail Loudly, Fail Early

**Statement:** Issues must be caught at the earliest possible stage. A migration error caught by a hook is better than one caught in review. A review catch is better than a production failure.

**Rationale:** The cost of fixing a defect increases exponentially with how far it travels. A typo caught by a lint hook costs seconds. The same typo caught in production costs hours of debugging, a hotfix, and a deploy. Progressive gates — hook, lint, test, review, UAT — form a series of increasingly expensive safety nets.

**Enforcement:**
- `validate-patterns.sh` fires on every file write (earliest possible catch).
- `task-completed-gate.sh` fires before task completion (pre-commit quality).
- Reviewer agent fires after implementation (design-level review).
- UAT tester fires on the integration branch (end-to-end verification).

**Correct:**
```
# validate-patterns.sh catches `agent_name TEXT` in a migration immediately
BLOCKED: 'agent_name TEXT' in migration. Use 'agent_id UUID NOT NULL
REFERENCES agent_configurations(id) ON DELETE CASCADE'.
```

**Incorrect:**
```
# agent_name TEXT in migration goes unnoticed until production query
# returns wrong results after an agent is renamed.
```

---

### S7: Institutional Knowledge Compounds

**Statement:** Every deviation, bug fix, and hard-won lesson becomes encoded in the system — as a hook, lint rule, skill doc, or gotcha entry. Knowledge that lives only in a person's head will be lost.

**Rationale:** This project is built by multiple agents and a human operator. No single participant has full context. The only reliable memory is the codebase itself: CLAUDE.md gotchas, skill checklists, enforcement hooks, and deviation logs. Each encoding makes the next agent smarter and the next bug less likely.

**Enforcement:**
- "Resolving Bugs and Problems" section in CLAUDE.md requires documentation updates with every fix.
- `docs/sdlc/DEVIATIONS.md` captures agent mistakes with root cause and correction.
- Corrections must update at least one of: CLAUDE.md, skill docs, hooks, or agent definitions.

**Correct:**
```
Bug: Agent used `from chatServer.module` in except ImportError block.
Fix: Corrected import. Added validate-patterns.sh rule to block this pattern.
Updated: CLAUDE.md gotcha #15, validate-patterns.sh hook.
```

**Incorrect:**
```
Bug: Agent used wrong import pattern.
Fix: Changed the import. Moved on.
```

---

## Foundation Principles

### F1: Architecture Is Prescriptive, Not Descriptive

**Statement:** The architecture defines repeatable patterns that determine where new code goes, how it is structured, and what it depends on. If an agent invents new structure, that is an architecture gap — not creativity.

**Rationale:** Descriptive architecture documents what exists today. Prescriptive architecture defines what must exist tomorrow. When an agent needs to add a "notifications" feature, the architecture should tell it exactly: `notification_service.py` in `chatServer/services/`, `notifications_router.py` in `chatServer/routers/`, `useNotificationHooks.ts` in `webApp/src/api/hooks/`. No guessing. No invention.

**Enforcement:**
- `task-completed-gate.sh` advisory checklist reminds agents of correct patterns per file type.
- Reviewer agent checks that new files follow prescribed naming and placement.
- A10 (naming predictability) makes correct placement derivable from the domain entity.

**Correct:**
```
New feature: "task management"
Agent derives: task_service.py, task_router.py (backend)
              useTaskHooks.ts, useTaskApi.ts (frontend)
              tests/chatServer/services/test_task_service.py
```

**Incorrect:**
```
New feature: "task management"
Agent creates: chatServer/task_handler.py (new pattern, wrong location)
              webApp/src/taskUtils.ts (not in api/hooks/, wrong naming)
```

---

### F2: Architecture Makes Standards Self-Evident

**Statement:** Knowing the layer relationships (router -> service -> database) predicts naming, data flow, shape, and test strategy. Standards should not need to be memorized — they should be derivable from understanding the architecture.

**Rationale:** If you understand that routers wire dependencies and delegate to services, you know that a router function should be 5-10 lines (inject deps, call service, return result). If you understand that React Query manages server state, you know not to duplicate API data into Zustand. The architecture is the standard — everything else is a corollary.

**Enforcement:**
- Reviewer agent checks that routers delegate to services (not inline logic).
- ESLint blocks direct Tailwind colors (enforces semantic token architecture).
- `task-completed-gate.sh` advisory checklist reminds of layer-appropriate patterns.

**Correct:**
```python
# Knowing the architecture, you can predict this router pattern:
@router.get("/sessions")
async def get_sessions(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    service = ChatHistoryService(db)
    return await service.get_sessions(user_id=user_id)
```

**Incorrect:**
```python
# Router with inline database queries — violates layer separation
@router.get("/sessions")
async def get_sessions(user_id: str = Depends(get_current_user)):
    result = supabase.table("chat_sessions").select("*").eq("user_id", user_id).execute()
    return result.data
```

---

## Architectural Principles

### A1: Thin Routers, Fat Services

**Statement:** Routers wire dependencies (`Depends()`) and delegate to services. Business logic, validation, and database interaction live in service classes.

**Rationale:** Thin routers are testable without HTTP, reusable across transports (REST today, WebSocket tomorrow), and readable at a glance. Fat routers couple business logic to HTTP, making it impossible to reuse for Telegram handlers or scheduled tasks. Services are the unit of business logic — routers are the unit of HTTP wiring.

**Enforcement:**
- Reviewer agent flags routers with more than ~15 lines per endpoint.
- `task-completed-gate.sh` advisory checklist reminds of service layer pattern.

**Correct:**
```python
# chatServer/routers/chat_history_router.py
@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    service = ChatHistoryService(db)
    return await service.get_session_messages(
        session_id=session_id, user_id=user_id, limit=limit
    )
```

**Incorrect:**
```python
@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, user_id: str = Depends(get_current_user)):
    db = get_supabase_client()
    result = db.table("chat_message_history").select("*").eq("session_id", session_id).execute()
    messages = [m for m in result.data if m["user_id"] == user_id]  # App-layer filtering!
    return sorted(messages, key=lambda m: m["created_at"])
```

---

### A2: DB-Driven Config, Code-Driven Behavior

**Statement:** Changes that should not require a deploy are config and belong in the database (agent_configurations, agent_tools, prompt templates). Changes that require tests are behavior and belong in code.

**Rationale:** Agent configurations, tool registrations, and prompt templates change frequently and per-user. Deploying code to add a new tool to an agent is too slow. But routing logic, authentication, and data transformation must be tested and version-controlled. The boundary is clear: if a change needs a test, it is code. If a user or operator should be able to change it at runtime, it is config.

**Enforcement:**
- Agent configurations loaded from DB via `agent_loader_db.py`, not YAML files.
- Tool registration is a DB row in `agent_tools`, not a code change.
- Reviewer agent flags hardcoded values that should be configurable.

**Correct:**
```sql
-- Adding a new tool to an agent: DB insert, no deploy needed
INSERT INTO agent_tools (agent_id, tool_name, tool_module, is_enabled)
VALUES ('uuid-here', 'schedule_reminder', 'chatServer.tools.reminder_tools', true);
```

**Incorrect:**
```python
# Hardcoding tool list in Python — requires deploy to change
AGENT_TOOLS = ["gmail", "memory", "reminders", "schedule"]
```

---

### A3: Two Data Planes, Clear Boundary

**Statement:** Supabase REST + RLS handles user-facing CRUD (sessions, tasks, settings). Direct PostgreSQL handles high-volume or framework operations (LangChain message history, agent execution logs).

**Rationale:** Supabase REST provides auto-generated APIs with row-level security — ideal for user CRUD where the frontend talks directly to the database or through thin API endpoints. But LangChain's `PostgresChatMessageHistory` needs direct SQL connections for performance and compatibility. Mixing these planes creates confusion about which client to use. The rule is simple: user data goes through Supabase REST (with RLS); framework data goes through direct PostgreSQL.

**Enforcement:**
- `get_supabase_client` dependency provides the Supabase REST client.
- `chatServer/database/connection.py` provides the direct PostgreSQL connection.
- Reviewer agent checks that user-facing operations use the Supabase client.

**Correct:**
```python
# User CRUD: Supabase REST with RLS
service = ChatHistoryService(supabase_client)
sessions = await service.get_sessions(user_id=user_id)

# Framework operation: direct PostgreSQL
from chatServer.database.connection import get_pg_connection
history = PostgresChatMessageHistory(connection=get_pg_connection(), session_id=chat_id)
```

**Incorrect:**
```python
# Using direct SQL for user CRUD (bypasses RLS)
cursor.execute("SELECT * FROM chat_sessions WHERE user_id = %s", (user_id,))
```

---

### A4: Server State in React Query, Client State in Zustand

**Statement:** Data that comes from the API lives in React Query caches. Data that exists only in the browser (UI state, overlay visibility, theme) lives in Zustand stores. Never duplicate API data into Zustand.

**Rationale:** Duplicating server state into Zustand creates two sources of truth that inevitably drift. React Query handles caching, background refetching, optimistic updates, and stale-while-revalidate — all of which you must reimplement if you put API data in Zustand. Zustand is for ephemeral client state that has no server-side representation.

**Enforcement:**
- ESLint and reviewer agent flag API data stored in Zustand.
- Hooks in `webApp/src/api/hooks/` use React Query exclusively for server data.
- Zustand stores (`useOverlayStore`, `useThemeStore`, `useTaskViewStore`) contain only client state.

**Correct:**
```typescript
// Server state: React Query
const { data: sessions } = useQuery({
  queryKey: ['chat-sessions'],
  queryFn: () => fetchSessions(token),
  enabled: !!user,
});

// Client state: Zustand
const isOverlayOpen = useOverlayStore((s) => s.isOpen);
```

**Incorrect:**
```typescript
// Duplicating API data into Zustand
const useChatStore = create((set) => ({
  sessions: [],
  fetchSessions: async () => {
    const data = await api.getSessions();
    set({ sessions: data });  // Now stale the moment another tab mutates
  },
}));
```

---

### A5: Auth via supabase.auth.getSession()

**Statement:** Frontend API calls always get the auth token from `supabase.auth.getSession()`. Never read auth tokens from Zustand stores, local variables, or cached values.

**Rationale:** `getSession()` returns the current, potentially refreshed token. Zustand's `getState()` returns a snapshot that may be stale or null — especially on first render before the auth listener fires. This is a recurring bug source (CLAUDE.md gotcha #3). The Supabase client handles token refresh transparently; bypassing it creates auth failures.

**Enforcement:**
- `task-completed-gate.sh` advisory checklist reminds of auth pattern for frontend changes.
- Reviewer agent checks that hooks use `getSession()`, not store access.
- Reference pattern in `webApp/src/api/hooks/useChatApiHooks.ts`.

**Correct:**
```typescript
// webApp/src/api/hooks/useChatApiHooks.ts pattern
const { data: sessionData } = await supabase.auth.getSession();
const token = sessionData?.session?.access_token;
const response = await fetch('/api/chat/sessions', {
  headers: { Authorization: `Bearer ${token}` },
});
```

**Incorrect:**
```typescript
// Reading from Zustand — may be null on first render
const token = useAuthStore.getState().session?.access_token;
```

---

### A6: Tools Are the Unit of Agent Capability

**Statement:** Adding a new capability to an agent means: (1) a `BaseTool` subclass in `chatServer/tools/`, (2) a row in the `agent_tools` table, (3) the tool module registered so `agent_loader_db.py` can discover it. No other mechanism exists for extending agent behavior.

**Rationale:** Tools are the composable, auditable, configurable unit of agent capability. They can be enabled/disabled per agent via DB config, wrapped with approval logic, and logged for audit. Hardcoding capabilities in the agent executor or prompt bypasses all of these systems. The tool registry is the single source of truth for what an agent can do.

**Enforcement:**
- `agent_loader_db.py` loads tools exclusively from `agent_tools` DB rows.
- `task-completed-gate.sh` advisory checklist flags changes to tool files.
- Reviewer agent verifies new tools follow the BaseTool pattern and have DB registration.

**Correct:**
```python
# chatServer/tools/reminder_tools.py
class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Create a reminder for the user"
    # ...

# DB registration (migration)
INSERT INTO agent_tools (agent_id, tool_name, tool_module, is_enabled)
VALUES (:agent_id, 'create_reminder', 'chatServer.tools.reminder_tools', true);
```

**Incorrect:**
```python
# Hardcoding capability in the agent executor
if user_message.contains("remind me"):
    create_reminder(user_id, message)  # Bypasses tool system entirely
```

---

### A7: Cross-Channel by Default

**Statement:** Every message feature works across web and Telegram via the shared `chat_id` in `chat_sessions`. A message sent from Telegram is visible on web. A response generated on web can be pushed to Telegram.

**Rationale:** Users interact through whichever channel is convenient. If features only work on one channel, the system fragments into two disconnected products. The shared `chat_id` is the unifying key: `chat_message_history.session_id = chat_sessions.chat_id`. Building channel-specific features creates technical debt that compounds with every new channel.

**Enforcement:**
- `chat_sessions` table has a `channel` column (web, telegram, scheduled).
- `chat.py` service includes `_push_to_telegram_if_linked()` for cross-channel sync.
- Reviewer agent checks that new message features do not assume a single channel.

**Correct:**
```python
# Service handles message storage channel-agnostically
async def store_message(self, chat_id: str, message: str, channel: str):
    # Store in chat_message_history keyed by chat_id
    # Push to Telegram if linked
    await self._push_to_telegram_if_linked(chat_id, message)
```

**Incorrect:**
```python
# Web-only message storage, Telegram can't see these messages
async def store_web_message(self, web_session_id: str, message: str):
    db.table("web_messages").insert({"session_id": web_session_id, ...})
```

---

### A8: RLS Is the Security Boundary

**Statement:** Every user-owned table has Row Level Security policies. Application-layer filtering (`WHERE user_id = ...`) is a convenience, not a security control. RLS is the security control.

**Rationale:** Application code has bugs. A missing `WHERE` clause in one query leaks all users' data. RLS enforces access at the database level — even if the application code is wrong, PostgreSQL will not return rows the user does not own. Defense in depth means the database does not trust the application.

**Enforcement:**
- `validate-patterns.sh` checks migrations for RLS-related patterns.
- `task-completed-gate.sh` advisory checklist flags migration changes.
- Reviewer agent verifies new tables have `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and appropriate policies.

**Correct:**
```sql
-- Migration for new table
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    ...
);
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own reminders" ON reminders
    FOR ALL USING (is_record_owner(user_id));
```

**Incorrect:**
```sql
-- Table with no RLS — relies entirely on application filtering
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    ...
);
-- "We filter by user_id in the service layer"
```

---

### A9: UUID FKs, Never Name Strings

**Statement:** All inter-table references use UUID foreign keys with explicit `ON DELETE` behavior. Never reference entities by name strings.

**Rationale:** Name-based references break when entities are renamed, create ambiguous joins when names collide, and cannot enforce referential integrity at the database level. UUID FKs provide: immutable identity (renaming an agent does not break references), cascade behavior (deleting an agent cleans up related rows), and indexed joins. Legacy tables with `agent_name TEXT` are tech debt being migrated away.

**Enforcement:**
- `validate-patterns.sh` blocks `agent_name TEXT` in new migration files.
- Reviewer agent flags any new TEXT-based entity reference.

**Correct:**
```sql
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    ...
);
```

**Incorrect:**
```sql
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,  -- BLOCKED by validate-patterns.sh
    tool_name TEXT NOT NULL,
    ...
);
```

---

### A10: Naming Is Predictable from Domain Model

**Statement:** Given an entity name "foo", you can predict all file locations: table `foos`, service `foo_service.py`, router `foo_router.py`, hooks `useFooHooks.ts`, tests `test_foo_service.py`.

**Rationale:** Predictable naming eliminates decision fatigue and makes the codebase navigable without a map. An agent asked to build "reminders" should produce exactly the same file structure as an agent asked to build "schedules". Inconsistent naming (e.g., `taskHandler.py` vs `reminder_service.py`) forces every reader to learn arbitrary conventions per feature.

**Enforcement:**
- Reviewer agent checks new files against naming conventions.
- F1 (prescriptive architecture) defines the expected locations.
- `task-completed-gate.sh` check 7 verifies new service files have matching test files by naming convention.

**Correct:**
```
Entity: "schedule"
├── chatServer/services/schedule_service.py
├── chatServer/routers/schedule_router.py (or registered in existing router)
├── chatServer/tools/schedule_tools.py
├── webApp/src/api/hooks/useScheduleHooks.ts
├── tests/chatServer/services/test_schedule_service.py
└── supabase/migrations/YYYYMMDD_create_schedules.sql
```

**Incorrect:**
```
Entity: "schedule"
├── chatServer/scheduling.py          (wrong location, wrong name)
├── chatServer/routers/cron_api.py    (unpredictable name)
├── webApp/src/scheduleUtils.ts       (wrong location, wrong pattern)
```

---

### A11: Design for N, Not for 1

**Statement:** Build pluggable patterns and configuration-driven systems. Adding the second instance of something should require config, not new infrastructure.

**Rationale:** Building for one creates throwaway code. Building for N creates a platform. The agent tool system is a good example: adding a new tool is a DB row and a Python class — not a new router, new migration, and new frontend page. When you build a feature, ask: "What happens when we need 10 of these?" If the answer is "10x the code," the design is wrong.

**Enforcement:**
- Reviewer agent flags one-off patterns that should be generalized.
- A6 (tools as capability unit) is an instance of this principle.
- A2 (DB-driven config) enables N configurations without N deploys.

**Correct:**
```python
# Tool registry: adding a tool is config, not infrastructure
# agent_tools table has rows for gmail, memory, reminders, schedules, tasks...
# Each tool is a BaseTool subclass. Same loading mechanism for all.
tools = load_tools_for_agent(agent_id)  # Works for any number of tools
```

**Incorrect:**
```python
# Hardcoded per-tool loading — adding a tool means modifying this function
def load_tools(agent_name):
    if agent_name == "assistant":
        return [GmailTool(), MemoryTool()]
    elif agent_name == "scheduler":
        return [ScheduleTool()]
```

---

### A12: Autonomy Requires Safety Rails

**Statement:** Agents can act autonomously within defined boundaries. Safety comes from approval tiers, RLS, and audit logs — not from restricting capability.

**Rationale:** An agent that must ask permission for every action is useless. An agent with no guardrails is dangerous. The correct balance is: low-risk actions execute immediately, medium-risk actions require user approval, high-risk actions are blocked. RLS prevents data leakage even if the agent misbehaves. Audit logs enable post-hoc review. This lets agents be useful while keeping humans in control of consequential decisions.

**Enforcement:**
- Pending actions system (`chatServer/routers/actions.py`, `PendingActionsService`) gates medium-risk actions.
- RLS policies enforce data boundaries regardless of agent behavior.
- `AuditService` logs all agent actions for review.
- Reviewer agent checks that new capabilities include appropriate approval tiers.

**Correct:**
```python
# Tool with approval tier — sends email only after user approves
class SendEmailTool(BaseTool):
    requires_approval = True  # Queued in pending_actions, user approves via UI

# Low-risk tool — executes immediately
class SearchMemoryTool(BaseTool):
    requires_approval = False
```

**Incorrect:**
```python
# Agent sends emails with no approval gate
class SendEmailTool(BaseTool):
    def _run(self, to, subject, body):
        gmail.send(to, subject, body)  # No approval, no audit, no undo
```

---

### A13: User-Facing Config Is First-Class

**Statement:** Users can inspect and modify their own settings, agent configurations, and data. Configuration is not hidden in env vars or admin panels.

**Rationale:** If users cannot see or change their settings, they cannot trust the system. Transparent config also reduces support burden — users can self-serve instead of filing tickets. Every user-facing setting should have a UI, an API endpoint, and RLS policies that let users manage their own data.

**Enforcement:**
- RLS policies use `is_record_owner(user_id)` to scope user access.
- A8 (RLS as security boundary) ensures users see only their own data.
- Reviewer agent checks that new user-facing tables have corresponding API endpoints.

**Correct:**
```
# User can view and edit their agent's prompt customizations
GET  /api/agents/{agent_id}/prompt-customizations  (user's own)
POST /api/agents/{agent_id}/prompt-customizations
# RLS ensures user only sees their own agent configs
```

**Incorrect:**
```
# Agent behavior configured only via env vars — users cannot inspect or change
AGENT_TEMPERATURE=0.7  # Hidden in .env, user has no visibility
```

---

### A14: Pragmatic Progressivism

**Statement:** Build abstractions when they are proven necessary, not when they might be needed. Do not over-engineer, but do not paint yourself into corners.

**Rationale:** Premature abstraction is as costly as no abstraction. A generic "plugin system" built before the second plugin exists wastes time and adds complexity. But hardcoding assumptions that will obviously need to change (e.g., "there will only ever be one agent") creates expensive rewrites. The heuristic: build concrete first, extract patterns after the second instance, design for extension from the start.

**Enforcement:**
- Reviewer agent flags over-engineering (unnecessary abstractions for single-use cases).
- Reviewer agent also flags under-engineering (hardcoded values that should be configurable).
- A11 (design for N) provides the threshold: when N=2 arrives, the abstraction is justified.

**Correct:**
```python
# First implementation: concrete and simple
class ReminderService:
    async def create_reminder(self, user_id, agent_id, text, remind_at):
        # Direct implementation, no unnecessary abstraction
        ...

# When schedules arrive: extract common patterns into shared base if needed
```

**Incorrect:**
```python
# Over-engineered: abstract base for a single implementation
class AbstractTemporalEventService(ABC):
    @abstractmethod
    async def create_event(self): ...
    @abstractmethod
    async def resolve_event(self): ...

class ReminderService(AbstractTemporalEventService):
    # The only implementation — abstraction adds complexity with no benefit
    ...
```

---

## Quick Reference

| ID | Principle | Enforcement |
|----|-----------|-------------|
| S1 | Done = verified | task-completed-gate.sh |
| S2 | Humans decide, machines verify | hooks + reviewer agent |
| S3 | Executable, not advisory | every principle has enforcement |
| S4 | WHY, not just WHAT | rationale in all docs |
| S5 | Spec = contract | orchestrator contracts + reviewer |
| S6 | Fail fast, fail early | progressive gates |
| S7 | Knowledge compounds | DEVIATIONS.md + doc updates |
| F1 | Prescriptive architecture | reviewer + naming conventions |
| F2 | Standards are self-evident | layer patterns + reviewer |
| A1 | Thin routers, fat services | reviewer (line count) |
| A2 | DB config, code behavior | agent_loader_db.py pattern |
| A3 | Two data planes | supabase_client vs pg connection |
| A4 | React Query = server, Zustand = client | reviewer + hook patterns |
| A5 | Auth via getSession() | reviewer + reference hook |
| A6 | Tools = capability unit | agent_tools table + BaseTool |
| A7 | Cross-channel by default | shared chat_id + reviewer |
| A8 | RLS = security boundary | migration review + validate-patterns |
| A9 | UUID FKs, not name strings | validate-patterns.sh |
| A10 | Predictable naming | reviewer + task-completed-gate |
| A11 | Design for N | reviewer |
| A12 | Autonomy + safety rails | pending_actions + RLS + audit |
| A13 | User config is first-class | RLS + API endpoints |
| A14 | Pragmatic progressivism | reviewer (over/under-engineering) |
