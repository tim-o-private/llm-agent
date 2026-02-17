#!/bin/bash
# Pre-commit validation hook for Claude Code
# Intercepts git commit commands and runs lint + .env checks

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only run checks on git commit commands
if ! echo "$COMMAND" | grep -qE 'git\s+commit'; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""

# Check 1: No .env files in staging area
if git -C "$PROJECT_DIR" diff --cached --name-only 2>/dev/null | grep -qE '\.env'; then
  ERRORS="${ERRORS}BLOCKED: .env file detected in staging area. Remove with: git reset HEAD <file>\n"
fi

# Check 2: Python linting with ruff
if command -v ruff &>/dev/null; then
  RUFF_OUTPUT=$(cd "$PROJECT_DIR" && ruff check src/ chatServer/ tests/ 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}BLOCKED: Ruff linting failed. Run: ruff check --fix src/ chatServer/ tests/\n${RUFF_OUTPUT}\n"
  fi
fi

# Check 3: ESLint
if [ -f "$PROJECT_DIR/webApp/node_modules/.bin/eslint" ]; then
  ESLINT_OUTPUT=$(cd "$PROJECT_DIR/webApp" && npx eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0 2>&1)
  if [ $? -ne 0 ]; then
    ERRORS="${ERRORS}BLOCKED: ESLint failed. Run: cd webApp && pnpm lint\n"
  fi
fi

# If there were errors, block the commit
if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS" >&2
  exit 2
fi

exit 0
