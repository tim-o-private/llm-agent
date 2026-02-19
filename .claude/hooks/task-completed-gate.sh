#!/bin/bash
# TaskCompleted quality gate — blocks task completion without proper checks
#
# Verifies:
# 1. Agent is NOT on the main branch (unless worktrees active)
# 2. No uncommitted changes remain
# 3. Pytest runs on changed Python files (not just collection)
# 4. Vitest runs if webApp/ files changed
# 5. Ruff check on changed Python files
# 6. pnpm lint if frontend files changed
# 7. New service/hook files have corresponding test files
# 8. Advisory pattern checklist (once per task, not per write)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""

# Detect worktree: if CWD is inside a worktree, use CWD for git checks
GIT_DIR="$PROJECT_DIR"
CURRENT_CWD=$(pwd 2>/dev/null)
if [ -n "$CURRENT_CWD" ] && git -C "$CURRENT_CWD" rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
  GIT_DIR="$CURRENT_CWD"
fi

# Get changed files relative to main
CHANGED_FILES=$(git -C "$GIT_DIR" diff --name-only main 2>/dev/null || true)

# ============================================================
# Check 1: Not on main branch (skip if worktrees with feature branches exist)
# ============================================================
CURRENT_BRANCH=$(git -C "$GIT_DIR" branch --show-current 2>/dev/null)
WORKTREE_BRANCHES=""
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  WORKTREE_BRANCHES=$(git -C "$GIT_DIR" worktree list --porcelain 2>/dev/null | grep '^branch ' | grep -v 'refs/heads/main$' | grep -v 'refs/heads/master$' || true)
  if [ -z "$WORKTREE_BRANCHES" ]; then
    ERRORS="${ERRORS}BLOCKED: You are on the '${CURRENT_BRANCH}' branch with no active feature worktrees. Tasks should be completed on feature branches.\n"
  fi
fi

# ============================================================
# Check 2: No uncommitted changes
# ============================================================
UNCOMMITTED=$(git -C "$GIT_DIR" status --porcelain 2>/dev/null)
if [ -n "$UNCOMMITTED" ]; then
  if [ -n "$WORKTREE_BRANCHES" ]; then
    echo "NOTE: Uncommitted changes in main repo (expected in team context)." >&2
  else
    ERRORS="${ERRORS}WARNING: Uncommitted changes detected. Commit your work before completing the task.\n"
  fi
fi

# ============================================================
# Check 3: Run pytest on changed directories (not just collection)
# ============================================================
PYTHON_CHANGED=$(echo "$CHANGED_FILES" | grep -E '\.(py)$' || true)
if [ -n "$PYTHON_CHANGED" ]; then
  PYTEST_CMD="pytest"
  if [ -f "$GIT_DIR/.venv/bin/pytest" ]; then
    PYTEST_CMD="$GIT_DIR/.venv/bin/pytest"
  elif ! command -v pytest &>/dev/null; then
    PYTEST_CMD=""
  fi

  if [ -n "$PYTEST_CMD" ]; then
    # Determine test directories from changed files
    TEST_DIRS=$(echo "$PYTHON_CHANGED" | grep -oP '^[^/]+' | sort -u | tr '\n' ' ')
    PYTEST_OUTPUT=$(timeout 120 $PYTEST_CMD -x -q --tb=short --rootdir="$GIT_DIR" 2>&1) || {
      PYTEST_EXIT=$?
      if [ $PYTEST_EXIT -eq 5 ]; then
        # Exit code 5 = no tests collected — OK
        :
      elif [ $PYTEST_EXIT -eq 124 ]; then
        ERRORS="${ERRORS}BLOCKED: pytest timed out after 120s. Fix slow tests or reduce scope.\n"
      else
        # Truncate output to last 40 lines for readability
        TRUNCATED=$(echo "$PYTEST_OUTPUT" | tail -40)
        ERRORS="${ERRORS}BLOCKED: pytest failed (exit $PYTEST_EXIT). Fix failing tests before completing.\n${TRUNCATED}\n"
      fi
    }
  fi
fi

# ============================================================
# Check 4: Run vitest if webApp/ files changed
# ============================================================
WEBAPP_CHANGED=$(echo "$CHANGED_FILES" | grep -E '^webApp/' || true)
if [ -n "$WEBAPP_CHANGED" ]; then
  if [ -f "$GIT_DIR/webApp/package.json" ]; then
    VITEST_OUTPUT=$(cd "$GIT_DIR/webApp" && timeout 120 npx vitest --run 2>&1) || {
      VITEST_EXIT=$?
      if [ $VITEST_EXIT -eq 124 ]; then
        ERRORS="${ERRORS}BLOCKED: vitest timed out after 120s.\n"
      else
        TRUNCATED=$(echo "$VITEST_OUTPUT" | tail -40)
        ERRORS="${ERRORS}BLOCKED: vitest failed (exit $VITEST_EXIT). Fix failing tests before completing.\n${TRUNCATED}\n"
      fi
    }
  fi
fi

# ============================================================
# Check 5: Ruff check on changed Python files
# ============================================================
if [ -n "$PYTHON_CHANGED" ]; then
  RUFF_CMD="ruff"
  if [ -f "$GIT_DIR/.venv/bin/ruff" ]; then
    RUFF_CMD="$GIT_DIR/.venv/bin/ruff"
  elif ! command -v ruff &>/dev/null; then
    RUFF_CMD=""
  fi

  if [ -n "$RUFF_CMD" ]; then
    # Pass only changed Python files that still exist
    EXISTING_PY_FILES=""
    while IFS= read -r f; do
      [ -f "$GIT_DIR/$f" ] && EXISTING_PY_FILES="$EXISTING_PY_FILES $GIT_DIR/$f"
    done <<< "$PYTHON_CHANGED"

    if [ -n "$EXISTING_PY_FILES" ]; then
      RUFF_OUTPUT=$($RUFF_CMD check $EXISTING_PY_FILES 2>&1) || {
        TRUNCATED=$(echo "$RUFF_OUTPUT" | tail -20)
        ERRORS="${ERRORS}BLOCKED: ruff check failed. Fix lint errors before completing.\n${TRUNCATED}\n"
      }
    fi
  fi
fi

# ============================================================
# Check 6: pnpm lint if frontend files changed
# ============================================================
if [ -n "$WEBAPP_CHANGED" ]; then
  if [ -f "$GIT_DIR/webApp/package.json" ] && command -v pnpm &>/dev/null; then
    LINT_OUTPUT=$(cd "$GIT_DIR/webApp" && timeout 120 pnpm lint 2>&1) || {
      LINT_EXIT=$?
      if [ $LINT_EXIT -eq 124 ]; then
        ERRORS="${ERRORS}BLOCKED: pnpm lint timed out after 120s.\n"
      else
        TRUNCATED=$(echo "$LINT_OUTPUT" | tail -20)
        ERRORS="${ERRORS}BLOCKED: pnpm lint failed. Fix lint errors before completing.\n${TRUNCATED}\n"
      fi
    }
  fi
fi

# ============================================================
# Check 7: New service files must have corresponding test files
# ============================================================
for SVC_FILE in $(git -C "$GIT_DIR" diff --name-only --diff-filter=A HEAD~1 2>/dev/null | grep -E '^chatServer/services/[^/]+\.py$' || true); do
  BASENAME=$(basename "$SVC_FILE" .py)
  if [ "$BASENAME" != "__init__" ]; then
    TEST_FILE="tests/chatServer/services/test_${BASENAME}.py"
    if [ ! -f "$GIT_DIR/$TEST_FILE" ]; then
      ERRORS="${ERRORS}BLOCKED: New service file '$SVC_FILE' has no corresponding test file '$TEST_FILE'.\n"
    fi
  fi
done

# Check 7b: New hook files must have corresponding test files
for HOOK_FILE in $(git -C "$GIT_DIR" diff --name-only --diff-filter=A HEAD~1 2>/dev/null | grep -E '^webApp/src/api/hooks/use.*\.ts$' | grep -v '\.test\.' || true); do
  TEST_FILE="${HOOK_FILE%.ts}.test.ts"
  ALT_TEST_FILE="${HOOK_FILE%.ts}.test.tsx"
  if [ ! -f "$GIT_DIR/$TEST_FILE" ] && [ ! -f "$GIT_DIR/$ALT_TEST_FILE" ]; then
    ERRORS="${ERRORS}BLOCKED: New hook file '$HOOK_FILE' has no corresponding test file.\n"
  fi
done

# ============================================================
# If there were errors, report to stderr and block
# ============================================================
if [ -n "$ERRORS" ]; then
  echo -e "$ERRORS" >&2
  exit 2
fi

# ============================================================
# Advisory pattern checklist (fires once per task completion)
# ============================================================
ADVISORY=""

# Detect changed file types and provide relevant reminders
if echo "$CHANGED_FILES" | grep -qE '^chatServer/tools/'; then
  ADVISORY="${ADVISORY}\n- Tool files changed: verify verb_resource naming, approved verbs, Depends() injection, business logic in services not routers"
fi

if echo "$CHANGED_FILES" | grep -qE '^(chatServer|src)/.*\.py$'; then
  ADVISORY="${ADVISORY}\n- Python backend files changed: verify Depends(get_supabase_client), service layer pattern, Pydantic models, RLS scoping, content block normalization"
fi

if echo "$CHANGED_FILES" | grep -qE '^supabase/migrations/'; then
  ADVISORY="${ADVISORY}\n- Migration files changed: verify RLS enabled, UUID PKs, timestamps, indexes, comments, agent_id UUID FK (not agent_name TEXT)"
fi

if echo "$CHANGED_FILES" | grep -qE '^webApp/src/'; then
  ADVISORY="${ADVISORY}\n- Frontend files changed: verify semantic color tokens, auth from getSession(), React Query hooks with enabled guard, ARIA labels"
fi

if echo "$CHANGED_FILES" | grep -qE '(Dockerfile|fly\.toml|\.github/workflows)'; then
  ADVISORY="${ADVISORY}\n- Deployment files changed: verify no secrets in config, CORS origins, .dockerignore, Fly secrets for new env vars"
fi

if [ -n "$ADVISORY" ]; then
  CONTEXT="Task completion verified. Pattern checklist for changed files:${ADVISORY}"
else
  CONTEXT="Task completion verified: on feature branch, no uncommitted changes, all tests and lint pass."
fi

ESCAPED_CONTEXT=$(echo "$CONTEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
echo "{\"additionalContext\": ${ESCAPED_CONTEXT}}"
