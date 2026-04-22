# AGENTS.md — llm-agent

Compact guide for OpenCode sessions. If a fact is obvious from filenames or standard tooling, it's omitted.

## Monorepo structure

- `chatServer/` — FastAPI backend (Python 3.12). Run as module: `python -m chatServer.main`
- `webApp/` — React + Vite frontend (Node 20, pnpm workspace). Package name: `clarity-frontend`
- `src/` — Core Python agent logic (loaded via `LLM_AGENT_SRC_PATH=src`)
- `supabase/migrations/` — PostgreSQL migrations (RLS-first, 44+)
- `tests/` — pytest (backend) + vitest (frontend)

## Quick commands

```bash
# Start everything (backend :3001, frontend :3000, ngrok)
pnpm dev

# Backend only (from repo root, .venv activated)
python -m chatServer.main

# Frontend only
pnpm --filter clarity-frontend dev

# Tests
pytest tests/                              # unit tests only
cd webApp && pnpm test                     # vitest + jsdom

# Lint / typecheck
ruff check src/ chatServer/ tests/
cd webApp && pnpm lint                     # eslint + tsc implied by build
cd webApp && pnpm validate:all             # lint + css + color + focus checks
```

## Environment setup

- Python virtual environment at repo root `.venv/` (not inside `chatServer/`)
- Root `.env` required. Key vars: `SUPABASE_*`, `GOOGLE_*`, `TELEGRAM_*`, `CLARITY_ANTHROPIC_API_KEY`, `LLM_AGENT_SRC_PATH=src`
- `webApp/.env` required with `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_SERVICE_KEY`
- No `.env.example` exists — copy patterns from existing `.env` files or ask for values

## Testing quirks

- **pytest.ini** sets `pythonpath = . src` and `asyncio_mode = auto`
- Integration tests (`marker = integration`) require `--run-integration` + live database
- Sandbox tests (`marker = sandbox`) require `--run-sandbox` + `bwrap` binary installed
- Both are deselected by default (see `tests/conftest.py`)
- Frontend tests use `vitest` + `jsdom` + `@testing-library/jest-dom/vitest`

## Python conventions

- **Single source of truth:** root `requirements.txt`. `pyproject.toml` reads from it dynamically. CI and Dockerfile both use this file.
- **Never run `chatServer` bare:** always `python -m chatServer.main`. It's a proper package; bare scripts break imports.
- **Ruff:** target `py312`, line-length 120, first-party packages: `chatServer`, `src`
- **JWT:** Supabase issues ES256 tokens. `auth.py` verifies ES256; don't revert to HS256-only.
- **Supabase clients:** Routers must use `get_user_scoped_client` (auto-filters by user_id). Background services use `get_system_client`. Never use raw `get_supabase_client` in services/routers.

## Frontend conventions

- **Dev server port:** 3000 (not 5173). Vite proxies `/api` and `/oauth` to `localhost:3001`.
- **Path aliases:** `@`, `@components`, `@features`, `@hooks`, `@lib`, `@styles`
- **Styling:** Radix Themes + Tailwind. Custom `validate:colors` script forbids Tailwind default colors, hex, rgb, hsl — use semantic tokens or Radix variables.
- **Build:** `tsc && vite build`. Type errors block the build.

## Database & migrations

- RLS-first: every table has Row Level Security. Application code does not manually filter by `user_id`.
- Agent definitions, tool registrations, and schedules live in PostgreSQL — not YAML files.
- Migrations are in `supabase/migrations/`. There is no local Supabase CLI dev server configured in this repo.

## Deployment

- Fly.io for both services. `fly-deploy.yml` deploys on push to `main`, conditional on path changes.
- Post-deploy smoke tests hit health endpoints; rollback on failure.
- New env vars need three places: local `.env`, Fly secrets (`flyctl secrets set`), and GitHub secrets if used in CI.

## Dev MCP server (`clarity-dev`)

- `scripts/mcp/clarity_dev_server.py` exposes `chat_with_clarity()` for end-to-end agent testing without a browser.
- Requires `pnpm dev` running + `CLARITY_DEV_USERNAME`/`CLARITY_DEV_PASSWORD` in `.env`.
- Registered in `.mcp.json` (Claude Code loads it automatically).

## Log locations

- `logs/chatserver.log` — backend output from `pnpm dev`
- `logs/webapp.log` — frontend output from `pnpm dev`

## CI workflows

- `.github/workflows/ci-tests.yml` — frontend (PR to `main`/`develop`, paths: `webApp/**`)
- `.github/workflows/python-pytest.yml` — backend (PR to `main`, paths: `chatServer/**`, `src/**`, `tests/**`)
- `.github/workflows/fly-deploy.yml` — deploy on push to `main`

## Where to look next

- `CLAUDE.md` — project vision, cross-domain gotchas, SDLC workflow
- `docs/sdlc/ARCHITECTURE-PRINCIPLES.md` — decision-making framework
- `.claude/skills/backend-patterns/` — FastAPI/Python patterns
- `.claude/skills/frontend-patterns/` — React/TypeScript patterns
- `.claude/skills/database-patterns/` — PostgreSQL/Supabase patterns
- `.claude/skills/integration-deployment/` — Docker, Fly.io, env vars
