"""Unit tests for ConfigChangeSafetyValidator — protected paths, blocked patterns, safe pass."""

from __future__ import annotations

import pytest

from chatServer.services.config_change_validator import ConfigChangeSafetyValidator


@pytest.fixture
def validator():
    return ConfigChangeSafetyValidator()


# ---------------------------------------------------------------------------
# Protected paths
# ---------------------------------------------------------------------------


class TestProtectedPaths:
    def test_security_path_blocked(self, validator):
        ok, reason = validator.validate("system/security/auth.yaml", "safe content")
        assert ok is False
        assert "protected path" in reason.lower()

    def test_auth_path_blocked(self, validator):
        ok, reason = validator.validate("system/auth/tokens.md", "safe content")
        assert ok is False
        assert "protected path" in reason.lower()

    def test_activity_path_blocked(self, validator):
        ok, reason = validator.validate("_activity/log.md", "safe content")
        assert ok is False

    def test_normal_path_allowed(self, validator):
        ok, reason = validator.validate("_workflows/my-workflow.flow.md", "safe content")
        assert ok is True
        assert reason is None

    def test_agent_path_allowed(self, validator):
        ok, reason = validator.validate(
            "agents/clarity/thread-planner.md", "safe content"
        )
        assert ok is True
        assert reason is None


# ---------------------------------------------------------------------------
# Blocked content patterns
# ---------------------------------------------------------------------------


class TestBlockedPatterns:
    def test_gate_policy_none_blocked(self, validator):
        content = "---\nname: my-workflow\ndefault_gate_policy: none\n---"
        ok, reason = validator.validate("_workflows/test.flow.md", content)
        assert ok is False
        assert "blocked pattern" in reason.lower()

    def test_approval_tier_auto_blocked(self, validator):
        content = "---\napproval_tier: auto\n---"
        ok, reason = validator.validate("agents/test.md", content)
        assert ok is False

    def test_approval_tier_none_blocked(self, validator):
        content = "---\napproval_tier: none\n---"
        ok, reason = validator.validate("agents/test.md", content)
        assert ok is False

    def test_delete_file_tool_blocked(self, validator):
        content = "---\ntools: [read_file, delete_file, write_file]\n---"
        ok, reason = validator.validate("agents/test.md", content)
        assert ok is False

    def test_case_insensitive(self, validator):
        content = "---\nDefault_Gate_Policy: None\n---"
        ok, reason = validator.validate("_workflows/test.flow.md", content)
        assert ok is False

    def test_safe_content_passes(self, validator):
        content = (
            "---\nname: my-workflow\n"
            "description: A safe workflow\n"
            "default_gate_policy: approval\n"
            "tools: [read_file, write_file]\n---"
        )
        ok, reason = validator.validate("_workflows/test.flow.md", content)
        assert ok is True
        assert reason is None

    def test_empty_content_passes(self, validator):
        ok, reason = validator.validate("agents/test.md", "")
        assert ok is True
        assert reason is None
