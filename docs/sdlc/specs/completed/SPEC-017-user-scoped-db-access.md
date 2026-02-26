# SPEC-017: User-Scoped Database Access

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-23
> **Updated:** 2026-02-23

## Goal

Eliminate cross-user data leakage risk by making the API layer the single, structural enforcement point for user data isolation. Today, every Supabase query uses `service_role` key (bypassing RLS), and user scoping depends on individual developers remembering `.eq("user_id", user_id)` — a pattern that has already produced gaps (see security audit: unauthenticated `/api/tasks`, missing filters in `gmail_tools`, `pending_actions`, `chat_history_service`). This spec introduces a `UserScopedClient` that structurally guarantees user isolation for all client-facing code paths, reserves direct DB access for truly backend-only operations, and enforces the separation via linting hooks.

## Background: Security Audit Findings

A comprehensive audit of all 25 tables and all Python DB access revealed:

1. **Service role key used everywhere** — RLS policies exist but are never enforced
2. **`/api/tasks` endpoint was unauthenticated** (P0 — fixed on `fix/rls-audit-p0`)
3. **3 queries missing defensive `user_id` filters** (P0 — fixed on `fix/rls-audit-p0`)
4. **`chat_message_history` has no user-scoped RLS policy** (only `service_role` blanket)
5. **No structural mechanism** prevents future queries from forgetting user_id filtering

The root cause is architectural: there is no abstraction that makes correct behavior the default and incorrect behavior require explicit opt-out.

## Design Principles

**A8 (revised):** The API layer is the single enforcement point for user data isolation. The `UserScopedClient` structurally guarantees that every query to a user-owned table includes `user_id` filtering. RLS remains as defense-in-depth. Background/system operations use an explicitly separate `SystemClient` that cannot be injected into user-facing code paths.

**Key invariant:** A service handling an authenticated HTTP request or channel message (web, Telegram) can NEVER issue an unscoped query to a user-owned table. This is enforced by the type system (different client types) and by linting hooks (block raw client usage in services).

## Acceptance Criteria

- [ ] **AC-01:** A `UserScopedClient` class wraps the Supabase `AsyncClient` and auto-injects `.eq("user_id", user_id)` on `select`, `insert`, `update`, `delete`, and `upsert` operations for all tables in a configured user-scoped table set. [A8 revised]
- [ ] **AC-02:** A `SystemClient` class wraps the Supabase `AsyncClient` with no auto-filtering, for use exclusively by background services. [A8 revised]
- [ ] **AC-03:** FastAPI dependency `get_user_scoped_client(user_id)` returns a `UserScopedClient` bound to the authenticated user. All existing routers that call `get_supabase_client()` are migrated to use this. [A1, A8]
- [ ] **AC-04:** FastAPI dependency `get_system_client()` returns a `SystemClient`. Only background services (`background_tasks.py`, `scheduled_execution_service.py`, `email_digest_service.py`) and system cache services use this. [A8]
- [ ] **AC-05:** The `USER_SCOPED_TABLES` set is defined in a single canonical location and includes all tables that have a `user_id` column: `tasks`, `notes`, `focus_sessions`, `reminders`, `agent_logs`, `agent_long_term_memory`, `agent_sessions`, `agent_schedules`, `audit_logs`, `channel_linking_tokens`, `email_digests`, `external_api_connections`, `notifications`, `pending_actions`, `user_agent_prompt_customizations`, `user_channels`, `user_tool_preferences`, `chat_sessions`, `agent_execution_results`. [A8]
- [ ] **AC-06:** `validate-patterns.sh` hook BLOCKS any `chatServer/services/*.py` file that imports or calls `get_supabase_client` directly (must use `get_user_scoped_client` or `get_system_client`). [S3, S6]
- [ ] **AC-07:** `validate-patterns.sh` hook BLOCKS any `chatServer/routers/*.py` file that imports or calls `get_system_client` (routers must always use user-scoped access). [S3, A1]
- [ ] **AC-08:** `validate-patterns.sh` hook BLOCKS any migration that creates a table with a `user_id` column unless `USER_SCOPED_TABLES` in `chatServer/database/user_scoped_tables.py` is also updated in the same commit. Advisory warning (not block) since the hook can't verify the Python file — but the `task-completed-gate.sh` check can verify at task completion. [S3, S6]
- [ ] **AC-09:** `chat_message_history` table gets a user-scoped RLS policy via `chat_sessions.user_id` subquery, as defense-in-depth. [A8]
- [ ] **AC-10:** Duplicate RLS policies on `email_digests` are cleaned up. Service role policy patterns are standardized to `TO "service_role"`. [A8]
- [ ] **AC-11:** Architecture principle A8 in `reference.md` and `SKILL.md` is updated to reflect the revised principle: API layer as enforcement point, RLS as defense-in-depth, `UserScopedClient` as the mechanism. [S7, F1]
- [ ] **AC-12:** `backend-patterns` skill is updated: checklist item changes from "RLS handles user scoping (no manual `user_id` filtering)" to "Use `get_user_scoped_client` for user-facing services; `get_system_client` for background-only services". [S7]
- [ ] **AC-13:** `database-patterns` skill is updated: table template includes note that RLS is defense-in-depth; primary isolation is via `UserScopedClient`. New table checklist includes "Add table to `USER_SCOPED_TABLES` if it has a `user_id` column." [S7]
- [ ] **AC-14:** All existing unit tests pass. New tests cover `UserScopedClient` auto-filtering, `SystemClient` passthrough, and hook enforcement. [S1]
- [ ] **AC-15:** `CLAUDE.md` cross-domain gotchas updated with new gotcha: "Use `get_user_scoped_client` in services, never raw `get_supabase_client`. Background services use `get_system_client`." [S7]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/database/scoped_client.py` | `UserScopedClient` and `SystemClient` wrappers |
| `chatServer/database/user_scoped_tables.py` | Canonical `USER_SCOPED_TABLES` set |
| `tests/chatServer/database/test_scoped_client.py` | Tests for scoped client auto-filtering |
| `supabase/migrations/YYYYMMDDHHMMSS_chat_history_rls_and_cleanup.sql` | RLS policy for `chat_message_history`, duplicate policy cleanup, standardization |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/database/__init__.py` | Export new client types |
| `chatServer/database/supabase_client.py` | Add `get_user_scoped_client()` and `get_system_client()` dependencies |
| `chatServer/routers/*.py` (all) | Replace `get_supabase_client` with `get_user_scoped_client` |
| `chatServer/services/*.py` (user-facing) | Replace `get_supabase_client` with `UserScopedClient` parameter |
| `chatServer/services/background_tasks.py` | Use `get_system_client()` explicitly |
| `chatServer/services/scheduled_execution_service.py` | Use `get_system_client()` for system ops, scoped client for per-user agent execution |
| `chatServer/tools/memory_tools.py` | Migrate from sync `create_client()` to injected scoped client |
| `chatServer/tools/gmail_tools.py` | Migrate from sync `create_client()` to injected scoped client |
| `.claude/hooks/validate-patterns.sh` | Add AC-06 and AC-07 enforcement rules |
| `.claude/skills/architecture-principles/SKILL.md` | Update A8 row |
| `.claude/skills/architecture-principles/reference.md` | Rewrite A8 section |
| `.claude/skills/backend-patterns/SKILL.md` | Update checklist and data plane guidance |
| `.claude/skills/database-patterns/SKILL.md` | Update checklist note on RLS |
| `CLAUDE.md` | Add cross-domain gotcha |

### Out of Scope

- **Migrating the Supabase client from service_role to anon key** — The `UserScopedClient` enforces filtering at the Python layer. Switching to anon key + RLS is a future enhancement that would add database-level enforcement but requires per-request client construction (significant Supabase SDK work).
- **Changing psycopg direct connections** — The `user_context.py` pattern for psycopg is already correct. `chat_message_history` access via psycopg is adequately scoped by session ownership checks. The new RLS policy (AC-08) adds defense-in-depth.
- **Frontend changes** — The frontend already uses the anon key for direct Supabase access (tasks, chat_sessions, focus_sessions, external_connections), which means RLS is enforced at the database level — Postgres makes cross-user reads structurally impossible. For chatServer API calls, the frontend sends JWT Bearer tokens and the backend extracts `user_id` — also correct. No frontend changes needed.
- **Consolidating dual-access tables** — `tasks`, `chat_sessions`, and `external_api_connections` are accessed from both frontend (anon key + RLS) and backend (service_role + UserScopedClient). Both paths enforce isolation. The dual access creates race conditions but not leakage. Consolidation is tracked in `docs/sdlc/BACKLOG.md` as a P2 item.
- **Telegram bot channel** — Telegram handlers resolve `user_id` from `user_channels` lookup. They should construct a `UserScopedClient` with that resolved `user_id`, same as HTTP handlers. This is in scope (covered by AC-03's "all routers" migration).

## Technical Approach

### 1. UserScopedClient Design

```python
# chatServer/database/scoped_client.py

from supabase import AsyncClient
from .user_scoped_tables import USER_SCOPED_TABLES

class UserScopedClient:
    """Wraps Supabase AsyncClient to auto-inject user_id filtering.

    Every query to a user-scoped table automatically includes
    .eq("user_id", self.user_id). Queries to system tables
    (agent_configurations, tools, etc.) pass through unmodified.
    """

    def __init__(self, client: AsyncClient, user_id: str):
        self.client = client
        self.user_id = user_id

    def table(self, table_name: str) -> "ScopedTableQuery":
        query = self.client.table(table_name)
        if table_name in USER_SCOPED_TABLES:
            return ScopedTableQuery(query, self.user_id)
        return query  # System tables pass through

    # Delegate rpc(), schema(), etc. to underlying client
    def rpc(self, *args, **kwargs):
        return self.client.rpc(*args, **kwargs)


class ScopedTableQuery:
    """Wraps a Supabase table query builder to auto-inject user_id.

    Intercepts select/insert/update/delete/upsert to ensure user_id
    filtering is present. If the caller already filtered by user_id
    (e.g., legacy code or explicit readability), the duplicate is
    detected and skipped — no double-append.

    Auto-injection appends to existing filters (PostgREST AND chain),
    never overwrites them.
    """

    def __init__(self, query, user_id: str):
        self._query = query
        self._user_id = user_id
        self._user_id_already_set = False

    def eq(self, column: str, value):
        """Proxy .eq() — detects if user_id is already being filtered."""
        if column == "user_id":
            self._user_id_already_set = True
            # Use the scoped user_id regardless of what was passed,
            # preventing spoofing via caller passing a different user_id
            return self._chain(self._query.eq(column, self._user_id))
        return self._chain(self._query.eq(column, value))

    def select(self, *args, **kwargs):
        result = self._query.select(*args, **kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def insert(self, data, **kwargs):
        # Ensure user_id is set on inserted data (overwrite if present
        # to prevent spoofing)
        if isinstance(data, dict):
            data["user_id"] = self._user_id
        elif isinstance(data, list):
            for row in data:
                row["user_id"] = self._user_id
        return self._query.insert(data, **kwargs)

    def update(self, data, **kwargs):
        result = self._query.update(data, **kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def delete(self, **kwargs):
        result = self._query.delete(**kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def upsert(self, data, **kwargs):
        if isinstance(data, dict):
            data["user_id"] = self._user_id
        elif isinstance(data, list):
            for row in data:
                row["user_id"] = self._user_id
        return self._query.upsert(data, **kwargs)

    def _chain(self, new_query):
        """Return a new ScopedTableQuery preserving state."""
        chained = ScopedTableQuery(new_query, self._user_id)
        chained._user_id_already_set = self._user_id_already_set
        return chained


class SystemClient:
    """Thin wrapper marking unscoped access as intentional.

    Provides the same interface as the raw Supabase client.
    Exists purely to make system access explicit in type signatures.
    """

    def __init__(self, client: AsyncClient):
        self.client = client

    def table(self, table_name: str):
        return self.client.table(table_name)

    def rpc(self, *args, **kwargs):
        return self.client.rpc(*args, **kwargs)
```

### 2. FastAPI Dependencies

```python
# In chatServer/database/supabase_client.py (additions)

async def get_user_scoped_client(
    user_id: str = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
) -> UserScopedClient:
    """Dependency for user-facing endpoints. Auto-scopes all queries."""
    return UserScopedClient(client, user_id)

async def get_system_client(
    client: AsyncClient = Depends(get_supabase_client),
) -> SystemClient:
    """Dependency for background services only. No user scoping."""
    return SystemClient(client)
```

### 3. Migration Pattern for Services

Before:
```python
async def list_tasks(self, user_id: str, db: AsyncClient) -> list:
    result = await db.table("tasks").select("*").eq("user_id", user_id).execute()
    return result.data
```

After:
```python
async def list_tasks(self, db: UserScopedClient) -> list:
    # user_id filter is auto-injected by UserScopedClient
    result = await db.table("tasks").select("*").execute()
    return result.data
```

Services no longer need `user_id` as a parameter for DB queries — it's baked into the client. Services that need `user_id` for non-DB purposes (e.g., logging) can access `db.user_id`.

### 4. Hook Enforcement

```bash
# Addition to validate-patterns.sh

*/chatServer/services/*.py)
    # A8: Block raw get_supabase_client in services
    if grep -qP 'get_supabase_client' "$FILE_PATH" 2>/dev/null; then
        echo "BLOCKED: Direct 'get_supabase_client' in service. Per A8, use 'UserScopedClient' or 'SystemClient'. See architecture-principles skill A8." >&2
        exit 2
    fi
    ;;

*/chatServer/routers/*.py)
    # A8: Block SystemClient in routers
    if grep -qP 'get_system_client|SystemClient' "$FILE_PATH" 2>/dev/null; then
        echo "BLOCKED: 'SystemClient' in router. Per A8, routers must use 'get_user_scoped_client'. Background operations belong in services." >&2
        exit 2
    fi
    ;;
```

### 5. RLS Defense-in-Depth Migration

```sql
-- chat_message_history: add user-scoped SELECT policy via chat_sessions join
CREATE POLICY "Users can view own chat history"
    ON chat_message_history FOR SELECT TO authenticated
    USING (session_id IN (
        SELECT session_id FROM chat_sessions WHERE user_id = auth.uid()
    ));

-- Standardize service_role patterns (replace CURRENT_USER = 'postgres')
-- Clean up duplicate email_digests policies
```

### Dependencies

- P0 fixes merged from `fix/rls-audit-p0` (removes `/api/tasks`, adds defensive filters)
- No external dependencies

## Testing Requirements

### Unit Tests (required)

- `UserScopedClient.table("tasks").select()` auto-injects `.eq("user_id", uid)`
- `UserScopedClient.table("tasks").insert({...})` sets `user_id` on data
- `UserScopedClient.table("tasks").update({...})` adds `.eq("user_id", uid)`
- `UserScopedClient.table("tasks").delete()` adds `.eq("user_id", uid)`
- `UserScopedClient.table("agent_configurations").select()` does NOT inject user_id (system table)
- `SystemClient.table("tasks").select()` does NOT inject user_id
- `ScopedTableQuery.insert(list_of_dicts)` sets user_id on each dict
- `USER_SCOPED_TABLES` set matches tables with `user_id` column in `schema.sql`

### Integration Tests (required)

- Hook enforcement: writing `get_supabase_client` to a service file triggers block
- Hook enforcement: writing `SystemClient` to a router file triggers block
- Existing service tests still pass after migration (may need mock updates)

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Unit | `test_ac_01_user_scoped_client_auto_filters` |
| AC-02 | Unit | `test_ac_02_system_client_no_filter` |
| AC-03 | Unit | `test_ac_03_dependency_injection` |
| AC-05 | Unit | `test_ac_05_user_scoped_tables_complete` |
| AC-06 | Integration | `test_ac_06_hook_blocks_raw_client_in_services` |
| AC-07 | Integration | `test_ac_07_hook_blocks_system_client_in_routers` |
| AC-13 | Integration | `test_ac_13_existing_tests_pass` (CI) |

### Manual Verification (UAT)

- [ ] Start `pnpm dev`, authenticate via web, send a chat message — verify response is scoped to user
- [ ] Create a task via API — verify it appears only for authenticated user
- [ ] Trigger a scheduled agent execution — verify it completes successfully using SystemClient path
- [ ] Verify `validate-patterns.sh` blocks a test edit adding `get_supabase_client` to a service file

## Frontend Access Model (No Changes Required)

The frontend has two data access paths, both structurally safe against cross-user data leakage:

| Path | Tables | Auth | Isolation mechanism |
|------|--------|------|---------------------|
| **Direct Supabase** (anon key) | tasks, chat_sessions, focus_sessions, external_connections, notes | `auth.uid()` via Supabase session | **RLS enforced by Postgres** — impossible to read other users' rows |
| **chatServer API** (JWT Bearer) | chat_message_history, notifications, reminders, agent tools | `get_current_user()` extracts from JWT | **`UserScopedClient`** (this spec) — auto-injects `user_id` filter |

### Why cross-user leakage is structurally impossible on both paths

**Frontend direct path:** Uses the anon key (`VITE_SUPABASE_ANON_KEY`), which means Postgres evaluates every RLS policy. The `auth.uid()` function returns the authenticated user from the Supabase session JWT. Even if frontend code omitted `.eq('user_id', user.id)`, the RLS policy `USING (auth.uid() = user_id)` would reject rows belonging to other users. The frontend cannot bypass RLS because it never has the service_role key.

**Backend API path:** Uses service_role key (bypasses RLS), but `UserScopedClient` structurally injects `.eq("user_id", user_id)` on every query to user-scoped tables. The `user_id` comes from the JWT, not from the request body. Even if service code omits filtering, the scoped client adds it.

### Dual-access tables

Three tables are accessed from both paths: `tasks`, `chat_sessions`, `external_api_connections`. Both paths enforce user isolation independently — the frontend via RLS, the backend via `UserScopedClient`. Cross-user leakage is prevented on both paths.

The dual-access pattern creates **consistency/race-condition risks** (not security risks) — e.g., an agent tool and the frontend editing the same task simultaneously. Consolidating these to a single access path is tracked as a backlog item (see `docs/sdlc/backlog.md`), but is out of scope for this spec.

**No frontend changes are needed for this spec.**

## Edge Cases

- **Service needs both scoped and system access in one method:** This should not happen. If a service method needs cross-user data (e.g., `get_due_reminders`), it belongs in a background service using `SystemClient`. Split the method if needed.
- **Agent tools that create their own Supabase client:** `memory_tools.py` and `gmail_tools.py` currently use sync `create_client()` directly. These must be migrated to accept an injected client. If sync access is required, create a sync `UserScopedClient` variant.
- **RPC calls:** `UserScopedClient.rpc()` passes through to the raw client because RPC functions handle their own auth (via `auth.uid()` set by `user_context.py`). This is documented and acceptable.
- **Telegram/webhook path:** The Telegram bot resolves `user_id` from `user_channels` lookup, then constructs `UserScopedClient(client, resolved_user_id)`. This is the same scoping mechanism as HTTP auth, just with a different `user_id` source.
- **Tables with no `user_id` column:** `chat_message_history` has `session_id` not `user_id`. It's excluded from `USER_SCOPED_TABLES`. Access is scoped via session ownership checks in service code + new RLS policy (AC-08).
- **Duplicate user_id filter:** If service code already calls `.eq("user_id", uid)`, the `ScopedTableQuery` detects it via the proxied `.eq()` method and skips auto-injection. No double-append. The scoped client always uses its own `user_id` (from JWT) even if the caller passes a different value — this prevents spoofing.
- **Caller passes wrong user_id:** On `insert`/`upsert`, the scoped client overwrites `data["user_id"]` with the authenticated `user_id`. On `.eq("user_id", ...)`, it substitutes the scoped `user_id`. This is intentional — the authenticated identity is authoritative.

## Functional Units (for PR Breakdown)

### FU-1: Core infrastructure — `UserScopedClient`, `SystemClient`, table registry
**Branch:** `feat/spec-017-scoped-client`
**Domain:** backend-dev
**Delivers:** AC-01, AC-02, AC-05
**Files:**
- Create `chatServer/database/scoped_client.py`
- Create `chatServer/database/user_scoped_tables.py`
- Create `tests/chatServer/database/test_scoped_client.py`
- Modify `chatServer/database/__init__.py`
- Modify `chatServer/database/supabase_client.py` (add dependency functions)

### FU-2: Service migration — migrate all services and routers to scoped clients
**Branch:** `feat/spec-017-service-migration`
**Domain:** backend-dev
**Depends on:** FU-1
**Delivers:** AC-03, AC-04, AC-13
**Files:**
- Modify all `chatServer/routers/*.py` — replace `get_supabase_client` with `get_user_scoped_client`
- Modify all `chatServer/services/*.py` — accept `UserScopedClient` or `SystemClient` as appropriate
- Modify `chatServer/tools/memory_tools.py` — use injected client instead of `create_client()`
- Modify `chatServer/tools/gmail_tools.py` — use injected client instead of `create_client()`
- Update all affected tests

### FU-3: Hook enforcement and documentation
**Branch:** `feat/spec-017-enforcement`
**Domain:** backend-dev
**Depends on:** FU-2
**Delivers:** AC-06, AC-07, AC-10, AC-11, AC-12, AC-14
**Files:**
- Modify `.claude/hooks/validate-patterns.sh`
- Modify `.claude/skills/architecture-principles/SKILL.md`
- Modify `.claude/skills/architecture-principles/reference.md`
- Modify `.claude/skills/backend-patterns/SKILL.md`
- Modify `.claude/skills/database-patterns/SKILL.md`
- Modify `CLAUDE.md`

### FU-4: RLS defense-in-depth migration
**Branch:** `feat/spec-017-rls-cleanup`
**Domain:** database-dev
**Depends on:** None (parallel with FU-1)
**Delivers:** AC-08, AC-09
**Files:**
- Create `supabase/migrations/YYYYMMDDHHMMSS_chat_history_rls_and_cleanup.sql`

**Merge order:** FU-1 → FU-2 → FU-3 (sequential). FU-4 is independent and can merge in parallel.

## Contracts

### FU-1 → FU-2 Contract

**FU-1 provides:**
- `UserScopedClient(client: AsyncClient, user_id: str)` with `.table()` method
- `SystemClient(client: AsyncClient)` with `.table()` method
- `ScopedTableQuery` with `.select()`, `.insert()`, `.update()`, `.delete()`, `.upsert()` — all auto-inject `user_id`
- `USER_SCOPED_TABLES: set[str]` — canonical set of user-scoped table names
- `get_user_scoped_client(user_id, client)` — FastAPI dependency
- `get_system_client(client)` — FastAPI dependency

**FU-2 must:**
- Replace every `Depends(get_supabase_client)` in routers with `Depends(get_user_scoped_client)`
- Replace every `db: AsyncClient` parameter in user-facing services with `db: UserScopedClient`
- Remove explicit `.eq("user_id", user_id)` from queries (now auto-injected)
- For background services, use `SystemClient` and document why
- Ensure all existing tests pass (mock updates as needed)

### FU-2 → FU-3 Contract

**FU-2 provides:**
- All services migrated — no remaining `get_supabase_client` imports in services/routers

**FU-3 must:**
- Add hook rules that BLOCK the old pattern
- Update all documentation to reflect new pattern

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-14)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (FU-1→FU-2, FU-2→FU-3)
- [x] Technical decisions reference principles (A8, A1, S3, S6, S7, F1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3; FU-4 parallel)
- [x] Out of scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
