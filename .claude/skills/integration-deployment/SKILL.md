---
name: integration-deployment
description: Integration testing, Docker builds, and Fly.io deployment patterns. Use when building Docker images, deploying to Fly.io, configuring CI/CD, managing environment variables and secrets, troubleshooting deployment issues, or running integration tests across webApp and chatServer.
---

# Integration & Deployment

## Platform: Fly.io

Both apps deploy as Docker containers to Fly.io in the `iad` (US East) region.

| App | Fly name | Port | VM | Image |
|-----|----------|------|-----|-------|
| chatServer | `clarity-chatserver` | 3001 | shared-cpu-1x, 1GB | python:3.12-slim |
| webApp | `clarity-webapp` | 80 | shared-cpu-1x, 256MB | nginx:stable-alpine |

Both use `auto_stop_machines = 'stop'` and `min_machines_running = 0` for cost control.

## Quick Reference

### Deploy commands
```bash
# Automatic: push to main triggers .github/workflows/fly-deploy.yml
# Both apps deploy in parallel via GitHub Actions

# Manual deploy from project root:
flyctl deploy --config chatServer/fly.toml --dockerfile chatServer/Dockerfile
flyctl deploy --config webApp/fly.toml --dockerfile webApp/Dockerfile
```

### Set secrets
```bash
# chatServer secrets
flyctl secrets set SUPABASE_URL="..." SUPABASE_SERVICE_ROLE_KEY="..." ANTHROPIC_API_KEY="..." -a clarity-chatserver

# webApp secrets (used at build time)
flyctl secrets set VITE_SUPABASE_URL="..." VITE_SUPABASE_ANON_KEY="..." VITE_API_BASE_URL="https://clarity-chatserver.fly.dev" -a clarity-webapp
```

### Check status
```bash
flyctl status -a clarity-chatserver
flyctl status -a clarity-webapp
flyctl logs -a clarity-chatserver
flyctl logs -a clarity-webapp
```

## Pre-Deploy Checklist

- [ ] All tests pass (`pytest` + `cd webApp && pnpm test`)
- [ ] Linting clean (`ruff check` + `pnpm lint`)
- [ ] No `.env` files in Docker context (check `.dockerignore`)
- [ ] Fly secrets set for any new env vars (chatServer AND webApp if applicable)
- [ ] GitHub repo secrets set if env var is used in CI/CD workflows (e.g., `--build-arg`)
- [ ] New Python deps added to BOTH `requirements.txt` (root) AND `chatServer/requirements.txt`
- [ ] Database migrations applied to production Supabase
- [ ] CORS origins in `chatServer/main.py` include the production frontend URL
- [ ] All frontend API hooks use `VITE_API_BASE_URL` (not `VITE_API_URL`) — only `VITE_API_BASE_URL` is passed at build time

## Environment Variables

### chatServer (runtime secrets on Fly)
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin key for server-side Supabase access |
| `SUPABASE_JWT_SECRET` | For HS256 JWT fallback verification |
| `ANTHROPIC_API_KEY` | Claude API key for agent LLM calls |
| `PORT` | `3001` (set in fly.toml) |
| `LLM_AGENT_SRC_PATH` | `src` (set in fly.toml) |
| `RUNNING_IN_DOCKER` | `true` (set in Dockerfile) |

### webApp (build-time ARGs via GitHub secrets + `--build-arg` in CI)
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL (public) |
| `SUPABASE_ANON_KEY` | Supabase anon key (public) |
| `VITE_API_BASE_URL` | chatServer URL (e.g., `https://clarity-chatserver.fly.dev`) |

**webApp vars are injected at build time** via Docker `ARG` in `.github/workflows/fly-deploy.yml`. These are GitHub repo secrets (not Fly secrets). They are NOT truly secret — they're baked into the JS bundle.

## Key Gotchas

1. **Fly deploy from repo root** — `fly.toml` lives in `chatServer/` and `webApp/`. Deploy with `flyctl deploy --config <app>/fly.toml --dockerfile <app>/Dockerfile`.
2. **CORS** — Both frontend ports must be in `settings.cors_origins` in `chatServer/main.py`.
3. **Telegram: one bot = one webhook URL** — Running locally with prod bot token steals the webhook from production. Use separate bot tokens per environment.

## Detailed Reference

For Dockerfiles, fly.toml configs, API routing (dev proxy vs production), Supabase environment management, and CI/CD plans, see [reference.md](reference.md).
