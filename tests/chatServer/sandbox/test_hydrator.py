"""Tests for ConfigHydrator — downloads config from Storage to local disk."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from chatServer.sandbox.hydrator import ConfigHydrator, _USER_TREE_DIRS


@pytest.fixture
def mock_config_service():
    svc = AsyncMock()
    svc.list_paths = AsyncMock(return_value=[])
    svc.read = AsyncMock(return_value=None)
    return svc


@pytest.fixture
def hydrator(mock_config_service):
    return ConfigHydrator(mock_config_service)


class TestHydrate:
    @pytest.mark.asyncio
    async def test_creates_user_dir(self, hydrator, tmp_path):
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        assert user_dir.exists()

    @pytest.mark.asyncio
    async def test_creates_subdirectories(self, hydrator, tmp_path):
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        for subdir in _USER_TREE_DIRS:
            assert (user_dir / subdir).is_dir()

    @pytest.mark.asyncio
    async def test_creates_gitignore(self, hydrator, tmp_path):
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        gitignore = user_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "/tmp/" in content
        assert "*.pyc" in content
        assert "__pycache__/" in content

    @pytest.mark.asyncio
    async def test_downloads_files_from_storage(self, mock_config_service, tmp_path):
        mock_config_service.list_paths.return_value = ["agents/clarity/soul.md", "preferences/theme.json"]
        mock_config_service.read.side_effect = lambda path, uid: f"content of {path}"

        hydrator = ConfigHydrator(mock_config_service)
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        assert (user_dir / "agents" / "clarity" / "soul.md").read_text() == "content of agents/clarity/soul.md"
        assert (user_dir / "preferences" / "theme.json").read_text() == "content of preferences/theme.json"

    @pytest.mark.asyncio
    async def test_calls_git_init(self, hydrator, tmp_path):
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        # Should have called git init, git add, git commit
        assert mock_git.call_count == 3
        calls = [c.args for c in mock_git.call_args_list]
        assert calls[0] == ("git", "init")
        assert calls[1] == ("git", "add", "-A")
        assert calls[2][:2] == ("git", "commit")

    @pytest.mark.asyncio
    async def test_handles_storage_list_failure(self, mock_config_service, tmp_path):
        """If list_paths fails, hydration continues with an empty tree."""
        mock_config_service.list_paths.side_effect = ConnectionError("unreachable")

        hydrator = ConfigHydrator(mock_config_service)
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        # Dir was still created with subdirs
        assert user_dir.exists()
        for subdir in _USER_TREE_DIRS:
            assert (user_dir / subdir).is_dir()

    @pytest.mark.asyncio
    async def test_handles_individual_file_download_failure(self, mock_config_service, tmp_path):
        """If one file fails to download, others still succeed."""
        mock_config_service.list_paths.return_value = ["good.md", "bad.md"]

        def read_side_effect(path, uid):
            if path == "bad.md":
                raise ConnectionError("download failed")
            return f"content of {path}"

        mock_config_service.read.side_effect = read_side_effect

        hydrator = ConfigHydrator(mock_config_service)
        user_dir = tmp_path / "user-1"

        with patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await hydrator.hydrate("user-1", user_dir)

        assert (user_dir / "good.md").read_text() == "content of good.md"
        assert not (user_dir / "bad.md").exists()
