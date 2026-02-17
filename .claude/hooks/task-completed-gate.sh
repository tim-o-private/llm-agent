#!/bin/bash
# TaskCompleted quality gate — blocks task completion without proper checks
#
# Verifies:
# 1. Agent is NOT on the main branch
# 2. No uncommitted changes remain

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""

# Check 1: Not on main branch
CURRENT_BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  ERRORS="${ERRORS}BLOCKED: You are on the '${CURRENT_BRANCH}' branch. Tasks should be completed on feature branches.\n"
fi

# Check 2: No uncommitted changes
UNCOMMITTED=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null)
if [ -n "$UNCOMMITTED" ]; then
  ERRORS="${ERRORS}WARNING: Uncommitted changes detected. Commit your work before completing the task.\n"
fi

# If there were errors, report to stderr and block
if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS" >&2
  exit 2
fi

# No blockers — provide context reminder
jq -n '{"additionalContext": "Task completion verified: on feature branch, no uncommitted changes. Ensure pytest and pnpm test both pass before marking complete."}'
