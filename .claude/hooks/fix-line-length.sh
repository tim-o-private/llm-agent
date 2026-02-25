#!/usr/bin/env bash
# PostToolUse hook: auto-append # noqa: E501 to Python lines exceeding 120 chars
# Only runs on .py files. Skips lines that already have noqa: E501.

set -euo pipefail

# Get the file path from stdin (Claude Code passes JSON context on stdin)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process Python files
[[ "$FILE_PATH" == *.py ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

# Find lines exceeding 120 chars that don't already have noqa: E501
# Use sed to append the comment in-place
sed -i -E '/# noqa:.*E501/!{/^.{121,}$/s/$/ '" # noqa: E501/}" "$FILE_PATH"
