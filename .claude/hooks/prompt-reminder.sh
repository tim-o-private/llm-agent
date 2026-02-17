#!/bin/bash
# Reminds Claude to check CLAUDE.md before proceeding

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
  jq -n '{
    "additionalContext": "Before proceeding: consult CLAUDE.md for project conventions, key patterns, and known gotchas. Plans must be documented before execution. Commits should be made after each completed task. If working on a spec, read docs/sdlc/specs/SPEC-NNN.md and stay within scope."
  }'
else
  exit 0
fi
