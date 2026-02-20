# CLAUDE.md — llm-agent Project Guide

## Project Overview

**llm-agent** is a platform for developing and interacting with LLM agents. Three components:

- **`webApp/`** — React frontend (Vite, TypeScript, Tailwind, Radix UI, React Query, Zustand)
- **`chatServer/`** — FastAPI backend (Python, LangChain, Supabase, PostgreSQL)
- **`src/`** — Core Python library (agent logic, CLI, config loading)

Monorepo managed with pnpm workspaces. Database on Supabase (27+ migrations in `supabase/migrations/`).

## Product Vision

Unified agent platform: all channels (web, Telegram, scheduled) share the same agent execution, approval, and notification systems. Every interaction registers in `chat_sessions` with a `channel` tag. See `.claude/skills/product-architecture/SKILL.md` for the full feature map and cross-cutting checklist.

## Architecture

```
llm-agent/
  chatServer/         # FastAPI backend — runs on :3001
    dependencies/     #   auth.py (JWT), agent_loader.py
    routers/          #   actions.py, external_api_router.py, email_agent_router.py
    services/         #   chat.py, pending_actions.py, audit_service.py
    database/         #   connection.py, supabase_client.py
    config/           #   settings.py, constants.py
    models/           #   chat.py, webhook.py, prompt_customization.py
  webApp/             # React frontend — runs on :5173 (proxies /api to :3001)
    src/
      api/hooks/      #   useChatApiHooks.ts, useActionsHooks.ts, useTaskHooks.ts
      components/     #   ui/, features/, navigation/
      features/       #   auth/ (useAuthStore, AuthProvider)
      pages/          #   TodayView, CoachPage, Login
      stores/         #   Zustand stores
      styles/         #   index.css, ui-components.css
  src/                # Core Python
    core/             #   agent_loader_db.py, customizable_agent.py, llm_interface.py
    cli/              #   CLI entry point
  config/agents/      # Agent YAML configs (assistant)
  supabase/           # Migrations and Supabase config
  tests/              # Python tests (pytest)
  docs/               # Architecture docs (chatServer decomposition)
  .archive/           # Archived legacy files (memory banks, old rules)
```

## Development Workflow

### Running locally
```bash
source .venv/bin/activate
pnpm dev                    # Starts both webApp (:5173) and chatServer (:3001)
# Or individually:
python -m chatServer.main   # Backend only
cd webApp && pnpm dev       # Frontend only
```

### Testing
```bash
# Python
pytest tests/                          # All Python tests
pytest tests/chatServer/security/      # Specific test dir

# Frontend
cd webApp && pnpm test                 # Vitest
```

### Linting
```bash
# Python
ruff check src/ chatServer/ tests/     # Lint
ruff format src/ chatServer/ tests/    # Format

# Frontend
cd webApp && pnpm lint                 # ESLint
cd webApp && pnpm format               # Prettier
cd webApp && pnpm validate:all         # ESLint + Stylelint + color/focus validation
```

### Before committing
1. All tests pass (`pytest` + `pnpm test`)
2. Linting passes (`ruff check` + `pnpm lint`)
3. No `.env` files staged
4. Changes match the plan/spec that was agreed upon

## Coding Standards

### Python (chatServer/, src/, tests/)
- **Linter/formatter:** Ruff (config in `ruff.toml`)
- Line length: 120
- Use type hints. Use `async`/`await` for IO operations.
- Follow existing service layer pattern: routers -> services -> database
- Dependencies injected via FastAPI `Depends()`

### TypeScript (webApp/)
- **Linter:** ESLint (config in `webApp/.eslintrc.cjs`)
- **Formatter:** Prettier (config in `webApp/.prettierrc`)
- **Colors:** Always use semantic tokens from `tailwind.config.js` (e.g., `bg-brand-primary`, `text-text-secondary`). Direct Tailwind colors (`bg-blue-500`) are ESLint errors.
- **Auth tokens:** Always get from `supabase.auth.getSession()`, never from Zustand store directly. See `useChatApiHooks.ts` for the pattern.
- Path aliases: `@/` maps to `src/`, `@components/` maps to `src/components/`

## Key Patterns

### Authentication (ES256 JWT)
Supabase issues **ES256** tokens (not HS256). `chatServer/dependencies/auth.py` handles both:
- ES256: fetches JWKS from Supabase, caches keys in memory
- HS256: fallback using `supabase_jwt_secret`
The `get_current_user` dependency extracts `sub` from the JWT payload.

### Agent execution
- Agents loaded from DB via `src/core/agent_loader_db.py`
- Cached in `AGENT_EXECUTOR_CACHE` (TTLCache, 15min TTL)
- LLM calls go through `langchain-anthropic` (ChatAnthropic)
- Response may be a list of content blocks — `chatServer/services/chat.py` normalizes to string

### Frontend API calls
- All hooks in `webApp/src/api/hooks/` follow the same pattern:
  1. Get session from `supabase.auth.getSession()`
  2. Attach `Authorization: Bearer <token>` header
  3. Use React Query for caching/refetching
- `enabled: !!user` guards prevent calls before auth is ready

### Actions/Approval system
- Endpoints in `chatServer/routers/actions.py` (prefix: `/api/actions`)
- Pending actions polled every 10s (`usePendingCount` hook)
- Services: `PendingActionsService`, `AuditService`

## Critical Files

| File | Purpose |
|------|---------|
| `chatServer/main.py` | FastAPI app, CORS, router registration, lifespan |
| `chatServer/dependencies/auth.py` | JWT verification (ES256 + HS256) |
| `chatServer/services/chat.py` | Chat endpoint logic, agent invocation |
| `chatServer/routers/actions.py` | Actions approval API |
| `chatServer/config/settings.py` | All server settings (env vars) |
| `src/core/agent_loader_db.py` | Agent loading from database |
| `src/core/agents/customizable_agent.py` | Agent executor with LLM init |
| `webApp/src/api/hooks/useChatApiHooks.ts` | Chat API hook (reference pattern) |
| `webApp/src/api/hooks/useActionsHooks.ts` | Actions hooks |
| `webApp/src/features/auth/useAuthStore.ts` | Auth state (Zustand) |
| `webApp/src/lib/supabaseClient.ts` | Supabase client singleton |
| `webApp/tailwind.config.js` | Semantic color tokens |
| `supabase/migrations/` | Database schema history |
| `tests/uat/conftest.py` | UAT shared fixtures (authenticated_client, supabase_fixture) |
| `tests/uat/fixtures/supabase_fixture.py` | Stateful in-memory Supabase mock for flow tests |

## Resolving Bugs and Problems

**Every bug fix or problem resolution MUST update project documentation.** Code fixes alone are insufficient — the root cause and solution must be captured so the same problem never recurs.

When you fix a bug or resolve a problem:

1. **Determine which documentation to update** (at least one is required):
   - **CLAUDE.md** — Add to "Known Gotchas" if it's a project-wide footgun or misconception
   - **Skills** (`.claude/skills/`) — Update the relevant pattern checklist or reference if the fix reveals a pattern violation or a missing pattern
   - **Hooks** (`.claude/hooks/`, `.claude/settings.json`) — Add or tighten a validation hook if the bug could have been caught automatically
   - **CLAUDE.md "Critical Files"** — Add the file if it was central to the bug and not already listed

2. **Write it down before closing the task.** The documentation update is part of the fix, not a follow-up.

3. **If the bug reveals a missing pattern**, create or update a skill. Patterns are only useful if they're discoverable.

4. **If the bug could have been caught by a hook**, add the hook. Prevention beats detection.

### What goes where

| Discovery | Update target |
|-----------|--------------|
| Misconception about how something works (e.g., ES256 vs HS256) | CLAUDE.md → Known Gotchas |
| Code written wrong way despite existing pattern | Skill checklist (make the rule more prominent) |
| No pattern existed for this scenario | New pattern in the relevant skill's reference.md |
| Bug could have been caught automatically | New or tightened hook |
| Critical file not listed | CLAUDE.md → Critical Files |

## SDLC Workflow

The project uses an agent-based SDLC for spec execution. See `.claude/skills/sdlc-workflow/SKILL.md` for the quick reference.

### Overview

```
Spec -> Orchestrator (team lead) -> Domain Agents + Reviewer (teammates) -> PR -> UAT -> Merge
```

Cross-domain dependency flow: `database-dev → backend-dev → frontend-dev`

### Agent Team

| Agent | Role | Scope | Mode |
|-------|------|-------|------|
| `.claude/agents/orchestrator.md` | Team lead — reads specs, creates tasks, writes contracts | All (read-only) | Delegate (no code) |
| `.claude/agents/database-dev.md` | SQL migrations, RLS, indexes | `supabase/migrations/`, `chatServer/database/` | Full capability |
| `.claude/agents/backend-dev.md` | Services, routers, models, API | `chatServer/`, `src/` | Full capability |
| `.claude/agents/frontend-dev.md` | Components, hooks, pages, stores | `webApp/src/` | Full capability |
| `.claude/agents/deployment-dev.md` | Docker, Fly.io, CI/CD, env config | Dockerfiles, fly.toml, CI/CD | Full capability |
| `.claude/agents/reviewer.md` | Reviews diffs, checks scope + patterns + tests | All (read-only) | Read-only |
| `.claude/agents/uat-tester.md` | Flow tests on integration branch | `tests/uat/` | Full capability |

### Cross-Team Contract Format

When one domain agent hands off to another, the orchestrator includes a contract in the task description:

```markdown
## Contract: [source-agent] -> [target-agent]

### Schema / API / Config provided:
- [concrete details: table DDL, endpoint paths, env var names]

### What [target] must implement:
- [specific deliverables]

### Assumptions [target] can make:
- [things already done and tested by the upstream agent]
```

### Git Conventions

- **Branch naming:** `feat/SPEC-NNN-short-description`
- **Commit format:** `SPEC-NNN: <imperative description>` + Co-Authored-By tag
- **PR-per-functional-unit:** Each self-contained piece (migration, service, API, UI) gets its own branch + PR
- **Worktrees:** Parallel implementers use `git worktree` for isolated working directories

### Testing Requirements

Every spec must include tests. Every new function gets a test. Missing tests are a BLOCKER in review.

- Python: `pytest tests/` mirroring source structure
- Frontend: Vitest with `@testing-library/react`
- Integration: `httpx.AsyncClient` for API, `msw` for frontend API mocking

### Feedback Loop

Agent mistakes are logged in `docs/sdlc/DEVIATIONS.md` with root cause and correction. Corrections update skills, hooks, agent definitions, or CLAUDE.md. See "Resolving Bugs and Problems" below for the pattern.

### Key SDLC Files

| File | Purpose |
|------|---------|
| `docs/sdlc/ROADMAP.md` | Milestones and goals |
| `docs/sdlc/BACKLOG.md` | Prioritized task queue |
| `docs/sdlc/specs/` | Spec files for autonomous execution |
| `docs/sdlc/DEVIATIONS.md` | Agent error log and corrections |
| `.claude/skills/sdlc-workflow/` | Workflow skill (quick ref + full reference) |

## Known Gotchas

1. **ES256 tokens** — Supabase issues ES256, not HS256. Don't revert auth.py to HS256-only.
2. **Content block lists** — Newer `langchain-anthropic` returns `[{"text": "...", "type": "text"}]` instead of plain strings. `chat.py` normalizes this.
3. **Auth token source** — Use `supabase.auth.getSession()` in frontend hooks, not `useAuthStore.getState().session` (Zustand may be stale/null on startup).
4. **Duplicate .env keys** — The root `.env` uses `export` prefix. If a key appears twice, the last one wins with `load_dotenv(override=True)`.
5. **Supabase client timing** — The Supabase client may not be initialized when agent tools are first wrapped. The approval wrapping logs a non-fatal warning.
6. **CORS** — Configured in `chatServer/main.py` via `settings.cors_origins`. Both frontend ports must be listed.
7. **Fly deploy from repo root** — `fly.toml` files live in `chatServer/` and `webApp/`, not the repo root. Use `flyctl deploy --config <app>/fly.toml --dockerfile <app>/Dockerfile` from root. Both Dockerfiles `COPY` paths are relative to the repo root.
8. **Color validation disabled** — `webApp/scripts/validate-colors.js` and `validate:colors` script exist but are removed from the build. The validation rules and tests (`validate:colors`, `validate:focus`) need review — they may not reflect the correct approach for semantic color enforcement with Tailwind. Revisit before re-enabling.
9. **Gmail tool factory functions** — `chatServer/tools/gmail_tools.py` does NOT export `create_gmail_digest_tool` or `create_gmail_search_tool`. A previous agent hallucinated these. The actual factories are `create_gmail_tool_provider()` and `get_gmail_tools_for_user()`.
10. **`.gitignore` `lib/` rule** — The root `.gitignore` contains `lib/` (Python packaging). `webApp/src/lib/` is negated with `!webApp/src/lib/`. If you add new `lib/` directories elsewhere, you may need similar negations.
11. **Settings created before `load_dotenv()`** — `chatServer/main.py` creates the `Settings` singleton at import time, but `load_dotenv()` runs later. Call `settings.reload_from_env()` after `load_dotenv()` so env vars from `.env` are picked up. Without this, any env var only present in `.env` (not shell env) will be `None`.
12. **Agent references use UUID FK, not `agent_name TEXT`** — `agent_tools` uses `agent_id UUID FK → agent_configurations(id)` (correct). Several legacy tables (`agent_long_term_memory`, `agent_schedules`, `agent_logs`, `reminders`) still use `agent_name TEXT` — this is tech debt. New tables MUST use `agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE` plus an explicit index. `agent_loader_db.py` has the UUID as `agent_db_config.get("id")` — pass it to tools/services instead of the name string.
13. **Frontend API base URL env var** — The only env var passed at Docker build time is `VITE_API_BASE_URL`. All frontend hooks must use `import.meta.env.VITE_API_BASE_URL || ''`. Never use `VITE_API_URL` — it doesn't exist in production and falls back to `http://localhost:3001`. In dev, the empty-string fallback makes relative `/api/...` calls that Vite's proxy routes to `localhost:3001`.
    - **Supabase env vars:** Backend reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (not `VITE_SUPABASE_URL` or `SUPABASE_SERVICE_KEY` — those are legacy names). Frontend reads `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (Vite requires `VITE_` prefix).
14. **AgentExecutor.agent must not be replaced with a raw RunnableSequence** — `AgentExecutor`'s Pydantic validator (`validate_runnable_agent`) wraps the runnable in `RunnableAgent`/`RunnableMultiActionAgent` during `__init__`, providing `aplan()` and `input_keys`. Directly assigning `self.agent = new_runnable_sequence` bypasses this validator and strips those methods, causing `AttributeError: 'RunnableSequence' object has no attribute 'aplan'` at runtime. **Always update `self.agent.runnable = new_runnable` instead of replacing `self.agent`.**
15. **chatServer is a proper Python package** — Always run via `python -m chatServer.main`, never `python -m chatServer.main`. This ensures `chatServer` is a real package so relative imports (`from .config.settings`) and absolute imports (`from chatServer.database.connection`) both work correctly. The Dockerfile uses `CMD ["python", "-m", "chatServer.main"]`. Never add try/except ImportError hacks for bare import fallbacks.
16. **Telegram: one bot = one webhook URL** — Each Telegram bot can only have one webhook. Running the server locally with a prod bot token steals the webhook from production. Use separate bot tokens per environment (create a dev bot via BotFather, set `TELEGRAM_BOT_TOKEN` differently in local `.env` vs Fly secrets).
17. **PostgREST upsert requires real UNIQUE constraint** — Supabase's PostgREST `ON CONFLICT` does not work with partial unique indexes (`WHERE ...`). If you need upsert, the column must have a plain `UNIQUE` constraint or primary key. Otherwise use select-then-insert.
18. **Two requirements.txt files** — Root `requirements.txt` is for local dev (installed into `.venv`). `chatServer/requirements.txt` is what the Dockerfile installs. **New dependencies must be added to both.** The Dockerfile only reads `chatServer/requirements.txt`, so missing deps there cause `ModuleNotFoundError` in production even if they work locally.
19. **New env vars require three places** — When adding a new environment variable: (1) local `.env`, (2) Fly secrets (`flyctl secrets set`), (3) GitHub repo secrets if used in CI/CD workflows (e.g., `--build-arg`). Missing any one causes failures in that environment.
20. **`os.getenv()` is scattered across many files** — Supabase credentials are read via `os.getenv()` in `settings.py`, `agent_loader_db.py`, `gmail_tools.py`, `memory_tools.py`, `update_instructions_tool.py`, and `email_digest_service.py`. When renaming an env var, grep the entire codebase — `settings.py` alone is not sufficient.
