#!/bin/bash
# TaskCompleted quality gate — blocks task completion without proper checks
#
# Verifies:
# 1. Agent is NOT on the main branch
# 2. No uncommitted changes remain

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""

# Detect worktree: if CWD is inside a worktree, use CWD for git checks
GIT_DIR="$PROJECT_DIR"
CURRENT_CWD=$(pwd 2>/dev/null)
if [ -n "$CURRENT_CWD" ] && git -C "$CURRENT_CWD" rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
  GIT_DIR="$CURRENT_CWD"
fi

# Check 1: Not on main branch (skip if worktrees with feature branches exist)
# In a team context, the team lead stays on main while agents work in worktrees.
# If any worktree is on a feature branch, allow task completion from main.
CURRENT_BRANCH=$(git -C "$GIT_DIR" branch --show-current 2>/dev/null)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  # Check if any worktrees are on feature branches
  WORKTREE_BRANCHES=$(git -C "$GIT_DIR" worktree list --porcelain 2>/dev/null | grep '^branch ' | grep -v 'refs/heads/main$' | grep -v 'refs/heads/master$' || true)
  if [ -z "$WORKTREE_BRANCHES" ]; then
    ERRORS="${ERRORS}BLOCKED: You are on the '${CURRENT_BRANCH}' branch with no active feature worktrees. Tasks should be completed on feature branches.\n"
  fi
fi

# Check 2: No uncommitted changes
# In team context (worktrees active), uncommitted changes on main are expected
# (team lead has spec drafts, hook edits, etc.) — warn but don't block.
UNCOMMITTED=$(git -C "$GIT_DIR" status --porcelain 2>/dev/null)
if [ -n "$UNCOMMITTED" ]; then
  if [ -n "$WORKTREE_BRANCHES" ]; then
    # Team context — warn only, don't block
    echo "NOTE: Uncommitted changes in main repo (expected in team context)." >&2
  else
    ERRORS="${ERRORS}WARNING: Uncommitted changes detected. Commit your work before completing the task.\n"
  fi
fi

# If there were errors, report to stderr and block
if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS" >&2
  exit 2
fi

# No blockers — provide context reminder
jq -n '{"additionalContext": "Task completion verified: on feature branch, no uncommitted changes. Ensure pytest and pnpm test both pass before marking complete."}'
