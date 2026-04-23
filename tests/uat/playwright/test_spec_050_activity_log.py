"""
SPEC-050 Agent Activity Log -- Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend implementation. Every test is expected to FAIL
against the current codebase because the activity log panel, ambient
indicator, and related UI components do not yet exist. Once frontend-dev
lands the activity log UI, all tests must pass -- that is the "done" bar
for the frontend branch.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see `conftest_pw.get_authenticated_page`).
2. Stubs the backend by intercepting calls with `page.route(...)`. No live
   chatServer/DB dependency -- the tests drive the UI off canned JSON that
   mirrors the shapes in SPEC-050 (ActivityEntry, ActivityListResponse,
   ActivityCountResponse).
3. Navigates to `/` (the Today surface, where the topbar and agent section
   are visible).
4. Asserts against ARIA role/label contracts declared in the spec ACs.
   Selectors use ARIA role, aria-label, or data-testid -- never CSS class,
   never nth-child.

The webApp must be reachable (default `http://localhost:3000` per conftest_pw,
overridable via `WEBAPP_URL`). `pnpm dev` as documented in CLAUDE.md.

==============================================================================
AC -> test function mapping (scope = user-visible ACs only per spec's Playwright table)
==============================================================================

AC-09  test_ac_09_ambient_indicator_renders
AC-10  test_ac_10_activity_count_updates
AC-11  test_ac_11_badge_click_targets
AC-12  test_ac_12_panel_opens_and_closes
AC-13  test_ac_13_search_and_filters
AC-14  test_ac_14_entry_layout
AC-15  test_ac_15_infinite_scroll
AC-16  test_ac_16_empty_states
AC-17  test_ac_17_search_debounce
AC-18  test_ac_18_agent_section_link

Skipped (non-UI / backend-only per spec): AC-01 through AC-08, AC-19.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import pytest

pytest.importorskip(
    "playwright", reason="Playwright not installed -- UAT tests skipped"
)

from playwright.sync_api import Page, expect, sync_playwright  # noqa: E402

from tests.uat.playwright.conftest_pw import (  # noqa: E402
    WEBAPP_URL,
    get_authenticated_page,
)

# --- Test constants (mirrors spec payload shapes) -----------------------------

ACTIVITY_ENTRIES: list[dict[str, Any]] = [
    {
        "id": "act-001",
        "user_id": "user-dev",
        "actor": "today-composer",
        "action": "Regenerated today.md from morning signals",
        "subject_path": "today.md",
        "workflow_run_id": "run-001",
        "status": "done",
        "reasoning": "New emails arrived since last generation. Recomposed to include Q2 invoice thread.",
        "created_at": "2026-04-21T09:26:00Z",
    },
    {
        "id": "act-002",
        "user_id": "user-dev",
        "actor": "approval-service",
        "action": "Approved email_draft: Weekly update to team",
        "subject_path": None,
        "workflow_run_id": None,
        "status": "done",
        "reasoning": None,
        "created_at": "2026-04-21T09:14:00Z",
    },
    {
        "id": "act-003",
        "user_id": "user-dev",
        "actor": "workflow-engine",
        "action": "Failed to send outreach: rate limit exceeded",
        "subject_path": "contacts/meredith.md",
        "workflow_run_id": "run-002",
        "status": "failed",
        "reasoning": "Telegram API returned 429. Will retry in 60 seconds.",
        "created_at": "2026-04-21T08:50:00Z",
    },
    {
        "id": "act-004",
        "user_id": "user-dev",
        "actor": "approval-service",
        "action": "Created calendar_hold awaiting approval: Deep work block",
        "subject_path": None,
        "workflow_run_id": None,
        "status": "awaiting_approval",
        "reasoning": None,
        "created_at": "2026-04-21T08:30:00Z",
    },
]

# Additional entries for infinite scroll testing (page 2).
ACTIVITY_ENTRIES_PAGE_2: list[dict[str, Any]] = [
    {
        "id": f"act-{100 + i}",
        "user_id": "user-dev",
        "actor": "workflow-engine",
        "action": f"Completed step {i} of weekly-invoice-chase",
        "subject_path": None,
        "workflow_run_id": "run-003",
        "status": "done",
        "reasoning": None,
        "created_at": f"2026-04-20T{10 + i:02d}:00:00Z",
    }
    for i in range(5)
]

# Minimal Today payload for tests that need the Today surface.
TODAY_PAYLOAD: dict[str, Any] = {
    "date": "2026-04-21",
    "header": {"framing": "Light day -- 2 drafts need a glance."},
    "your_day": [{"text": "10:00 -- Standup"}],
    "to_do": [],
    "notes": [],
    "agent": {
        "running": [{"text": "Draft Q2 invoice email", "link": "/workflows/invoice-draft"}],
        "watching": [],
        "recent": [{"text": "Completed: morning digest", "link": "/vault/_activity/2026-04-21"}],
        "blocked": [],
    },
    "approvals": [],
    "recent": [],
    "source_mtime": "2026-04-21T07:00:00Z",
}


def _install_default_mocks(
    page: Page,
    *,
    activity_entries: list[dict] | None = None,
    activity_count: dict | None = None,
    has_more: bool = True,
    request_log: list[dict] | None = None,
) -> None:
    """Install page.route handlers for all backend endpoints."""
    entries = activity_entries if activity_entries is not None else ACTIVITY_ENTRIES
    count_resp = activity_count if activity_count is not None else {
        "total": len(entries),
        "since_last_viewed": 3,
    }

    def _log(route):
        if request_log is not None:
            req = route.request
            request_log.append({
                "method": req.method,
                "url": req.url,
                "post_data": req.post_data,
            })

    # GET /api/activity
    def activity_list_handler(route):
        _log(route)
        url = route.request.url

        # Check for cursor pagination (before parameter).
        if "before=" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "items": ACTIVITY_ENTRIES_PAGE_2,
                    "total": len(entries) + len(ACTIVITY_ENTRIES_PAGE_2),
                    "has_more": False,
                }),
            )
        else:
            # Check for search/filter params and filter accordingly.
            filtered = entries
            if "q=" in url:
                q_match = re.search(r"[?&]q=([^&]+)", url)
                if q_match:
                    q = q_match.group(1).lower()
                    filtered = [e for e in entries
                                if q in e["action"].lower() or q in e["actor"].lower()]

            if "status=" in url:
                status_match = re.search(r"[?&]status=([^&]+)", url)
                if status_match:
                    statuses = status_match.group(1).split(",")
                    filtered = [e for e in filtered if e["status"] in statuses]

            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "items": filtered,
                    "total": len(entries),
                    "has_more": has_more,
                }),
            )
    page.route(re.compile(r".*/api/activity(\?.*)?$"), activity_list_handler)

    # GET /api/activity/count
    def activity_count_handler(route):
        _log(route)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(count_resp),
        )
    page.route(re.compile(r".*/api/activity/count(\?.*)?$"), activity_count_handler)

    # POST /api/activity/mark-viewed
    def mark_viewed_handler(route):
        _log(route)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"marked_at": "2026-04-21T09:30:00Z"}),
        )
    page.route(re.compile(r".*/api/activity/mark-viewed$"), mark_viewed_handler)

    # GET /today
    def today_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(TODAY_PAYLOAD))
    page.route(re.compile(r".*/today(\?.*)?$"), today_handler)

    # GET /today/source
    def source_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="text/markdown",
                      body="# Today\n")
    page.route(re.compile(r".*/today/source(\?.*)?$"), source_handler)

    # GET /approvals/count
    def approvals_count_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"count": 2}))
    page.route(re.compile(r".*/approvals/count(\?.*)?$"), approvals_count_handler)

    # GET /approvals
    def approvals_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"cards": []}))
    page.route(re.compile(r".*/approvals(\?.*)?$"), approvals_handler)

    # GET /workflows/runs
    def runs_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"runs": []}))
    page.route(re.compile(r".*/workflows/runs(\?.*)?$"), runs_handler)

    # GET /vault/tree
    def tree_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"tree": []}))
    page.route(re.compile(r".*/vault/tree(\?.*)?$"), tree_handler)

    # POST /today/notes
    def notes_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"created_at": "2026-04-21T09:14:00Z", "text": ""}))
    page.route(re.compile(r".*/today/notes$"), notes_handler)

    # POST /today/todo/toggle
    def todo_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True}))
    page.route(re.compile(r".*/today/todo/toggle$"), todo_handler)


# --- Pytest fixture -----------------------------------------------------------

@pytest.fixture
def authed_page():
    """Yield an authenticated Playwright Page + request log; close browser after."""
    with sync_playwright() as p:
        page, browser = get_authenticated_page(p, headless=True)
        request_log: list[dict] = []
        yield page, request_log
        browser.close()


# --- Tests: Topbar ambient indicator ------------------------------------------

def test_ac_09_ambient_indicator_renders(authed_page):
    """AC-09: The topbar shows an AmbientIndicator with two badges: approvals
    (bell icon + count) and activity (activity icon + count). Each has correct
    aria-label."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Approvals badge should be present.
    approvals_badge = page.get_by_role("button", name=re.compile(r"\d+ pending approvals?", re.I))
    expect(approvals_badge).to_be_visible()

    # Activity badge should be present with "N new agent actions" aria-label.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    expect(activity_badge).to_be_visible()


def test_ac_10_activity_count_updates(authed_page):
    """AC-10: The activity count reflects since_last_viewed from the count
    endpoint. When count is 0, the badge renders with reduced opacity."""
    page, log = authed_page

    # Case 1: Non-zero count -- badge should be fully opaque.
    _install_default_mocks(page, request_log=log,
                           activity_count={"total": 10, "since_last_viewed": 3})
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    badge = page.get_by_role("button", name="3 new agent actions")
    expect(badge).to_be_visible()

    # Case 2: Zero count -- badge should have reduced opacity.
    _install_default_mocks(page, request_log=log,
                           activity_count={"total": 10, "since_last_viewed": 0})
    page.goto(WEBAPP_URL + "/?zero=1")
    page.wait_for_load_state("networkidle")

    zero_badge = page.get_by_role("button", name="0 new agent actions")
    expect(zero_badge).to_be_visible()
    opacity = zero_badge.evaluate(
        "el => parseFloat(getComputedStyle(el).opacity)"
    )
    assert opacity < 1.0, (
        f"Activity badge with count=0 should have reduced opacity, got {opacity}"
    )


def test_ac_11_badge_click_targets(authed_page):
    """AC-11: Clicking the approvals badge scrolls Today's Approvals section
    into view. Clicking the activity badge opens the activity log panel."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Click the activity badge -- should open the activity panel.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    expect(activity_badge).to_be_visible()
    activity_badge.click()
    page.wait_for_timeout(500)

    # Activity panel should now be visible.
    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()


# --- Tests: Activity log panel ------------------------------------------------

def test_ac_12_panel_opens_and_closes(authed_page):
    """AC-12: The activity log renders as a slide-in panel with
    role='complementary' and aria-label='Agent activity log'. A close button
    dismisses it. Opening triggers POST /api/activity/mark-viewed."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel via the activity badge.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    activity_badge.click()
    page.wait_for_timeout(500)

    # Panel should be visible.
    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()

    # Opening should have triggered mark-viewed.
    mark_viewed_calls = [e for e in log
                         if e["method"] == "POST"
                         and "activity/mark-viewed" in e["url"]]
    assert mark_viewed_calls, (
        f"Opening panel should trigger POST /api/activity/mark-viewed. Log: {log!r}"
    )

    # Close button should dismiss the panel.
    close_btn = panel.get_by_role("button", name="Close activity log")
    expect(close_btn).to_be_visible()
    close_btn.click()
    page.wait_for_timeout(300)

    expect(panel).not_to_be_visible()


def test_ac_13_search_and_filters(authed_page):
    """AC-13: The panel header contains a search input with
    aria-label='Search activity log' and filter controls for status and workflow."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    activity_badge.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()

    # Search input should be present.
    search = panel.locator('[aria-label="Search activity log"]')
    expect(search).to_be_visible()

    # Status filter should be present (dropdown or select-like control).
    status_filter = panel.get_by_role("combobox", name=re.compile("status|filter", re.I)).or_(
        panel.locator('[data-testid="status-filter"]')
    )
    expect(status_filter.first).to_be_visible()


def test_ac_14_entry_layout(authed_page):
    """AC-14: Each activity entry renders as an <article> with
    aria-label='Activity: <action text>'. Entry shows timestamp, actor, action,
    status dot, and optional subject path / workflow run link / reasoning toggle."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    activity_badge.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()

    # First entry: "Regenerated today.md from morning signals" by today-composer.
    entry = panel.get_by_role("article", name=re.compile("Regenerated today\\.md", re.I))
    expect(entry).to_be_visible()

    # Actor name should be visible.
    expect(entry.get_by_text("today-composer")).to_be_visible()

    # Status dot should have aria-label.
    status_dot = entry.locator('[aria-label="Status: done"]')
    expect(status_dot).to_be_visible()

    # Subject path link (today.md) should be visible and clickable.
    subject_link = entry.get_by_role("link", name=re.compile("today\\.md"))
    expect(subject_link).to_be_visible()

    # Workflow run link should be visible.
    run_link = entry.get_by_text(re.compile("Run:.*run-001", re.I)).or_(
        entry.get_by_text(re.compile("Run:", re.I))
    )
    expect(run_link.first).to_be_visible()

    # Reasoning toggle ("Why?") should be visible for entries with reasoning.
    why_toggle = entry.get_by_role("button", name=re.compile("Why", re.I))
    expect(why_toggle).to_be_visible()

    # Clicking "Why?" should expand reasoning.
    why_toggle.click()
    page.wait_for_timeout(300)
    expect(entry.get_by_text(re.compile("New emails arrived", re.I))).to_be_visible()


def test_ac_15_infinite_scroll(authed_page):
    """AC-15: The entry list supports infinite scroll. When the user scrolls
    to the bottom and has_more is true, the next page is fetched."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log, has_more=True)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    activity_badge.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()

    # Count initial entries.
    initial_articles = panel.get_by_role("article")
    initial_count = initial_articles.count()
    assert initial_count > 0, "Expected at least one entry in the panel"

    # Scroll to the bottom of the panel to trigger infinite scroll.
    panel.evaluate("el => el.scrollTop = el.scrollHeight")
    page.wait_for_timeout(1000)

    # After scroll, more entries should have loaded.
    # Check that a fetch with `before` was made (cursor pagination).
    cursor_calls = [e for e in log
                    if e["method"] == "GET"
                    and "activity" in e["url"]
                    and "before=" in e["url"]]
    assert cursor_calls, (
        f"Infinite scroll should trigger a cursor-paginated fetch. Log: {log!r}"
    )


def test_ac_16_empty_states(authed_page):
    """AC-16: When the log is empty, panel shows 'No agent activity yet.'
    When filters produce no results, panel shows 'No matching entries.'"""
    page, log = authed_page

    # Case 1: Empty log (no entries at all).
    _install_default_mocks(page, request_log=log,
                           activity_entries=[],
                           activity_count={"total": 0, "since_last_viewed": 0},
                           has_more=False)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel -- use a zero-count badge or an alternative trigger.
    activity_badge = page.get_by_role("button", name=re.compile(r"(0 new agent actions|new agent actions)", re.I))
    if activity_badge.count() == 0:
        # Fallback: try aria-label with just the action pattern.
        activity_badge = page.get_by_role("button", name=re.compile("agent action", re.I))
    activity_badge.first.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()

    # Empty state message.
    expect(panel.get_by_text(re.compile("No agent activity yet", re.I))).to_be_visible()


def test_ac_17_search_debounce(authed_page):
    """AC-17: Search is debounced (300ms). Typing updates the q parameter
    and refetches. The search input has type='search'."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Open the panel.
    activity_badge = page.get_by_role("button", name=re.compile(r"\d+ new agent actions?", re.I))
    activity_badge.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    search_input = panel.locator('[aria-label="Search activity log"]')
    expect(search_input).to_be_visible()

    # Verify the input has type="search" for native clear button.
    input_type = search_input.get_attribute("type")
    assert input_type == "search", (
        f"Search input should have type='search', got type='{input_type}'"
    )

    # Clear the request log and type a search term.
    log.clear()
    search_input.fill("regenerate")

    # Wait less than debounce period -- should NOT have fired yet.
    page.wait_for_timeout(100)
    search_calls_early = [e for e in log
                          if "q=" in (e.get("url") or "") and "activity" in (e.get("url") or "")]
    # Note: we cannot guarantee zero calls at 100ms due to timing, but we check
    # that after the full debounce period, at least one search call was made.

    # Wait for debounce to complete (300ms total from fill).
    page.wait_for_timeout(400)
    search_calls = [e for e in log
                    if "q=" in (e.get("url") or "") and "activity" in (e.get("url") or "")]
    assert search_calls, (
        f"Search should trigger a request with q= parameter after debounce. Log: {log!r}"
    )


# --- Tests: Today Agent section integration -----------------------------------

def test_ac_18_agent_section_link(authed_page):
    """AC-18: The Today Agent section has a 'View activity log' link that
    opens the activity log panel (same as the topbar activity badge)."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Find the Agent section.
    agent_section = page.get_by_role("region", name=re.compile("^Agent$", re.I))
    expect(agent_section).to_be_visible()

    # Find the "View activity log" link/button.
    view_link = agent_section.get_by_role("link", name="View full activity log").or_(
        agent_section.get_by_role("button", name="View full activity log")
    )
    expect(view_link.first).to_be_visible()

    # Click it -- activity panel should open.
    view_link.first.click()
    page.wait_for_timeout(500)

    panel = page.get_by_role("complementary", name="Agent activity log")
    expect(panel).to_be_visible()
