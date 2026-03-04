#!/bin/bash
# Wait for chatServer to be healthy before proceeding.
# Usage: ./scripts/wait-for-server.sh [url] [max_retries] [retry_delay]

URL="${1:-http://localhost:3001/health}"
MAX_RETRIES="${2:-15}"
RETRY_DELAY="${3:-2}"

echo "Waiting for server at $URL ..."
curl --retry "$MAX_RETRIES" --retry-delay "$RETRY_DELAY" --retry-connrefused -sf "$URL" > /dev/null

if [ $? -eq 0 ]; then
  echo "Server is healthy."
else
  echo "Server failed to become healthy after $MAX_RETRIES retries." >&2
  exit 1
fi
