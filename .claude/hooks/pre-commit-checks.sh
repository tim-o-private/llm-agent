#!/bin/bash
# Pre-commit validation hook for Claude Code
# Intercepts git commit commands and runs lint + .env checks

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""

# Detect if the command targets a worktree via `git -C <path>`
# Use that path for branch checks instead of PROJECT_DIR
GIT_DIR="$PROJECT_DIR"
if echo "$COMMAND" | grep -qoP 'git\s+-C\s+\S+'; then
  EXTRACTED_DIR=$(echo "$COMMAND" | grep -oP '(?<=git\s-C\s)\S+' | head -1)
  if [ -d "$EXTRACTED_DIR" ]; then
    GIT_DIR="$EXTRACTED_DIR"
  fi
fi

# Block destructive git operations
if echo "$COMMAND" | grep -qE 'git\s+push\s+(.*\s)?(-f(\s|$)|--force(\s|$))'; then
  echo "BLOCKED: git push --force is not allowed. Use regular push or ask the user." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
  echo "BLOCKED: git reset --hard is not allowed. This discards uncommitted work." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+checkout\s+\.'; then
  echo "BLOCKED: git checkout . discards all uncommitted changes." >&2
  exit 2
fi

# Block git checkout -- <file> (discard specific file changes)
# Matches: git checkout -- file, git checkout HEAD -- file, git checkout abc123 -- file
if echo "$COMMAND" | grep -qE 'git\s+checkout\s+(\S+\s+)?--(\s|$)'; then
  echo "BLOCKED: git checkout -- <file> discards uncommitted changes. Flag unrelated changes to your engineering lead instead of removing them." >&2
  exit 2
fi

# Block git restore (all forms except --staged, which only unstages)
if echo "$COMMAND" | grep -qE 'git\s+restore\s' && ! echo "$COMMAND" | grep -qP 'git\s+restore\s+--staged\b'; then
  echo "BLOCKED: git restore <file> discards uncommitted changes. Flag unrelated changes to your engineering lead instead of removing them." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+clean\s+-f'; then
  echo "BLOCKED: git clean -f deletes untracked files. Ask the user first." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+branch\s+-D\s+main'; then
  echo "BLOCKED: Deleting the main branch is not allowed." >&2
  exit 2
fi

# Block push to main branch
if echo "$COMMAND" | grep -qE 'git\s+push'; then
  CURRENT_BRANCH=$(git -C "$GIT_DIR" branch --show-current 2>/dev/null)
  if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "BLOCKED: Cannot push directly to ${CURRENT_BRANCH}. Create a feature branch and PR instead." >&2
    exit 2
  fi
fi

# Only run lint/env checks on git commit commands
if ! echo "$COMMAND" | grep -qE 'git\s+commit'; then
  exit 0
fi

# Check 1: No .env files in staging area
if git -C "$GIT_DIR" diff --cached --name-only 2>/dev/null | grep -qE '\.env'; then
  ERRORS="${ERRORS}BLOCKED: .env file detected in staging area. Remove with: git reset HEAD <file>\n"
fi

# Get list of staged files for targeted lint checks
STAGED_PY=$(git -C "$GIT_DIR" diff --cached --name-only --diff-filter=d 2>/dev/null | grep -E '\.py$' || true)
STAGED_TS=$(git -C "$GIT_DIR" diff --cached --name-only --diff-filter=d 2>/dev/null | grep -E '\.(ts|tsx)$' || true)

# Check 2: Python linting with ruff (only staged .py files)
if [ -n "$STAGED_PY" ]; then
  if command -v ruff &>/dev/null; then
    RUFF_OUTPUT=$(cd "$PROJECT_DIR" && echo "$STAGED_PY" | xargs ruff check 2>&1)
    if [ $? -ne 0 ]; then
      ERRORS="${ERRORS}BLOCKED: Ruff linting failed. Run: ruff check --fix src/ chatServer/ tests/\n${RUFF_OUTPUT}\n"
    fi
  else
    echo "WARNING: ruff not found — skipping Python lint check. Install with: pip install ruff" >&2
  fi
fi

# Check 3: ESLint (only staged .ts/.tsx files)
if [ -n "$STAGED_TS" ]; then
  if [ -f "$PROJECT_DIR/webApp/node_modules/.bin/eslint" ]; then
    # Filter to only webApp files and make paths relative to webApp/
    WEBAPP_FILES=$(echo "$STAGED_TS" | grep '^webApp/' | sed 's|^webApp/||' || true)
    if [ -n "$WEBAPP_FILES" ]; then
      ESLINT_OUTPUT=$(cd "$PROJECT_DIR/webApp" && echo "$WEBAPP_FILES" | xargs npx eslint --ext ts,tsx --report-unused-disable-directives --max-warnings 0 2>&1)
      if [ $? -ne 0 ]; then
        ERRORS="${ERRORS}BLOCKED: ESLint failed. Run: cd webApp && pnpm lint\n"
      fi
    fi
  else
    echo "WARNING: eslint not found — skipping TypeScript lint check. Run: cd webApp && pnpm install" >&2
  fi
fi

# If there were errors, block the commit
if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS" >&2
  exit 2
fi

exit 0
