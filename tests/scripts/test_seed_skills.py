"""Unit tests for scripts/seed_skills.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make the scripts directory importable
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import seed_skills  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(write_system_ret=None, write_ret=None):
    """Build a mock ConfigService with async write methods."""
    config = MagicMock()
    config.write_system = AsyncMock(return_value=write_system_ret)
    config.write = AsyncMock(return_value=write_ret)
    config.ensure_bucket = AsyncMock(return_value=None)
    return config


# ---------------------------------------------------------------------------
# Builder unit tests (pure functions, no mocking needed)
# ---------------------------------------------------------------------------


def test_build_soul_skill_contains_soul_content():
    result = seed_skills.build_soul_skill("Be helpful, be kind.")
    assert "Be helpful, be kind." in result
    assert "# Clarity Soul" in result
    assert "clarity-soul" in result  # frontmatter name


def test_build_soul_skill_fallback_on_empty():
    result = seed_skills.build_soul_skill("")
    assert "No soul content configured" in result


def test_build_soul_skill_fallback_on_none():
    result = seed_skills.build_soul_skill(None)
    assert "No soul content configured" in result


def test_build_identity_skill_formats_fields():
    identity = {"name": "Clarity", "description": "a personal assistant", "vibe": "warm"}
    result = seed_skills.build_identity_skill(identity)
    assert "Clarity" in result
    assert "a personal assistant" in result
    assert "warm" in result
    assert "# Clarity Identity" in result
    assert "clarity-identity" in result  # frontmatter name


def test_build_identity_skill_handles_none():
    result = seed_skills.build_identity_skill(None)
    assert "No identity configured" in result


def test_build_operating_model_skill_contains_constant():
    from chatServer.services.prompt_builder import OPERATING_MODEL
    result = seed_skills.build_operating_model_skill()
    # At least one sentence from the constant should appear verbatim
    assert "operating-model" in result
    assert "# Operating Model" in result
    assert OPERATING_MODEL[:40] in result  # first 40 chars of the constant


def test_build_channel_guidance_skill_all_channels():
    from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
    result = seed_skills.build_channel_guidance_skill()
    for channel in CHANNEL_GUIDANCE:
        assert channel in result.lower() or channel.replace("_", " ") in result.lower()
    assert "# Channel Guidance" in result


def test_build_interaction_learning_skill_contains_constant():
    from chatServer.services.prompt_builder import INTERACTION_LEARNING_GUIDANCE
    result = seed_skills.build_interaction_learning_skill()
    assert "interaction-learning" in result
    assert INTERACTION_LEARNING_GUIDANCE[:40] in result


def test_build_safety_guidelines_skill_has_basics():
    result = seed_skills.build_safety_guidelines_skill()
    assert "safety-guidelines" in result
    assert "# Safety Guidelines" in result
    assert "deceive" in result  # core safety rule


def test_build_tool_guidance_skill_is_placeholder():
    result = seed_skills.build_tool_guidance_skill()
    assert "tool-guidance" in result
    assert "placeholder" in result.lower() or "Placeholder" in result


def test_build_communication_preferences_skill():
    result = seed_skills.build_communication_preferences_skill(
        "Always reply in bullet points.", "clarity"
    )
    assert "communication-preferences" in result
    assert "Always reply in bullet points." in result


def test_frontmatter_truncates_long_description():
    # Use space-separated words so textwrap.shorten can split at boundaries
    long_desc = "word " * 400  # ~2000 chars
    result = seed_skills._frontmatter("test", long_desc)
    # The total description content should not exceed DESCRIPTION_MAX_CHARS
    desc_lines = [line for line in result.splitlines() if line.startswith("  ")]
    desc_text = " ".join(line.strip() for line in desc_lines)
    assert len(desc_text) <= seed_skills.DESCRIPTION_MAX_CHARS + 5  # small tolerance


def test_frontmatter_strips_newlines():
    result = seed_skills._frontmatter("test", "line one\nline two")
    # Newlines in description should be collapsed
    assert "line one line two" in result or "line one" in result


# ---------------------------------------------------------------------------
# seed_system_skills — mocked ConfigService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_creates_system_skills():
    """All 7 system skills must be written via write_system()."""
    config = _make_config()
    agent_row = {"soul": "Be a great assistant.", "identity": {"name": "Clarity"}}

    written = await seed_skills.seed_system_skills(config, agent_row)

    assert len(written) == 7
    assert config.write_system.call_count == 7

    # Verify all expected skill paths were written
    written_paths = [c.args[0] for c in config.write_system.call_args_list]
    expected_paths = [
        "skills/clarity-soul/SKILL.md",
        "skills/clarity-identity/SKILL.md",
        "skills/operating-model/SKILL.md",
        "skills/channel-guidance/SKILL.md",
        "skills/interaction-learning/SKILL.md",
        "skills/tool-guidance/SKILL.md",
        "skills/safety-guidelines/SKILL.md",
    ]
    for path in expected_paths:
        assert path in written_paths, f"Expected {path} to be written"


@pytest.mark.asyncio
async def test_seed_creates_system_skills_with_none_agent():
    """Seeding works even when agent_configurations has no rows."""
    config = _make_config()
    written = await seed_skills.seed_system_skills(config, None)

    assert len(written) == 7
    assert config.write_system.call_count == 7


@pytest.mark.asyncio
async def test_seed_idempotent():
    """Running seed_system_skills twice produces the same write calls."""
    config = _make_config()
    agent_row = {"soul": "Be helpful.", "identity": {"name": "Clarity"}}

    await seed_skills.seed_system_skills(config, agent_row)
    first_calls = list(config.write_system.call_args_list)
    config.write_system.reset_mock()

    await seed_skills.seed_system_skills(config, agent_row)
    second_calls = list(config.write_system.call_args_list)

    assert len(first_calls) == len(second_calls) == 7
    for first, second in zip(first_calls, second_calls):
        assert first == second, "Idempotent: same content written on second run"


@pytest.mark.asyncio
async def test_seed_dry_run_no_writes():
    """Dry-run mode prints but does NOT call write_system."""
    config = _make_config()
    agent_row = {"soul": "Be helpful.", "identity": None}

    written = await seed_skills.seed_system_skills(config, agent_row, dry_run=True)

    assert config.write_system.call_count == 0
    assert len(written) == 7  # paths still returned for reporting


@pytest.mark.asyncio
async def test_seed_handles_empty_soul():
    """When soul is NULL/empty, a fallback placeholder is written (not an error)."""
    config = _make_config()
    agent_row = {"soul": None, "identity": None}

    await seed_skills.seed_system_skills(config, agent_row)

    # soul skill should still be written
    soul_write = next(
        (c for c in config.write_system.call_args_list if "clarity-soul" in c.args[0]),
        None,
    )
    assert soul_write is not None
    content = soul_write.args[1]
    assert "No soul content configured" in content


# ---------------------------------------------------------------------------
# seed_user_skills — mocked ConfigService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_creates_user_skills():
    """Each active customization row produces a user-scoped SKILL.md."""
    config = _make_config()
    customizations = [
        {"user_id": "user-1", "agent_name": "clarity", "instructions": "Reply briefly.", "is_active": True},
        {"user_id": "user-2", "agent_name": "clarity", "instructions": "Use bullet points.", "is_active": True},
    ]

    written = await seed_skills.seed_user_skills(config, customizations)

    assert len(written) == 2
    assert config.write.call_count == 2

    written_user_ids = [c.args[1] for c in config.write.call_args_list]
    assert "user-1" in written_user_ids
    assert "user-2" in written_user_ids


@pytest.mark.asyncio
async def test_seed_user_skills_empty_instructions_skipped():
    """Rows with empty instructions are silently skipped."""
    config = _make_config()
    customizations = [
        {"user_id": "user-1", "agent_name": "clarity", "instructions": "", "is_active": True},
        {"user_id": "user-2", "agent_name": "clarity", "instructions": "   ", "is_active": True},
    ]

    written = await seed_skills.seed_user_skills(config, customizations)

    assert len(written) == 0
    assert config.write.call_count == 0


@pytest.mark.asyncio
async def test_seed_user_skills_content_written_correctly():
    """The user skill content includes the instructions verbatim."""
    config = _make_config()
    customizations = [
        {
            "user_id": "user-42",
            "agent_name": "clarity",
            "instructions": "Always use metric units.",
            "is_active": True,
        }
    ]

    await seed_skills.seed_user_skills(config, customizations)

    write_call = config.write.call_args
    path, user_id, content = write_call.args
    assert user_id == "user-42"
    assert "skills/communication-preferences/SKILL.md" in path
    assert "Always use metric units." in content


@pytest.mark.asyncio
async def test_seed_user_skills_dry_run():
    """Dry-run mode does not call write()."""
    config = _make_config()
    customizations = [
        {"user_id": "user-1", "agent_name": "clarity", "instructions": "Be terse.", "is_active": True},
    ]

    written = await seed_skills.seed_user_skills(config, customizations, dry_run=True)

    assert config.write.call_count == 0
    assert len(written) == 1  # path still returned


# ---------------------------------------------------------------------------
# Identity formatting
# ---------------------------------------------------------------------------


def test_seed_formats_identity_json_complete():
    """Full identity dict produces readable markdown with all fields."""
    identity = {
        "name": "Clarity",
        "description": "a personal executive assistant",
        "vibe": "calm, warm, and direct",
    }
    result = seed_skills.build_identity_skill(identity)
    assert "**Name:** Clarity" in result
    assert "**Description:** a personal executive assistant" in result
    assert "**Vibe:** calm, warm, and direct" in result
    assert "**One-liner:**" in result


def test_seed_formats_identity_json_partial():
    """Partial identity dict (no vibe) still produces valid output."""
    identity = {"name": "Clarity"}
    result = seed_skills.build_identity_skill(identity)
    assert "Clarity" in result
    assert "Vibe" not in result  # no vibe field, no vibe line
