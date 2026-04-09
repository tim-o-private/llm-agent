"""Tests for SyncService — sync sandbox changes to Supabase Storage."""

from unittest.mock import AsyncMock

import pytest

from chatServer.sandbox.security_boundary import SecurityBoundary
from chatServer.sandbox.sync import SyncService


@pytest.fixture()
def mock_config_service():
    svc = AsyncMock()
    svc.write = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest.fixture()
def mock_git_tracker():
    tracker = AsyncMock()
    tracker.diff_files = AsyncMock(return_value=["agent/greeting.md", "preferences/tone.yaml"])
    return tracker


class TestSyncToStorage:
    @pytest.mark.asyncio
    async def test_syncs_changed_files(self, tmp_path, mock_config_service, mock_git_tracker):
        # Create files on disk
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "greeting.md").write_text("Hello!")
        (tmp_path / "preferences").mkdir()
        (tmp_path / "preferences" / "tone.yaml").write_text("tone: warm")

        sync = SyncService(
            security_boundary=SecurityBoundary(),
            config_service=mock_config_service,
        )
        synced = await sync.sync_to_storage(
            user_id="user-1",
            git_tracker=mock_git_tracker,
            user_dir=tmp_path,
        )

        assert len(synced) == 2
        assert "agent/greeting.md" in synced
        assert "preferences/tone.yaml" in synced
        assert mock_config_service.write.call_count == 2

    @pytest.mark.asyncio
    async def test_deletes_removed_files(self, tmp_path, mock_config_service):
        tracker = AsyncMock()
        tracker.diff_files = AsyncMock(return_value=["agent/removed.md"])

        # File does NOT exist on disk (was deleted)
        (tmp_path / "agent").mkdir()

        sync = SyncService(
            security_boundary=SecurityBoundary(),
            config_service=mock_config_service,
        )
        synced = await sync.sync_to_storage(
            user_id="user-1",
            git_tracker=tracker,
            user_dir=tmp_path,
        )

        assert "agent/removed.md" in synced
        mock_config_service.delete.assert_called_once_with("agent/removed.md", "user-1")

    @pytest.mark.asyncio
    async def test_rejects_immutable_paths(self, tmp_path, mock_config_service):
        tracker = AsyncMock()
        # Simulate a file that somehow ended up referencing /system/
        tracker.diff_files = AsyncMock(return_value=["../system/security/hack.yaml"])

        sync = SyncService(
            security_boundary=SecurityBoundary(),
            config_service=mock_config_service,
        )
        synced = await sync.sync_to_storage(
            user_id="user-1",
            git_tracker=tracker,
            user_dir=tmp_path,
        )

        # The path /user/../system/security/hack.yaml should NOT be synced
        assert len(synced) == 0
        mock_config_service.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_config_service_returns_empty(self, tmp_path, mock_git_tracker):
        sync = SyncService(security_boundary=SecurityBoundary())
        synced = await sync.sync_to_storage(
            user_id="user-1",
            git_tracker=mock_git_tracker,
            user_dir=tmp_path,
        )
        assert synced == []

    @pytest.mark.asyncio
    async def test_handles_write_errors_gracefully(self, tmp_path, mock_config_service):
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "greeting.md").write_text("Hello!")

        tracker = AsyncMock()
        tracker.diff_files = AsyncMock(return_value=["agent/greeting.md"])
        mock_config_service.write = AsyncMock(side_effect=Exception("Storage error"))

        sync = SyncService(
            security_boundary=SecurityBoundary(),
            config_service=mock_config_service,
        )
        synced = await sync.sync_to_storage(
            user_id="user-1",
            git_tracker=tracker,
            user_dir=tmp_path,
        )
        # Should not raise, but file not in synced list
        assert synced == []
