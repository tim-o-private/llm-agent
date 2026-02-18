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
  */chatServer/tools/*.py)
    CONTEXT="PATTERN CHECK: You just modified a tool file. Verify against backend patterns:
- Tool name follows verb_resource pattern (e.g., create_reminder, list_reminders)?
- Approved verbs: create, list, get, update, delete, search, save, read, send, fetch?
- Domain prefix on the resource, not the verb: search_gmail_messages NOT gmail_search?
- Class name matches: Create{Resource}Tool, List{Resources}Tool, etc.?
- Using Depends(get_supabase_client) or Depends(get_db_connection) — no new connections?
- Business logic in services, not routers?
Run /backend-patterns for full reference."
    ;;
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
    # Check for agent_name TEXT anti-pattern
    AGENT_NAME_CHECK=""
    if grep -qiE 'agent_name\s+TEXT' "$FILE_PATH" 2>/dev/null; then
      AGENT_NAME_CHECK="
⚠️  CRITICAL: This migration uses 'agent_name TEXT'. This is WRONG.
Use instead: agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE
See CLAUDE.md gotcha #12."
    fi

    # Check for migration timestamp collision
    COLLISION_CHECK=""
    MIGRATION_BASENAME=$(basename "$FILE_PATH")
    PREFIX=$(echo "$MIGRATION_BASENAME" | grep -oP '^\d{14}' || true)
    if [ -n "$PREFIX" ]; then
      # Find the common git dir (works in worktrees)
      COMMON_DIR=$(git -C "$(dirname "$FILE_PATH")" rev-parse --git-common-dir 2>/dev/null || true)
      if [ -n "$COMMON_DIR" ] && [ "$COMMON_DIR" != ".git" ]; then
        MAIN_REPO=$(dirname "$COMMON_DIR")
        EXISTING=$(ls "$MAIN_REPO/supabase/migrations/" 2>/dev/null | grep "^${PREFIX}" | grep -v "$MIGRATION_BASENAME" || true)
        if [ -n "$EXISTING" ]; then
          NEXT_PREFIX=$(ls "$MAIN_REPO/supabase/migrations/" 2>/dev/null | grep -oP '^\d{14}' | sort | tail -1 || true)
          if [ -n "$NEXT_PREFIX" ]; then
            NEXT_PREFIX=$((NEXT_PREFIX + 1))
          fi
          COLLISION_CHECK="
⚠️  WARNING: Migration prefix '$PREFIX' already exists in main repo: $EXISTING
Next available prefix: ${NEXT_PREFIX}"
        fi
      fi
    fi

    CONTEXT="PATTERN CHECK: You just modified a database migration. Verify against database patterns:
- RLS enabled with is_record_owner() policy?
- UUID primary key with gen_random_uuid()?
- user_id FK to auth.users(id) ON DELETE CASCADE?
- created_at and updated_at TIMESTAMPTZ columns?
- Auto-update trigger on updated_at?
- Indexes on user_id and common query columns?
- Table and column COMMENT statements?
- snake_case naming throughout?
- Agent references use agent_id UUID FK, NOT agent_name TEXT?
Run /database-patterns for full reference.${AGENT_NAME_CHECK}${COLLISION_CHECK}"
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
