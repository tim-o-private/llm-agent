# SPEC-018: Proactive Agent Memory + min-memory Integration

> **Status:** Implemented
> **Author:** Tim + Claude
> **Created:** 2026-02-23
> **Updated:** 2026-02-23
> **Branch:** `feat/spec-018-proactive-memory`

## Goal

Make the agent proactive — earning trust by doing things, not asking what to do. Replace the 4000-char memory blob with min-memory (semantic search, hierarchical scoping, cross-tool continuity with Claude Desktop/Code/ChatGPT). Rewrite bootstrap and onboarding prompts to be tool-first.

## Background

The agent has the infrastructure for proactive behavior (heartbeat, session_open, onboarding) but the behavioral prompting is passive — "What are your priorities?" instead of using tools to demonstrate value. OpenClaw's key insight: agents earn trust by acting, not asking.

The memory system (`agent_long_term_memory`) is a single TEXT blob with no search, no structure, and no continuity with other tools. A production-grade memory server (min-memory) already exists with semantic vector search, entity relationships, hierarchical scoping (global/project/task), and multi-user isolation via Auth0 OAuth.

Integration design was researched in `docs/sdlc/research/memory_research.md` (Feature A4).

## Acceptance Criteria

- [x] **AC-01:** min-memory accepts trusted backend requests via `X-Backend-Key` + `X-User-Id` headers, bypassing OAuth for server-to-server calls. [A8]
- [x] **AC-02:** `MemoryClient` in chatServer makes async HTTP calls to min-memory's `/api/tools/call` REST endpoint (direct JSON, not MCP transport). [A1, A3]
- [x] **AC-03:** Eleven new LangChain tools replace `SaveMemoryTool`/`ReadMemoryTool`, exposing the full min-memory API: `store_memory`, `recall`, `search_memory`, `fetch_memory`, `delete_memory`, `update_memory`, `set_project`, `link_memories`, `list_entities`, `search_entities`, `get_context_info`. [A6, A10]
- [x] **AC-04:** Agent loader resolves Supabase UUID → min-memory user identity (`google-oauth2|{provider_id}`) via `auth.users.raw_user_meta_data`. [A8]
- [x] **AC-05:** "What You Know" prompt section is populated by pre-fetching top 10 `core_identity` + `project_context` memories from min-memory (not from `agent_long_term_memory` blob). `build_agent_prompt()` stays sync. [A14]
- [x] **AC-06:** Onboarding detection (`is_new_user`) checks min-memory for existing memories instead of `agent_long_term_memory` table. [A14]
- [x] **AC-07:** `SESSION_OPEN_BOOTSTRAP_GUIDANCE` is rewritten to be tool-first: agent uses tools before greeting, reports findings, suggests one next step. Does NOT ask about preferences. [A14]
- [x] **AC-08:** `ONBOARDING_SECTION` is rewritten with same philosophy — demonstrate value, don't interrogate. [A14]
- [x] **AC-09:** Memory tool `prompt_section()` encourages proactive observation: "record what you learn from their messages, email patterns, task habits, and tone — don't wait to be asked." [A14]
- [x] **AC-10:** Old `SaveMemoryTool`/`ReadMemoryTool` removed. Old tool rows deactivated in `agent_tools`. `agent_long_term_memory` table kept but not used. [A6]
- [x] **AC-11:** `session_open_service.py` `_has_memory()` checks min-memory instead of Supabase. [A14]
- [x] **AC-12:** Cross-tool continuity verified: memory stored via Claude Desktop MCP is visible to agent in "What You Know" section. [A14]

## Manual Steps (User must do before/during implementation)

### min-memory side (~/github/min-memory)

1. **Generate a trusted backend key:** `openssl rand -hex 32`
2. **Add to min-memory environment** (local `.env` + GCP deployment): `TRUSTED_BACKEND_KEY=<key>`
3. **No Auth0 changes needed** — trusted backend auth bypasses Auth0 for server-to-server calls

### Supabase

4. **Verify user identity mapping:** `raw_user_meta_data->>'provider_id'` must contain Google provider ID (populated automatically by Supabase Google OAuth)
5. **No new tables or RLS policies needed** — memory moves out of Supabase entirely

### chatServer environment

6. **Add env vars** to `.env`, Fly secrets, and GitHub secrets:
   - `MEMORY_SERVER_URL=http://localhost:8080` (local) / `https://memory.yourdomain.com` (prod)
   - `MEMORY_SERVER_BACKEND_KEY=<same-key>`

### DB tool registration

7. **After implementation:** Migration deactivates old tools, registers new ones. Server restart required (executor cache).

## Spec Deviations (vs. Original Plan)

| Area | Planned | Actual | Rationale |
|------|---------|--------|-----------|
| Tool count | 3 tools (store, recall, search) | 11 tools (full min-memory API) | Expose all capabilities; thin wrappers are cheap |
| Transport | MCP JSON-RPC over `/mcp` | Direct REST via `/api/tools/call` | MCP Streamable HTTP requires session management — unsuitable for server-to-server |
| DB tool type | `agent_tool_type` enum | `VARCHAR(100)` | Enum required ALTER TYPE for every new tool class; VARCHAR is flexible |
| Approval tiers | Not in spec | All 11 tools added as AUTO_APPROVE | Unknown tools default to REQUIRES_APPROVAL; needed explicit registration |

## Scope

### Files Created

| File | Purpose |
|------|---------|
| `chatServer/services/memory_client.py` | Async HTTP client for min-memory `/api/tools/call` endpoint |
| `supabase/migrations/20260223000002_register_memory_tools.sql` | Convert enum to VARCHAR, deactivate old tools, register 11 new ones |
| `scripts/wipe_user_memories.py` | Dev utility: wipe test user memories (guards against OAuth users) |

### Files Modified

| File | Change |
|------|--------|
| `chatServer/tools/memory_tools.py` | Replace SaveMemory/ReadMemory with 11 `_MemoryToolBase` subclasses |
| `chatServer/services/prompt_builder.py` | Rewrite bootstrap, onboarding, returning guidance; update prompt_section text |
| `src/core/agent_loader_db.py` | MemoryClient creation, user identity resolution, pre-fetch from min-memory, TOOL_REGISTRY for all 11 tools |
| `chatServer/services/session_open_service.py` | Update `_has_memory()` to check min-memory via direct REST |
| `chatServer/security/approval_tiers.py` | Add all 11 memory tools as AUTO_APPROVE |
| `~/github/min-memory/` | Trusted backend key auth + `/api/tools/call` endpoint (external repo) |

### Out of Scope

- Dropping `agent_long_term_memory` table (keep as fallback)
- Migrating existing blob data (let agent accumulate fresh structured memories)
- Making `build_agent_prompt()` async (pre-fetch in loader instead)
- Composable prompt system refactor (future spec)
- Session lifecycle model changes (future spec)
- Frontend changes (no UI work in this spec)

## Technical Approach

### FU-1: Trusted Backend Auth in min-memory

**File:** `~/github/min-memory/src/auth.py`

Add `X-Backend-Key` + `X-User-Id` header check before OAuth fallback in `get_current_user()`. Uses Starlette request context.

### FU-2: MemoryClient + New LangChain Tools

**New:** `chatServer/services/memory_client.py`
- `MemoryClient(base_url, backend_key, user_id)`
- `async call_tool(tool_name, arguments) -> dict` — direct REST to `/api/tools/call`

**Replace:** `chatServer/tools/memory_tools.py` — 11 tools via `_MemoryToolBase` pattern:
- `StoreMemoryTool` (name: `store_memory`) — write structured memories
- `RecallMemoryTool` (name: `recall`) — semantic context retrieval
- `SearchMemoryTool` (name: `search_memory`) — keyword search
- `FetchMemoryTool` (name: `fetch_memory`) — get by ID
- `DeleteMemoryTool` (name: `delete_memory`) — soft delete
- `UpdateMemoryTool` (name: `update_memory`) — modify existing memory
- `SetProjectTool` (name: `set_project`) — set project scope
- `LinkMemoriesTool` (name: `link_memories`) — create relationships
- `ListEntitiesTool` (name: `list_entities`) — browse entities
- `SearchEntitiesTool` (name: `search_entities`) — fuzzy entity search
- `GetContextInfoTool` (name: `get_context_info`) — environment info

### FU-3: Agent Loader Wiring

**File:** `src/core/agent_loader_db.py`

1. `_resolve_memory_user_id()` — reads `auth.users.raw_user_meta_data->>'provider_id'`, formats as `google-oauth2|{id}`, falls back to Supabase UUID
2. Create `MemoryClient` in async tool loading path, pass to tool constructors
3. `_prefetch_memory_notes()` calls min-memory `retrieve_context` (top 10 core_identity + project_context), parses direct REST response format
4. Onboarding detection checks min-memory

### FU-4: Proactive Prompt Rewrites

**File:** `chatServer/services/prompt_builder.py`

- **Bootstrap:** Tool-first. Use tools → introduce → share findings → suggest next step → store_memory. No preference questions.
- **Onboarding:** Same philosophy. Demonstrate, don't interrogate.
- **Memory prompt_section:** Proactive observation guidance. Record from behavior, not just explicit asks.
- **Learn from Interaction:** Notice patterns, infer preferences, record observations periodically.

### FU-5: Deprecation and Cleanup

- Remove old tool classes (`SaveMemoryTool`, `ReadMemoryTool`)
- Remove old memory fetch helpers from agent loader
- Update session_open_service `_has_memory()`
- Migration: convert `agent_tool_type` enum → VARCHAR(100), deactivate old tools, register new ones
- Add all 11 tools to `approval_tiers.py` as AUTO_APPROVE
- Keep `agent_long_term_memory` table (don't drop)

## Dependencies

- SPEC-017 (User-Scoped DB Access) — branching from this
- min-memory server with `/api/tools/call` endpoint and trusted backend auth

## Testing

### Unit Tests (751 passed, 10 skipped)

- `test_memory_client.py` (7 tests): payload format, headers, URL, response types, error handling
- `test_memory_tools.py` (25 tests): all 11 tools — invocation, schema validation, error handling, prompt_section
- `test_prompt_builder.py`: updated bootstrap, onboarding, memory prompt_section text
- `test_ltm_loading.py` (7 tests): pre-fetch formatting, dict/list responses, error handling, user identity resolution

### Manual Verification (UAT)

- [x] store_memory: agent stores memory, confirmed in min-memory
- [x] recall: agent retrieves cross-tool memories from Claude Desktop
- [x] Cross-tool continuity: memories stored via Claude Code MCP visible in agent's "What You Know"
- [ ] New user bootstrap: zero memories → agent uses tools before greeting

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-12)
- [x] Every AC maps to at least one functional unit
- [x] Manual steps documented for user
- [x] External repo changes identified (min-memory)
- [x] Env vars documented (MEMORY_SERVER_URL, MEMORY_SERVER_BACKEND_KEY, TRUSTED_BACKEND_KEY)
- [x] Out-of-scope is explicit
- [x] Testing requirements map to ACs
- [x] Dependencies documented
- [x] Spec deviations documented
