#!/usr/bin/env bash
# Usage: curlpost <endpoint> [json-payload]
# Example: curlpost api/notifications/debug/create '{"title":"Test","body":"Hello"}'
#
# Requires CLARITY_DEV_BEARER_TOKEN in .env or environment.
set -euo pipefail

ENDPOINT="${1:?Usage: curlpost <endpoint> [json-payload]}"
PAYLOAD="${2:-{}}"
BASE_URL="${CLARITY_DEV_BASE_URL:-http://localhost:3001}"

# Load token from environment or .env
if [ -z "${CLARITY_DEV_BEARER_TOKEN:-}" ]; then
  ENV_FILE="$(dirname "$0")/../.env"
  if [ -f "$ENV_FILE" ]; then
    CLARITY_DEV_BEARER_TOKEN=$(grep -oP '^CLARITY_DEV_BEARER_TOKEN=\K.*' "$ENV_FILE" || true)
  fi
fi

if [ -z "${CLARITY_DEV_BEARER_TOKEN:-}" ]; then
  echo "Error: CLARITY_DEV_BEARER_TOKEN not set in environment or .env" >&2
  exit 1
fi

# Strip leading slash if present
ENDPOINT="${ENDPOINT#/}"

curl -s -X POST "${BASE_URL}/${ENDPOINT}" \
  -H "Authorization: Bearer ${CLARITY_DEV_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" | python3 -m json.tool 2>/dev/null || cat
