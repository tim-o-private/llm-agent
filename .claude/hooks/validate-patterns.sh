#!/usr/bin/env bash
# PostToolUse hook: validates Write/Edit operations against project patterns
# Reads tool_input from stdin, outputs JSON with additionalContext

set -euo pipefail

INPUT=$(cat)

# Extract the file path from tool input
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)

if [ -z "$FILE_PATH" ]; then
  echo '{"additionalContext": ""}'
  exit 0
fi

# Determine which pattern set applies based on file path/extension
CONTEXT=""

case "$FILE_PATH" in
  */chatServer/*.py|*/src/*.py|*/tests/*.py)
    CONTEXT="PATTERN CHECK: You just modified a Python backend file. Verify against backend patterns:
- Using Depends(get_supabase_client) or Depends(get_db_connection) — no new connections?
- Business logic in services, not routers?
- Pydantic models for request/response validation?
- RLS handles user scoping (no manual user_id filtering)?
- Depends(get_current_user) for auth — no manual header parsing?
- Error handling re-raises HTTPException, logs unexpected errors?
- Content block lists normalized to strings in chat responses?
Run /backend-patterns for full reference."
    ;;
  */supabase/migrations/*.sql)
    CONTEXT="PATTERN CHECK: You just modified a database migration. Verify against database patterns:
- RLS enabled with is_record_owner() policy?
- UUID primary key with gen_random_uuid()?
- user_id FK to auth.users(id) ON DELETE CASCADE?
- created_at and updated_at TIMESTAMPTZ columns?
- Auto-update trigger on updated_at?
- Indexes on user_id and common query columns?
- Table and column COMMENT statements?
- snake_case naming throughout?
Run /database-patterns for full reference."
    ;;
  */webApp/src/*.ts|*/webApp/src/*.tsx)
    CONTEXT="PATTERN CHECK: You just modified a frontend file. Verify against frontend patterns:
- No @radix-ui/themes component imports (only Theme provider)?
- All colors use semantic tokens (bg-brand-primary, text-text-secondary)?
- Data fetching via React Query hooks, not useState+useEffect?
- Auth tokens from supabase.auth.getSession(), not Zustand?
- Modals via useOverlayStore, not local state?
- Loading + error states handled?
- Forms use react-hook-form + Zod?
- Keyboard support + ARIA labels on interactive elements?
Run /frontend-patterns for full reference."
    ;;
  *Dockerfile*|*/fly.toml|*/nginx.conf|*/.dockerignore)
    CONTEXT="PATTERN CHECK: You just modified a deployment file. Verify against integration-deployment patterns:
- chatServer Dockerfile copies all needed Python packages (not just main.py)?
- webApp Dockerfile uses --mount=type=secret for VITE_ vars (not ARGs)?
- Fly secrets set for any new env vars?
- CORS origins updated if frontend URL changed?
- .dockerignore excludes .env, node_modules, .venv?
Run /integration-deployment for full reference."
    ;;
  *)
    # Not a recognized pattern file — no check needed
    echo '{"additionalContext": ""}'
    exit 0
    ;;
esac

# Output JSON with the pattern reminder
ESCAPED_CONTEXT=$(echo "$CONTEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
echo "{\"additionalContext\": ${ESCAPED_CONTEXT}}"
