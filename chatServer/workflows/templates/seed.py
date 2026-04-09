"""Seed workflow templates into ConfigService on startup.

Writes templates and step prompts to system/ config paths if they
don't already exist (idempotent).
"""

import logging

logger = logging.getLogger(__name__)

# Template name → (config path, content module attr)
_TEMPLATES = {
    "email-triage": "workflows/email-triage.md",
    "morning-briefing": "workflows/morning-briefing.md",
    "evening-briefing": "workflows/evening-briefing.md",
    "draft-reply": "workflows/draft-reply.md",
    "introspection-loop": "workflows/introspection-loop.md",
}

# Step prompt path → content module attr
_PROMPTS = {
    "workflows/prompts/email-triage/categorize.md": None,
    "workflows/prompts/email-triage/summarize.md": None,
    "workflows/prompts/morning-briefing/compose-briefing.md": None,
    "workflows/prompts/evening-briefing/compose-briefing.md": None,
    "workflows/prompts/draft-reply/compose-draft.md": None,
    "workflows/prompts/introspection-loop/gather-signals.md": None,
    "workflows/prompts/introspection-loop/analyze-patterns.md": None,
    "workflows/prompts/introspection-loop/propose-changes.md": None,
    "workflows/prompts/introspection-loop/apply-changes.md": None,
}


def _load_all_content() -> dict[str, str]:
    """Load all template and prompt content. Returns {config_path: content}."""
    from . import draft_reply, email_triage, evening_briefing, introspection, morning_briefing

    return {
        # Templates
        "workflows/email-triage.md": email_triage.TEMPLATE,
        "workflows/morning-briefing.md": morning_briefing.TEMPLATE,
        "workflows/evening-briefing.md": evening_briefing.TEMPLATE,
        "workflows/draft-reply.md": draft_reply.TEMPLATE,
        "workflows/introspection-loop.md": introspection.TEMPLATE,
        # Step prompts
        "workflows/prompts/email-triage/categorize.md": email_triage.PROMPT_CATEGORIZE,
        "workflows/prompts/email-triage/summarize.md": email_triage.PROMPT_SUMMARIZE,
        "workflows/prompts/morning-briefing/compose-briefing.md": morning_briefing.PROMPT_COMPOSE_BRIEFING,
        "workflows/prompts/evening-briefing/compose-briefing.md": evening_briefing.PROMPT_COMPOSE_BRIEFING,
        "workflows/prompts/draft-reply/compose-draft.md": draft_reply.PROMPT_COMPOSE_DRAFT,
        "workflows/prompts/introspection-loop/gather-signals.md": introspection.PROMPT_GATHER_SIGNALS,
        "workflows/prompts/introspection-loop/analyze-patterns.md": introspection.PROMPT_ANALYZE_PATTERNS,
        "workflows/prompts/introspection-loop/propose-changes.md": introspection.PROMPT_PROPOSE_CHANGES,
        "workflows/prompts/introspection-loop/apply-changes.md": introspection.PROMPT_APPLY_CHANGES,
    }


async def seed_workflow_templates(config_service) -> int:
    """Write all workflow templates and prompts to ConfigService.

    Uses write_system() with upsert — safe to call on every startup.

    Returns:
        Number of files written.
    """
    content_map = _load_all_content()
    count = 0

    for path, content in content_map.items():
        try:
            await config_service.write_system(path, content)
            count += 1
        except Exception as e:
            logger.error("Failed to seed %s: %s", path, e)

    logger.info("Seeded %d workflow template/prompt files", count)
    return count
