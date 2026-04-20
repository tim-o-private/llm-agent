"""Pure parser + patcher for Today-style markdown with H2 section headings.

The parser splits a body on ``## <name>`` boundaries. It preserves unknown
sections and the body order, and the round-trip is idempotent.

Used by ``today_service`` to read and mutate ``today.md`` without mangling
sections it doesn't understand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Known H2 section names (lower-cased, spaces collapsed). Any section outside
# this set is still preserved — we never delete content.
KNOWN_SECTIONS: tuple[str, ...] = (
    "header",
    "your day",
    "to do",
    "notes",
    "agent",
    "approvals",
    "recent",
)

_SECTION_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*\n", re.MULTILINE)


@dataclass
class Section:
    """A single H2 section.

    ``name`` is the display-cased heading from the markdown (``"Your day"``).
    ``key`` is the normalized lookup key (``"your day"``).
    ``body`` is everything between this heading and the next H2 (or EOF),
    without surrounding newlines trimmed — we keep the raw interstitial so
    round-trips are byte-idempotent.
    """

    name: str
    key: str
    body: str


@dataclass
class ParsedDocument:
    """The parsed form of a markdown doc.

    ``prologue`` is whatever sits before the first H2 (e.g. an H1 title).
    ``sections`` is the ordered list of sections as they appeared.
    """

    prologue: str = ""
    sections: list[Section] = field(default_factory=list)

    def get(self, key: str) -> Optional[Section]:
        key_norm = _normalize_key(key)
        for sec in self.sections:
            if sec.key == key_norm:
                return sec
        return None

    def has(self, key: str) -> bool:
        return self.get(key) is not None


def _normalize_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def parse(body: str) -> ParsedDocument:
    """Parse a markdown body into a ParsedDocument.

    Headings are identified by ``## <name>`` at line start. Content before
    the first H2 becomes ``prologue``. Unknown sections are preserved.
    """
    if not body:
        return ParsedDocument(prologue="", sections=[])

    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        return ParsedDocument(prologue=body, sections=[])

    prologue = body[: matches[0].start()]
    sections: list[Section] = []
    for idx, match in enumerate(matches):
        name = match.group(1).strip()
        key = _normalize_key(name)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        # ``body`` preserves the full interstitial exactly as it appeared in
        # source, including the newline that terminates the heading line and
        # any blank lines before the next heading.
        sections.append(Section(name=name, key=key, body=body[start:end]))
    return ParsedDocument(prologue=prologue, sections=sections)


def render(doc: ParsedDocument) -> str:
    """Render a parsed document back to markdown.

    Idempotent with ``parse``: ``render(parse(x)) == x`` for any well-formed
    input (modulo the leading-newline normalization inside sections).
    """
    out: list[str] = []
    if doc.prologue:
        out.append(doc.prologue)
    for sec in doc.sections:
        out.append(f"## {sec.name}\n")
        out.append(sec.body)
    return "".join(out)


def patch_section(body: str, section_name: str, new_body: str) -> str:
    """Replace the body of ``section_name`` (case-insensitive).

    If the section doesn't exist, append it at the end with the given name.
    Other sections are left untouched.
    """
    doc = parse(body)
    formatted = _format_section_body(new_body)
    existing = doc.get(section_name)
    if existing:
        existing.body = formatted
    else:
        doc.sections.append(
            Section(
                name=section_name,
                key=_normalize_key(section_name),
                body=formatted,
            )
        )
    return render(doc)


def append_to_section(body: str, section_name: str, line: str) -> str:
    """Append a line to the named section. Creates the section if absent."""
    doc = parse(body)
    existing = doc.get(section_name)
    stripped_line = line.rstrip("\n")
    if existing:
        current = _extract_section_content(existing.body)
        # If the section only contains empty-state prose, replace it wholesale.
        if _looks_like_empty_state(current.strip()):
            existing.body = _format_section_body(stripped_line)
        else:
            new_content = (current.rstrip("\n") + "\n" + stripped_line) if current.strip() else stripped_line
            existing.body = _format_section_body(new_content)
    else:
        doc.sections.append(
            Section(
                name=section_name,
                key=_normalize_key(section_name),
                body=_format_section_body(stripped_line),
            )
        )
    return render(doc)


def _format_section_body(content: str) -> str:
    """Normalize a raw section-body string into the on-wire format.

    On-wire format: ``"\\n<content>\\n\\n"`` so that rendering looks like::

        ## Name
        <blank line>
        <content>
        <blank line>
        ## Next
    """
    inner = content.strip("\n")
    if inner == "":
        return "\n\n"
    return f"\n{inner}\n\n"


def _extract_section_content(raw_body: str) -> str:
    """Return the inner content of a section body, stripping the surrounding
    blank lines added by ``_format_section_body``."""
    return raw_body.strip("\n")


def replace_todo_line(body: str, line_id: str, *, checked: bool) -> tuple[str, bool]:
    """Find the todo in the ``To do`` section whose stable id matches
    ``line_id`` and flip its checked state.

    Returns ``(new_body, found)``.
    """
    doc = parse(body)
    sec = doc.get("to do")
    if not sec:
        return body, False
    lines = sec.body.split("\n")
    changed = False
    for idx, line in enumerate(lines):
        m = _TODO_RE.match(line)
        if not m:
            continue
        text = m.group("text").rstrip()
        if compute_todo_line_id("to do", idx, text) != line_id:
            continue
        mark = "x" if checked else " "
        lines[idx] = f"{m.group('prefix')}- [{mark}] {text}"
        changed = True
        break
    if not changed:
        return body, False
    sec.body = "\n".join(lines)
    return render(doc), True


def extract_todos(body: str) -> list[dict]:
    """Extract todo items as ``[{line_id, text, checked}]``."""
    doc = parse(body)
    sec = doc.get("to do")
    if not sec:
        return []
    results: list[dict] = []
    for idx, line in enumerate(sec.body.split("\n")):
        m = _TODO_RE.match(line)
        if not m:
            continue
        text = m.group("text").rstrip()
        results.append({
            "line_id": compute_todo_line_id("to do", idx, text),
            "text": text,
            "checked": m.group("mark").lower() == "x",
        })
    return results


def extract_notes(body: str) -> list[dict]:
    """Extract captured notes (ISO-timestamp bullets)."""
    doc = parse(body)
    sec = doc.get("notes")
    if not sec:
        return []
    results: list[dict] = []
    for line in sec.body.split("\n"):
        m = _NOTE_RE.match(line)
        if not m:
            continue
        results.append({
            "created_at": m.group("ts"),
            "text": m.group("text").rstrip(),
        })
    return results


def extract_your_day(body: str) -> list[dict]:
    """Extract your_day items (bullets). Simple: strip leading ``- `` from
    each non-empty line in the section."""
    doc = parse(body)
    sec = doc.get("your day")
    if not sec:
        return []
    items: list[dict] = []
    for line in sec.body.split("\n"):
        stripped = line.lstrip()
        if not stripped.startswith("- "):
            continue
        text = stripped[2:].rstrip()
        if not text:
            continue
        # Wikilink: [[path]] or [[path|display]] — extract the first occurrence.
        wl = _WIKILINK_RE.search(text)
        items.append(
            {"text": text, "wikilink": wl.group(1) if wl else None}
        )
    return items


def extract_framing(body: str) -> Optional[str]:
    """Return the first non-empty line of the Header section, if any."""
    doc = parse(body)
    sec = doc.get("header")
    if not sec:
        return None
    for line in sec.body.split("\n"):
        stripped = line.strip()
        if stripped:
            if _looks_like_empty_state(stripped):
                return None
            return stripped
    return None


# --- helpers ---------------------------------------------------------------


_TODO_RE = re.compile(
    r"^(?P<prefix>\s*)- \[(?P<mark>[ xX])\] (?P<text>.*)$"
)
_NOTE_RE = re.compile(
    r"^\s*- \[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]\s+(?P<text>.*)$"
)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

_EMPTY_STATE_MARKERS = (
    "no framing yet",
    "nothing on your calendar today",
    "no to-dos",
    "no notes captured today",
    "nothing running, watching",
    "nothing awaiting approval",
    "no recent activity",
)


def _looks_like_empty_state(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _EMPTY_STATE_MARKERS)


def _ensure_trailing_newline(s: str) -> str:
    if not s:
        return "\n"
    return s if s.endswith("\n") else s + "\n"


def compute_todo_line_id(section: str, line_index: int, raw_text: str) -> str:
    """Stable id for a todo line.

    Deterministic hash of ``(section, line-index, raw text)`` so that
    ``POST /today/todo/toggle`` can locate the line to flip. Short-ish hex
    so it fits comfortably in a DOM ``data-id``.
    """
    import hashlib

    key = f"{_normalize_key(section)}|{line_index}|{raw_text.strip()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
