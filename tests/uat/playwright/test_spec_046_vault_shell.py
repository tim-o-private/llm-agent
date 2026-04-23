"""
SPEC-046 Vault Shell & Browser -- Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend implementation. Every test is expected to FAIL
against the current codebase because the vault shell and three-pane layout
do not yet exist. Once frontend-dev lands the vault shell, all tests must
pass -- that is the "done" bar for the frontend branch.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see `conftest_pw.get_authenticated_page`).
2. Stubs the backend by intercepting calls with `page.route(...)`. No live
   chatServer/DB dependency -- the tests drive the UI off canned JSON that
   mirrors the shapes in SPEC-046 (TreeNode, FolderEntry, file content).
3. Navigates to the appropriate route (`/`, `/vault/<path>`, etc.).
4. Asserts against ARIA role/label contracts declared in the spec ACs.
   Selectors use ARIA role, aria-label, or data-testid -- never CSS class,
   never nth-child.

The webApp must be reachable (default `http://localhost:3000` per conftest_pw,
overridable via `WEBAPP_URL`). `pnpm dev` as documented in CLAUDE.md.

==============================================================================
AC -> test function mapping (scope = user-visible ACs only per spec's Playwright table)
==============================================================================

AC-01  test_ac_01_three_pane_layout
AC-06  test_ac_06_file_tree_renders
AC-10  test_ac_10_tree_navigation
AC-12  test_ac_12_today_renders_in_vault
AC-13  test_ac_13_folder_grid
AC-14  test_ac_14_file_preview
AC-19  test_ac_19_chat_scope

Skipped (non-UI or backend-only per spec): AC-02 through AC-05, AC-07
through AC-09, AC-11, AC-15 through AC-18, AC-20 through AC-26.
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

# --- Test constants (mirrors spec payload shapes) -----------------------------

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
            {
                "name": "ideas.md",
                "path": "notes/ideas.md",
                "type": "file",
                "mtime": "2026-04-19T10:00:00Z",
                "size": 256,
            },
        ],
    },
    {
        "name": "contacts",
        "path": "contacts/",
        "type": "folder",
        "mtime": "2026-04-20T19:00:00Z",
        "size": 0,
        "children": [
            {
                "name": "meredith.md",
                "path": "contacts/meredith.md",
                "type": "file",
                "mtime": "2026-04-20T19:02:00Z",
                "size": 128,
            },
        ],
    },
    {
        "name": "_workflows",
        "path": "_workflows/",
        "type": "folder",
        "mtime": "2026-04-18T12:00:00Z",
        "size": 0,
        "children": [
            {
                "name": "weekly-invoice-chase.flow.md",
                "path": "_workflows/weekly-invoice-chase.flow.md",
                "type": "file",
                "mtime": "2026-04-18T12:00:00Z",
                "size": 300,
            },
        ],
    },
]

FOLDER_ENTRIES: list[dict[str, Any]] = [
    {
        "name": "standup.md",
        "path": "notes/standup.md",
        "type": "file",
        "mtime": "2026-04-20T14:00:00Z",
        "size": 512,
    },
    {
        "name": "ideas.md",
        "path": "notes/ideas.md",
        "type": "file",
        "mtime": "2026-04-19T10:00:00Z",
        "size": 256,
    },
]

FILE_CONTENT = {
    "content": "# Standup Notes\n\n- Discussed Q2 priorities\n- Reviewed SPEC-046 progress\n",
    "mtime": "2026-04-20T14:00:00Z",
    "size": 512,
}

# Minimal Today payload for AC-12 (reuse SPEC-045 shape).
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
        "running": [],
        "watching": [],
        "recent": [],
        "blocked": [],
    },
    "approvals": [],
    "recent": [],
    "source_mtime": "2026-04-21T07:00:00Z",
}


def _install_vault_mocks(page: Page) -> None:
    """Install page.route handlers for vault API endpoints."""

    # GET /vault/tree
    def tree_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"tree": VAULT_TREE}),
        )
    page.route(re.compile(r".*/vault/tree(\?.*)?$"), tree_handler)

    # GET /vault/folder
    def folder_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"entries": FOLDER_ENTRIES}),
        )
    page.route(re.compile(r".*/vault/folder(\?.*)?$"), folder_handler)

    # GET /vault/file
    def file_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(FILE_CONTENT),
        )
    page.route(re.compile(r".*/vault/file(\?.*)?$"), file_handler)

    # GET /today (for Today rendering inside vault)
    def today_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(TODAY_PAYLOAD),
        )
    page.route(re.compile(r".*/today(\?.*)?$"), today_handler)

    # GET /approvals/count
    def approvals_count_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"count": 0}),
        )
    page.route(re.compile(r".*/approvals/count(\?.*)?$"), approvals_count_handler)

    # GET /approvals
    def approvals_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"cards": []}),
        )
    page.route(re.compile(r".*/approvals(\?.*)?$"), approvals_handler)

    # GET /workflows/runs
    def runs_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"runs": []}),
        )
    page.route(re.compile(r".*/workflows/runs(\?.*)?$"), runs_handler)

    # GET /today/source
    def source_handler(route):
        route.fulfill(
            status=200,
            content_type="text/markdown",
            body="# Today\n",
        )
    page.route(re.compile(r".*/today/source(\?.*)?$"), source_handler)

    # GET /api/activity/count (for ambient indicator if present)
    def activity_count_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"total": 0, "since_last_viewed": 0}),
        )
    page.route(re.compile(r".*/activity/count(\?.*)?$"), activity_count_handler)


# --- Pytest fixture -----------------------------------------------------------

@pytest.fixture
def authed_page():
    """Yield an authenticated Playwright Page; close browser after."""
    with sync_playwright() as p:
        page, browser = get_authenticated_page(p, headless=True)
        yield page
        browser.close()


# --- Tests --------------------------------------------------------------------

def test_ac_01_three_pane_layout(authed_page):
    """AC-01: AppShell renders three resizable panes -- left (file tree),
    center (content), right (chat rail). Uses react-resizable-panels."""
    page = authed_page
    _install_vault_mocks(page)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Three panes should be visible as panel groups.
    # react-resizable-panels renders with data-panel-id attributes.
    panels = page.locator('[data-panel]')
    assert panels.count() >= 3, (
        f"Expected at least 3 resizable panels, got {panels.count()}"
    )

    # Resize handles should exist between panes.
    handles = page.locator('[data-panel-resize-handle-id]')
    assert handles.count() >= 2, (
        f"Expected at least 2 resize handles, got {handles.count()}"
    )


def test_ac_06_file_tree_renders(authed_page):
    """AC-06: File tree renders the user's vault directory hierarchy.
    Folders expand/collapse. Files show in the tree."""
    page = authed_page
    _install_vault_mocks(page)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # The file tree should be present as a navigation landmark or tree role.
    tree = page.get_by_role("tree")
    expect(tree).to_be_visible()

    # Tree items should include the vault contents from our mock.
    expect(page.get_by_role("treeitem", name=re.compile("today\\.md", re.I))).to_be_visible()
    expect(page.get_by_role("treeitem", name=re.compile("notes", re.I))).to_be_visible()
    expect(page.get_by_role("treeitem", name=re.compile("contacts", re.I))).to_be_visible()


def test_ac_10_tree_navigation(authed_page):
    """AC-10: Clicking a file in the tree navigates to /vault/<path>.
    Clicking today.md navigates to / (or /vault/today.md -- same view)."""
    page = authed_page
    _install_vault_mocks(page)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Expand the notes folder and click on standup.md.
    notes_folder = page.get_by_role("treeitem", name=re.compile("notes", re.I))
    expect(notes_folder).to_be_visible()
    notes_folder.click()
    page.wait_for_timeout(300)

    standup = page.get_by_role("treeitem", name=re.compile("standup\\.md", re.I))
    expect(standup).to_be_visible()
    standup.click()
    page.wait_for_timeout(500)

    # URL should now contain the vault path.
    assert "/vault/notes/standup.md" in page.url, (
        f"Expected URL to contain /vault/notes/standup.md, got {page.url}"
    )


def test_ac_12_today_renders_in_vault(authed_page):
    """AC-12: When path is / or /vault/today.md, renders the existing Today
    page components (all SPEC-045 section components, unchanged)."""
    page = authed_page
    _install_vault_mocks(page)

    # Test root route.
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Today main landmark should be visible.
    expect(page.get_by_role("main", name="Today")).to_be_visible()

    # Key Today sections should render.
    for section_name in ("Your day", "To do", "Agent", "Approvals"):
        expect(
            page.get_by_role("region", name=re.compile(f"^{section_name}$", re.I))
        ).to_be_visible()

    # Also verify /vault/today.md renders the same view.
    page.goto(WEBAPP_URL + "/vault/today.md")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("main", name="Today")).to_be_visible()


def test_ac_13_folder_grid(authed_page):
    """AC-13: When path is /vault/<folder>/, renders a file grid showing
    folder contents: filename, type chip, last modified."""
    page = authed_page
    _install_vault_mocks(page)
    page.goto(WEBAPP_URL + "/vault/notes/")
    page.wait_for_load_state("networkidle")

    # The content area should show the folder grid, not Today.
    # Grid entries should render as list items or grid cells.
    grid = page.get_by_role("grid").or_(page.get_by_role("list", name=re.compile("folder contents", re.I)))
    expect(grid).to_be_visible()

    # Individual file entries should be visible.
    expect(page.get_by_text("standup.md")).to_be_visible()
    expect(page.get_by_text("ideas.md")).to_be_visible()


def test_ac_14_file_preview(authed_page):
    """AC-14: When path is /vault/<file>.md, renders a read-only markdown
    preview using react-markdown + remark-gfm."""
    page = authed_page
    _install_vault_mocks(page)
    page.goto(WEBAPP_URL + "/vault/notes/standup.md")
    page.wait_for_load_state("networkidle")

    # The file preview should render the markdown content.
    # The heading from our mock content should be visible.
    expect(page.get_by_role("heading", name="Standup Notes")).to_be_visible()

    # Content should be rendered as HTML, not raw markdown.
    expect(page.get_by_text("Discussed Q2 priorities")).to_be_visible()
    expect(page.get_by_text("Reviewed SPEC-046 progress")).to_be_visible()


def test_ac_19_chat_scope(authed_page):
    """AC-19: Chat rail shows a scope indicator: 'Today', 'Folder: <name>',
    or 'File: <name>' based on current navigation."""
    page = authed_page
    _install_vault_mocks(page)

    # Navigate to root -- scope should show "Today".
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    chat_rail = page.get_by_role("complementary", name="Chat")
    expect(chat_rail).to_be_visible()

    # Scope indicator should show "Today".
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_be_visible()
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("Today", re.I)
    )

    # Navigate to a folder -- scope should update.
    page.goto(WEBAPP_URL + "/vault/notes/")
    page.wait_for_load_state("networkidle")
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("Folder.*notes", re.I)
    )

    # Navigate to a file -- scope should update.
    page.goto(WEBAPP_URL + "/vault/notes/standup.md")
    page.wait_for_load_state("networkidle")
    scope_indicator = page.locator('[aria-label*="Chat scope"]')
    expect(scope_indicator).to_have_attribute(
        "aria-label", re.compile("File.*standup", re.I)
    )
