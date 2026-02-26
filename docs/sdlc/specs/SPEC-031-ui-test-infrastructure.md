# SPEC-031: UI Test Infrastructure

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-26
> **Updated:** 2026-02-26

## Goal

Give agents the ability to autonomously write and run deterministic UI tests. Today, Playwright tests depend on the dev user's OAuth credentials and whatever data happens to be in the database. There's no way to set up "a new user" or "a user with a pending approval" programmatically. This spec creates three things: ephemeral test users via Supabase Admin API, a composable state seeder for test scenarios, and pytest-integrated Playwright fixtures that tie them together.

The outcome: UX designer writes a Playwright test that declares "I need a user with a pending approval," the fixture creates the user, seeds the data, runs the test, and tears everything down. Fully deterministic, fully autonomous, runnable in CI.

## Acceptance Criteria

- [ ] **AC-01:** A `TestUserManager` class can create an ephemeral Supabase Auth user with email/password, return a valid session (access_token, refresh_token), and hard-delete the user on cleanup. [A8]
- [ ] **AC-02:** A `TestStateManager` class can seed named scenarios into remote Supabase for a given user_id. At minimum: `empty` (wipe all user data), `chat_history` (N chat sessions with messages), `pending_approval` (pending_action + approval notification), `unread_notifications` (mix of read/unread). [A8]
- [ ] **AC-03:** `TestStateManager.reset(user_id)` deletes all application data for a user across all user-scoped tables (same tables as `wipe_dev_user.py`), but does NOT delete the Auth user. [A8]
- [ ] **AC-04:** Playwright tests are pytest-integrated — runnable via `pytest tests/uat/playwright/ -m playwright` with proper fixtures, not standalone scripts with `sys.exit()`. [A4]
- [ ] **AC-05:** A `test_user` pytest fixture creates an ephemeral user before the test, yields session info (user_id, tokens, email), and deletes the user after the test — including on test failure. [A8]
- [ ] **AC-06:** A `seeded_page` pytest fixture accepts a scenario name, creates an ephemeral user, seeds the scenario, launches an authenticated Playwright page, and tears everything down after. [A8]
- [ ] **AC-07:** The existing `conftest_pw.py` auth helpers (`get_authenticated_page`, `screenshot`, `CheckRunner`) are preserved and work with both the old dev-user flow and the new ephemeral-user fixtures. [S5]
- [ ] **AC-08:** At least one example Playwright test using the new fixtures passes end-to-end — demonstrating the full lifecycle (create user → seed state → authenticate → verify UI → cleanup). [A4]
- [ ] **AC-09:** The `TestStateManager` is importable and usable from non-Playwright contexts (e.g., `chat_with_clarity()` testing, manual scripts). [A8]
- [ ] **AC-10:** UX designer agent instructions are updated to specify scenario fixtures when writing Playwright tests. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `tests/uat/playwright/test_user_manager.py` | `TestUserManager` — creates/deletes ephemeral Supabase Auth users |
| `tests/uat/playwright/test_state_manager.py` | `TestStateManager` — seeds named scenarios into remote Supabase |
| `tests/uat/playwright/conftest.py` | pytest fixtures: `test_user`, `seeded_page`, `playwright_instance` |
| `tests/uat/playwright/scenarios/` | Scenario definitions (data factories for each named scenario) |
| `tests/uat/playwright/scenarios/__init__.py` | Scenario registry |
| `tests/uat/playwright/scenarios/empty.py` | `empty` scenario — just wipe |
| `tests/uat/playwright/scenarios/pending_approval.py` | `pending_approval` — pending_action + notification rows |
| `tests/uat/playwright/scenarios/chat_history.py` | `chat_history` — N sessions with messages |
| `tests/uat/playwright/scenarios/unread_notifications.py` | `unread_notifications` — mix of read/unread |
| `tests/uat/playwright/test_spec_031_smoke.py` | Example smoke test proving the full lifecycle |

### Files to Modify

| File | Change |
|------|--------|
| `tests/uat/playwright/conftest_pw.py` | Add `inject_session(page, session_dict)` helper extracted from inline JS. Keep existing functions. |
| `.claude/agents/ux-designer.md` | Update Playwright workflow to reference scenario fixtures |
| `.claude/skills/sdlc-workflow/SKILL.md` | Add testing tier reference (state-seeded Playwright vs manual UAT) |

### Out of Scope

- CI pipeline integration for Playwright (needs `pnpm dev` running — separate concern)
- Migrating existing `playwright_spec025_approval.py` to the new fixture system (can be done later)
- Frontend component changes
- Backend API changes
- Mocking the LLM/agent responses — Playwright tests hit the real running agent
- Memory server test user isolation (min-memory doesn't have per-user test data concerns yet)

## Technical Approach

### 1. TestUserManager (Supabase Admin API)

Uses `supabase-py` admin client with `SUPABASE_SERVICE_ROLE_KEY`:

```python
class TestUserManager:
    async def create(self, email_prefix: str = "uat") -> TestUser:
        """Create ephemeral user. Returns TestUser with id, email, password, session."""
        # email: uat-{uuid8}@playwright.local
        # password: random UUID
        # admin.create_user(email_confirm=True) — skips email verification
        # sign_in_with_password via anon key — gets ES256 JWT

    async def delete(self, user_id: str) -> None:
        """Hard-delete user from auth.users. App table data cleaned by TestStateManager."""
        # admin.delete_user(user_id, should_soft_delete=False)
```

Key decisions:
- Use **anon key** for sign-in (produces correct `role: authenticated` JWT for RLS)
- Use **service_role key** for create/delete (admin operations)
- `email_confirm=True` is mandatory — without it, sign-in fails with "Email not confirmed"
- Emails use `@playwright.local` domain — clearly not real, easy to filter if needed

### 2. TestStateManager (Scenario Seeding)

Uses `supabase-py` with service_role key to bypass RLS for data setup:

```python
class TestStateManager:
    async def reset(self, user_id: str) -> None:
        """Delete all app data for user_id. Same table list as wipe_dev_user.py."""

    async def seed(self, user_id: str, scenario: str, **kwargs) -> dict:
        """Seed a named scenario. Returns dict of created row IDs."""
        # Looks up scenario in registry, calls its seed function
```

Each scenario is a module in `scenarios/` with a `seed(client, user_id, **kwargs)` function:

```python
# scenarios/pending_approval.py
async def seed(client, user_id: str, **kwargs) -> dict:
    """Creates a pending_action + linked approval notification."""
    action_id = str(uuid.uuid4())
    # Insert into pending_actions
    # Insert into notifications with requires_approval=True, pending_action_id=action_id
    return {"action_id": action_id, "notification_id": notif_id}
```

The scenario registry pattern means agents can add new scenarios without modifying the manager.

### 3. Pytest Fixtures

```python
# conftest.py (simplified)

@pytest.fixture
async def test_user():
    """Ephemeral user with session. Cleaned up after test."""
    mgr = TestUserManager()
    user = await mgr.create()
    yield user
    await TestStateManager().reset(user.id)
    await mgr.delete(user.id)

@pytest.fixture
def seeded_page(test_user, request):
    """Authenticated Playwright page with scenario pre-seeded."""
    scenario = request.param  # e.g., "pending_approval"
    # seed scenario
    # launch browser, inject session
    # yield page
    # browser.close()

# Usage in tests:
@pytest.mark.parametrize("seeded_page", ["pending_approval"], indirect=True)
def test_ac_13_approval_card_renders(seeded_page):
    page = seeded_page
    page.goto(f"{WEBAPP_URL}/today")
    # ...
```

### 4. Session Injection

Extract the localStorage injection pattern from `conftest_pw.py` and `playwright_spec025_approval.py` into a shared helper:

```python
def inject_supabase_session(page, supabase_url: str, session: dict):
    """Inject tokens into localStorage so the app recognizes the user."""
    # Same pattern as existing code, parameterized
```

### Dependencies

- `supabase-py` (already installed)
- `playwright` (already installed for existing tests)
- `pytest-playwright` — evaluate if needed or if raw `sync_playwright` context manager is sufficient
- Running `pnpm dev` (chatServer + webApp)
- `.env` with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `VITE_SUPABASE_ANON_KEY`

## Testing Requirements

### Unit Tests (required)

- `TestUserManager.create()` — returns valid user with session tokens
- `TestUserManager.delete()` — user no longer exists after deletion
- `TestStateManager.reset()` — all tables empty for user after reset
- `TestStateManager.seed()` — correct rows exist after seeding each scenario
- Each scenario's `seed()` function — produces expected row structure

These are integration tests by nature (they hit remote Supabase). Mark with `@pytest.mark.integration`.

### Integration Tests

- Full lifecycle: create user → seed → authenticate Playwright → verify page loads → cleanup
- Verify RLS works: seeded data for user A is NOT visible to user B
- Verify cleanup is complete: no orphaned rows after test

### UI Acceptance Tests

AC-08 is itself a Playwright test — the smoke test proving the infrastructure works.

### AC-to-Test Mapping

| AC | Test | Type |
|----|------|------|
| AC-01 | `test_create_and_delete_ephemeral_user` | Integration |
| AC-02 | `test_seed_scenario_{name}` (one per scenario) | Integration |
| AC-03 | `test_reset_clears_all_tables` | Integration |
| AC-04 | `pytest tests/uat/playwright/ -m playwright` runs | Integration |
| AC-05 | `test_user_fixture_lifecycle` | Integration |
| AC-06 | `test_seeded_page_fixture_lifecycle` | Integration |
| AC-07 | Manual: existing `conftest_pw.py` functions still importable | Manual |
| AC-08 | `test_spec_031_smoke.py::test_full_lifecycle` | Playwright |
| AC-09 | `test_state_manager_importable_standalone` | Unit |
| AC-10 | Review of updated `ux-designer.md` | Manual |

### Manual Verification (UAT)

1. Run `pytest tests/uat/playwright/test_spec_031_smoke.py -v` — should pass
2. Check Supabase Auth dashboard — no leftover `@playwright.local` users after test run
3. Verify screenshots in `/tmp/uat-spec031/` show expected UI state

## Edge Cases

- **Test failure during setup** — fixture must still clean up (use try/finally in fixtures)
- **Stale test users** — if cleanup fails (network error, crash), `@playwright.local` users accumulate in Supabase Auth. Add a `scripts/cleanup_test_users.py` utility that deletes all `@playwright.local` users.
- **Rate limiting** — Supabase Auth has rate limits on user creation. If running many tests in parallel, may need to pool/reuse users instead of creating one per test. Start with create-per-test, optimize later if needed.
- **RLS on app tables** — `TestStateManager` uses service_role key to bypass RLS for seeding. This is correct — we're setting up test state, not testing RLS (RLS is tested separately in flow tests).
- **Token expiry during long tests** — Supabase access tokens expire (default 1hr). For normal Playwright tests this is fine. If tests run longer, the `refresh_token` can be used.
- **Concurrent test runs** — each test gets its own user, so parallel execution is safe by design. No shared state.

## Functional Units

Single branch, sequential. All Python, no migrations, no frontend changes.

1. **FU-1: TestUserManager + TestStateManager** — core classes with `empty` scenario only. Integration tests proving create/seed/reset/delete lifecycle. (`backend-dev`)
2. **FU-2: Scenario library** — `pending_approval`, `chat_history`, `unread_notifications` scenarios with integration tests. (`backend-dev`)
3. **FU-3: Pytest fixtures + smoke test** — `conftest.py` with `test_user`, `seeded_page` fixtures. `conftest_pw.py` updated with `inject_supabase_session`. Smoke test proving Playwright + fixtures end-to-end. (`backend-dev`)
4. **FU-4: Agent + process updates** — update `ux-designer.md` and `SKILL.md` with new testing patterns. (`orchestrator`)

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-10)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract — N/A, single domain (test infrastructure)
- [x] Technical decisions reference principles (A8, A4, S5, S1)
- [x] Merge order is explicit — single branch, sequential FUs
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
