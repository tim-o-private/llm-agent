"""
SPEC-045 Today Surface — Playwright UI acceptance tests (RED baseline).

Written BEFORE frontend implementation (FU-3). Every test is expected to FAIL
against the current `main` / `spec/SPEC-045-today` codebase because the Today
surface does not yet exist. Once frontend-dev lands FU-3, all tests must pass —
that is the "done" bar for the frontend branch.

==============================================================================
Fixture pattern
==============================================================================

Each test:
1. Authenticates the dev user via Supabase (see `conftest_pw.get_authenticated_page`).
2. Stubs the backend by intercepting calls with `page.route(...)`. No live
   chatServer/DB dependency — the tests drive the UI off canned JSON that
   mirrors the shapes in SPEC-045 §"Technical Approach" §2 (`TodayResponse`)
   and §3 (`ApprovalCard` tagged union). Network-effect assertions (e.g.
   "approve logs to activity_log but does NOT hit send") are verified by
   watching intercepted requests rather than inspecting the DB.
3. Navigates to `/` (root — AC-01 points the index route at Today).
4. Asserts against ARIA role/label contracts declared in
   `docs/ux/SPEC-045-today-surface-brief.md` §6. NEVER CSS class, NEVER
   nth-child, NEVER data-testid — if a test fails because ARIA is missing,
   that's the frontend-dev contract violation we want to surface.

The webApp must be reachable (default `http://localhost:3000` per conftest_pw,
overridable via `WEBAPP_URL`). `pnpm dev` as documented in CLAUDE.md.

==============================================================================
AC → test function mapping (scope = user-visible ACs only per spec's UI Test column)
==============================================================================

AC-01  test_ac_01_root_route_renders_today
AC-02  test_ac_02_main_landmark_and_heading
AC-03  test_ac_03_seven_sections_in_order
AC-04  test_ac_04_header_framing
AC-05  test_ac_05_your_day_list
AC-06  test_ac_06_todo_checkbox_roundtrip
AC-07  test_ac_07_note_capture_roundtrip           (OQ-3 Textarea: role=textbox + aria-multiline=true)
AC-08  test_ac_08_agent_section_groups
AC-09  test_ac_09_approvals_empty_state
AC-10  test_ac_10_recent_list_renders
AC-11  test_ac_11_source_toggle_roundtrip
AC-12  test_ac_12_all_six_card_shapes_render
AC-13  test_ac_13_approve_logs_no_execute
AC-14  test_ac_14_reject_persists
AC-15  test_ac_15_edit_roundtrip
AC-16  test_ac_16_approvals_badge
AC-17  test_ac_17_regenerate_button_dispatches
AC-20  test_ac_20_today_refetches_on_completion
AC-21  test_ac_21_first_login_populated

Skipped (non-UI per spec): AC-18, AC-19, AC-22, AC-23, AC-24, AC-25, AC-26.
"""

from __future__ import annotations

import json
import re
import threading
from typing import Any

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.uat.playwright.conftest_pw import WEBAPP_URL, get_authenticated_page

# --- Test constants (mirrors spec payload shapes) -----------------------------

TODAY_DATE_ISO = "2026-04-21"

# One card per six shapes for AC-12.
SIX_CARDS: list[dict[str, Any]] = [
    {
        "id": "card-email-01",
        "card_type": "email_draft",
        "title": "Re: Q2 invoicing",
        "payload": {
            "to": ["bob@example.com", "alice@example.com"],
            "subject": "Re: Q2 invoicing",
            "body": "Hi Bob,\n\nAttaching the Q2 invoice for your review.\n\nThanks,\nT",
        },
        "status": "pending",
    },
    {
        "id": "card-cal-01",
        "card_type": "calendar_hold",
        "title": "Deep work — client proposal",
        "payload": {
            "title": "Deep work — client proposal",
            "start_at": "2026-04-22T09:00:00Z",
            "end_at": "2026-04-22T11:00:00Z",
        },
        "status": "pending",
    },
    {
        "id": "card-outreach-01",
        "card_type": "outreach",
        "title": "Ping @meredith re: invoice",
        "payload": {
            "recipient": "@meredith",
            "message": "Hey — quick nudge on the March invoice whenever you have a sec.",
            "channel": "telegram",
        },
        "status": "pending",
    },
    {
        "id": "card-wf-01",
        "card_type": "workflow_proposal",
        "title": "Weekly invoice chase",
        "payload": {
            "filename": "_workflows/weekly-invoice-chase.flow.md",
            "body": "---\nname: weekly-invoice-chase\n---\n## Steps\n...",
            "pattern_observed": "Unpaid invoices tend to need a 7-day nudge.",
        },
        "status": "pending",
    },
    {
        "id": "card-cfg-01",
        "card_type": "config_change",
        "title": "Tighten today-composer prompt",
        "payload": {
            "file_path": "agents/today-composer.md",
            "diff": "@@ -12,3 +12,5 @@\n- You produce a short summary.\n+ You produce a short summary.\n+ Match the user's framing tone.",  # noqa: E501
            "summary": "Add framing-tone guidance to system prompt",
        },
        "status": "pending",
    },
    {
        "id": "card-file-01",
        "card_type": "file_operation",
        "title": "Archive 2023 notes",
        "payload": {
            "operation": "move",
            "source": "_inbox/2023-notes.md",
            "target": "_archive/2023-notes.md",
        },
        "status": "pending",
    },
]


def _today_payload(
    *,
    framing: str | None = "Light day — 2 drafts need a glance.",
    your_day: list[dict] | None = None,
    to_do: list[dict] | None = None,
    notes: list[dict] | None = None,
    approvals: list[dict] | None = None,
    recent: list[dict] | None = None,
) -> dict[str, Any]:
    """Canonical TodayResponse payload — override slices per test."""
    return {
        "date": TODAY_DATE_ISO,
        "header": {"framing": framing},
        "your_day": your_day if your_day is not None else [
            {"text": "10:00 — Standup", "wikilink": "meetings/2026-04-21-standup"},
            {"text": "14:00 — Client review"},
        ],
        "to_do": to_do if to_do is not None else [
            {"line_id": "todo-1", "text": "Ship SPEC-045 brief", "checked": False},
            {"line_id": "todo-2", "text": "Review backend PR", "checked": True},
        ],
        "notes": notes if notes is not None else [],
        "agent": {
            "running": [{"text": "Draft Q2 invoice email", "link": "/workflows/invoice-draft"}],
            "watching": [{"text": "@meredith reply", "link": "/vault/contacts/meredith"}],
            "recent": [{"text": "Completed: morning digest", "link": "/vault/_activity/2026-04-21"}],
            "blocked": [],
        },
        "approvals": approvals if approvals is not None else [],
        "recent": recent if recent is not None else [
            {"path": "notes/2026-04-20.md", "updated_at": "2026-04-21T08:15:00Z"},
            {"path": "contacts/meredith.md", "updated_at": "2026-04-20T19:02:00Z"},
        ],
        "source_mtime": "2026-04-21T07:00:00Z",
    }


def _install_default_mocks(page: Page, *, today: dict[str, Any] | None = None,
                           approvals_count: int = 0,
                           request_log: list[dict] | None = None) -> None:
    """Install default `page.route` handlers for the Today/Approvals API.

    request_log: optional list that captures intercepted requests (method, url, post_data)
    for later network-effect assertions (AC-13, AC-17, AC-20).
    """
    today = today if today is not None else _today_payload()

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
        route.fulfill(status=200, content_type="application/json", body=json.dumps(today))
    page.route(re.compile(r".*/today(\?.*)?$"), today_handler)

    # GET /today/source
    def source_handler(route):
        _log(route)
        raw = (
            "# Today — 2026-04-21\n\n"
            "## Header\nLight day — 2 drafts need a glance.\n\n"
            "## Your day\n- 10:00 — Standup [[meetings/2026-04-21-standup]]\n\n"
            "## To do\n- [ ] Ship SPEC-045 brief\n- [x] Review backend PR\n\n"
            "## Notes\n\n"
            "## Agent\n### Running\n- Draft Q2 invoice email\n\n"
            "## Approvals\n\n"
            "## Recent\n"
        )
        route.fulfill(status=200, content_type="text/markdown", body=raw)
    page.route(re.compile(r".*/today/source(\?.*)?$"), source_handler)

    # POST /today/notes
    def notes_handler(route):
        _log(route)
        post = route.request.post_data_json or {}
        saved = {"created_at": "2026-04-21T09:14:00Z", "text": post.get("text", "")}
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(saved))
    page.route(re.compile(r".*/today/notes$"), notes_handler)

    # POST /today/todo/toggle
    def todo_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True}))
    page.route(re.compile(r".*/today/todo/toggle$"), todo_handler)

    # POST /today/regenerate
    def regen_handler(route):
        _log(route)
        route.fulfill(status=202, content_type="application/json",
                      body=json.dumps({"run_id": "run-regen-001"}))
    page.route(re.compile(r".*/today/regenerate$"), regen_handler)

    # GET /approvals/count
    def count_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"count": approvals_count}))
    page.route(re.compile(r".*/approvals/count(\?.*)?$"), count_handler)

    # GET /approvals
    def approvals_list_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"cards": today["approvals"]}))
    page.route(re.compile(r".*/approvals(\?.*)?$"), approvals_list_handler)

    # POST /approvals/{id}/approve|reject|edit
    def approvals_mutate_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"ok": True}))
    page.route(re.compile(r".*/approvals/[^/]+/(approve|reject|edit)$"),
               approvals_mutate_handler)

    # GET /workflows/runs?template_name=regenerate-today&limit=1
    def runs_handler(route):
        _log(route)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"runs": []}))
    page.route(re.compile(r".*/workflows/runs(\?.*)?$"), runs_handler)


# --- Pytest fixture -----------------------------------------------------------

@pytest.fixture
def authed_page():
    """Yield an authenticated Playwright Page + request log; close browser after."""
    with sync_playwright() as p:
        page, browser = get_authenticated_page(p, headless=True)
        request_log: list[dict] = []
        yield page, request_log
        browser.close()


# --- Tests --------------------------------------------------------------------

def test_ac_01_root_route_renders_today(authed_page):
    """AC-01: Visiting `/` (root, authenticated) renders the Today surface."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    # AC-01: URL stays at root, main landmark labelled "Today" is present.
    assert page.url.rstrip("/") == WEBAPP_URL.rstrip("/"), (
        f"Expected root URL, got {page.url}"
    )
    expect(page.get_by_role("main", name="Today")).to_be_visible()


def test_ac_02_main_landmark_and_heading(authed_page):
    """AC-02: <main aria-label="Today"> + <h1> containing today's locale date."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    main = page.get_by_role("main", name="Today")
    expect(main).to_be_visible()
    h1 = main.get_by_role("heading", level=1).first
    expect(h1).to_be_visible()
    h1_text = h1.inner_text()
    # Accept any locale rendering of 2026-04-21 that contains the year + month name or numeric.
    assert "2026" in h1_text, f"h1 missing year: {h1_text!r}"
    assert ("April" in h1_text or "Apr" in h1_text or "04" in h1_text), (
        f"h1 missing month: {h1_text!r}"
    )


def test_ac_03_seven_sections_in_order(authed_page):
    """AC-03: Seven labelled sections in order, all visible (empties do not disappear)."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(
                               framing=None, your_day=[], to_do=[], notes=[],
                               approvals=[], recent=[]))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    expected = ["Your day", "To do", "Notes", "Agent", "Approvals", "Recent"]
    main = page.get_by_role("main", name="Today")
    # Collect section headings in DOM order; Header uses the page h1 (no h2 per brief §6).
    section_headings = main.locator('section >> role=heading[level=2]')
    count = section_headings.count()
    assert count == len(expected), (
        f"Expected {len(expected)} section <h2>s, got {count}"
    )
    for i, name in enumerate(expected):
        assert section_headings.nth(i).inner_text().strip() == name, (
            f"Section {i} heading mismatch: got {section_headings.nth(i).inner_text()!r}, "
            f"expected {name!r}"
        )


def test_ac_04_header_framing(authed_page):
    """AC-04: Header shows date + framing sentence; empty state when framing=None."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(framing="Light day — 2 drafts need a glance."))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Light day — 2 drafts need a glance.")).to_be_visible()

    # Empty-state branch: reload with framing=None.
    page2, _log2 = authed_page  # same fixture, but we want a fresh nav — reuse page.
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(framing=None))
    page.goto(WEBAPP_URL + "/?reload=1")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text(re.compile(r"No framing yet", re.I))).to_be_visible()


def test_ac_05_your_day_list(authed_page):
    """AC-05: Your day renders one <li> per item, wikilinks as links."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(your_day=[
                               {"text": "10:00 — Standup",
                                "wikilink": "meetings/2026-04-21-standup"},
                               {"text": "14:00 — Client review"},
                           ]))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    section = page.get_by_role("region", name=re.compile("Your day", re.I))
    items = section.get_by_role("listitem")
    assert items.count() == 2, f"Expected 2 your_day items, got {items.count()}"
    expect(items.nth(0)).to_contain_text("Standup")
    expect(section.get_by_role("link", name=re.compile("standup", re.I))).to_be_visible()


def test_ac_06_todo_checkbox_roundtrip(authed_page):
    """AC-06: Todo checkboxes render with aria-label=item text; toggling fires API."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(to_do=[
                               {"line_id": "todo-1", "text": "Ship SPEC-045 brief",
                                "checked": False},
                               {"line_id": "todo-2", "text": "Review backend PR",
                                "checked": True},
                           ]))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    unchecked = page.get_by_role("checkbox", name="Ship SPEC-045 brief")
    checked = page.get_by_role("checkbox", name="Review backend PR")
    expect(unchecked).to_be_visible()
    expect(unchecked).not_to_be_checked()
    expect(checked).to_be_checked()

    unchecked.click()
    page.wait_for_timeout(500)
    # Round-trip: expect a POST to /today/todo/toggle.
    assert any(e["method"] == "POST" and e["url"].endswith("/today/todo/toggle")
               for e in log), f"No toggle POST seen. Log: {log!r}"


def test_ac_07_note_capture_roundtrip(authed_page):
    """AC-07: Multi-line Textarea (OQ-3) with role=textbox + aria-multiline=true;
    submit via Cmd/Ctrl+Enter posts to /today/notes; input clears on success."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    textbox = page.get_by_role("textbox", name="Capture a note")
    expect(textbox).to_be_visible()

    # OQ-3 contract: native <textarea> → role="textbox" + aria-multiline="true".
    aria_multiline = textbox.get_attribute("aria-multiline")
    tag = textbox.evaluate("el => el.tagName.toLowerCase()")
    assert aria_multiline == "true" or tag == "textarea", (
        f"Note capture must be multi-line (OQ-3). tag={tag!r} aria-multiline={aria_multiline!r}"
    )

    textbox.click()
    textbox.fill("Think about the onboarding copy —\nthe vault metaphor is fuzzy.")
    # Submit via Save button (also valid per brief §2 Notes).
    save_btn = page.get_by_role("button", name="Save note")
    expect(save_btn).to_be_visible()
    save_btn.click()
    page.wait_for_timeout(500)

    assert any(e["method"] == "POST" and e["url"].endswith("/today/notes")
               for e in log), f"No notes POST seen. Log: {log!r}"
    # Optimistic clear on success.
    expect(textbox).to_have_value("")


def test_ac_08_agent_section_groups(authed_page):
    """AC-08: Four sub-groups (running/watching/recent/blocked), each role=group."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    agent = page.get_by_role("region", name=re.compile("^Agent$", re.I))
    expect(agent).to_be_visible()
    # Per brief §6: each sub-group is role="group" with an h3 label.
    for label in ("Running", "Watching", "Recent", "Blocked"):
        expect(agent.get_by_role("group", name=re.compile(label, re.I))).to_be_visible()


def test_ac_09_approvals_empty_state(authed_page):
    """AC-09: Approvals section renders empty-state text when no cards."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(approvals=[]))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    approvals = page.get_by_role("region", name=re.compile("^Approvals$", re.I))
    expect(approvals).to_be_visible()
    expect(approvals.get_by_text(re.compile(r"Nothing awaiting approval", re.I))).to_be_visible()


def test_ac_10_recent_list_renders(authed_page):
    """AC-10: Recent section shows a list of recently-touched files."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(recent=[
                               {"path": "notes/2026-04-20.md",
                                "updated_at": "2026-04-21T08:15:00Z"},
                               {"path": "contacts/meredith.md",
                                "updated_at": "2026-04-20T19:02:00Z"},
                           ]))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    recent = page.get_by_role("region", name=re.compile("^Recent$", re.I))
    expect(recent).to_be_visible()
    # Brief §6: <ul aria-label="Recently touched files"> with <li><a>+<time>.
    ul = page.get_by_role("list", name=re.compile("Recently touched files", re.I))
    expect(ul).to_be_visible()
    items = ul.get_by_role("listitem")
    assert items.count() == 2, f"Expected 2 recent items, got {items.count()}"
    expect(recent.get_by_role("link", name=re.compile(r"2026-04-20\.md"))).to_be_visible()


def test_ac_11_source_toggle_roundtrip(authed_page):
    """AC-11: View-source toggle swaps to markdown block and back."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    toggle = page.get_by_role("button", name="View source")
    expect(toggle).to_be_visible()
    toggle.click()
    page.wait_for_timeout(300)

    source_block = page.get_by_role("region", name="Today source (markdown)")
    expect(source_block).to_be_visible()
    expect(source_block).to_contain_text("## Your day")

    # Rendered sections should be hidden in source mode.
    expect(page.get_by_role("region", name=re.compile("^Your day$", re.I))).to_have_count(0)

    # Toggle back.
    toggle_back = page.get_by_role("button", name="View rendered")
    expect(toggle_back).to_be_visible()
    toggle_back.click()
    page.wait_for_timeout(300)
    expect(page.get_by_role("region", name=re.compile("^Your day$", re.I))).to_be_visible()


def test_ac_12_all_six_card_shapes_render(authed_page):
    """AC-12: All six approval card shapes render as role=region with correct aria-label prefix."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(approvals=SIX_CARDS))
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    # Brief §6: each card is role="region" aria-label="<Type label> approval: <title>".
    type_labels = [
        ("Email draft", "Re: Q2 invoicing"),
        ("Calendar hold", "Deep work — client proposal"),
        ("Outreach", "Ping @meredith re: invoice"),
        ("Workflow proposal", "Weekly invoice chase"),
        ("Config change", "Tighten today-composer prompt"),
        ("File operation", "Archive 2023 notes"),
    ]
    for type_label, title in type_labels:
        locator = page.get_by_role(
            "region",
            name=re.compile(rf"{re.escape(type_label)} approval: {re.escape(title)}", re.I),
        )
        expect(locator).to_be_visible()

    # Per-shape primary action naming (brief §3).
    expect(page.get_by_role("button", name="Send").first).to_be_visible()      # email_draft / outreach
    expect(page.get_by_role("button", name="Confirm").first).to_be_visible()   # calendar_hold
    expect(page.get_by_role("button", name="Accept").first).to_be_visible()    # workflow_proposal
    expect(page.get_by_role("button", name="Approve").first).to_be_visible()   # config_change / file_operation


def test_ac_13_approve_logs_no_execute(authed_page):
    """AC-13: Approve hits /approvals/{id}/approve; no outbound effect endpoint is called."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(approvals=[SIX_CARDS[0]]))  # email_draft
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    card = page.get_by_role("region", name=re.compile("Email draft approval", re.I))
    expect(card).to_be_visible()
    card.get_by_role("button", name="Send").click()
    page.wait_for_timeout(500)

    approve_calls = [e for e in log
                     if e["method"] == "POST"
                     and re.search(r"/approvals/card-email-01/approve$", e["url"])]
    assert approve_calls, f"No approve POST seen. Log: {log!r}"

    forbidden = [e for e in log
                 if any(term in e["url"] for term in
                        ("/gmail/send", "/email/send", "/calendar/events"))]
    assert not forbidden, f"Outbound effect leaked. Forbidden calls: {forbidden!r}"


def test_ac_14_reject_persists(authed_page):
    """AC-14: Reject on any card hits /approvals/{id}/reject with optional reason."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(approvals=[SIX_CARDS[1]]))  # calendar_hold
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    card = page.get_by_role("region", name=re.compile("Calendar hold approval", re.I))
    card.get_by_role("button", name="Reject").click()
    page.wait_for_timeout(200)

    # Brief §3 "Reject-with-reason pattern": Input + Confirm reject.
    reason_input = card.get_by_role("textbox", name=re.compile("reason", re.I))
    expect(reason_input).to_be_visible()
    reason_input.fill("Time conflict")
    card.get_by_role("button", name=re.compile("Confirm reject", re.I)).click()
    page.wait_for_timeout(500)

    reject_calls = [e for e in log
                    if e["method"] == "POST"
                    and re.search(r"/approvals/card-cal-01/reject$", e["url"])]
    assert reject_calls, f"No reject POST seen. Log: {log!r}"
    assert any("Time conflict" in (e.get("post_data") or "") for e in reject_calls), (
        f"Reject reason not forwarded. Calls: {reject_calls!r}"
    )


def test_ac_15_edit_roundtrip(authed_page):
    """AC-15: Edit opens inline editor; Save hits /approvals/{id}/edit with updated payload."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log,
                           today=_today_payload(approvals=[SIX_CARDS[0]]))  # email_draft
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    card = page.get_by_role("region", name=re.compile("Email draft approval", re.I))
    card.get_by_role("button", name="Edit").click()
    page.wait_for_timeout(200)

    subject_input = card.get_by_role("textbox", name=re.compile("subject", re.I))
    expect(subject_input).to_be_visible()
    subject_input.fill("Re: Q2 invoicing (updated)")
    card.get_by_role("button", name=re.compile(r"^Save$", re.I)).click()
    page.wait_for_timeout(500)

    edit_calls = [e for e in log
                  if e["method"] == "POST"
                  and re.search(r"/approvals/card-email-01/edit$", e["url"])]
    assert edit_calls, f"No edit POST seen. Log: {log!r}"
    assert any("(updated)" in (e.get("post_data") or "") for e in edit_calls), (
        f"Edited subject not in payload. Calls: {edit_calls!r}"
    )


def test_ac_16_approvals_badge(authed_page):
    """AC-16: TopBar badge reflects count. count=0 → reduced-opacity, aria-label="No pending approvals".
       count>0 → full badge with count in aria-label. Clicking scrolls approvals into view."""
    page, log = authed_page

    # Case 1: count=0.
    _install_default_mocks(page, request_log=log, approvals_count=0)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    zero_badge = page.get_by_role("button", name="No pending approvals")
    expect(zero_badge).to_be_visible()
    opacity = zero_badge.evaluate(
        "el => parseFloat(getComputedStyle(el).opacity)"
    )
    assert opacity < 1.0, f"count=0 badge should be reduced opacity, got {opacity}"

    # Case 2: count=3, click scrolls Approvals into view.
    _install_default_mocks(page, request_log=log, approvals_count=3,
                           today=_today_payload(approvals=SIX_CARDS[:3]))
    page.goto(WEBAPP_URL + "/?count=3")
    page.wait_for_load_state("networkidle")
    badge = page.get_by_role("button", name="3 pending approvals")
    expect(badge).to_be_visible()
    badge.click()
    page.wait_for_timeout(400)
    # Per brief §1: click sets URL hash to #today-approvals.
    assert "today-approvals" in page.url, (
        f"Expected #today-approvals in URL after badge click, got {page.url!r}"
    )


def test_ac_17_regenerate_button_dispatches(authed_page):
    """AC-17: Regenerate Today calls POST /today/regenerate and receives 202 + run_id."""
    page, log = authed_page
    _install_default_mocks(page, request_log=log)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    btn = page.get_by_role("button", name="Regenerate Today")
    expect(btn).to_be_visible()
    btn.click()
    page.wait_for_timeout(500)

    regen_calls = [e for e in log
                   if e["method"] == "POST" and e["url"].endswith("/today/regenerate")]
    assert regen_calls, f"No regenerate POST seen. Log: {log!r}"


def test_ac_20_today_refetches_on_completion(authed_page):
    """AC-20: When /workflows/runs reports a newer completed run, the UI refetches /today."""
    page, log = authed_page
    state = {"completed": False, "today_calls": 0}
    lock = threading.Lock()

    def today_route(route):
        with lock:
            state["today_calls"] += 1
            framing = ("Fresh framing after regen."
                       if state["completed"] else "Initial framing.")
        body = _today_payload(framing=framing)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(body))

    def runs_route(route):
        with lock:
            runs = ([{"run_id": "run-regen-001",
                      "template_name": "regenerate-today",
                      "status": "completed",
                      "completed_at": "2026-04-21T09:30:00Z"}]
                    if state["completed"] else [])
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"runs": runs}))

    # Install default stubs FIRST so later-registered overrides win
    # (Playwright resolves conflicting page.route handlers LIFO).
    _install_default_mocks(page, request_log=log)
    page.route(re.compile(r".*/today(\?.*)?$"), today_route)
    page.route(re.compile(r".*/workflows/runs(\?.*)?$"), runs_route)

    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_text("Initial framing.")).to_be_visible()

    initial_calls = state["today_calls"]
    with lock:
        state["completed"] = True

    # UI polls workflow_runs at 30s; in tests we wait up to 45s for the refetch + render.
    page.wait_for_function(
        "() => document.body.innerText.includes('Fresh framing after regen.')",
        timeout=45_000,
    )
    assert state["today_calls"] > initial_calls, (
        f"Today was not refetched. calls={state['today_calls']}, initial={initial_calls}"
    )


def test_ac_21_first_login_populated(authed_page):
    """AC-21: First login (no today.md) still renders a populated seven-section page."""
    page, log = authed_page
    # Backend seeds from template → first GET /today still returns a TodayResponse with
    # all seven sections populated with empty-state content. UI must render all seven.
    seeded = _today_payload(
        framing=None,
        your_day=[],
        to_do=[],
        notes=[],
        approvals=[],
        recent=[],
    )
    _install_default_mocks(page, request_log=log, today=seeded)
    page.goto(WEBAPP_URL + "/")
    page.wait_for_load_state("networkidle")

    expect(page.get_by_role("main", name="Today")).to_be_visible()
    for name in ("Your day", "To do", "Notes", "Agent", "Approvals", "Recent"):
        expect(page.get_by_role("region", name=re.compile(f"^{name}$", re.I))).to_be_visible()
    # Sanity: at least one empty-state string appears (brief §2 table).
    expect(page.get_by_text(
        re.compile(r"(No framing yet|Nothing on your calendar|No to-dos|"
                   r"No notes yet|Nothing awaiting approval|No recent activity)", re.I)
    ).first).to_be_visible()
