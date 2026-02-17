# CLAUDE.md — llm-agent Project Guide

## Project Overview

**llm-agent** is a platform for developing and interacting with LLM agents. Three components:

- **`webApp/`** — React frontend (Vite, TypeScript, Tailwind, Radix UI, React Query, Zustand)
- **`chatServer/`** — FastAPI backend (Python, LangChain, Supabase, PostgreSQL)
- **`src/`** — Core Python library (agent logic, CLI, config loading)

Monorepo managed with pnpm workspaces. Database on Supabase (27+ migrations in `supabase/migrations/`).

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
  config/agents/      # Agent YAML configs (assistant, architect, test_agent)
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
python chatServer/main.py   # Backend only
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

## Known Gotchas

1. **ES256 tokens** — Supabase issues ES256, not HS256. Don't revert auth.py to HS256-only.
2. **Content block lists** — Newer `langchain-anthropic` returns `[{"text": "...", "type": "text"}]` instead of plain strings. `chat.py` normalizes this.
3. **Auth token source** — Use `supabase.auth.getSession()` in frontend hooks, not `useAuthStore.getState().session` (Zustand may be stale/null on startup).
4. **Duplicate .env keys** — The root `.env` uses `export` prefix. If a key appears twice, the last one wins with `load_dotenv(override=True)`.
5. **Supabase client timing** — The Supabase client may not be initialized when agent tools are first wrapped. The approval wrapping logs a non-fatal warning.
6. **CORS** — Configured in `chatServer/main.py` via `settings.cors_origins`. Both frontend ports must be listed.
