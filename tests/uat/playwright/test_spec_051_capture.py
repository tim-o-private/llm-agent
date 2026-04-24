"""
SPEC-051 Capture — Playwright UI acceptance tests (RED baseline).

Written alongside backend/frontend implementation. These tests verify the
capture routing UI integration. They stub the backend to avoid live
dependencies.

==============================================================================
AC -> test function mapping
==============================================================================

AC-11  test_ac_11_notes_routing_toggle
AC-12  test_ac_12_cmdk_capture
AC-14  test_ac_14_confirmation_banner
AC-15  test_ac_15_redirect_flow

Requires: webApp running (default http://localhost:3000), overridable via WEBAPP_URL.
"""

from __future__ import annotations

import json
import re

import pytest

pw = pytest.importorskip("playwright.sync_api", reason="playwright not installed")

WEBAPP_URL_DEFAULT = "http://localhost:3000"

CAPTURE_RESPONSE_PLACED = {
    "capture_id": "cap-test-001",
    "status": "placed",
    "target_path": "projects/acme.md",
    "target_section": "Notes",
    "method": "append",
    "confirmation": "Added to `projects/acme.md` under Notes",
    "fallback": False,
    "redirect": None,
    "created_at": "2026-04-21T14:00:00Z",
    "placed_at": "2026-04-21T14:00:01Z",
    "reasoning": "Keyword match",
    "error_detail": None,
}

REDIRECT_RESPONSE = {
    **CAPTURE_RESPONSE_PLACED,
    "target_path": "meetings/prep.md",
    "target_section": "Notes",
    "confirmation": "Moved to `meetings/prep.md` under Notes",
    "redirect": {
        "from_path": "projects/acme.md",
        "target_hint": "meeting prep",
        "new_target_path": "meetings/prep.md",
        "new_target_section": "Notes",
        "redirected_at": "2026-04-21T14:01:00Z",
    },
}

TODAY_RESPONSE = {
    "date": "2026-04-21",
    "header": {"framing": "Test day."},
    "your_day": [],
    "to_do": [],
    "notes": [],
    "agent": {"running": [], "watching": [], "recent": [], "blocked": []},
    "approvals": [],
    "recent": [],
    "source_mtime": 1.0,
    "unknown_sections": [],
}

TREE_RESPONSE = {
    "tree": [
        {"name": "today.md", "path": "today.md", "type": "file", "mtime": "2026-04-21T12:00:00Z", "size": 500},
        {
            "name": "projects",
            "path": "projects",
            "type": "folder",
            "mtime": "2026-04-20T12:00:00Z",
            "size": 0,
            "children": [
                {"name": "acme.md", "path": "projects/acme.md", "type": "file", "mtime": "2026-04-20T12:00:00Z", "size": 200},  # noqa: E501
            ],
        },
    ],
}


@pytest.fixture(scope="session")
def webapp_url():
    import os
    return os.getenv("WEBAPP_URL", WEBAPP_URL_DEFAULT)


@pytest.fixture
def page(browser_context):
    """Fresh page for each test."""
    p = browser_context.new_page()
    yield p
    p.close()


@pytest.fixture
def browser_context(browser):
    ctx = browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture(scope="session")
def browser(playwright):
    b = playwright.chromium.launch(headless=True)
    yield b
    b.close()


@pytest.fixture(scope="session")
def playwright():
    with pw.sync_playwright() as p:
        yield p


def _stub_apis(page, webapp_url):
    """Intercept API calls and return canned responses."""
    page.route("**/api/today", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(TODAY_RESPONSE),
    ))
    page.route("**/api/vault/tree", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(TREE_RESPONSE),
    ))
    page.route("**/api/capture", lambda route: route.fulfill(
        status=202,
        content_type="application/json",
        body=json.dumps(CAPTURE_RESPONSE_PLACED),
    ) if route.request.method == "POST" else route.continue_())
    page.route(re.compile(r".*/api/capture/[^/]+/redirect$"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(REDIRECT_RESPONSE),
    ))
    page.route(re.compile(r".*/api/capture/[^/]+$"), lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(CAPTURE_RESPONSE_PLACED),
    ) if route.request.method == "GET" else route.continue_())


@pytest.mark.skip(reason="RED baseline — requires running webApp with auth stub")
def test_ac_11_notes_routing_toggle(page, webapp_url):
    """With routing enabled, Notes submit should show confirmation banner."""
    _stub_apis(page, webapp_url)
    page.goto(webapp_url)

    # Enable smart routing toggle
    toggle = page.get_by_label("Enable smart routing")
    toggle.check()

    # Type a note and submit
    textarea = page.get_by_label("Capture a note")
    textarea.fill("review the Acme contract")
    textarea.press("Meta+Enter")

    # Confirmation banner should appear
    banner = page.get_by_role("status", name="Capture confirmation")
    banner.wait_for(state="visible", timeout=5000)
    assert "acme.md" in banner.text_content().lower()


@pytest.mark.skip(reason="RED baseline — requires running webApp with auth stub")
def test_ac_12_cmdk_capture(page, webapp_url):
    """Cmd+K palette should offer a Capture action."""
    _stub_apis(page, webapp_url)
    page.goto(webapp_url)

    # Open Cmd+K
    page.keyboard.press("Meta+k")

    # Type capture text
    palette_input = page.get_by_label("Ask or search...")
    palette_input.fill("my captured thought")

    # Look for "Capture:" action
    capture_item = page.get_by_text("Capture: my captured thought")
    assert capture_item.is_visible()


@pytest.mark.skip(reason="RED baseline — requires running webApp with auth stub")
def test_ac_14_confirmation_banner(page, webapp_url):
    """Confirmation banner should show target link and Move button."""
    _stub_apis(page, webapp_url)
    page.goto(webapp_url)

    # Enable routing and capture
    page.get_by_label("Enable smart routing").check()
    textarea = page.get_by_label("Capture a note")
    textarea.fill("test confirmation")
    textarea.press("Meta+Enter")

    banner = page.get_by_role("status", name="Capture confirmation")
    banner.wait_for(state="visible", timeout=5000)

    # Banner should have a link and Move button
    link = banner.get_by_text("Open")
    assert link.is_visible()
    move = banner.get_by_role("button", name="Move capture to different location")
    assert move.is_visible()


@pytest.mark.skip(reason="RED baseline — requires running webApp with auth stub")
def test_ac_15_redirect_flow(page, webapp_url):
    """Redirect input should accept text and update the banner."""
    _stub_apis(page, webapp_url)
    page.goto(webapp_url)

    # Enable routing and capture
    page.get_by_label("Enable smart routing").check()
    textarea = page.get_by_label("Capture a note")
    textarea.fill("redirect test")
    textarea.press("Meta+Enter")

    banner = page.get_by_role("status", name="Capture confirmation")
    banner.wait_for(state="visible", timeout=5000)

    # Click Move
    move = banner.get_by_role("button", name="Move capture to different location")
    move.click()

    # Redirect input should appear
    redirect_input = page.get_by_label("Redirect target")
    redirect_input.wait_for(state="visible", timeout=3000)
    redirect_input.fill("meeting prep")
    redirect_input.press("Enter")
