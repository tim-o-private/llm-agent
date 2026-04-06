# SPEC-035: Config Service — Supabase Storage + Overlay Resolution

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** PRD-003 (Orchestration Layer), Phase 0 — Foundation
> **Architecture:** `docs/product/ARCHITECTURE-PROPOSAL-next-gen.md`, Section Q3

## Goal

Replace the scattered DB-column config model (agent personality in `agent_configurations.soul`/`identity`, user instructions in `user_agent_prompt_customizations.instructions`) with a file-based config system backed by Supabase Storage. Introduce overlay resolution: system defaults at `/system/`, per-user overrides at `/users/{user_id}/`, with user paths winning. Config is **read-only from the agent's perspective** — the server reads config at session init and injects it into the prompt, same as today. This is the foundation for Phase 3's bwrap sandbox where the agent edits config files directly.

**Why now:** Every future spec in the next-gen architecture (Capability Gateway, Conversation Handler, Trust Tiers, Workflows) depends on config living in a file-addressable store rather than scattered DB columns. This decouples "what the agent is" from the database schema and makes config inspectable, diffable, and eventually editable by the agent itself.

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| Supabase Storage | Object storage with RLS, bucket policies | Available (not yet used) |
| SPEC-019 (Tool Registry) | `agent_configurations` table structure, prompt_template rendering | Complete |
| SPEC-022 (Agent Personality) | Current soul/identity content in `agent_configurations` | Complete |

## Acceptance Criteria

### Storage Setup

- [ ] **AC-01:** A Supabase Storage bucket `config` is created via migration. The bucket is private (no public access). [A3, A8]
- [ ] **AC-02:** System-default config files are seeded into `/system/agents/clarity/soul.md` and `/system/agents/clarity/identity.json` via a migration script. Content is extracted from the current `agent_configurations` row for the `assistant` agent (renamed to `clarity` in the config layer). [A3]
- [ ] **AC-03:** RLS policies on the `storage.objects` table enforce: (a) service_role can read/write all paths, (b) authenticated users can read `/system/*` paths, (c) authenticated users can read/write only their own `/users/{auth.uid()}/*` paths, (d) no cross-user access to `/users/` paths. [A8]

### Overlay Resolution Service

- [ ] **AC-04:** A `ConfigService` class in `chatServer/services/config_service.py` provides `async read(path: str, user_id: str) -> str | None`. It checks `/users/{user_id}/{path}` first; if not found (404), falls back to `/system/{path}`. Returns file content as string, or `None` if neither exists. [A1]
- [ ] **AC-05:** `ConfigService` provides `async read_with_source(path: str, user_id: str) -> tuple[str | None, str]` that returns `(content, source)` where source is `"user"`, `"system"`, or `"none"`. Used for debugging and future file browser metadata. [A1]
- [ ] **AC-06:** `ConfigService` provides `async list_paths(prefix: str, user_id: str) -> list[str]` that returns the merged set of paths under the prefix — user paths shadow system paths with the same relative name. [A1]
- [ ] **AC-07:** `ConfigService` uses the Supabase Storage Python client (`supabase.storage.from_("config")`) with service_role credentials for reads (bypassing RLS for server-side operations). User-facing API endpoints use the user's JWT for RLS enforcement. [A3, A8]

### Caching Layer

- [ ] **AC-08:** A `ConfigCacheService` wraps `ConfigService` with in-memory TTL caching. Cache key is `(path, user_id)`. Default TTL is 300 seconds (config changes are rare). Cache is invalidated on write operations. [A1]
- [ ] **AC-09:** `ConfigCacheService` follows the existing `TTLCacheService` pattern (see `agent_config_cache_service.py`). It registers as `"Config"` via `register_ttl_cache_service`. Initialized/shutdown in `main.py` lifespan alongside existing cache services. [A1]
- [ ] **AC-10:** The system-path layer (`/system/*`) uses a separate cache with longer TTL (3600s) since system config only changes on deployment. User-path cache uses 300s TTL. [A1]

### Config Read API

- [ ] **AC-11:** A `GET /api/config/{path:path}` endpoint in `chatServer/routers/config_router.py` returns the resolved config file content for the authenticated user. Uses overlay resolution (user → system fallback). Returns 404 if neither layer has the file. Response is `text/plain` or `application/json` based on file extension. [A1, A5]
- [ ] **AC-12:** A `GET /api/config/_list?prefix={prefix}` endpoint returns the merged file listing for the authenticated user under the given prefix. Response is JSON array of `{path, source, updated_at}` objects. [A1, A5]
- [ ] **AC-13:** A `PUT /api/config/user/{path:path}` endpoint writes a file to the user's config layer (`/users/{user_id}/{path}`). Request body is the file content. Invalidates the config cache for this user+path. This replaces the `update_instructions` tool's DB write path. [A1, A5]
- [ ] **AC-14:** All config API endpoints use `Depends(get_current_user)` for auth and scope operations to the authenticated user. No user can read or write another user's config. [A5, A8]

### Migration: Agent Identity to Config Files

- [ ] **AC-15:** The `soul` text from the `assistant` row in `agent_configurations` is written to `/system/agents/clarity/soul.md` in Supabase Storage. The `identity` JSONB is written to `/system/agents/clarity/identity.json`. These become the source of truth for agent personality. [A3]
- [ ] **AC-16:** All `agent_configurations` rows are migrated to `/system/agents/{agent_name}/soul.md` and `/system/agents/{agent_name}/identity.json`. The `assistant` agent is mapped to the `clarity` namespace. The default agent name for config resolution is `clarity`. [A3]
- [ ] **AC-17:** `ConfigService.read()` and the agent loader use lazy fallback: read from config service first; if the config file doesn't exist yet (pre-migration), fall back to reading from the `agent_configurations` DB table. This eliminates the need for a manual migration step — data migrates lazily on first read, or eagerly via the migration script. DB columns are retained but no longer the source of truth once the config file exists. [A1]

### Migration: User Instructions to Config Files

- [ ] **AC-18:** A data migration script reads all rows from `user_agent_prompt_customizations` and writes each user's instructions to `/users/{user_id}/agent/instructions.md` in Supabase Storage. One file per user (not per agent_name). [A3]
- [ ] **AC-19:** `user_instructions_cache_service.py` reads from the config service overlay (`agent/instructions.md`) with lazy DB fallback: if the config file doesn't exist, fall back to `user_agent_prompt_customizations`. The DB table is retained but no longer the source of truth once the config file exists. [A1]
- [ ] **AC-20:** The `UpdateInstructionsTool` writes to the config service (`PUT /users/{user_id}/agent/instructions.md` via `ConfigService.write()`) instead of upserting into `user_agent_prompt_customizations`. Cache is invalidated on write. [A6]

### Prompt Builder Integration

- [ ] **AC-21:** `build_agent_prompt()` signature is unchanged — callers still pass `soul`, `identity`, `user_instructions` as before. The change is upstream: `load_agent_executor_db_async()` and `load_agent_executor_db()` now source these values from the config service instead of from DB columns. [A1]
- [ ] **AC-22:** `prompt_template` continues to be read from `agent_configurations.prompt_template` (it's a rendering concern, not an identity concern). It will move to config files in a future spec. [A14]

### Testing

- [ ] **AC-23:** Unit tests for `ConfigService`: overlay resolution (user wins over system), system fallback when no user file, `None` when neither exists, `list_paths` merges both layers with user shadowing system. [S1]
- [ ] **AC-24:** Unit tests for `ConfigCacheService`: cache hit returns cached value, cache miss calls through to `ConfigService`, cache invalidation on write, separate TTLs for system vs user paths. [S1]
- [ ] **AC-25:** Integration test: two users; user A writes to their config path; user B cannot read user A's config via the API (RLS enforcement). Service-role can read both. [S1, A8]
- [ ] **AC-26:** Migration test: after running the data migration, `ConfigService.read("agents/clarity/soul.md", user_id)` returns the same content as the current `agent_configurations.soul` for the assistant agent. Same for `agent/instructions.md` matching `user_agent_prompt_customizations.instructions`. [S1]
- [ ] **AC-27:** Regression test: an end-to-end prompt assembly test that loads an agent via `load_agent_executor_db_async()` and asserts the system prompt contains the soul text and user instructions from config files (not from DB columns). [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/config_service.py` | Overlay resolution service — `read()`, `write()`, `list_paths()` |
| `chatServer/services/config_cache_service.py` | TTL cache wrapper around ConfigService |
| `chatServer/routers/config_router.py` | REST API for config read/write/list |
| `chatServer/models/config.py` | Pydantic response models (`ConfigFileResponse`, `ConfigListItem`) |
| `tests/chatServer/services/test_config_service.py` | Unit tests for overlay resolution |
| `tests/chatServer/services/test_config_cache_service.py` | Unit tests for caching layer |
| `tests/chatServer/routers/test_config_router.py` | API endpoint tests |
| `supabase/migrations/2026MMDD000001_create_config_bucket.sql` | Bucket creation + RLS policies |
| `scripts/migrate_config_to_storage.py` | Optional eager data migration script (lazy fallback works without it) |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Register config_router, initialize/shutdown config cache in lifespan |
| `src/core/agent_loader_db.py` | Read soul/identity from ConfigService instead of agent_configurations columns |
| `chatServer/services/agent_config_cache_service.py` | Remove soul/identity from SELECT (still cache llm_config, prompt_template) |
| `chatServer/services/user_instructions_cache_service.py` | Read from ConfigService overlay instead of DB table |
| `chatServer/tools/update_instructions_tool.py` | Write to ConfigService instead of DB upsert |
| `chatServer/services/prompt_builder.py` | No changes (receives soul/identity as params — upstream change is transparent) |
| `chatServer/services/prompt_customization.py` | Read/write instructions via ConfigService instead of direct DB queries |

### Out of Scope

- **Agent writing config** — agent-initiated config edits via bwrap sandbox (SPEC-037/038).
- **File browser frontend** — React UI for browsing/editing config files (SPEC-039).
- **Trust tiers and allowlists** — tool permission config files (SPEC-034).
- **Workflow templates in storage** — graph definitions as config files (SPEC-035/036).
- **Prompt template migration** — `prompt_template` stays in `agent_configurations` for now.
- **Removing deprecated DB columns** — `soul`, `identity`, `instructions` columns remain for rollback safety and lazy fallback. A future cleanup spec removes them after config service proves stable.
- **Operating model / channel guidance migration** — `OPERATING_MODEL`, `CHANNEL_GUIDANCE`, etc. stay as code constants in `prompt_builder.py`. Deferred to a follow-up spec.

## Blast Radius

Every file that currently reads `soul`, `identity`, or `user_instructions` from the database is affected. Exhaustive list:

### Direct reads from `agent_configurations` (soul/identity)

| File | Current behavior | Change needed |
|------|-----------------|---------------|
| `src/core/agent_loader_db.py` (`_fetch_agent_config_from_db_async`, lines 926-948) | `SELECT soul, identity FROM agent_configurations` | Read from ConfigService instead |
| `src/core/agent_loader_db.py` (`load_agent_executor_db`, sync path, ~line 700) | Same SELECT via Supabase REST | Read from ConfigService instead |
| `chatServer/services/agent_config_cache_service.py` (`_fetch_all_agent_configs`, line 71) | `SELECT soul, identity ...` in cache refresh | Remove soul/identity from SELECT; service still caches llm_config, prompt_template |
| `chatServer/services/agent_config_cache_service.py` (`_fetch_agent_config`, line 98) | Same for single-agent fetch | Same change |
| `chatServer/services/schedule_service.py` (line 51) | `table("agent_configurations").select("id")` — only reads `id` for validation | No change needed (doesn't read soul/identity) |
| `chatServer/agents/email_digest_agent.py` | Deprecated — delegates to `load_agent_executor_db()` | No direct change; inherits fix via agent_loader_db |

### Direct reads from `user_agent_prompt_customizations` (instructions)

| File | Current behavior | Change needed |
|------|-----------------|---------------|
| `chatServer/services/user_instructions_cache_service.py` (`_fetch_user_instructions`, line 64) | `SELECT instructions FROM user_agent_prompt_customizations` | Read from ConfigService overlay |
| `chatServer/services/prompt_customization.py` (`get_user_instructions`, line 102) | Supabase REST query | Read from ConfigService |
| `chatServer/services/prompt_customization.py` (`create/update_prompt_customization`) | Supabase REST insert/update | Write via ConfigService |
| `chatServer/tools/update_instructions_tool.py` (`_arun`, line 84) | Supabase REST upsert | Write via ConfigService, invalidate cache |

### Downstream consumers (no changes needed — transparent)

| File | Why no change |
|------|---------------|
| `chatServer/services/prompt_builder.py` | Receives `soul`, `identity`, `user_instructions` as function params — doesn't know the source |
| `chatServer/main.py` | Only initializes/shuts down cache services — will add config cache alongside |
| `tests/chatServer/services/test_prompt_builder.py` | Tests prompt assembly with explicit param values — source-agnostic |
| `tests/chatServer/services/test_prompt_customization.py` | Will need updates to mock ConfigService instead of DB |
| `tests/core/test_agent_loader_db.py` | Will need updates to mock ConfigService |
| `tests/core/test_agent_loader_db_async.py` | Will need updates to mock ConfigService |

## Technical Approach

### 1. Supabase Storage Bucket Setup

Supabase Storage uses the `storage` schema with `storage.buckets` and `storage.objects` tables. A migration creates the bucket and applies RLS policies.

```sql
-- Create the config bucket (private, no public access)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'config',
    'config',
    false,
    1048576,  -- 1MB max per file (config files are small)
    ARRAY['text/plain', 'text/markdown', 'application/json']
);

-- RLS: service_role has full access (implicit — bypasses RLS)

-- RLS: authenticated users can read system config
CREATE POLICY "Users can read system config"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'system/%'
);

-- RLS: authenticated users can read their own user config
CREATE POLICY "Users can read own config"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);

-- RLS: authenticated users can write their own user config
CREATE POLICY "Users can write own config"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);

CREATE POLICY "Users can update own config"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'config'
    AND name LIKE 'users/' || auth.uid()::text || '/%'
);
```

### 2. Config File Layout

```
config/                          # Supabase Storage bucket
├── system/                      # Read-only defaults (deployed as code)
│   └── agents/
│       └── clarity/             # Default agent (mapped from DB "assistant")
│           ├── soul.md          # Behavioral philosophy (from agent_configurations.soul)
│           └── identity.json    # Structured identity (from agent_configurations.identity)
│
└── users/{user_id}/             # Per-user mutable layer
    └── agent/                   # User-specific agent config (one file per user, not per agent)
        ├── instructions.md      # Standing instructions (from user_agent_prompt_customizations)
        ├── soul.md              # User override of soul (future — not seeded)
        └── identity.json        # User override of identity (future — not seeded)
```

**Path resolution for agent config:** The agent loader resolves `agents/clarity/soul.md` — checking `/users/{user_id}/agents/clarity/soul.md` first, then `/system/agents/clarity/soul.md`. User instructions resolve at `agent/instructions.md` (not namespaced by agent — one file per user for MVP).

### 3. ConfigService Implementation

```python
class ConfigService:
    """Reads config files from Supabase Storage with overlay resolution."""

    def __init__(self, supabase_client):
        self._storage = supabase_client.storage.from_("config")

    async def read(self, path: str, user_id: str) -> str | None:
        """Read with overlay: user path → system fallback."""
        content, _ = await self.read_with_source(path, user_id)
        return content

    async def read_with_source(self, path: str, user_id: str) -> tuple[str | None, str]:
        # Try user path first
        user_path = f"users/{user_id}/{path}"
        content = await self._download(user_path)
        if content is not None:
            return content, "user"

        # Fall back to system path
        system_path = f"system/{path}"
        content = await self._download(system_path)
        if content is not None:
            return content, "system"

        return None, "none"

    async def write(self, path: str, user_id: str, content: str) -> None:
        """Write to user config layer."""
        user_path = f"users/{user_id}/{path}"
        self._storage.upload(user_path, content.encode(), {"content-type": "text/plain", "upsert": "true"})

    async def _download(self, full_path: str) -> str | None:
        try:
            response = self._storage.download(full_path)
            return response.decode("utf-8")
        except Exception:
            return None
```

### 4. UpdateInstructionsTool Migration

The tool switches from DB upsert to config service write:

```python
# Before (current):
client.table("user_agent_prompt_customizations").upsert({...}).execute()

# After:
config_service = get_config_service()
await config_service.write("agent/instructions.md", self.user_id, instructions)
# Invalidate cache
config_cache = get_config_cache_service()
await config_cache.invalidate(path="agent/instructions.md", user_id=self.user_id)
```

### 5. Agent Loader Integration (Lazy Fallback)

In `load_agent_executor_db_async()`, after fetching `agent_db_config` from cache/DB:

```python
# Lazy fallback: config service → DB columns
config_svc = get_config_cache_service()

soul = await config_svc.read("agents/clarity/soul.md", user_id)
if soul is None:
    # Config file doesn't exist yet — fall back to DB (pre-migration)
    soul = agent_db_config.get("soul") or ""

identity_json = await config_svc.read("agents/clarity/identity.json", user_id)
if identity_json is not None:
    identity = json.loads(identity_json)
else:
    identity = agent_db_config.get("identity")

# User instructions: config service → DB fallback
user_instructions = await config_svc.read("agent/instructions.md", user_id)
if user_instructions is None:
    user_instructions = await get_cached_user_instructions(user_id, agent_name)
```

This eliminates the need for a manual migration deploy step. Data migrates either lazily (first read triggers fallback) or eagerly via the migration script. Once a config file exists, it is the source of truth.

### 6. Data Migration Script

`scripts/migrate_config_to_storage.py` — optional eager migration (the lazy fallback in the agent loader means this is not required for correctness, but recommended for consistency):

1. Connect to Supabase with service_role key
2. Read all `agent_configurations` rows → write soul/identity to `/system/agents/{name}/` (mapping `assistant` → `clarity`)
3. Read all `user_agent_prompt_customizations` rows → write instructions to `/users/{user_id}/agent/instructions.md`
4. Log counts and any failures
5. Idempotent — re-running overwrites with latest values

**Migration timing:** The lazy fallback pattern means the code works before, during, and after migration. The migration script can be run at any time after the bucket exists. No deploy coordination required.

## Functional Units

### FU-1: Storage Infrastructure (Database)
**ACs:** AC-01, AC-02, AC-03
**Domain:** database-dev

Create the config bucket, seed system defaults, apply RLS policies. Write the data migration script for existing config data.

Migration prefix: assigned by orchestrator.

### FU-2: Config Service + Cache (Backend)
**ACs:** AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-23, AC-24
**Domain:** backend-dev
**Depends on:** FU-1

Implement `ConfigService`, `ConfigCacheService`, integrate into `main.py` lifespan. Unit tests for overlay resolution and caching.

### FU-3: Config API Endpoints (Backend)
**ACs:** AC-11, AC-12, AC-13, AC-14, AC-25
**Domain:** backend-dev
**Depends on:** FU-2

REST API for config read/write/list. Integration test for RLS isolation.

### FU-4: Config Source Migration (Backend)
**ACs:** AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-26, AC-27
**Domain:** backend-dev
**Depends on:** FU-2

Switch all config readers from DB to ConfigService. Update `agent_loader_db.py`, `agent_config_cache_service.py`, `user_instructions_cache_service.py`, `update_instructions_tool.py`, `prompt_customization.py`. Migration verification tests.

## Rollback Strategy

DB columns (`soul`, `identity` in `agent_configurations`; `instructions` in `user_agent_prompt_customizations`) are **not removed** in this spec. If the config service fails:

1. Revert the code changes (FU-2/3/4) — readers fall back to DB columns
2. The storage bucket and seeded files remain harmless
3. No data loss — DB still has all values

A future cleanup spec removes the deprecated columns after the config service has been stable in production for at least 2 weeks.

## Resolved Decisions

1. **Config path convention:** `/system/agents/{name}/` (plural, namespaced). Default agent is `clarity` (mapped from DB `assistant`). Supports multiple agents naturally.

2. **User instructions:** One file per user for MVP: `/users/{id}/agent/instructions.md`. No per-agent-name keying — simplifies the model since there's effectively one agent per user.

3. **Data migration:** Lazy fallback — `ConfigService` reads from storage first, falls back to DB if the config file doesn't exist yet. No manual deploy step required. An optional eager migration script (`scripts/migrate_config_to_storage.py`) can be run at any time for consistency.

4. **Operating model constants:** Deferred. Only `identity` (soul/personality) and `instructions` (user customizations) migrate in this spec. `OPERATING_MODEL`, `CHANNEL_GUIDANCE`, etc. stay as code constants in `prompt_builder.py` for a follow-up spec.
