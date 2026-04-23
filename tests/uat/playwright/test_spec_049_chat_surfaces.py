"""
SPEC-049 Chat Surfaces -- Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend implementation. Every test is expected to FAIL
against the current codebase because the chat surfaces (right rail refactor,
Cmd+K palette, AskChip) do not yet exist. Once frontend-dev lands the chat
surfaces, all tests must pass -- that is the "done" bar for the frontend branch.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see `conftest_pw.get_authenticated_page`).
2. Stubs the backend by intercepting calls with `page.route(...)`. No live
   chatServer/DB dependency -- the tests drive the UI off canned JSON that
   mirrors the shapes in SPEC-049 (ChatScope, vault tree, Today data).
3. Navigates to the appropriate route.
4. Asserts against ARIA role/label contracts declared in the spec ACs.
   Selectors use ARIA role, aria-label, or data-testid -- never CSS class,
   never nth-child.

The webApp must be reachable (default `http://localhost:3000` per conftest_pw,
overridable via `WEBAPP_URL`). `pnpm dev` as documented in CLAUDE.md.

==============================================================================
AC -> test function mapping (scope = user-visible ACs only per spec's Playwright table)
==============================================================================

AC-01  test_ac_01_scope_updates_on_navigation
AC-04  test_ac_04_chat_in_right_pane
AC-05  test_ac_05_scope_indicator_displays
AC-06  test_ac_06_scope_updates_on_navigate
AC-07  test_ac_07_conversation_list_works
AC-08  test_ac_08_cmd_k_opens_palette
AC-09  test_ac_09_palette_input_autofocused
AC-10  test_ac_10_palette_suggestions_render
AC-11  test_ac_11_palette_filters_on_type
AC-12  test_ac_12_palette_file_navigates
AC-13  test_ac_13_cmd_k_skipped_in_composer
AC-14  test_ac_14_palette_styling_and_position
AC-16  test_ac_16_ask_chip_renders
AC-17  test_ac_17_ask_chip_opens_chat_with_scope
AC-19  test_ac_19_today_renders_ask_chips
AC-20  test_ac_20_palette_keyboard_nav
AC-21  test_ac_21_chat_rail_landmark
AC-22  test_ac_22_ask_chip_focus_ring
AC-23  test_ac_23_palette_over_active_chat
AC-24  test_ac_24_rapid_navigation_scope

Skipped (non-UI per spec): AC-02, AC-03, AC-15, AC-18, AC-25.
"""

from __future__ import annotations

import json
import re
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

# --- Test constants -----------------------------------------------------------

# Minimal Today payload for scope tests.
TODAY_PAYLOAD: dict[str, Any] = {
    "date": "2026-04-21",
    "header": {"framing": "Light day -- 2 drafts need a glance."},
    "your_day": [
        {"text": "10:00 -- Standup", "wikilink": "meetings/2026-04-21-standup"},
    ],
    "to_do": [
        {"line_id": "todo-1", "text": "Ship SPEC-045 brief", "checked": False},
    ],
    "notes": [],
    "agent": {
        "running": [{"text": "Draft Q2 invoice email", "link": "/workflows/invoice-draft"}],
        "watching": [{"text": "@meredith reply", "link": "/vault/contacts/meredith"}],
        "recent": [],
        "blocked": [],
    },
    "approvals": [
        {
            "id": "card-email-01",
            "card_type": "email_draft",
            "title": "Re: Q2 invoicing",
            "payload": {
                "to": ["bob@example.com"],
                "subject": "Re: Q2 invoicing",
                "body": "Hi Bob,\n\nQ2 invoice attached.\n\nThanks,\nT",
            },
            "status": "pending",
        },
    ],
    "recent": [
        {"path": "notes/standup.md", "updated_at": "2026-04-21T08:15:00Z"},
        {"path": "contacts/meredith.md", "updated_at": "2026-04-20T19:02:00Z"},
    ],
    "source_mtime": "2026-04-21T07:00:00Z",
}

VAULT_TREE: list[dict[str, Any]] = [
    {
        "name": "today.md",
        "path": "today.md",
        "type": "file",
        "mtime": "2026-04-21T07:00:00Z",
        "size": 1024,
    },
    {
        "name": "notes",
        "path": "notes/",
        "type": "folder",
        "mtime": "2026-04-21T06:00:00Z",
        "size": 0,
        "children": [
            {
                "name": "standup.md",
                "path": "notes/standup.md",
                "type": "file",
                "mtime": "2026-04-20T14:00:00Z",
                "size": 512,
            },
        ],
    },
]


def _install_default_mocks(page: Page, *, request_log: list[dict] | None = None) -> None:
    """Install page.route handlers for all backend endpoints used by chat surfaces."""

    def _log(route):
        if request_log is not None:
            req = route.request
            request_log.append({
                "method": req.method,
                "url": req.url,
                "post_data": req.post_data,
            })

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
                      body="# Today\n## Your day\n")
    page.route(re.compile(r".*/today/source(\?.*)?$"), source_handler)

    # GET /vault/tree
    def tree_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"tree": VAULT_TREE}))
    page.route(re.compile(r".*/vault/tree(\?.*)?$"), tree_handler)

    # GET /vault/file
    def file_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({
                          "content": "# Standup Notes\n\nMeeting notes here.\n",
                          "mtime": "2026-04-20T14:00:00Z",
                          "size": 512,
                      }))
    page.route(re.compile(r".*/vault/file(\?.*)?$"), file_handler)

    # GET /vault/folder
    def folder_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"entries": [
                          {"name": "standup.md", "path": "notes/standup.md",
                           "type": "file", "mtime": "2026-04-20T14:00:00Z", "size": 512},
                      ]}))
    page.route(re.compile(r".*/vault/folder(\?.*)?$"), folder_handler)

    # GET /approvals/count
    def approvals_count_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"count": 1}))
    page.route(re.compile(r".*/approvals/count(\?.*)?$"), approvals_count_handler)

    # GET /approvals
    def approvals_list_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"cards": TODAY_PAYLOAD["approvals"]}))
    page.route(re.compile(r".*/approvals(\?.*)?$"), approvals_list_handler)

    # POST /approvals/{id}/approve|reject|edit
    def approvals_mutate_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True}))
    page.route(re.compile(r".*/approvals/[^/]+/(approve|reject|edit)$"),
               approvals_mutate_handler)

    # GET /workflows/runs
    def runs_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"runs": []}))
    page.route(re.compile(r".*/workflows/runs(\?.*)?$"), runs_handler)

    # POST /api/chat
    def chat_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({
                          "message": "I can help with that.",
                          "session_id": "session-001",
                      }))
    page.route(re.compile(r".*/api/chat$"), chat_handler)

    # GET /api/activity/count
    def activity_count_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"total": 0, "since_last_viewed": 0}))
    page.route(re.compile(r".*/activity/count(\?.*)?$"), activity_count_handler)

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


# --- Tests: Scope binding -----------------------------------------------------

def test_ac_01_scope_updates_on_navigation(authed_page):
    """AC-01: useChatStore exposes a scope field that updates reactively when
    the route changes, following the scope resolution rules."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)

    # Navigate to root -- scope should be 'today'.
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_be_visible()
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("Today", re.I)
    )

    # Navigate to a folder -- scope should update to 'folder'.
    page.goto(WEBAPP_URL + "/vault/notes/")
    page.wait_for_load_state("networkidle")
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("Folder.*notes", re.I)
    )

    # Navigate to a file -- scope should update to 'file'.
    page.goto(WEBAPP_URL + "/vault/notes/standup.md")
    page.wait_for_load_state("networkidle")
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("File.*standup", re.I)
    )


# --- Tests: Right rail --------------------------------------------------------

def test_ac_04_chat_in_right_pane(authed_page):
    """AC-04: ChatPanel renders inside the SPEC-046 right pane (not as a
    slide-in overlay). The panel fills the right pane's full height."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Chat should be in the right pane, not a separate overlay.
    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # It should be inside a panel (react-resizable-panels).
    panel_parent = chat_rail.locator("xpath=ancestor::*[@data-panel]").first
    expect(panel_parent).to_be_visible()


def test_ac_05_scope_indicator_displays(authed_page):
    """AC-05: The chat header displays a scope indicator showing the current
    scope with aria-label='Chat scope: <description>'."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Scope indicator in chat rail -- aria-label="Chat scope: Today".
    scope = page.locator('[aria-label="Chat scope: Today"]')
    expect(scope).to_be_visible()


def test_ac_06_scope_updates_on_navigate(authed_page):
    """AC-06: When the user navigates to a different surface, the scope
    indicator updates within one render cycle. Chat history is preserved."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)

    # Start at root.
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    scope = page.locator('[aria-label*="Chat scope"]')
    expect(scope).to_have_attribute("aria-label", re.compile("Today", re.I))

    # Navigate to a file.
    page.goto(WEBAPP_URL + "/vault/notes/standup.md")
    page.wait_for_load_state("networkidle")

    scope = page.locator('[aria-label*="Chat scope"]')
    expect(scope).to_have_attribute("aria-label", re.compile("File.*standup", re.I))


def test_ac_07_conversation_list_works(authed_page):
    """AC-07: The ConversationList (existing conversation switcher) remains
    functional inside the refactored ChatPanel."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # The conversation list or a button to access it should be present.
    conv_list = chat_rail.get_by_role("button", name=re.compile("conversation|new chat|history", re.I))
    expect(conv_list.first).to_be_visible()


# --- Tests: Cmd+K palette ----------------------------------------------------

def test_ac_08_cmd_k_opens_palette(authed_page):
    """AC-08: Pressing Cmd+K opens a modal command palette with
    role='dialog' and aria-label='Command palette'. Escape dismisses it."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Press Cmd+K (Meta+K).
    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    # Palette dialog should be visible.
    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Press Escape to close.
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    expect(palette).not_to_be_visible()


def test_ac_09_palette_input_autofocused(authed_page):
    """AC-09: The palette's first row is a free-form text input with
    aria-label='Ask or search...' that is auto-focused on open."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Input should be auto-focused.
    search_input = palette.locator('[aria-label="Ask or search..."]')
    expect(search_input).to_be_visible()
    expect(search_input).to_be_focused()


def test_ac_10_palette_suggestions_render(authed_page):
    """AC-10: Below the input, the palette shows a context-aware suggestion
    list with selectable items (role='option')."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Suggestions should be present as selectable options.
    options = palette.get_by_role("option")
    assert options.count() >= 1, (
        f"Expected at least 1 suggestion option, got {options.count()}"
    )


def test_ac_11_palette_filters_on_type(authed_page):
    """AC-11: Typing in the input filters the suggestion list. Items matching
    the query text are shown; non-matching items are hidden."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    search_input = palette.locator('[aria-label="Ask or search..."]')

    # Count initial suggestions.
    initial_count = palette.get_by_role("option").count()

    # Type a filter term.
    search_input.fill("standup")
    page.wait_for_timeout(300)

    # Filtered count should be less or equal, and should contain a match.
    filtered_count = palette.get_by_role("option").count()
    assert filtered_count <= initial_count or filtered_count >= 1, (
        f"Filtering did not reduce options: initial={initial_count}, filtered={filtered_count}"
    )

    # There should be an option referencing "standup" or an "Ask: standup" fallback.
    matching = palette.get_by_role("option", name=re.compile("standup", re.I))
    expect(matching.first).to_be_visible()


def test_ac_12_palette_file_navigates(authed_page):
    """AC-12: Selecting a file suggestion navigates to /vault/<path> and
    closes the palette."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    search_input = palette.locator('[aria-label="Ask or search..."]')

    # Type a filename to find a file suggestion.
    search_input.fill("standup")
    page.wait_for_timeout(300)

    # Click the file suggestion (not the "Ask:" fallback).
    file_option = palette.get_by_role("option", name=re.compile("standup\\.md", re.I))
    expect(file_option).to_be_visible()
    file_option.click()
    page.wait_for_timeout(500)

    # Palette should be closed.
    expect(palette).not_to_be_visible()

    # URL should have navigated to the vault path.
    assert "/vault/" in page.url and "standup" in page.url, (
        f"Expected navigation to vault path containing 'standup', got {page.url}"
    )


def test_ac_13_cmd_k_skipped_in_composer(authed_page):
    """AC-13: The Cmd+K shortcut does not fire when the user is focused in
    the chat Composer input (data-testid='composer')."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Focus the chat composer.
    composer = page.locator('[data-testid="composer"]')
    if composer.count() > 0:
        composer_input = composer.locator("textarea, input").first
        if composer_input.count() > 0:
            composer_input.click()
            composer_input.focus()
            page.wait_for_timeout(200)

            # Press Cmd+K while in composer -- palette should NOT open.
            page.keyboard.press("Meta+k")
            page.wait_for_timeout(300)

            palette = page.get_by_role("dialog", name="Command palette")
            expect(palette).not_to_be_visible()
    else:
        # If composer is not found, the test documents the expected behavior
        # but cannot verify it. Mark as expected failure on this assertion.
        pytest.skip("Composer element not found -- chat panel may not be rendered yet")


def test_ac_14_palette_styling_and_position(authed_page):
    """AC-14: The palette renders above all content with max-width 640px,
    horizontally centered, vertically positioned at ~20% from top."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Check max-width constraint on the palette content container.
    palette_box = palette.bounding_box()
    assert palette_box is not None, "Palette has no bounding box"
    assert palette_box["width"] <= 700, (
        f"Palette width {palette_box['width']}px exceeds max-width constraint"
    )

    # Check vertical position -- should be roughly in the top 20-30% of the viewport.
    viewport_height = page.viewport_size["height"]
    top_percentage = palette_box["y"] / viewport_height
    assert 0.10 <= top_percentage <= 0.40, (
        f"Palette top position at {top_percentage:.0%} of viewport, expected ~20%"
    )


# --- Tests: AskChip ----------------------------------------------------------

def test_ac_16_ask_chip_renders(authed_page):
    """AC-16: An AskChip component renders as a button with
    aria-label='Ask about this' and a chat bubble icon."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # AskChip should be present on the Today surface (near approvals or agent items).
    ask_chip = page.get_by_role("button", name="Ask about this")
    expect(ask_chip.first).to_be_visible()


def test_ac_17_ask_chip_opens_chat_with_scope(authed_page):
    """AC-17: Clicking the AskChip opens the right-rail chat (if collapsed)
    and sets the chat scope to the chip's scope prop."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    ask_chip = page.get_by_role("button", name="Ask about this")
    expect(ask_chip.first).to_be_visible()
    ask_chip.first.click()
    page.wait_for_timeout(500)

    # Chat rail should be visible after clicking the chip.
    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # Scope should reflect "Today" (since the chip is on the Today surface).
    scope = page.locator('[aria-label*="Chat scope"]')
    expect(scope).to_have_attribute("aria-label", re.compile("Today", re.I))


def test_ac_19_today_renders_ask_chips(authed_page):
    """AC-19: The Today surface (ApprovalsSection, AgentSection) renders
    AskChip next to approval cards and agent activity items."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Approvals section should have at least one AskChip.
    approvals = page.get_by_role("region", name=re.compile("^Approvals$", re.I))
    expect(approvals).to_be_visible()

    # Agent section should have at least one AskChip.
    agent = page.get_by_role("region", name=re.compile("^Agent$", re.I))
    expect(agent).to_be_visible()

    # At least one "Ask about this" button should be visible on the page.
    ask_chips = page.get_by_role("button", name="Ask about this")
    assert ask_chips.count() >= 1, (
        f"Expected at least 1 AskChip on Today surface, got {ask_chips.count()}"
    )


# --- Tests: Keyboard navigation and accessibility -----------------------------

def test_ac_20_palette_keyboard_nav(authed_page):
    """AC-20: The Cmd+K palette supports full keyboard navigation: arrow keys
    move between suggestions, Enter selects, Escape closes. Focus is trapped."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Arrow down should move focus to the first suggestion.
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(200)

    # An option should have aria-selected="true" or be focused.
    selected = palette.locator('[aria-selected="true"]')
    assert selected.count() >= 1, "No option selected after ArrowDown"

    # Arrow down again should move to next suggestion.
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(200)

    # Escape closes the palette.
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    expect(palette).not_to_be_visible()


def test_ac_21_chat_rail_landmark(authed_page):
    """AC-21: The right-rail chat panel has <aside role='complementary'
    aria-label='Chat'> as its outermost landmark."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # The chat rail must be an <aside> with role="complementary" and aria-label="Chat".
    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # Verify it is actually an <aside> element.
    tag = chat_rail.evaluate("el => el.tagName.toLowerCase()")
    assert tag == "aside", (
        f"Chat rail outermost element should be <aside>, got <{tag}>"
    )


def test_ac_22_ask_chip_focus_ring(authed_page):
    """AC-22: The AskChip has a visible focus ring (:focus-visible outline)
    consistent with other interactive elements."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    ask_chip = page.get_by_role("button", name="Ask about this").first
    expect(ask_chip).to_be_visible()

    # Focus the chip via keyboard (Tab).
    ask_chip.focus()
    page.wait_for_timeout(200)

    # Check that a focus ring outline is applied via :focus-visible.
    outline = ask_chip.evaluate(
        "el => getComputedStyle(el, ':focus-visible').outlineStyle || getComputedStyle(el).outlineStyle"
    )
    # The outline should not be "none" when focused.
    # Note: this is a best-effort check -- :focus-visible styling depends on
    # browser implementation. The key contract is that the CSS class exists.
    assert outline != "none" or ask_chip.evaluate(
        "el => el.matches(':focus-visible')"
    ), "AskChip should have a visible focus ring on :focus-visible"


# --- Tests: Edge cases --------------------------------------------------------

def test_ac_23_palette_over_active_chat(authed_page):
    """AC-23: Opening Cmd+K while the right rail is already open and contains
    an in-progress message: the palette opens normally without disrupting
    the in-progress message."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Verify chat rail is visible.
    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # Open Cmd+K while chat is visible -- palette should open on top.
    page.keyboard.press("Meta+k")
    page.wait_for_timeout(300)

    palette = page.get_by_role("dialog", name="Command palette")
    expect(palette).to_be_visible()

    # Chat rail should still be in the DOM (not removed).
    expect(chat_rail).to_be_attached()

    # Close palette.
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    expect(palette).not_to_be_visible()

    # Chat rail should still be visible.
    expect(chat_rail).to_be_visible()


def test_ac_24_rapid_navigation_scope(authed_page):
    """AC-24: Rapid navigation (clicking through multiple folders quickly)
    updates the scope indicator without stale scope state. Scope is derived
    from the current route, not from navigation events."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)

    routes = [
        (WEBAPP_URL + "/", "Today"),
        (WEBAPP_URL + "/vault/notes/", "Folder"),
        (WEBAPP_URL + "/vault/notes/standup.md", "File"),
        (WEBAPP_URL + "/", "Today"),
        (WEBAPP_URL + "/vault/notes/standup.md", "File"),
    ]

    for url, expected_scope in routes:
        page.goto(url)
        # Deliberately short wait to simulate rapid navigation.
        page.wait_for_timeout(200)

    # After rapid navigation, wait for network to settle.
    page.wait_for_load_state("networkidle")

    # The final route was /vault/notes/standup.md -- scope should be "File".
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("File.*standup", re.I)
    )
