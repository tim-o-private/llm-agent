#!/usr/bin/env bash
# PostToolUse hook: blocks known anti-patterns on Write/Edit
# Exit 0 = silent pass, Exit 2 = block
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
[ -z "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  */supabase/migrations/*.sql)
    if grep -qiE 'agent_name\s+TEXT' "$FILE_PATH" 2>/dev/null; then
      echo "BLOCKED: 'agent_name TEXT' in migration. Use 'agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE'. See CLAUDE.md gotcha #12." >&2
      exit 2
    fi
    ;;
  */chatServer/*.py|*/src/*.py|*/tests/*.py)
    if grep -qP 'except ImportError' "$FILE_PATH" 2>/dev/null; then
      BAD=$(awk '/except ImportError/{found=1; count=0} found{count++; if(/from chatServer\./){print NR": "$0; found=0} if(count>5){found=0}}' "$FILE_PATH")
      if [ -n "$BAD" ]; then
        echo "BLOCKED: 'from chatServer.xxx' inside 'except ImportError'. Use bare module path. See CLAUDE.md gotcha #15." >&2
        echo "$BAD" >&2
        exit 2
      fi
    fi
    ;;
esac
exit 0
