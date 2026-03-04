"""Unit tests for briefing_prompts.py — prompt constants, validation, and formatting."""

import pytest

from chatServer.services.briefing_prompts import (
    BRIEFING_SECTION_KEYS,
    BRIEFING_SECTIONS_DEFAULT,
    EVENING_BRIEFING_PROMPT,
    MORNING_BRIEFING_PROMPT,
    _format_context_block,
    get_enabled_sections,
)


# --- AC-32: Prompt constants exist ---

def test_ac_32_prompt_constants_exist():
    """Verify all required exports exist in briefing_prompts module."""
    assert MORNING_BRIEFING_PROMPT
    assert EVENING_BRIEFING_PROMPT
    assert BRIEFING_SECTIONS_DEFAULT
    assert BRIEFING_SECTION_KEYS
    assert callable(get_enabled_sections)
    assert callable(_format_context_block)


def test_ac_32_morning_prompt_has_rules():
    """Morning prompt includes word limit and importance ordering."""
    assert "300 words" in MORNING_BRIEFING_PROMPT
    assert "importance" in MORNING_BRIEFING_PROMPT.lower()
    assert "3-5" in MORNING_BRIEFING_PROMPT


def test_ac_32_evening_prompt_has_rules():
    """Evening prompt includes word limit and reflective framing."""
    assert "250 words" in EVENING_BRIEFING_PROMPT
    assert "reflect" in EVENING_BRIEFING_PROMPT.lower() or "Reflect" in EVENING_BRIEFING_PROMPT


# --- AC-33: _format_context_block omits empty ---

def test_ac_33_format_context_block_omits_empty():
    """Empty sections should be omitted entirely."""
    context = {
        "calendar": ["9:00 AM: Standup"],
        "tasks": [],
        "email": None,
        "observations": ["User mentioned backlog growing"],
    }
    result = _format_context_block(context)
    assert "## Calendar" in result
    assert "## Observations" in result
    assert "## Tasks" not in result
    assert "## Email" not in result


def test_ac_33_format_context_block_all_empty():
    """All empty sections produces empty string."""
    result = _format_context_block({"calendar": [], "tasks": None, "email": []})
    assert result == ""


def test_ac_33_format_context_block_list_items():
    """List items are rendered as bullet points."""
    result = _format_context_block({"tasks": ["Item 1", "Item 2"]})
    assert "- Item 1" in result
    assert "- Item 2" in result


def test_ac_33_format_context_block_string_value():
    """String values are rendered directly."""
    result = _format_context_block({"summary": "All clear today"})
    assert "All clear today" in result


# --- AC-34: get_enabled_sections validation ---

def test_ac_34_none_returns_defaults():
    """None input returns a copy of defaults."""
    result = get_enabled_sections(None)
    assert result == BRIEFING_SECTIONS_DEFAULT
    # Verify it's a copy, not the same object
    result["calendar"] = False
    assert BRIEFING_SECTIONS_DEFAULT["calendar"] is True


def test_ac_34_valid_booleans():
    """Valid boolean values pass through."""
    result = get_enabled_sections({"calendar": False, "tasks": True})
    assert result == {"calendar": False, "tasks": True}


def test_ac_34_rejects_unknown_keys():
    """Unknown section keys raise ValueError."""
    with pytest.raises(ValueError, match="Unknown briefing section"):
        get_enabled_sections({"weather": True})


def test_ac_34_rejects_non_boolean_string():
    """String values like 'yes' are rejected."""
    with pytest.raises(ValueError, match="must be boolean"):
        get_enabled_sections({"calendar": "yes"})


def test_ac_34_rejects_non_boolean_int():
    """Integer values are rejected."""
    with pytest.raises(ValueError, match="must be boolean"):
        get_enabled_sections({"calendar": 1})


def test_ac_34_forward_compat_dict_is_truthy():
    """Dict values are forward-compatible — treated as truthy."""
    result = get_enabled_sections({"calendar": {"enabled": True, "max_items": 3}})
    assert result["calendar"] is True


def test_ac_34_forward_compat_empty_dict_is_falsy():
    """Empty dict is falsy."""
    result = get_enabled_sections({"calendar": {}})
    assert result["calendar"] is False


# --- AC-36: format_for_telegram ---

def test_ac_36_format_for_telegram_strips_h3_headers():
    """### headers convert to **bold**."""
    from chatServer.services.briefing_service import format_for_telegram

    result = format_for_telegram("### Your Morning\nSome content")
    assert "### " not in result
    assert "**Your Morning**" in result


def test_ac_36_format_for_telegram_strips_h2_headers():
    """## headers also convert to **bold**."""
    from chatServer.services.briefing_service import format_for_telegram

    result = format_for_telegram("## Calendar\n- Event 1")
    assert "## " not in result
    assert "**Calendar**" in result


# --- AC-39: Telegram format nested lists and truncation ---

def test_ac_39_format_for_telegram_flattens_nested_lists():
    """Nested lists are flattened to single-level."""
    from chatServer.services.briefing_service import format_for_telegram

    text = "- Top level\n  - Nested item\n    - Deep nested"
    result = format_for_telegram(text)
    assert "  - " not in result
    assert "- Nested item" in result
    assert "- Deep nested" in result


def test_ac_39_format_for_telegram_preserves_bold_italic():
    """Bold and italic are preserved."""
    from chatServer.services.briefing_service import format_for_telegram

    text = "**bold text** and _italic text_"
    result = format_for_telegram(text)
    assert "**bold text**" in result
    assert "_italic text_" in result


def test_ac_39_format_for_telegram_truncation():
    """Output exceeding 4000 chars is truncated."""
    from chatServer.services.briefing_service import TELEGRAM_CHAR_LIMIT, format_for_telegram

    long_text = "x" * 5000
    result = format_for_telegram(long_text)
    assert len(result) <= TELEGRAM_CHAR_LIMIT
    assert result.endswith("...")


def test_ac_39_format_for_telegram_no_truncation_under_limit():
    """Short text is not truncated."""
    from chatServer.services.briefing_service import format_for_telegram

    short_text = "Hello world"
    result = format_for_telegram(short_text)
    assert result == "Hello world"


# --- AC-40: Prompt assembly within word limits ---

def test_ac_40_morning_prompt_within_word_limit():
    """Morning prompt template itself stays within 300 words."""
    word_count = len(MORNING_BRIEFING_PROMPT.split())
    # The prompt template itself should be concise — under 100 words
    # The 300-word limit is for the LLM output, not the prompt
    assert word_count < 200, f"Morning prompt is {word_count} words"


def test_ac_40_evening_prompt_within_word_limit():
    """Evening prompt template itself stays within 250 words."""
    word_count = len(EVENING_BRIEFING_PROMPT.split())
    assert word_count < 200, f"Evening prompt is {word_count} words"


# --- AC-41: Prompt scenario tests ---

def test_ac_41_scenario_typical_weekday_morning():
    """Typical weekday: all 4 sources populated."""
    context = {
        "calendar": [
            "09:00: Team standup",
            "11:00: Design review",
            "14:00: 1:1 with Sarah",
            "16:00: Sprint planning",
        ],
        "tasks": [
            "[overdue] Submit Q1 report (due Mar 1)",
            "[today] Review PR #42",
        ],
        "email": [
            '"Urgent: contract renewal" from legal@company.com',
            '"Q1 numbers ready" from finance@company.com',
            '"Lunch today?" from alice@company.com',
            '"Re: project update" from bob@company.com',
            '"Meeting moved" from calendar@company.com',
        ],
        "observations": [
            "You've had 3 meetings cancelled this week — might be worth checking in with the team",
        ],
    }
    result = MORNING_BRIEFING_PROMPT + "\n\n" + _format_context_block(context)
    assert "## Calendar" in result
    assert "## Tasks" in result
    assert "## Email" in result
    assert "## Observations" in result
    assert "Team standup" in result


def test_ac_41_scenario_empty_day():
    """Empty day: no events, tasks, email, observations."""
    context = {
        "calendar": [],
        "tasks": [],
        "email": [],
        "observations": [],
    }
    formatted = _format_context_block(context)
    # All sections omitted
    assert formatted == ""
    # Prompt still valid on its own
    result = MORNING_BRIEFING_PROMPT + "\n\n" + formatted
    assert "300 words" in result


def test_ac_41_scenario_crisis_day():
    """Crisis day: many overdue tasks, urgent emails, conflicts."""
    context = {
        "calendar": [
            "09:00: Emergency standup",
            "09:30: Incident review",
            "10:00: Customer call (CONFLICT with above)",
        ],
        "tasks": [
            "[overdue] Fix production bug (due Feb 28)",
            "[overdue] Deploy hotfix (due Mar 1)",
            "[overdue] Update status page (due Mar 1)",
            "[overdue] Write post-mortem (due Mar 2)",
            "[overdue] Review security patch (due Mar 2)",
            "[overdue] Update runbook (due Mar 3)",
        ],
        "email": [
            '"URGENT: Production down" from ops@company.com',
            '"Customer complaint" from support@company.com',
            '"Incident report needed ASAP" from vp@company.com',
        ],
        "observations": [],
    }
    result = _format_context_block(context)
    assert "## Calendar" in result
    assert "## Tasks" in result
    assert "## Email" in result
    # Observations section omitted (empty)
    assert "## Observations" not in result


def test_ac_41_scenario_evening_productive_day():
    """Evening productive day: many tasks completed, some still open."""
    context = {
        "completed_today": [
            "Deploy v2.1",
            "Review PR #42",
            "Update documentation",
            "Fix login bug",
            "Write unit tests",
        ],
        "still_open": [
            "[today] Merge feature branch",
            "Write API docs (due Mar 6)",
        ],
        "tomorrow": [
            "09:00: Sprint review",
            "14:00: Team retro",
            "16:00: Planning poker",
        ],
    }
    result = EVENING_BRIEFING_PROMPT + "\n\n" + _format_context_block(context)
    assert "## Completed_Today" in result or "## Completed Today" in result
    assert "## Still_Open" in result or "## Still Open" in result
    assert "## Tomorrow" in result
    assert "Deploy v2.1" in result


def test_ac_41_scenario_no_connected_services():
    """No connected services: all sections unavailable."""
    context = {
        "calendar": [],
        "tasks": [],
        "email": [],
        "observations": [],
    }
    formatted = _format_context_block(context)
    # No context sections at all
    assert formatted == ""
    # Prompt assembles with only the base template
    result = MORNING_BRIEFING_PROMPT + "\n\n" + formatted
    assert "3-5 most important" in result
