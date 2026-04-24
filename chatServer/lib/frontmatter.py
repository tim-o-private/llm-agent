"""Shared YAML frontmatter parser for vault markdown files."""

import re

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and body from markdown content.

    Returns ``(frontmatter_dict, body_string)``. If no frontmatter is found
    or parsing fails, returns ``({}, content)``.
    """
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    try:
        fm = yaml.safe_load(m.group(1))
        if not isinstance(fm, dict):
            return {}, content
    except yaml.YAMLError:
        return {}, content
    body = content[m.end() :].lstrip("\n")
    return fm, body


def serialize_frontmatter(frontmatter: dict, body: str, *, sort_keys: bool = False) -> str:
    """Serialize frontmatter dict + body back to a markdown document.

    ``sort_keys`` defaults to ``False`` to preserve insertion order (matching
    the existing behavior of thread_service and entity_service).
    """
    fm_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=sort_keys,
    )
    return f"---\n{fm_str}---\n\n{body}"
