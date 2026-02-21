#!/usr/bin/env bash
# PostToolUse hook: auto-append # noqa: E501 to Python lines exceeding 120 chars
# Only runs on .py files. Skips lines that already have noqa: E501.

set -euo pipefail

# Get the file path from the tool input
FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // empty')

# Only process Python files
[[ "$FILE_PATH" == *.py ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

# Find lines exceeding 120 chars that don't already have noqa: E501
# Use sed to append the comment in-place
sed -i -E '/# noqa:.*E501/!{/^.{121,}$/s/$/ '" # noqa: E501/}" "$FILE_PATH"
