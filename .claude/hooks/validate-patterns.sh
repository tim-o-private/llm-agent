#!/usr/bin/env bash
# PostToolUse hook: blocks known anti-patterns on Write/Edit
# Exit 0 = silent pass, Exit 2 = block
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
[ -z "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  */supabase/migrations/*.sql)
    # tools table: ON CONFLICT DO UPDATE must include 'type =' in SET clause
    # Omitting it leaves stale type values (e.g., CRUDTool instead of CreateTaskTool),
    # causing tool loading to silently fail until server restart.
    if grep -qiE 'ON\s+CONFLICT.*DO\s+UPDATE' "$FILE_PATH" 2>/dev/null; then
      if grep -qiE '\btools\b' "$FILE_PATH" 2>/dev/null; then
        SET_BLOCK=$(grep -A20 -iE 'ON\s+CONFLICT.*DO\s+UPDATE' "$FILE_PATH" | head -25)
        if ! echo "$SET_BLOCK" | grep -qiE '\btype\s*='; then
          echo "BLOCKED: ON CONFLICT DO UPDATE on 'tools' table is missing 'type =' in the SET clause. Omitting type leaves stale CRUDTool values that silently break tool loading. Add 'type = EXCLUDED.type' to the SET clause." >&2
          exit 2
        fi
      fi
    fi
    # A9: Block agent_name TEXT — must use agent_id UUID FK
    if grep -qiE 'agent_name\s+TEXT' "$FILE_PATH" 2>/dev/null; then
      echo "BLOCKED: 'agent_name TEXT' in migration. Per A9, use 'agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE'. See architecture-principles skill A9." >&2
      exit 2
    fi
    # A8: RLS enforcement — CREATE TABLE must have ENABLE ROW LEVEL SECURITY
    if grep -qiE 'CREATE\s+TABLE' "$FILE_PATH" 2>/dev/null; then
      TABLE_NAME=$(grep -oiP 'CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?\K\S+' "$FILE_PATH" | head -1)
      if [ -n "$TABLE_NAME" ] && ! grep -qiE "ENABLE\s+ROW\s+LEVEL\s+SECURITY" "$FILE_PATH" 2>/dev/null; then
        echo "BLOCKED: Table created without RLS. Per A8, every user-owned table must have 'ALTER TABLE ... ENABLE ROW LEVEL SECURITY'. See architecture-principles skill A8." >&2
        exit 2
      fi
    fi
    ;;
  */chatServer/routers/*.py)
    # A1: Block database operations in routers — must delegate to services
    if grep -qP '\.(select|insert|update|delete|upsert)\(' "$FILE_PATH" 2>/dev/null; then
      BAD=$(grep -nP '\.(select|insert|update|delete|upsert)\(' "$FILE_PATH")
      echo "BLOCKED: Database operations in router file. Per A1, routers delegate to services — no DB calls in routers. Move to chatServer/services/. See architecture-principles skill A1." >&2
      echo "$BAD" >&2
      exit 2
    fi
    ;;
  */webApp/src/api/hooks/*.ts|*/webApp/src/api/hooks/*.tsx)
    # A5: Block useAuthStore in API hooks — auth must come from supabase.auth.getSession()
    if grep -qP 'useAuthStore' "$FILE_PATH" 2>/dev/null; then
      echo "BLOCKED: 'useAuthStore' imported in API hooks. Per A5, auth tokens must come from supabase.auth.getSession(), not Zustand. See architecture-principles skill A5." >&2
      exit 2
    fi
    ;;
  */chatServer/tools/*.py)
    # A10: Tool name must follow verb_resource pattern
    if grep -qP 'name\s*=\s*"[^"]*"' "$FILE_PATH" 2>/dev/null; then
      NAMES=$(grep -oP 'name\s*=\s*"\K[^"]+' "$FILE_PATH" 2>/dev/null || true)
      for NAME in $NAMES; do
        if ! echo "$NAME" | grep -qP '^(create|list|get|update|delete|search|save|read|send|fetch)_'; then
          echo "BLOCKED: Tool name '$NAME' doesn't follow verb_resource pattern. Per A10, tool names must start with an approved verb (create, list, get, update, delete, search, save, read, send, fetch). See architecture-principles skill A10." >&2
          exit 2
        fi
      done
    fi
    ;;
  */chatServer/*.py|*/src/*.py|*/tests/*.py)
    # Gotcha #15: Block 'from chatServer.xxx' inside 'except ImportError'
    if grep -qP 'except ImportError' "$FILE_PATH" 2>/dev/null; then
      BAD=$(awk '/except ImportError/{found=1; count=0} found{count++; if(/from chatServer\./){print NR": "$0; found=0} if(count>5){found=0}}' "$FILE_PATH")
      if [ -n "$BAD" ]; then
        echo "BLOCKED: 'from chatServer.xxx' inside 'except ImportError'. Use bare module path. See CLAUDE.md gotcha #3." >&2
        echo "$BAD" >&2
        exit 2
      fi
    fi
    ;;
esac
exit 0
