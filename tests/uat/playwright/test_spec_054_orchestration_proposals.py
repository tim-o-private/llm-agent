"""
SPEC-054 Orchestration Proposals — Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend implementation. Every test is expected to FAIL
against the current codebase because the orchestration proposals UI does not
yet exist. Once the frontend lands, all tests must pass — that is the "done"
bar.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see conftest_pw).
2. Stubs the backend by intercepting calls with ``page.route(...)``.
3. Navigates to the Today surface (``/``).
4. Asserts against ARIA role/label contracts.

The webApp must be reachable (default ``http://localhost:3000`` per conftest_pw).
"""

import json

import pytest

pw = pytest.importorskip("playwright.sync_api")

# ---------------------------------------------------------------------------
# Stub data
# ---------------------------------------------------------------------------

THREAD_LIST_RESPONSE = {
    "threads": [
        {
            "path": "_threads/2026-04-22-santa-fe-trip.md",
            "title": "Santa Fe Trip Planning",
            "status": "active",
            "next_action": "Research flights for May 10-14",
            "blocked_on": None,
            "created_at": "2026-04-22T08:30:00Z",
            "updated_at": "2026-04-22T14:15:00Z",
        },
        {
            "path": "_threads/2026-04-20-q3-budget.md",
            "title": "Q3 Budget Review",
            "status": "watching",
            "next_action": None,
            "blocked_on": "Waiting for Sarah's input",
            "created_at": "2026-04-20T09:00:00Z",
            "updated_at": "2026-04-21T10:00:00Z",
        },
    ]
}


# ---------------------------------------------------------------------------
# AC-06: Threads surface in Today's Agent section
# ---------------------------------------------------------------------------


class TestThreadsInToday:
    """AC-06: Thread-docs surface in Today's Agent section."""

    @pytest.mark.skip(reason="RED baseline — no thread UI yet")
    def test_active_thread_shows_in_running(self, authenticated_page):
        """An active thread should appear under Running in the Agent section."""
        page = authenticated_page

        # Stub the threads API
        def handle_threads(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(THREAD_LIST_RESPONSE),
            )

        page.route("**/api/vault/threads*", handle_threads)
        page.goto("/")

        # The Agent section should contain the active thread
        agent_section = page.get_by_role("region", name="Agent")
        running = agent_section.get_by_text("Santa Fe Trip Planning")
        assert running.is_visible()

    @pytest.mark.skip(reason="RED baseline — no thread UI yet")
    def test_watching_thread_shows_in_watching(self, authenticated_page):
        """A watching thread should appear under Watching in the Agent section."""
        page = authenticated_page

        def handle_threads(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(THREAD_LIST_RESPONSE),
            )

        page.route("**/api/vault/threads*", handle_threads)
        page.goto("/")

        agent_section = page.get_by_role("region", name="Agent")
        watching = agent_section.get_by_text("Q3 Budget Review")
        assert watching.is_visible()

    @pytest.mark.skip(reason="RED baseline — no thread UI yet")
    def test_blocked_thread_shows_blocked_on(self, authenticated_page):
        """A thread with blocked_on should show the blocking reason."""
        page = authenticated_page

        def handle_threads(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(THREAD_LIST_RESPONSE),
            )

        page.route("**/api/vault/threads*", handle_threads)
        page.goto("/")

        agent_section = page.get_by_role("region", name="Agent")
        blocked = agent_section.get_by_text("Waiting for Sarah's input")
        assert blocked.is_visible()


# ---------------------------------------------------------------------------
# AC-07: Threads accessible via vault browser
# ---------------------------------------------------------------------------


class TestThreadVaultAccess:
    """AC-07: Thread-docs accessible via vault browser."""

    @pytest.mark.skip(reason="RED baseline — no thread-specific vault UI yet")
    def test_thread_link_navigates_to_vault(self, authenticated_page):
        """Clicking a thread title in Today should navigate to the file detail view."""
        page = authenticated_page

        def handle_threads(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(THREAD_LIST_RESPONSE),
            )

        page.route("**/api/vault/threads*", handle_threads)
        page.goto("/")

        # Click the thread title
        page.get_by_text("Santa Fe Trip Planning").click()

        # Should navigate to the vault file view
        page.wait_for_url("**/vault/_threads/**")


# ---------------------------------------------------------------------------
# AC-03: Status transitions via UI
# ---------------------------------------------------------------------------


class TestThreadStatusChange:
    """AC-03: Thread status changes from the UI."""

    @pytest.mark.skip(reason="RED baseline — no status-change UI yet")
    def test_pause_thread(self, authenticated_page):
        """User can pause a thread from the thread detail view."""
        page = authenticated_page

        status_changed = []

        def handle_status(route):
            body = json.loads(route.request.post_data)
            status_changed.append(body["status"])
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"status": body["status"]}),
            )

        page.route("**/api/vault/threads/*/status", handle_status)

        def handle_threads(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(THREAD_LIST_RESPONSE),
            )

        page.route("**/api/vault/threads*", handle_threads)

        page.goto("/")
        page.get_by_text("Santa Fe Trip Planning").click()
        page.get_by_role("button", name="Pause").click()

        assert "paused" in status_changed
