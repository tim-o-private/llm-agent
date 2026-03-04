"""Briefing prompt constants, JSONB schema definitions, and context formatting helpers.

Used by BriefingService to compose morning and evening briefing prompts.
All prompt templates, section validation, and context block formatting live here.
"""

BRIEFING_SECTIONS_DEFAULT = {
    "calendar": True,
    "tasks": True,
    "email": True,
    "observations": True,
}
BRIEFING_SECTION_KEYS = frozenset(BRIEFING_SECTIONS_DEFAULT.keys())

MORNING_BRIEFING_PROMPT = """You are composing a morning briefing for the user.

Pick the 3-5 most important items from the context below. Order by importance,
not by category. Explain WHY each item matters in one sentence.

Rules:
- Maximum 300 words
- Use markdown: **bold** for emphasis, ### for section headers, bullet points
- If a section has nothing noteworthy, skip it entirely
- Be opinionated — "You have a 1:1 with Sarah at 2pm and 3 overdue tasks"
  is better than "You have 5 calendar events and 8 tasks"
- End with one actionable suggestion for the day
"""

EVENING_BRIEFING_PROMPT = """You are composing an evening briefing for the user.

Reflect on the day: what got done, what's still open, what's tomorrow.

Rules:
- Maximum 250 words
- Use markdown: **bold** for emphasis, ### for section headers, bullet points
- Reflective framing — "You knocked out 4 tasks today" not "4 tasks were completed"
- If nothing happened, say so briefly
- End with what to expect tomorrow (preview from calendar)
"""


def get_enabled_sections(sections_input: dict | None) -> dict:
    """Validate and return enabled sections dict.

    - None/null -> use BRIEFING_SECTIONS_DEFAULT
    - All keys must be in BRIEFING_SECTION_KEYS — reject unknowns
    - All values must be boolean — reject non-boolean truthy values like "yes"
    - Forward-compatible: future dict values like {"enabled": true, "max_items": 3} are truthy
    """
    if sections_input is None:
        return dict(BRIEFING_SECTIONS_DEFAULT)

    validated = {}
    for key, value in sections_input.items():
        if key not in BRIEFING_SECTION_KEYS:
            raise ValueError(f"Unknown briefing section: {key}")
        if not isinstance(value, bool):
            # Forward-compat: dicts are truthy (future {"enabled": true, ...})
            if isinstance(value, dict):
                validated[key] = bool(value)
            else:
                raise ValueError(
                    f"briefing_sections[{key}] must be boolean, got {type(value).__name__}"
                )
        else:
            validated[key] = value
    return validated


def _format_context_block(context: dict) -> str:
    """Format gathered context as tagged markdown sections.

    Omits sections with empty/None data entirely.

    Example output:
        ## Calendar
        - 9:00 AM: Team standup (30 min)
        - 2:00 PM: 1:1 with Sarah (1 hr)

        ## Tasks
        - [overdue] Submit Q1 report (due Mar 1)
        - [today] Review PR #42
    """
    blocks = []
    for label, items in context.items():
        if not items:
            continue
        if isinstance(items, list):
            formatted = "\n".join(f"- {item}" for item in items)
        else:
            formatted = str(items)
        blocks.append(f"## {label.title()}\n{formatted}")
    return "\n\n".join(blocks)
