# Integration & Deployment — Full Reference

## Docker: chatServer

`chatServer/Dockerfile`:
```dockerfile
FROM python:3.12-slim-bullseye
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER="true"
ENV PYTHONPATH="/app/src"
ENV CHAT_SERVER_BASE_URL="https://clarity-chatserver.fly.dev"

COPY chatServer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY config /app/config
COPY data/global_context /app/data/global_context
COPY chatServer/main.py /app/main.py

EXPOSE 3001
CMD ["python", "main.py"]
```

Key points:
- `PYTHONPATH="/app/src"` so `from src.core...` imports work
- `RUNNING_IN_DOCKER="true"` adjusts sys.path and .env loading in main.py
- Only `main.py` is copied (not the whole chatServer dir) — this needs updating if new files are added
- `data/global_context` contains shared context files for agents

## Docker: webApp

`webApp/Dockerfile` (multi-stage):
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY webApp/package.json ./webApp/
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
COPY webApp/ ./webApp/

# Secrets mounted at build time (not ARGs, not ENV)
RUN --mount=type=secret,id=VITE_API_BASE_URL \
    --mount=type=secret,id=VITE_SUPABASE_ANON_KEY \
    --mount=type=secret,id=VITE_SUPABASE_URL \
    VITE_API_BASE_URL="$(cat /run/secrets/VITE_API_BASE_URL)" \
    VITE_SUPABASE_URL="$(cat /run/secrets/VITE_SUPABASE_URL)" \
    VITE_SUPABASE_ANON_KEY="$(cat /run/secrets/VITE_SUPABASE_ANON_KEY)" \
    pnpm --filter clarity-frontend build

# Stage 2: Serve
FROM nginx:stable-alpine
COPY --from=builder /app/webApp/dist /usr/share/nginx/html
COPY webApp/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Key points:
- VITE_ vars are build-time only (baked into JS bundle by Vite)
- Uses `--mount=type=secret` instead of ARGs for security
- Requires `webApp/nginx.conf` for SPA routing (all paths → index.html)
- `pnpm --filter clarity-frontend build` targets the webApp workspace

## Fly.io Configuration

### chatServer (`chatServer/fly.toml`)
```toml
app = 'clarity-chatserver'
primary_region = 'iad'

[build]
  dockerfile = 'Dockerfile'

[env]
  PORT = '3001'
  LLM_AGENT_SRC_PATH = 'src'

[http_service]
  internal_port = 3001
  force_https = true
  auto_stop_machines = 'stop'
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = '1gb'
  cpu_kind = 'shared'
  cpus = 1
```

### webApp (`webApp/fly.toml`)
```toml
app = 'clarity-webapp'
primary_region = 'iad'

[build]
  dockerfile = 'Dockerfile'

[http_service]
  internal_port = 80
  force_https = true
  auto_stop_machines = 'stop'
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = '256mb'
  cpu_kind = 'shared'
  cpus = 1

[[statics]]
  guest_path = '/usr/share/nginx/html'
  url_prefix = '/'
```

## API Routing: Dev vs Production

### Development (Vite dev server)
Frontend runs on `:5173`, proxy forwards `/api/*` to `localhost:3001`:
```typescript
// webApp/vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:3001',
      changeOrigin: true,
    },
  },
}
```
Frontend code calls relative paths: `fetch('/api/chat')`.

### Production (Fly.io)
No proxy. Frontend must use `VITE_API_BASE_URL` for absolute URLs:
```typescript
const apiUrl = `${import.meta.env.VITE_API_BASE_URL}/api/chat`;
```
chatServer CORS must include the production frontend URL.

## Supabase Environment Management

| Environment | Database | How to use |
|-------------|----------|------------|
| Local dev | `supabase start` (local Docker) or dev project on Supabase Cloud | Automatic with `.env` |
| Staging | Separate Supabase Cloud project (optional) | Separate secrets |
| Production | Dedicated Supabase Cloud project | Fly.io secrets |

### Applying migrations
```bash
# Local
supabase db push

# Production (via linked project)
supabase link --project-ref <project-id>
supabase db push
```

## Known Deployment Issues

1. **chatServer Dockerfile only copies `main.py`** — if new Python modules are added to chatServer (routers, services, etc.), the Dockerfile needs updating to copy the full package
2. **webApp secrets are build-time** — changing VITE_ vars requires a rebuild, not just a restart
3. **Auto-stop machines** — first request after idle has cold start latency (~2-5s for chatServer)
4. **CORS** — production CORS origins must be updated in `chatServer/main.py` when domains change

## CI/CD — GitHub Actions

Automated deployment via `.github/workflows/fly-deploy.yml`:
- **Trigger:** push to `main`
- **Jobs:** `deploy-chatserver` and `deploy-webapp` run in parallel
- **Each job:** checkout → setup flyctl → `flyctl deploy --remote-only --config <app>/fly.toml --dockerfile <app>/Dockerfile`
- **Secret:** `FLY_API_TOKEN` stored as GitHub repo secret

Both Dockerfiles use `COPY` paths relative to the repo root (e.g., `COPY chatServer/requirements.txt`, `COPY src /app/src`), so the build context must be the repo root — not the app subdirectory.

### Key constraint
The `--config` and `--dockerfile` flags must both be specified when running from repo root, because `fly.toml` is in a subdirectory but the Docker build context is the repo root.

### Not yet automated
- Running tests before deploy (should be added as a prerequisite job)
- `supabase db push` for migrations (still manual before deploy)

## Integration Testing Approach

```bash
# 1. Start both services locally
source .venv/bin/activate
python chatServer/main.py &
cd webApp && pnpm dev &

# 2. Run Python integration tests
pytest tests/ -m integration

# 3. Run frontend tests
cd webApp && pnpm test

# 4. Manual smoke test
# - Login via webApp
# - Send a chat message
# - Check pending actions count
# - Verify agent response displays correctly
```
