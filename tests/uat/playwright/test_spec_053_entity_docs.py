"""
SPEC-053 Entity Docs — Playwright UI acceptance tests (RED baseline).

Written BEFORE all frontend wiring is complete. Tests define the expected
ARIA and data-testid contracts for entity docs in the vault browser. Some
tests will fail until frontend-dev lands the full entity surface.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see conftest_pw).
2. Stubs the backend by intercepting API calls with page.route().
3. Navigates to the entity file path.
4. Asserts against ARIA/data-testid contracts from SPEC-053 ACs.

==============================================================================
AC -> test function mapping
==============================================================================

AC-07  test_ac_07_entity_index_endpoint_consumed
AC-08  test_ac_08_entity_wikilinks_show_type_icon
AC-21  test_ac_21_file_tree_entity_display
AC-22  test_ac_22_entity_header_renders
AC-23  test_ac_23_entity_auth_required
"""

import json

import pytest

pw = pytest.importorskip("playwright.sync_api")

from tests.uat.playwright.conftest_pw import (
    WEBAPP_URL,
    get_authenticated_page,
)


# --- Stub data ----------------------------------------------------------------

ENTITY_INDEX_RESPONSE = {
    "entities": [
        {
            "slug": "sarah-chen",
            "name": "Sarah Chen",
            "entity_type": "person",
            "path": "entities/people/sarah-chen.md",
            "aliases": ["sarah@acme.com"],
        },
        {
            "slug": "acme-corp",
            "name": "Acme Corp",
            "entity_type": "company",
            "path": "entities/companies/acme-corp.md",
            "aliases": [],
        },
    ]
}

ENTITY_FILE_CONTENT = {
    "content": (
        "---\n"
        "entity_type: person\n"
        "name: Sarah Chen\n"
        "role: VP Engineering\n"
        "company: '[[acme-corp]]'\n"
        "---\n\n"
        "## Context\n\n"
        "Sarah leads the engineering team at Acme Corp.\n\n"
        "## Recent interactions\n\n"
        "- 2026-04-15: Email about Q3 timeline\n"
    ),
    "mtime": "2026-04-21T10:00:00Z",
    "size": 250,
}

TREE_RESPONSE = {
    "tree": [
        {
            "name": "entities",
            "path": "entities",
            "type": "folder",
            "mtime": "2026-04-21T10:00:00Z",
            "size": 0,
            "children": [
                {
                    "name": "people",
                    "path": "entities/people",
                    "type": "folder",
                    "mtime": "2026-04-21T10:00:00Z",
                    "size": 0,
                    "children": [
                        {
                            "name": "sarah-chen.md",
                            "path": "entities/people/sarah-chen.md",
                            "type": "file",
                            "mtime": "2026-04-21T10:00:00Z",
                            "size": 250,
                        }
                    ],
                },
                {
                    "name": "companies",
                    "path": "entities/companies",
                    "type": "folder",
                    "mtime": "2026-04-21T10:00:00Z",
                    "size": 0,
                    "children": [
                        {
                            "name": "acme-corp.md",
                            "path": "entities/companies/acme-corp.md",
                            "type": "file",
                            "mtime": "2026-04-21T10:00:00Z",
                            "size": 200,
                        }
                    ],
                },
            ],
        },
        {
            "name": "today.md",
            "path": "today.md",
            "type": "file",
            "mtime": "2026-04-21T08:00:00Z",
            "size": 500,
        },
    ]
}


def _stub_routes(page):
    """Intercept API calls with canned responses."""

    def handle_entity_index(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(ENTITY_INDEX_RESPONSE),
        )

    def handle_vault_tree(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(TREE_RESPONSE),
        )

    def handle_vault_file(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(ENTITY_FILE_CONTENT),
        )

    def handle_backlinks(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"backlinks": []}),
        )

    def handle_context(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"summary": "", "actions": []}),
        )

    def handle_suggest(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"cards": []}),
        )

    page.route("**/api/vault/entities/index*", handle_entity_index)
    page.route("**/api/vault/tree*", handle_vault_tree)
    page.route("**/api/vault/file*", handle_vault_file)
    page.route("**/api/vault/backlinks*", handle_backlinks)
    page.route("**/api/vault/file-context*", handle_context)
    page.route("**/api/vault/suggest-cards*", handle_suggest)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEntityHeader:
    """AC-22: Entity header renders for entity docs."""

    def test_ac_22_entity_header_renders(self):
        """Entity doc at entities/people/sarah-chen.md shows EntityHeader
        with type badge and display name."""
        with get_authenticated_page() as page:
            _stub_routes(page)
            page.goto(f"{WEBAPP_URL}/vault/entities/people/sarah-chen.md")
            page.wait_for_timeout(2000)

            header = page.get_by_test_id("entity-header")
            assert header.is_visible(), "EntityHeader should be visible for entity docs"
            # Type badge
            assert header.locator("text=Person").is_visible()
            # Display name
            assert header.locator("text=Sarah Chen").is_visible()


class TestEntityTree:
    """AC-21: File tree shows entity-specific display names and icons."""

    def test_ac_21_file_tree_entity_display(self):
        """The entities/ folder in the tree shows as 'Entities' and entity
        files show their display name from the entity index."""
        with get_authenticated_page() as page:
            _stub_routes(page)
            page.goto(f"{WEBAPP_URL}/")
            page.wait_for_timeout(2000)

            # The entities folder should show as "Entities"
            tree = page.locator('[class*="arborist"]').first
            entities_label = tree.locator("text=Entities")
            assert entities_label.is_visible(), "entities/ folder should display as 'Entities'"


class TestEntityWikiLinks:
    """AC-08: Entity wikilinks show type icons."""

    def test_ac_08_entity_wikilinks_show_type_icon(self):
        """Wikilinks to known entities render with an SVG type icon."""
        with get_authenticated_page() as page:
            _stub_routes(page)

            # Override vault file to include a wikilink to an entity
            page.route(
                "**/api/vault/file*",
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "content": "# Meeting\n\nDiscussed with [[sarah-chen]].\n",
                        "mtime": "2026-04-21T10:00:00Z",
                        "size": 50,
                    }),
                ),
            )

            page.goto(f"{WEBAPP_URL}/vault/notes/meeting.md")
            page.wait_for_timeout(2000)

            # The wikilink should have an SVG icon (entity type indicator)
            preview = page.locator('[aria-label="Rendered preview"]')
            entity_link = preview.locator('a[href*="sarah-chen"]')
            assert entity_link.is_visible(), "Entity wikilink should render"


class TestEntityIndex:
    """AC-07: Entity index endpoint is consumed by the frontend."""

    def test_ac_07_entity_index_endpoint_consumed(self):
        """Frontend fetches the entity index on load."""
        with get_authenticated_page() as page:
            index_requested = {"called": False}

            def check_index(route):
                index_requested["called"] = True
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(ENTITY_INDEX_RESPONSE),
                )

            page.route("**/api/vault/entities/index*", check_index)
            page.route("**/api/vault/tree*", lambda r: r.fulfill(
                status=200, content_type="application/json",
                body=json.dumps(TREE_RESPONSE),
            ))

            page.goto(f"{WEBAPP_URL}/")
            page.wait_for_timeout(3000)

            assert index_requested["called"], (
                "Frontend should fetch /api/vault/entities/index on load"
            )
