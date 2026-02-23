# SPEC-018: Proactive Agent Memory + min-memory Integration

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-23
> **Updated:** 2026-02-23

## Goal

Make Clarity proactive — an agent that earns trust by doing things, not asking what to do. Replace the 4000-char memory blob with min-memory (semantic search, hierarchical scoping, cross-tool continuity with Claude Desktop/Code/ChatGPT). Rewrite bootstrap and onboarding prompts to be tool-first.

## Background

Clarity has the infrastructure for proactive behavior (heartbeat, session_open, onboarding) but the behavioral prompting is passive — "What are your priorities?" instead of using tools to demonstrate value. OpenClaw's key insight: agents earn trust by acting, not asking.

The memory system (`agent_long_term_memory`) is a single TEXT blob with no search, no structure, and no continuity with other tools. A production-grade memory server (min-memory) already exists with semantic vector search, entity relationships, hierarchical scoping (global/project/task), and multi-user isolation via Auth0 OAuth.

Integration design was researched in `docs/sdlc/research/memory_research.md` (Feature A4).

## Acceptance Criteria

- [ ] **AC-01:** min-memory accepts trusted backend requests via `X-Backend-Key` + `X-User-Id` headers, bypassing OAuth for server-to-server calls. [A8]
- [ ] **AC-02:** `MemoryClient` in chatServer makes async HTTP calls to min-memory's MCP JSON-RPC endpoint. [A1, A3]
- [ ] **AC-03:** Three new LangChain tools replace `SaveMemoryTool`/`ReadMemoryTool`: `store_memory` (write), `recall` (semantic search), `search_memory` (keyword search). [A6, A10]
- [ ] **AC-04:** Agent loader resolves Supabase UUID → min-memory user identity (`google-oauth2|{provider_id}`) via `auth.users.raw_user_meta_data`. [A8]
- [ ] **AC-05:** "What You Know" prompt section is populated by pre-fetching top 10 `core_identity` + `project_context` memories from min-memory (not from `agent_long_term_memory` blob). `build_agent_prompt()` stays sync. [A14]
- [ ] **AC-06:** Onboarding detection (`is_new_user`) checks min-memory for existing memories instead of `agent_long_term_memory` table. [A14]
- [ ] **AC-07:** `SESSION_OPEN_BOOTSTRAP_GUIDANCE` is rewritten to be tool-first: agent uses tools before greeting, reports findings, suggests one next step. Does NOT ask about preferences. [A14]
- [ ] **AC-08:** `ONBOARDING_SECTION` is rewritten with same philosophy — demonstrate value, don't interrogate. [A14]
- [ ] **AC-09:** Memory tool `prompt_section()` encourages proactive observation: "record what you learn from their messages, email patterns, task habits, and tone — don't wait to be asked." [A14]
- [ ] **AC-10:** Old `SaveMemoryTool`/`ReadMemoryTool` removed. Old tool rows deactivated in `agent_tools`. `agent_long_term_memory` table kept but not used. [A6]
- [ ] **AC-11:** `session_open_service.py` `_has_memory()` checks min-memory instead of Supabase. [A14]
- [ ] **AC-12:** Cross-tool continuity verified: memory stored via Claude Desktop MCP is visible to Clarity agent in "What You Know" section. [A14]

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

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/memory_client.py` | Async HTTP client for min-memory MCP endpoint |
| `supabase/migrations/XXXXXXXX_register_memory_tools.sql` | Deactivate old tools, register new ones |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/tools/memory_tools.py` | Replace SaveMemory/ReadMemory with StoreMemory/Recall/SearchMemory |
| `chatServer/services/prompt_builder.py` | Rewrite bootstrap, onboarding, returning guidance; update prompt_section text |
| `src/core/agent_loader_db.py` | MemoryClient creation, user identity resolution, pre-fetch from min-memory |
| `chatServer/services/session_open_service.py` | Update `_has_memory()` to check min-memory |
| `~/github/min-memory/src/auth.py` | Add trusted backend key auth path (external repo) |

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
- `async call_tool(tool_name, arguments) -> dict` — MCP JSON-RPC over HTTP

**Replace:** `chatServer/tools/memory_tools.py`
- `StoreMemoryTool` (name: `store_memory`) — args: text, memory_type, entity, scope, tags
- `RecallMemoryTool` (name: `recall`) — args: query, limit, memory_type
- `SearchMemoryTool` (name: `search_memory`) — args: query

### FU-3: Agent Loader Wiring

**File:** `src/core/agent_loader_db.py`

1. `_resolve_memory_user_id()` — reads `auth.users.raw_user_meta_data->>'provider_id'`, formats as `google-oauth2|{id}`, falls back to Supabase UUID
2. Create `MemoryClient` in async tool loading path, pass to tool constructors
3. Replace `_fetch_memory_notes_async` with min-memory `retrieve_context` call (top 10 core_identity + project_context)
4. Update onboarding detection to check min-memory

### FU-4: Proactive Prompt Rewrites

**File:** `chatServer/services/prompt_builder.py`

- **Bootstrap:** Tool-first. Use tools → introduce → share findings → suggest next step → store_memory. No preference questions.
- **Onboarding:** Same philosophy. Demonstrate, don't interrogate.
- **Memory prompt_section:** Proactive observation guidance. Record from behavior, not just explicit asks.
- **Learn from Interaction:** Notice patterns, infer preferences, record observations periodically.

### FU-5: Deprecation and Cleanup

- Remove old tool classes
- Remove old memory fetch helpers from agent loader
- Update session_open_service `_has_memory()`
- Migration: deactivate/register tool rows
- Keep `agent_long_term_memory` table (don't drop)

## Dependencies

- SPEC-017 (User-Scoped DB Access) — branching from this
- min-memory server running locally for dev/test
- SPEC-016 (Session Open) — already complete, provides the bootstrap/onboarding infrastructure we're rewriting

## Testing Requirements

### Unit Tests

- `test_memory_client.py`: HTTP call construction, error handling, response parsing
- `test_memory_tools.py`: StoreMemory/Recall/SearchMemory tool invocation, schema validation
- `test_prompt_builder.py`: Updated bootstrap text, onboarding text, memory prompt_section text
- `test_agent_loader_db.py`: User identity resolution, MemoryClient creation, pre-fetch formatting

### Integration Tests

- Round-trip: store via chatServer tool → retrieve via min-memory MCP → verify match
- Cross-tool: store via Claude Code min-memory MCP → verify appears in agent's "What You Know"

### Manual Verification (UAT)

- [ ] New user: open web app → agent uses tools before greeting, doesn't ask about preferences
- [ ] Existing user: agent's "What You Know" populated from min-memory
- [ ] Remember something: tell agent a fact → verify in min-memory via `mcp__claude_ai_memory-http__search`
- [ ] Cross-tool: store memory in Claude Desktop → verify Clarity sees it

## Functional Units (for Implementation)

1. **FU-1:** Trusted backend auth (min-memory repo, ~30 lines)
2. **FU-2:** MemoryClient + tools (chatServer, ~200 lines)
3. **FU-3:** Agent loader wiring (agent_loader_db.py, ~80 lines)
4. **FU-4:** Prompt rewrites (prompt_builder.py, text changes)
5. **FU-5:** Deprecation + migration (cleanup)

**Implementation order:** FU-1 → FU-2 → FU-3 → FU-4 → FU-5

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-12)
- [x] Every AC maps to at least one functional unit
- [x] Manual steps documented for user
- [x] External repo changes identified (min-memory)
- [x] Env vars documented (MEMORY_SERVER_URL, MEMORY_SERVER_BACKEND_KEY, TRUSTED_BACKEND_KEY)
- [x] Out-of-scope is explicit
- [x] Testing requirements map to ACs
- [x] Dependencies documented
