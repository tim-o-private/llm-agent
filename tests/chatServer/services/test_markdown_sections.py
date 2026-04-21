"""Unit tests for the markdown_sections parser + patcher."""

from __future__ import annotations

import pytest

from chatServer.services import markdown_sections as md


SEED = """# Today

## Header

No framing yet — run today's briefing.

## Your day

- Meet Alice at 10
- Ship [[specs/SPEC-045-today-surface]]

## To do

- [ ] Tidy the inbox
- [x] Stretch

## Notes

- [2026-04-20T14:00:00Z] thought one

## Agent

Nothing running, watching, or blocked right now.

## Approvals

Nothing awaiting approval.

## Recent

No recent activity.
"""


def test_parse_roundtrip_is_idempotent():
    doc = md.parse(SEED)
    rendered = md.render(doc)
    assert rendered == SEED


def test_parse_recognizes_all_seven_sections():
    doc = md.parse(SEED)
    keys = [s.key for s in doc.sections]
    assert keys == [
        "header",
        "your day",
        "to do",
        "notes",
        "agent",
        "approvals",
        "recent",
    ]


def test_parse_preserves_unknown_sections():
    body = SEED + "\n## Custom\n\nHello.\n"
    doc = md.parse(body)
    keys = [s.key for s in doc.sections]
    assert keys[-1] == "custom"
    # Still round-trips.
    assert md.render(doc) == body


def test_parse_no_h2_puts_body_in_prologue():
    body = "Just a free-form paragraph.\n"
    doc = md.parse(body)
    assert doc.prologue == body
    assert doc.sections == []


def test_empty_body_returns_empty_doc():
    doc = md.parse("")
    assert doc.prologue == ""
    assert doc.sections == []


def test_patch_section_replaces_body_only():
    patched = md.patch_section(SEED, "Header", "A new framing line.\n")
    doc = md.parse(patched)
    assert doc.get("header").body.strip() == "A new framing line."
    # Other sections untouched.
    assert doc.get("your day").body.strip().startswith("- Meet Alice at 10")


def test_patch_section_creates_missing():
    stripped = md.parse(SEED)
    stripped.sections = [s for s in stripped.sections if s.key != "recent"]
    body = md.render(stripped)
    assert "Recent" not in body.split("## ")[1:][-1].split("\n")[0]

    patched = md.patch_section(body, "Recent", "Hello\n")
    assert md.parse(patched).get("recent").body.strip() == "Hello"


def test_append_to_section_replaces_empty_state():
    """An empty-state line should be replaced, not appended to."""
    new = md.append_to_section(
        SEED,
        "Recent",
        "- [2026-04-20T15:00:00Z] thing",
    )
    doc = md.parse(new)
    body = doc.get("recent").body
    assert "No recent activity" not in body
    assert "- [2026-04-20T15:00:00Z] thing" in body


def test_append_to_section_appends_to_existing():
    new = md.append_to_section(
        SEED,
        "Notes",
        "- [2026-04-20T15:00:00Z] thought two",
    )
    notes = md.parse(new).get("notes").body
    assert "thought one" in notes
    assert "thought two" in notes
    assert notes.index("thought one") < notes.index("thought two")


def test_extract_todos():
    todos = md.extract_todos(SEED)
    assert len(todos) == 2
    assert todos[0]["text"] == "Tidy the inbox"
    assert todos[0]["checked"] is False
    assert todos[1]["text"] == "Stretch"
    assert todos[1]["checked"] is True
    # line_ids are stable and distinct.
    assert todos[0]["line_id"] != todos[1]["line_id"]
    todos2 = md.extract_todos(SEED)
    assert [t["line_id"] for t in todos] == [t["line_id"] for t in todos2]


def test_replace_todo_line_flips_check():
    todos = md.extract_todos(SEED)
    first_id = todos[0]["line_id"]

    new_body, found = md.replace_todo_line(SEED, first_id, checked=True)
    assert found is True
    flipped = md.extract_todos(new_body)
    assert flipped[0]["checked"] is True
    assert flipped[0]["line_id"] == first_id  # id stable across check flip
    # Other todo untouched.
    assert flipped[1]["checked"] is True
    assert flipped[1]["text"] == "Stretch"


def test_replace_todo_line_unknown_id_returns_false():
    new_body, found = md.replace_todo_line(SEED, "deadbeef00000000", checked=True)
    assert found is False
    assert new_body == SEED


def test_extract_notes():
    notes = md.extract_notes(SEED)
    assert notes == [
        {"created_at": "2026-04-20T14:00:00Z", "text": "thought one"}
    ]


def test_extract_your_day_with_wikilink():
    items = md.extract_your_day(SEED)
    assert items[0] == {"text": "Meet Alice at 10", "wikilink": None}
    assert items[1]["wikilink"] == "specs/SPEC-045-today-surface"


def test_extract_framing_empty_state_returns_none():
    assert md.extract_framing(SEED) is None


def test_extract_framing_returns_first_nonempty():
    body = "## Header\n\nToday is a good day.\n"
    assert md.extract_framing(body) == "Today is a good day."


def test_section_lookup_is_case_insensitive():
    doc = md.parse(SEED)
    assert doc.get("HEADER") is not None
    assert doc.get("header").key == "header"


def test_compute_todo_line_id_is_deterministic():
    a = md.compute_todo_line_id("to do", 0, "  Tidy the inbox  ")
    b = md.compute_todo_line_id("to do", 0, "Tidy the inbox")
    assert a == b  # whitespace doesn't matter
