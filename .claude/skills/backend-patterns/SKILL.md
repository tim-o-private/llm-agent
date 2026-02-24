---
name: backend-patterns
description: FastAPI backend and LangChain agent patterns for chatServer/ and src/. Use when writing or modifying Python code in chatServer/, src/core/, or tests/. Covers service layer, dependency injection, Pydantic validation, RLS, auth (ES256), CRUDTool, agent loading, executor caching, and content block handling.
---

# Backend Patterns

## Architecture: Routers → Services → Database

```
chatServer/
  routers/      → HTTP handling only (request/response)
  services/     → Business logic only
  models/       → Pydantic schemas
  dependencies/ → auth.py, agent_loader.py (FastAPI Depends)
  database/     → connection.py, supabase_client.py
  config/       → settings.py
```

**Never put business logic in routers. Never put HTTP handling in services.**

## Quick Checklist

Before writing backend code, verify:
- [ ] Env vars use canonical names: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (not `VITE_SUPABASE_URL` or `SUPABASE_SERVICE_KEY`)
- [ ] New Python deps added to BOTH `requirements.txt` AND `chatServer/requirements.txt`
- [ ] Using `Depends(get_user_scoped_client)` in routers, `get_system_client()` in background services — never raw `get_supabase_client` (A8/SPEC-017)
- [ ] Business logic in services, not routers
- [ ] Pydantic models for request/response validation
- [ ] RLS handles user scoping (no manual `user_id` filtering)
- [ ] `Depends(get_current_user)` for auth — no manual header parsing
- [ ] Error handling re-raises HTTPException, logs unexpected errors
- [ ] Agent tools use the right pattern (see "Choosing a Tool Pattern" below)
- [ ] Content block lists normalized to strings in chat responses
- [ ] Tool name follows `verb_resource` pattern (e.g., `create_reminder`, `list_reminders`)
- [ ] Tool verb is from approved list: create, list, get, update, delete, search, save, read, send, fetch

## Scheduled Execution Patterns

### Heartbeat vs Regular Schedules

`ScheduledExecutionService.execute()` handles both types based on `config.schedule_type`:

- **`"scheduled"` (default)**: channel=`"scheduled"`, always notifies, status=`"success"`
- **`"heartbeat"`**: channel=`"heartbeat"`, appends checklist to prompt, suppresses notification when output starts with `HEARTBEAT_OK`, status=`"heartbeat_ok"`

Checklist lives in `agent_schedules.config` JSONB under `heartbeat_checklist` key. See `docs/architecture/heartbeat-system.md`.

### Onboarding Detection

`build_agent_prompt()` accepts `memory_notes` parameter. When both `memory_notes` and `user_instructions` are empty on interactive channels (`web`/`telegram`), an onboarding section is injected into the system prompt. Self-resolving: once the agent calls `save_memory` or `update_instructions`, subsequent loads skip onboarding.

## Choosing a Tool Pattern

Two patterns exist for agent tools. Choose based on the resource characteristics:

| Use **CRUDTool** (DB-configured) when... | Use **dedicated BaseTool** subclasses when... |
|-------------------------------------------|-----------------------------------------------|
| Flat table, no relationships | Hierarchical or relational data (e.g., tasks + subtasks) |
| No business logic beyond insert/select | Status transitions, computed fields, validation |
| Schema is stable and simple | Rich query filtering (date ranges, status, parent) |
| Tool is low-priority / experimental | Tool is core to agent UX |
| Async is not required | Must be async (event loop safety) |

**Dedicated tool pattern** (preferred for new tools): `BaseTool` subclass in `chatServer/tools/` + `Service` in `chatServer/services/`. See `task_tools.py` / `task_service.py` or `reminder_tools.py` / `reminder_service.py` as references.

**CRUDTool pattern**: configured entirely via `agent_tools` JSONB. See `src/core/tools/crud_tool.py`. Appropriate for simple flat-table operations.

## Recipe: Add a New Tool (End-to-End)

Per A6 (tools are the unit of agent capability):

1. **DB row:** Insert into `agent_tools` with `agent_id` UUID FK, tool `name` (verb_resource per A10), `description`, `config` JSONB
2. **Service:** Create `chatServer/services/<resource>_service.py` with business logic (per A1)
3. **Tool class:** Create `chatServer/tools/<resource>_tools.py` — `BaseTool` subclass calling the service
4. **Registry:** Register in `chatServer/tools/__init__.py` or via `agent_tools` DB config
5. **Tests:** `tests/chatServer/tools/test_<resource>_tools.py` + `tests/chatServer/services/test_<resource>_service.py`
6. **Agent config:** Add tool name to agent's `tool_names` array in `agent_configurations`

Reference implementations: `task_tools.py`/`task_service.py`, `reminder_tools.py`/`reminder_service.py`

## Recipe: Add a New API Endpoint

Per A1 (thin routers, fat services):

1. **Router:** `chatServer/routers/<resource>_router.py` — `Depends(get_current_user)`, delegates to service
2. **Service:** `chatServer/services/<resource>_service.py` — business logic, DB calls
3. **Models:** `chatServer/models/<resource>.py` — Pydantic request/response schemas
4. **Register:** Add router to `chatServer/main.py` with appropriate prefix
5. **Tests:** `tests/chatServer/routers/test_<resource>_router.py` + service tests
6. **Frontend hook:** (handed off to frontend-dev) `webApp/src/api/hooks/use<Resource>Hooks.ts`

## Data Plane Guidance (A3)

| Use Supabase REST+RLS when... | Use PostgreSQL (psycopg) when... |
|-------------------------------|----------------------------------|
| User CRUD operations | High-volume reads/writes |
| RLS handles authorization | Framework operations (LangChain message history) |
| Simple queries (select, insert, update) | Complex joins or CTEs |
| Frontend-initiated operations | Background/scheduled jobs |

## Key Gotchas

1. **ES256 tokens** — Supabase issues ES256, not HS256. Don't revert auth.py to HS256-only.
2. **Content block lists** — Newer `langchain-anthropic` returns `[{"text": "...", "type": "text"}]`. Normalize in chat.py.
3. **Auth token source** — Frontend must use `supabase.auth.getSession()`, not Zustand.
4. **Supabase client timing** — May not be initialized when agent tools are first wrapped. Non-fatal warning.
5. **AgentExecutor.agent must not be replaced** — Use `self.agent.runnable = new_runnable`, not `self.agent = new_runnable_sequence`. Bypasses Pydantic validator, strips `aplan()`.
6. **Settings created before load_dotenv()** — Call `settings.reload_from_env()` after `load_dotenv()` in main.py.
7. **PostgREST upsert requires real UNIQUE constraint** — Partial unique indexes don't work with Supabase `ON CONFLICT`. Use select-then-insert if needed.
8. **Executor cache survives new sessions** — The agent executor is cached per `(user_id, agent_name)`, not per session. After changing tool rows in the DB, a new session ID won't pick up the changes. **Restart chatServer** to clear the executor cache after any tool DB changes.
9. **Mocking a method entirely hides its internals** — If a test mocks `_digest_single` entirely, the query-building logic inside it is never exercised. When you mock a whole method, ask: "is the logic inside this method tested anywhere?" If not, add a direct test of the internals (e.g., call `_digest_single` with a mock search tool and assert the query string).

## Detailed Reference

For full patterns with code examples, see [reference.md](reference.md).
