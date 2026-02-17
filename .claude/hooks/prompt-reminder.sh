#!/bin/bash
# Reminds Claude to check CLAUDE.md before proceeding

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
  jq -n '{
    "additionalContext": "Before proceeding: consult CLAUDE.md for project conventions, key patterns, and known gotchas. Plans must be documented before execution. Commits should be made after each completed task."
  }'
else
  exit 0
fi
