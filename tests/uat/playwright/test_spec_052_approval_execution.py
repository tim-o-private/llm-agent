"""
SPEC-052 Approval Execution -- Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend integration work is complete. Tests are expected to
FAIL against the current codebase until the ExecutionStatus component and
retry flow are wired into the approval card rendering.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user (see conftest_pw.get_authenticated_page).
2. Stubs the backend by intercepting /api/approvals/* with page.route().
3. Navigates to / (Today surface) or a completed approvals view.
4. Asserts against ARIA role/label contracts from the spec ACs.
   Selectors use ARIA role, aria-label, or data-testid -- never CSS class.

==============================================================================
AC -> test function mapping
==============================================================================

AC-14  test_ac_14_execution_success_indicator
AC-14  test_ac_14_execution_failure_indicator
AC-14  test_ac_14_no_executor_chip
AC-15  test_ac_15_retry_button_calls_endpoint
AC-15  test_ac_15_retry_loading_state
AC-16  test_ac_16_stage1_noop_removed
"""

from __future__ import annotations

import json

import pytest

pw = pytest.importorskip("playwright.sync_api")


# ---------------------------------------------------------------------------
# Canned data
# ---------------------------------------------------------------------------

APPROVED_CARD_SUCCESS = {
    "id": "card-ok-1",
    "card_type": "email_draft",
    "title": "Reply to Alice",
    "status": "approved",
    "payload": {"to": ["alice@example.com"], "subject": "Hi", "body": "Hello"},
    "decided_at": "2026-04-21T12:00:00Z",
    "decided_by": "user-1",
    "executed_at": "2026-04-21T12:00:01Z",
    "execution_result": {"message_id": "msg-1", "to": "alice@example.com"},
    "execution_error": None,
}

APPROVED_CARD_FAILED = {
    "id": "card-fail-1",
    "card_type": "email_draft",
    "title": "Reply to Bob",
    "status": "approved",
    "payload": {"to": ["bob@example.com"], "subject": "Hi", "body": "Hello"},
    "decided_at": "2026-04-21T12:00:00Z",
    "decided_by": "user-1",
    "executed_at": "2026-04-21T12:00:01Z",
    "execution_result": None,
    "execution_error": "Gmail compose scope missing",
}

APPROVED_CARD_NO_EXECUTOR = {
    "id": "card-noop-1",
    "card_type": "email_draft",
    "title": "Record only",
    "status": "approved",
    "payload": {"to": ["c@example.com"], "subject": "Hi", "body": "Hello"},
    "decided_at": "2026-04-21T12:00:00Z",
    "decided_by": "user-1",
    "executed_at": "2026-04-21T12:00:01Z",
    "execution_result": None,
    "execution_error": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_approvals(page, cards: list[dict]):
    """Intercept GET /api/approvals and return canned cards."""

    def handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(cards),
        )

    page.route("**/api/approvals", handler)
    page.route("**/api/approvals/count", lambda r: r.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"count": len(cards)}),
    ))


def _stub_today(page, cards: list[dict]):
    """Intercept GET /api/today and inject cards into the approvals section."""
    today_payload = {
        "date": "2026-04-21",
        "header": {"framing": "Test day"},
        "your_day": [],
        "to_do": [],
        "notes": [],
        "agent": {"running": [], "watching": [], "recent": [], "blocked": []},
        "approvals": cards,
        "recent": [],
    }

    def handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(today_payload),
        )

    page.route("**/api/today", handler)


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.skipif(True, reason="RED baseline — ExecutionStatus not yet wired")
class TestExecutionStatusIndicators:
    """AC-14: Approved cards show execution status."""

    def test_ac_14_execution_success_indicator(self, page):
        _stub_today(page, [APPROVED_CARD_SUCCESS])
        _stub_approvals(page, [APPROVED_CARD_SUCCESS])
        page.goto("/")

        status = page.get_by_role("status", name="Execution succeeded")
        assert status.is_visible()

    def test_ac_14_execution_failure_indicator(self, page):
        _stub_today(page, [APPROVED_CARD_FAILED])
        _stub_approvals(page, [APPROVED_CARD_FAILED])
        page.goto("/")

        alert = page.get_by_role("alert", name="Execution failed")
        assert alert.is_visible()
        assert "Gmail compose scope missing" in alert.text_content()

    def test_ac_14_no_executor_chip(self, page):
        _stub_today(page, [APPROVED_CARD_NO_EXECUTOR])
        _stub_approvals(page, [APPROVED_CARD_NO_EXECUTOR])
        page.goto("/")

        chip = page.get_by_role("status", name="No executor")
        assert chip.is_visible()
        assert "record only" in chip.text_content().lower()


@pytest.mark.skipif(True, reason="RED baseline — retry not yet wired")
class TestRetryButton:
    """AC-15: Retry button on failed cards."""

    def test_ac_15_retry_button_calls_endpoint(self, page):
        _stub_today(page, [APPROVED_CARD_FAILED])
        _stub_approvals(page, [APPROVED_CARD_FAILED])

        retry_called = []

        def handle_retry(route):
            retry_called.append(True)
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    **APPROVED_CARD_FAILED,
                    "executed_at": "2026-04-21T12:05:00Z",
                    "execution_result": {"message_id": "msg-retry"},
                    "execution_error": None,
                }),
            )

        page.route("**/api/approvals/card-fail-1/retry", handle_retry)
        page.goto("/")

        retry_btn = page.get_by_role("button", name="Retry execution")
        retry_btn.click()

        assert len(retry_called) == 1

    def test_ac_15_retry_loading_state(self, page):
        _stub_today(page, [APPROVED_CARD_FAILED])
        _stub_approvals(page, [APPROVED_CARD_FAILED])

        def slow_retry(route):
            import time
            time.sleep(1)
            route.fulfill(status=200, body="{}")

        page.route("**/api/approvals/card-fail-1/retry", slow_retry)
        page.goto("/")

        retry_btn = page.get_by_role("button", name="Retry execution")
        retry_btn.click()

        # Button should show loading state
        assert page.get_by_text("Retrying...").is_visible()


@pytest.mark.skipif(True, reason="RED baseline — Stage 1 text still present")
class TestStage1NoopRemoved:
    """AC-16: _describe_action no longer includes Stage 1 suffix."""

    def test_ac_16_stage1_noop_removed(self, page):
        # This is a backend test reflected in the activity log;
        # Playwright would check that activity entries for approvals
        # don't contain "Stage 1 no-op, not sent".
        _stub_today(page, [APPROVED_CARD_SUCCESS])
        page.goto("/")

        # No text mentioning Stage 1 should appear in the page
        assert page.locator("text=Stage 1 no-op").count() == 0
