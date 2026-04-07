#!/usr/bin/env bash
# UAT script for ConversationHandler v2 (SPECs 033-040)
#
# Tests the new Anthropic Messages API tool-loop, feature flag routing,
# tool execution, message persistence, SSE streaming, and session_open.
#
# Prerequisites:
#   - pnpm dev running (chatServer on :3001)
#   - CONVERSATION_HANDLER_V2=true in .env
#   - SUPABASE_JWT_SECRET + CLARITY_DEV_USER_ID in .env (for token minting)
#
# Usage: ./scripts/uat-conversation-handler.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"
BASE_URL="${CLARITY_DEV_BASE_URL:-http://localhost:3001}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0

pass() { echo -e "  ${GREEN}PASS${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}FAIL${NC} $1"; ((FAIL++)); }
skip() { echo -e "  ${YELLOW}SKIP${NC} $1"; ((SKIP++)); }

# ------------------------------------------------------------------
# Auth: mint a fresh HS256 JWT (same approach as clarity_dev_server.py)
# ------------------------------------------------------------------
load_env_var() {
  local key="$1"
  grep -oP "^(export\s+)?${key}=['\"]?\K[^'\"]*" "${PROJECT_ROOT}/.env" 2>/dev/null || true
}

JWT_SECRET=$(load_env_var "SUPABASE_JWT_SECRET")
DEV_USER_ID=$(load_env_var "CLARITY_DEV_USER_ID")

if [ -z "$JWT_SECRET" ] || [ -z "$DEV_USER_ID" ]; then
  echo -e "${RED}Error: SUPABASE_JWT_SECRET and CLARITY_DEV_USER_ID must be set in .env${NC}" >&2
  exit 1
fi

BEARER_TOKEN=$("$VENV_PYTHON" -c "
import jwt, time
now = int(time.time())
token = jwt.encode(
    {'sub': '${DEV_USER_ID}', 'aud': 'authenticated', 'iat': now, 'exp': now + 3600},
    '${JWT_SECRET}', algorithm='HS256'
)
print(token)
" 2>/dev/null)

if [ -z "$BEARER_TOKEN" ]; then
  echo -e "${RED}Error: Failed to mint JWT. Check PyJWT is installed in .venv.${NC}" >&2
  exit 1
fi

AUTH_HEADER="Authorization: Bearer ${BEARER_TOKEN}"
CONTENT_TYPE="Content-Type: application/json"
SESSION_ID="uat-$(date +%s)-$(head -c 4 /dev/urandom | xxd -p)"
LLM_DELAY=8  # seconds between tests that hit the Anthropic API

# Helper: POST with auth
post() {
  local endpoint="$1"
  local payload="$2"
  curl -sf -X POST "${BASE_URL}/${endpoint}" \
    -H "$AUTH_HEADER" \
    -H "$CONTENT_TYPE" \
    -d "$payload" 2>/dev/null
}

echo "============================================"
echo " ConversationHandler v2 — UAT"
echo " $(date)"
echo " Server: ${BASE_URL}"
echo " Session: ${SESSION_ID}"
echo "============================================"
echo ""

# ------------------------------------------------------------------
# 1. Health check
# ------------------------------------------------------------------
echo "1. Server health"

HEALTH=$(curl -sf "${BASE_URL}/health" 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"status"'; then
  pass "GET /health returns status"
else
  fail "GET /health unreachable — is pnpm dev running?"
  echo -e "${RED}Cannot continue without server.${NC}"
  exit 1
fi

ROOT=$(curl -sf "${BASE_URL}/" 2>/dev/null || echo "FAIL")
if echo "$ROOT" | grep -qi 'clarity\|running'; then
  pass "GET / returns service info"
else
  fail "GET / unexpected response"
fi

echo ""

# ------------------------------------------------------------------
# 2. Feature flag verification
# ------------------------------------------------------------------
echo "2. Feature flag (CONVERSATION_HANDLER_V2)"

FLAG_VAL=$(load_env_var "CONVERSATION_HANDLER_V2")
if [ "$FLAG_VAL" = "true" ]; then
  pass "CONVERSATION_HANDLER_V2=true in .env"
else
  fail "CONVERSATION_HANDLER_V2 not set to true in .env (got: '${FLAG_VAL:-<empty>}')"
  echo -e "${YELLOW}  Tests will hit the OLD code path unless the server was started with the flag${NC}"
fi

echo ""

# ------------------------------------------------------------------
# 3. Auth check
# ------------------------------------------------------------------
echo "3. Auth"

AUTH_CODE=$(curl -so /dev/null -w "%{http_code}" -X GET "${BASE_URL}/api/notifications" \
  -H "$AUTH_HEADER" 2>/dev/null || echo "000")
if [ "$AUTH_CODE" = "200" ]; then
  pass "Minted JWT accepted (200 from authenticated endpoint)"
else
  fail "Minted JWT rejected (got $AUTH_CODE from /api/notifications)"
  echo -e "${RED}Auth is broken — remaining tests will fail.${NC}"
fi

NOAUTH_CODE=$(curl -so /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/chat" \
  -H "$CONTENT_TYPE" \
  -d '{"agent_name":"assistant","message":"test","session_id":"x"}' 2>/dev/null || echo "000")
if [ "$NOAUTH_CODE" = "401" ] || [ "$NOAUTH_CODE" = "403" ]; then
  pass "Missing auth correctly returns $NOAUTH_CODE"
else
  fail "Missing auth returned $NOAUTH_CODE (expected 401 or 403)"
fi

echo ""

# ------------------------------------------------------------------
# 4. Chat endpoint (non-streaming) — basic message
# ------------------------------------------------------------------
echo ""
echo "4. Chat endpoint — non-streaming (waiting ${LLM_DELAY}s for rate limit)..."
sleep "$LLM_DELAY"

CHAT_PAYLOAD=$(cat <<EOF
{
  "agent_name": "assistant",
  "message": "What is 2 + 2? Reply with just the number, nothing else.",
  "session_id": "${SESSION_ID}"
}
EOF
)

CHAT_RESP=$(post "api/chat" "$CHAT_PAYLOAD" || echo "HTTP_ERROR")

if [ "$CHAT_RESP" = "HTTP_ERROR" ]; then
  fail "POST /api/chat returned HTTP error"
else
  if echo "$CHAT_RESP" | "$VENV_PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert 'response' in d and 'session_id' in d" 2>/dev/null; then
    pass "Response has 'response' and 'session_id' fields"
  else
    fail "Response missing expected fields: $(echo "$CHAT_RESP" | head -c 200)"
  fi

  HAS_ERROR=$(echo "$CHAT_RESP" | "$VENV_PYTHON" -c "import sys,json; print(d.get('error','') if (d:=json.load(sys.stdin)) else '')" 2>/dev/null || echo "parse_fail")
  if [ -z "$HAS_ERROR" ] || [ "$HAS_ERROR" = "None" ]; then
    pass "No error in response"
  else
    fail "Response contains error: $HAS_ERROR"
  fi

  RESP_TEXT=$(echo "$CHAT_RESP" | "$VENV_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('response',''))" 2>/dev/null || echo "")
  if [ -n "$RESP_TEXT" ] && [ "$RESP_TEXT" != "None" ]; then
    pass "Agent returned text: $(echo "$RESP_TEXT" | head -c 80)"
  else
    fail "Agent returned empty response"
  fi
fi

echo ""

# ------------------------------------------------------------------
# 5. Tool execution
# ------------------------------------------------------------------
echo "5. Tool execution (waiting ${LLM_DELAY}s)..."
sleep "$LLM_DELAY"

TOOL_SESSION="uat-tool-$(date +%s)-$(head -c 4 /dev/urandom | xxd -p)"
TOOL_PAYLOAD=$(cat <<EOF
{
  "agent_name": "assistant",
  "message": "What's on my calendar today? Use search_calendar to check.",
  "session_id": "${TOOL_SESSION}"
}
EOF
)

TOOL_RESP=$(post "api/chat" "$TOOL_PAYLOAD" || echo "HTTP_ERROR")

if [ "$TOOL_RESP" = "HTTP_ERROR" ]; then
  fail "POST /api/chat (tool test) returned HTTP error"
else
  TOOL_TEXT=$(echo "$TOOL_RESP" | "$VENV_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('response',''))" 2>/dev/null || echo "")
  if [ -n "$TOOL_TEXT" ] && [ "$TOOL_TEXT" != "None" ]; then
    pass "Tool-calling message returned response: $(echo "$TOOL_TEXT" | head -c 100)..."
  else
    TOOL_ERR=$(echo "$TOOL_RESP" | "$VENV_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null || echo "unknown")
    fail "Tool-calling message returned empty response (error: $TOOL_ERR)"
  fi
fi

echo ""

# ------------------------------------------------------------------
# 6. SSE streaming
# ------------------------------------------------------------------
echo "6. SSE streaming (waiting ${LLM_DELAY}s)..."
sleep "$LLM_DELAY"

STREAM_SESSION="uat-stream-$(date +%s)-$(head -c 4 /dev/urandom | xxd -p)"
STREAM_PAYLOAD=$(cat <<EOF
{
  "agent_name": "assistant",
  "message": "Say hello in exactly 3 words.",
  "session_id": "${STREAM_SESSION}"
}
EOF
)

STREAM_RESP=$(curl -sf -N -X POST "${BASE_URL}/api/chat" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -H "Accept: text/event-stream" \
  -d "$STREAM_PAYLOAD" \
  --max-time 30 2>/dev/null | head -30 || echo "STREAM_ERROR")

if [ "$STREAM_RESP" = "STREAM_ERROR" ] || [ -z "$STREAM_RESP" ]; then
  fail "SSE streaming request failed or empty"
elif echo "$STREAM_RESP" | grep -q "^data:"; then
  pass "SSE stream returns data: events"
  if echo "$STREAM_RESP" | grep -q "text_delta\|content_block_delta\|message_complete"; then
    pass "SSE stream contains expected event types"
  else
    skip "SSE event types not detected in first 30 lines"
  fi
else
  if echo "$STREAM_RESP" | "$VENV_PYTHON" -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    fail "Got JSON instead of SSE — streaming path not active"
  else
    fail "Unexpected streaming response: $(echo "$STREAM_RESP" | head -c 120)"
  fi
fi

echo ""

# ------------------------------------------------------------------
# 7. Session open (wakeup)
# ------------------------------------------------------------------
echo "7. Session open (waiting ${LLM_DELAY}s)..."
sleep "$LLM_DELAY"

SO_SESSION="uat-so-$(date +%s)-$(head -c 4 /dev/urandom | xxd -p)"
SO_PAYLOAD=$(cat <<EOF
{
  "session_id": "${SO_SESSION}",
  "agent_name": "assistant"
}
EOF
)

SO_RESP=$(post "api/chat/session_open" "$SO_PAYLOAD" || echo "HTTP_ERROR")

if [ "$SO_RESP" = "HTTP_ERROR" ]; then
  fail "POST /api/session_open returned HTTP error"
else
  if echo "$SO_RESP" | "$VENV_PYTHON" -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    pass "Session open returned valid JSON"
  else
    fail "Session open returned non-JSON: $(echo "$SO_RESP" | head -c 120)"
  fi
fi

echo ""

# ------------------------------------------------------------------
# 8. Message history persistence (multi-turn)
# ------------------------------------------------------------------
echo "8. Message persistence (waiting ${LLM_DELAY}s)..."
sleep "$LLM_DELAY"

MT_SESSION="uat-mt-$(date +%s)-$(head -c 4 /dev/urandom | xxd -p)"

MT1_PAYLOAD=$(cat <<EOF
{
  "agent_name": "assistant",
  "message": "Remember: the secret word is 'pineapple'. Just acknowledge with 'noted'.",
  "session_id": "${MT_SESSION}"
}
EOF
)
MT1_RESP=$(post "api/chat" "$MT1_PAYLOAD" || echo "HTTP_ERROR")

if [ "$MT1_RESP" = "HTTP_ERROR" ]; then
  fail "Multi-turn: Turn 1 failed"
else
  pass "Multi-turn: Turn 1 succeeded"
  sleep "$LLM_DELAY"

  MT2_PAYLOAD=$(cat <<EOF
{
  "agent_name": "assistant",
  "message": "What was the secret word I just told you?",
  "session_id": "${MT_SESSION}"
}
EOF
)
  MT2_RESP=$(post "api/chat" "$MT2_PAYLOAD" || echo "HTTP_ERROR")

  if [ "$MT2_RESP" = "HTTP_ERROR" ]; then
    fail "Multi-turn: Turn 2 failed"
  else
    MT2_TEXT=$(echo "$MT2_RESP" | "$VENV_PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('response','').lower())" 2>/dev/null || echo "")
    if echo "$MT2_TEXT" | grep -qi "pineapple"; then
      pass "Multi-turn: Agent recalled 'pineapple' — history persistence works"
    else
      fail "Multi-turn: Agent did not recall 'pineapple' — response: $(echo "$MT2_TEXT" | head -c 100)"
    fi
  fi
fi

echo ""

# ------------------------------------------------------------------
# 9. Error handling
# ------------------------------------------------------------------
echo "9. Error handling"

BAD_PAYLOAD='{"agent_name":"assistant","message":"test"}'
BAD_RESP_CODE=$(curl -so /dev/null -w "%{http_code}" -X POST "${BASE_URL}/api/chat" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d "$BAD_PAYLOAD" 2>/dev/null || echo "000")

if [ "$BAD_RESP_CODE" = "422" ]; then
  pass "Missing session_id returns 422 (validation error)"
elif [ "$BAD_RESP_CODE" = "400" ]; then
  pass "Missing session_id returns 400 (bad request)"
else
  fail "Missing session_id returned $BAD_RESP_CODE (expected 422 or 400)"
fi

echo ""

# ------------------------------------------------------------------
# 10. Module imports
# ------------------------------------------------------------------
echo "10. Module imports (new components)"

IMPORT_CHECK=$(cd "$PROJECT_ROOT" && "$VENV_PYTHON" -c "
import sys
results = []

checks = [
    ('conversation_handler', 'chatServer.services.conversation_handler', ['ConversationHandler', 'ConversationResult']),
    ('builder', 'chatServer.services.conversation_handler_builder', ['build_conversation_handler']),
    ('bridge', 'chatServer.services.langchain_tool_bridge', ['LangChainToolBridge']),
    ('history_adapter', 'chatServer.services.message_history_adapter', ['MessageHistoryAdapter']),
    ('sse_stream', 'chatServer.services.sse_stream', ['_format_sse']),
    ('config_service', 'chatServer.services.config_service', ['ConfigService']),
    ('template_parser', 'chatServer.workflows.template_parser', ['parse_template']),
    ('graph_builder', 'chatServer.workflows.builder', ['GraphBuilder']),
    ('engine', 'chatServer.workflows.engine', ['AnthropicEngine']),
    ('run_manager', 'chatServer.workflows.run_manager', ['WorkflowRunManager']),
    ('dispatch', 'chatServer.workflows.dispatch', ['dispatch_workflow']),
    ('bwrap', 'chatServer.sandbox.bwrap', ['BwrapSandbox']),
    ('provisioner', 'chatServer.sandbox.provisioner', ['SandboxProvisioner']),
    ('security_boundary', 'chatServer.sandbox.security_boundary', ['SecurityBoundary']),
    ('git_tracker', 'chatServer.sandbox.git_tracker', ['GitTracker']),
    ('self_improvement', 'chatServer.sandbox.self_improvement', ['SelfImprovementService']),
]

for label, module, names in checks:
    try:
        mod = __import__(module, fromlist=names)
        for name in names:
            getattr(mod, name)
        results.append(f'OK:{label}')
    except Exception as e:
        results.append(f'FAIL:{label}:{e}')

print('|'.join(results))
" 2>&1)

IMPORT_OK=0
IMPORT_FAIL=0
IFS='|' read -ra ITEMS <<< "$IMPORT_CHECK"
for item in "${ITEMS[@]}"; do
  if [[ "$item" == OK:* ]]; then
    ((IMPORT_OK++))
  elif [[ "$item" == FAIL:* ]]; then
    label=$(echo "$item" | cut -d: -f2)
    err=$(echo "$item" | cut -d: -f3-)
    fail "Import $label: $err"
    ((IMPORT_FAIL++))
  fi
done
if [ "$IMPORT_FAIL" -eq 0 ]; then
  pass "All ${IMPORT_OK} new modules import cleanly"
fi

echo ""

# ------------------------------------------------------------------
# 11. Regression — existing endpoints
# ------------------------------------------------------------------
echo "11. Regression — existing endpoints"

for endpoint in "api/notifications" "api/actions/pending" "api/tasks"; do
  CODE=$(curl -so /dev/null -w "%{http_code}" -X GET "${BASE_URL}/${endpoint}" \
    -H "$AUTH_HEADER" 2>/dev/null || echo "000")
  if [ "$CODE" = "200" ]; then
    pass "GET /${endpoint} returns 200"
  else
    fail "GET /${endpoint} returned $CODE"
  fi
done

echo ""

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
TOTAL=$((PASS + FAIL + SKIP))
echo "============================================"
echo -e " Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${SKIP} skipped${NC} (${TOTAL} total)"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
