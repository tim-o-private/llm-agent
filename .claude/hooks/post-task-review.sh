#!/bin/bash
# Post-task review reminder — fires when Claude stops responding

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CURRENT_BRANCH=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null)
UNCOMMITTED=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | head -5)

CONTEXT="Before ending: verify your changes match the original plan/spec. If tests exist for modified code, confirm they pass. If this task is complete, commit the changes."

if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  CONTEXT="${CONTEXT} WARNING: You are on the ${CURRENT_BRANCH} branch. If you made changes, they should be on a feature branch."
fi

if [ -n "$UNCOMMITTED" ]; then
  CONTEXT="${CONTEXT} NOTE: There are uncommitted changes. Review and commit before ending."
fi

jq -n --arg ctx "$CONTEXT" '{"additionalContext": $ctx}'
