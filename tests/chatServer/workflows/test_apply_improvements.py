"""Tests for the apply_improvements service node (SPEC-040)."""

import json

import pytest


class TestApplyImprovements:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_proposals(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        state = {
            "step_outputs": {},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert data["applied"] == []
        assert data["skipped"] == []
        assert data["failed"] == []

    @pytest.mark.asyncio
    async def test_applies_mutable_path_proposal(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "file_path": "/user/preferences/communication.yaml",
            "change_type": "update",
            "diff_preview": "- briefing_length: 500\n+ briefing_length: 300",
            "rationale": "User feedback says briefings too long",
            "expected_impact": "Shorter briefings",
            "risk": "Low",
            "elevated": False,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["applied"]) == 1
        assert data["applied"][0]["file_path"] == "/user/preferences/communication.yaml"

    @pytest.mark.asyncio
    async def test_skips_immutable_path(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "file_path": "/system/security/tool_allowlist.yaml",
            "change_type": "update",
            "rationale": "Wants to modify security config",
            "elevated": False,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["skipped"]) == 1
        assert "Security boundary" in data["skipped"][0]["reason"]

    @pytest.mark.asyncio
    async def test_skips_capability_requests(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "type": "capability_request",
            "tool_name": "send_email_reply",
            "requested_tier": "act",
            "current_tier": "recommend",
            "justification": "User always approves",
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["skipped"]) == 1
        assert "Capability request" in data["skipped"][0]["reason"]

    @pytest.mark.asyncio
    async def test_skips_elevated_at_inform_tier(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "file_path": "/user/workflows/custom-workflow.md",
            "change_type": "create",
            "rationale": "New workflow",
            "elevated": True,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["skipped"]) == 1
        assert "Elevated" in data["skipped"][0]["reason"]

    @pytest.mark.asyncio
    async def test_allows_elevated_at_recommend_tier(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "file_path": "/user/workflows/custom-workflow.md",
            "change_type": "create",
            "rationale": "New workflow",
            "elevated": True,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "recommend"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["applied"]) == 1

    @pytest.mark.asyncio
    async def test_handles_multiple_proposals(self):
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([
            {
                "file_path": "/user/preferences/communication.yaml",
                "change_type": "update",
                "rationale": "Shorten briefings",
                "elevated": False,
            },
            {
                "file_path": "/system/security/config.yaml",
                "change_type": "update",
                "rationale": "Modify security",
                "elevated": False,
            },
            {
                "type": "capability_request",
                "tool_name": "calendar",
                "justification": "Needs calendar",
            },
        ])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }
        result = await apply_improvements(state)
        data = json.loads(result)
        assert len(data["applied"]) == 1
        assert len(data["skipped"]) == 2


class TestParseProposals:
    def test_parses_json_array(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        raw = json.dumps([{"file_path": "/user/test.yaml"}])
        result = _parse_proposals(raw)
        assert len(result) == 1

    def test_parses_single_object(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        raw = json.dumps({"file_path": "/user/test.yaml"})
        result = _parse_proposals(raw)
        assert len(result) == 1

    def test_parses_wrapper_with_proposals_key(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        raw = json.dumps({"proposals": [{"file_path": "/user/a.yaml"}, {"file_path": "/user/b.yaml"}]})
        result = _parse_proposals(raw)
        assert len(result) == 2

    def test_parses_markdown_code_blocks(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        raw = """Here are my proposals:

```json
[{"file_path": "/user/test.yaml", "change_type": "update"}]
```
"""
        result = _parse_proposals(raw)
        assert len(result) == 1

    def test_returns_empty_for_unparseable(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        result = _parse_proposals("This is just plain text with no JSON")
        assert result == []

    def test_parses_line_by_line_json(self):
        from chatServer.workflows.nodes.apply_improvements import _parse_proposals

        raw = '{"file_path": "/user/a.yaml"}\n{"file_path": "/user/b.yaml"}'
        result = _parse_proposals(raw)
        assert len(result) == 2
