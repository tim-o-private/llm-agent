"""Tests for the apply_improvements service node (SPEC-040/041)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# All tests operate with sandbox unavailable (BWRAP_ENABLED=false default)
# to avoid needing a real bwrap binary. Sandbox-execution path is tested
# separately in TestApplyImprovementsSandbox.

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
    async def test_applies_mutable_path_proposal_when_sandbox_unavailable(self):
        """When sandbox is unavailable, mutable proposals are recorded as 'proposed'."""
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

        # Sandbox provisioner not initialized — get_provisioner raises RuntimeError
        with patch("chatServer.sandbox.provisioner.get_provisioner",
                   side_effect=RuntimeError("not initialized")):
            result = await apply_improvements(state)

        data = json.loads(result)
        assert len(data["applied"]) == 1
        assert data["applied"][0]["file_path"] == "/user/preferences/communication.yaml"
        assert data["applied"][0]["status"] == "proposed"

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


class TestApplyImprovementsSandbox:
    """Tests for the sandbox-execution path (provisioner available)."""

    def _make_mock_provisioner(self, tmp_path, user_id="user-123"):
        """Build a minimal provisioner mock that satisfies apply_improvements."""
        prov = MagicMock()
        prov.get_or_create = AsyncMock(return_value=MagicMock())
        prov.get_user_dir.return_value = tmp_path / "users" / user_id
        (tmp_path / "users" / user_id).mkdir(parents=True, exist_ok=True)
        return prov

    @pytest.mark.asyncio
    async def test_sandbox_unavailable_degrades_gracefully(self):
        """SandboxNotAvailableError → proposal recorded as 'proposed', no crash."""
        from chatServer.sandbox.provisioner import SandboxNotAvailableError
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        proposals = json.dumps([{
            "file_path": "/user/preferences/tone.yaml",
            "change_type": "update",
            "content": "tone: concise",
            "rationale": "User prefers brevity",
            "elevated": False,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": "user-123", "trust_tier": "inform"},
        }

        with patch("chatServer.sandbox.provisioner.get_provisioner",
                   side_effect=SandboxNotAvailableError("BWRAP_ENABLED=false")):
            result = await apply_improvements(state)

        data = json.loads(result)
        assert len(data["applied"]) == 1
        assert data["applied"][0]["status"] == "proposed"

    @pytest.mark.asyncio
    async def test_sandbox_execution_writes_and_commits(self, tmp_path):
        """When sandbox is available, proposal is written to disk and committed."""
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        user_id = "user-123"
        proposals = json.dumps([{
            "file_path": "/user/preferences/tone.yaml",
            "change_type": "update",
            "content": "tone: concise",
            "rationale": "User prefers brevity",
            "elevated": False,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": user_id, "trust_tier": "inform"},
        }

        mock_provisioner = self._make_mock_provisioner(tmp_path, user_id)
        mock_proposal = MagicMock()
        mock_proposal.id = "proposal-abc"
        mock_proposal.git_commit_hash = "sha123"

        with patch("chatServer.sandbox.provisioner.get_provisioner",
                   return_value=mock_provisioner), \
             patch(
                 "chatServer.sandbox.self_improvement.SelfImprovementService.propose_change",
                 new_callable=AsyncMock,
                 return_value=mock_proposal,
             ):
            result = await apply_improvements(state)

        data = json.loads(result)
        assert len(data["applied"]) == 1
        assert data["applied"][0]["status"] == "committed"
        assert data["applied"][0]["proposal_id"] == "proposal-abc"
        assert data["applied"][0]["commit_sha"] == "sha123"

    @pytest.mark.asyncio
    async def test_sandbox_execution_records_failure_on_exception(self, tmp_path):
        """If sandbox write fails, proposal goes to failed list."""
        from chatServer.workflows.nodes.apply_improvements import apply_improvements

        user_id = "user-123"
        proposals = json.dumps([{
            "file_path": "/user/preferences/tone.yaml",
            "change_type": "update",
            "content": "tone: concise",
            "rationale": "User prefers brevity",
            "elevated": False,
        }])

        state = {
            "step_outputs": {"propose-changes": proposals},
            "parameters": {"user_id": user_id, "trust_tier": "inform"},
        }

        mock_provisioner = self._make_mock_provisioner(tmp_path, user_id)

        with patch("chatServer.sandbox.provisioner.get_provisioner",
                   return_value=mock_provisioner), \
             patch(
                 "chatServer.sandbox.self_improvement.SelfImprovementService.propose_change",
                 new_callable=AsyncMock,
                 side_effect=ValueError("git commit failed"),
             ):
            result = await apply_improvements(state)

        data = json.loads(result)
        assert len(data["failed"]) == 1
        assert "git commit failed" in data["failed"][0]["error"]


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
