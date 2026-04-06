"""Tests for SelfImprovementService — propose/approve/reject/rollback flow."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from chatServer.sandbox.disclosure import DisclosureModel
from chatServer.sandbox.git_tracker import CommitInfo, GitTracker
from chatServer.sandbox.security_boundary import SecurityBoundary
from chatServer.sandbox.self_improvement import (
    ProposalStatus,
    SelfImprovementService,
)


@pytest.fixture()
def service():
    return SelfImprovementService(
        security_boundary=SecurityBoundary(),
        disclosure_model=DisclosureModel(),
    )


@pytest.fixture()
def service_with_notifications():
    notif = AsyncMock()
    notif.notify_user = AsyncMock(return_value="notif-123")
    return SelfImprovementService(
        security_boundary=SecurityBoundary(),
        disclosure_model=DisclosureModel(),
        notification_service=notif,
    ), notif


@pytest.fixture()
def mock_tracker():
    tracker = GitTracker(Path("/fake/user"))
    tracker.commit = AsyncMock(return_value=CommitInfo(
        sha="abc123",
        message="Agent: updated /user/preferences/tone.yaml",
        timestamp="2026-04-06T00:00:00+00:00",
    ))
    tracker.diff = AsyncMock(return_value="+new setting\n-old setting")
    tracker.revert = AsyncMock(return_value=CommitInfo(
        sha="rev789",
        message="Revert: Agent: updated /user/preferences/tone.yaml",
        timestamp="2026-04-06T01:00:00+00:00",
    ))
    return tracker


class TestProposeChange:
    @pytest.mark.asyncio
    async def test_propose_mutable_path(self, service, mock_tracker):
        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/preferences/tone.yaml",
            content="new content",
            description="Adjusted tone preference",
        )

        assert proposal.status == ProposalStatus.PENDING
        assert proposal.file_path == "/user/preferences/tone.yaml"
        assert proposal.git_commit_hash == "abc123"
        assert proposal.diff_text == "+new setting\n-old setting"
        mock_tracker.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_immutable_path_raises(self, service, mock_tracker):
        with pytest.raises(PermissionError, match="rejected by security boundary"):
            await service.propose_change(
                user_id="user-1",
                git_tracker=mock_tracker,
                file_path="/system/security/tool_allowlist.yaml",
                content="hacked",
                description="Trying to modify security config",
            )

    @pytest.mark.asyncio
    async def test_propose_no_changes_raises(self, service):
        tracker = GitTracker(Path("/fake/user"))
        tracker.commit = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="No changes to commit"):
            await service.propose_change(
                user_id="user-1",
                git_tracker=tracker,
                file_path="/user/agent/greeting.md",
                content="hi",
                description="Change greeting",
            )

    @pytest.mark.asyncio
    async def test_propose_sends_notification(self, service_with_notifications, mock_tracker):
        svc, notif = service_with_notifications

        await svc.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/preferences/tone.yaml",
            content="new",
            description="Adjusted tone",
            trust_tier="inform",
        )

        notif.notify_user.assert_called_once()
        call_kwargs = notif.notify_user.call_args.kwargs
        assert call_kwargs["category"] == "config_change"
        assert "approve" in call_kwargs["metadata"]["actions"]
        assert "revert" in call_kwargs["metadata"]["actions"]

    @pytest.mark.asyncio
    async def test_propose_act_tier_no_notification(self, service_with_notifications, mock_tracker):
        svc, notif = service_with_notifications

        await svc.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style tweak",
            trust_tier="act",
        )

        notif.notify_user.assert_not_called()


class TestApproveChange:
    @pytest.mark.asyncio
    async def test_approve_existing_proposal(self, service, mock_tracker):
        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/greeting.md",
            content="hello",
            description="Changed greeting",
        )

        approved = await service.approve_change(proposal.id)
        assert approved is not None
        assert approved.status == ProposalStatus.APPROVED
        assert approved.user_approved is True

    @pytest.mark.asyncio
    async def test_approve_nonexistent_returns_none(self, service):
        result = await service.approve_change("nonexistent-id")
        assert result is None


class TestRejectChange:
    @pytest.mark.asyncio
    async def test_reject_reverts_commit(self, service, mock_tracker):
        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/preferences/scheduling.yaml",
            content="new schedule",
            description="Changed schedule",
        )

        rejected = await service.reject_change(proposal.id, mock_tracker)
        assert rejected is not None
        assert rejected.status == ProposalStatus.REVERTED
        assert rejected.metadata["revert_commit"] == "rev789"
        mock_tracker.revert.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_reject_revert_failure(self, service, mock_tracker):
        mock_tracker.revert = AsyncMock(return_value=None)

        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style change",
        )

        rejected = await service.reject_change(proposal.id, mock_tracker)
        assert rejected.status == ProposalStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_nonexistent_returns_none(self, service, mock_tracker):
        result = await service.reject_change("nonexistent", mock_tracker)
        assert result is None


class TestAutoRollbackCheck:
    @pytest.mark.asyncio
    async def test_no_rollback_when_no_proposals(self, service, mock_tracker):
        result = await service.auto_rollback_check("user-1", mock_tracker)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_rollback_below_threshold(self, service, mock_tracker):
        await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style tweak",
        )

        result = await service.auto_rollback_check(
            "user-1",
            mock_tracker,
            metrics={"degradation_sigma": 1.5},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_rollback_on_significant_degradation(self, service, mock_tracker):
        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style tweak",
        )

        result = await service.auto_rollback_check(
            "user-1",
            mock_tracker,
            metrics={
                "degradation_sigma": 3.0,
                "causal_proposal_id": proposal.id,
            },
        )
        assert result is not None
        assert result.status == ProposalStatus.REVERTED
        assert result.metadata["auto_rollback"] is True

    @pytest.mark.asyncio
    async def test_no_rollback_for_user_approved(self, service, mock_tracker):
        proposal = await service.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style tweak",
        )
        await service.approve_change(proposal.id)

        result = await service.auto_rollback_check(
            "user-1",
            mock_tracker,
            metrics={
                "degradation_sigma": 3.0,
                "causal_proposal_id": proposal.id,
            },
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_unattributed_degradation_notifies_only(self, service_with_notifications, mock_tracker):
        svc, notif = service_with_notifications

        await svc.propose_change(
            user_id="user-1",
            git_tracker=mock_tracker,
            file_path="/user/agent/style.md",
            content="new",
            description="Style tweak",
        )

        # Reset the notify mock from the propose call
        notif.notify_user.reset_mock()

        result = await svc.auto_rollback_check(
            "user-1",
            mock_tracker,
            metrics={
                "degradation_sigma": 3.0,
                # No causal_proposal_id
            },
        )
        assert result is None
        # Should have notified about unattributed degradation
        notif.notify_user.assert_called_once()
        call_kwargs = notif.notify_user.call_args.kwargs
        assert call_kwargs["category"] == "auto_rollback"
