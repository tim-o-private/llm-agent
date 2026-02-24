#!/usr/bin/env bash
# PreToolUse hook: enforces agent scope boundaries on Write/Edit
# Exit 0 = allow, Exit 2 = block
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oP '"file_path"\s*:\s*"([^"]*)"' | head -1 | sed 's/.*"\([^"]*\)"/\1/' || true)
[ -z "$FILE_PATH" ] && exit 0

# Block orchestrator agents from modifying files entirely.
# Orchestrators plan and delegate — they do not write code.
# No branch-name fallback here (risk of false positives per SPEC-020 edge cases).
if [ "${CLAUDE_AGENT_TYPE:-}" = "orchestrator" ]; then
  NORM_PATH="$FILE_PATH"
  NORM_PATH="${NORM_PATH#./}"
  PROJECT_DIR_TMP="${CLAUDE_PROJECT_DIR:-}"
  if [ -n "$PROJECT_DIR_TMP" ]; then
    NORM_PATH="${NORM_PATH#$PROJECT_DIR_TMP/}"
  fi
  case "$NORM_PATH" in
    docs/*|.claude/*)
      exit 0
      ;;
    *)
      echo "BLOCKED: Orchestrator agents cannot modify files. Delegate to a domain agent instead." >&2
      exit 2
      ;;
  esac
fi

# Detect agent type from env var (set by orchestrator in spawn prompt)
AGENT_TYPE="${CLAUDE_AGENT_TYPE:-}"

# Fallback: try to detect from branch name — but ONLY inside a git worktree.
# In the main repo, this is the team lead (unrestricted). In a worktree, it's
# a domain agent. git rev-parse --git-dir returns ".git/worktrees/<name>" in
# worktrees vs ".git" in the main repo.
if [ -z "$AGENT_TYPE" ]; then
  GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || true)
  if [[ "$GIT_DIR" == *"/worktrees/"* ]]; then
    BRANCH=$(git branch --show-current 2>/dev/null || true)
    case "$BRANCH" in
      *database*|*migration*|*schema*) AGENT_TYPE="database-dev" ;;
      *backend*|*service*|*api*) AGENT_TYPE="backend-dev" ;;
      *frontend*|*webapp*|*ui*) AGENT_TYPE="frontend-dev" ;;
      *deploy*|*docker*|*ci*|*cd*) AGENT_TYPE="deployment-dev" ;;
    esac
  fi
fi

# No agent type detected — allow (manual/orchestrator use)
[ -z "$AGENT_TYPE" ] && exit 0

# Normalize file path: strip leading ./ or project dir prefix for matching
MATCH_PATH="$FILE_PATH"
MATCH_PATH="${MATCH_PATH#./}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -n "$PROJECT_DIR" ]; then
  MATCH_PATH="${MATCH_PATH#$PROJECT_DIR/}"
fi

# Scope rules
case "$AGENT_TYPE" in
  database-dev)
    case "$MATCH_PATH" in
      supabase/migrations/*) exit 0 ;;
      chatServer/database/*) exit 0 ;;
      tests/chatServer/database/*) exit 0 ;;
      *)
        echo "BLOCKED: database-dev scope violation. You can only modify: supabase/migrations/*, chatServer/database/*, tests/chatServer/database/*. Attempted: $MATCH_PATH" >&2
        exit 2
        ;;
    esac
    ;;
  backend-dev)
    case "$MATCH_PATH" in
      supabase/migrations/*)
        echo "BLOCKED: backend-dev cannot modify migrations (database-dev's scope). Attempted: $MATCH_PATH" >&2
        exit 2
        ;;
      chatServer/*|src/*|tests/*) exit 0 ;;
      *)
        echo "BLOCKED: backend-dev scope violation. You can only modify: chatServer/*, src/*, tests/* (not migrations). Attempted: $MATCH_PATH" >&2
        exit 2
        ;;
    esac
    ;;
  frontend-dev)
    case "$MATCH_PATH" in
      webApp/src/*) exit 0 ;;
      webApp/*.config.*) exit 0 ;;
      webApp/*.test.*) exit 0 ;;
      *)
        echo "BLOCKED: frontend-dev scope violation. You can only modify: webApp/src/*, webApp/*.config.*, webApp/*.test.*. Attempted: $MATCH_PATH" >&2
        exit 2
        ;;
    esac
    ;;
  deployment-dev)
    case "$MATCH_PATH" in
      *Dockerfile*) exit 0 ;;
      */fly.toml) exit 0 ;;
      .github/workflows/*) exit 0 ;;
      requirements.txt) exit 0 ;;
      *)
        echo "BLOCKED: deployment-dev scope violation. You can only modify: *Dockerfile*, */fly.toml, .github/workflows/*, requirements.txt. Attempted: $MATCH_PATH" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    # Unknown agent type — allow
    exit 0
    ;;
esac
