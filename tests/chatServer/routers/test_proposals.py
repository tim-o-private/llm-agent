"""Tests for the proposals router — config change approve/revert."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.proposals import router
from chatServer.sandbox.self_improvement import ChangeProposal, ProposalStatus

TEST_USER_ID = "user-abc"
mock_db = MagicMock()


def override_get_current_user():
    return TEST_USER_ID


def override_get_user_scoped_client():
    return mock_db


@pytest.fixture
def app():
    """Create a FastAPI app with the proposals router and mocked auth."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_current_user] = override_get_current_user
    test_app.dependency_overrides[get_user_scoped_client] = override_get_user_scoped_client
    return test_app


@pytest.fixture
def mock_proposal():
    return ChangeProposal(
        id="prop-123",
        user_id="user-abc",
        file_path="/user/agent/persona.md",
        description="Updated persona tone",
        git_commit_hash="abc123",
        diff_text="--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new",
    )


@pytest.fixture
def mock_proposal_other_user():
    return ChangeProposal(
        id="prop-456",
        user_id="user-other",
        file_path="/user/agent/persona.md",
        description="Other user's change",
        git_commit_hash="def456",
        diff_text="diff",
    )


@pytest.mark.asyncio
async def test_approve_proposal_success(app, mock_proposal):
    """Approve flow: approve_change -> sync -> resolve notification."""
    mock_self_improvement = AsyncMock()
    mock_self_improvement.approve_change.return_value = mock_proposal

    mock_sync = AsyncMock()
    mock_sync.sync_to_storage.return_value = ["agent/persona.md"]

    mock_provisioner = MagicMock()
    mock_provisioner.get_user_dir.return_value = "/sandbox/users/user-abc"
    mock_provisioner.get_or_create = AsyncMock()

    with (
        patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, mock_sync)),
        patch("chatServer.routers.proposals._get_sandbox", return_value=(mock_provisioner, "/sandbox/users/user-abc", MagicMock())),  # noqa: E501
        patch("chatServer.routers.proposals.NotificationService", return_value=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/prop-123/approve")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "1 file(s) synced" in data["message"]
    assert data["synced_files"] == ["agent/persona.md"]
    mock_self_improvement.approve_change.assert_awaited_once_with("prop-123")
    mock_sync.sync_to_storage.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_proposal_not_found(app):
    """404 when proposal doesn't exist."""
    mock_self_improvement = AsyncMock()
    mock_self_improvement.approve_change.return_value = None

    with patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, AsyncMock())):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/nonexistent/approve")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_proposal_wrong_user(app, mock_proposal_other_user):
    """403 when proposal belongs to a different user."""
    mock_self_improvement = AsyncMock()
    mock_self_improvement.approve_change.return_value = mock_proposal_other_user

    with patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, AsyncMock())):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/prop-456/approve")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_sandbox_unavailable_still_approves(app, mock_proposal):
    """Approval is recorded even when sandbox is down (sync skipped)."""
    mock_self_improvement = AsyncMock()
    mock_self_improvement.approve_change.return_value = mock_proposal

    with (
        patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, AsyncMock())),
        patch("chatServer.routers.proposals._get_sandbox", side_effect=RuntimeError("Sandbox disabled")),
        patch("chatServer.routers.proposals.NotificationService", return_value=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/prop-123/approve")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["synced_files"] == []


@pytest.mark.asyncio
async def test_revert_proposal_success(app, mock_proposal):
    """Revert flow: reject_change (git revert) + resolve notification."""
    mock_proposal.status = ProposalStatus.REVERTED

    mock_self_improvement = AsyncMock()
    mock_self_improvement.reject_change.return_value = mock_proposal

    mock_provisioner = MagicMock()
    mock_provisioner.get_user_dir.return_value = "/sandbox/users/user-abc"
    mock_provisioner.get_or_create = AsyncMock()

    with (
        patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, AsyncMock())),
        patch("chatServer.routers.proposals._get_sandbox", return_value=(mock_provisioner, "/sandbox/users/user-abc", MagicMock())),  # noqa: E501
        patch("chatServer.routers.proposals.NotificationService", return_value=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/prop-123/revert")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "reverted" in data["message"].lower()
    mock_self_improvement.reject_change.assert_awaited_once()


@pytest.mark.asyncio
async def test_revert_sandbox_unavailable_returns_503(app):
    """503 when sandbox is down — can't revert without git."""
    mock_self_improvement = AsyncMock()

    with (
        patch("chatServer.routers.proposals._build_services", return_value=(mock_self_improvement, AsyncMock())),
        patch("chatServer.routers.proposals._get_sandbox", side_effect=RuntimeError("Sandbox disabled")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/proposals/prop-123/revert")

    assert resp.status_code == 503
