"""Tests for StorageSync — Supabase Storage hydration and sync."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.storage_sync import BUCKET, StorageSync


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temp directory as the data root."""
    return tmp_path


@pytest.fixture
def mock_bucket():
    """Mock Supabase Storage bucket proxy."""
    bucket = MagicMock()
    bucket.list = AsyncMock(return_value=[])
    bucket.download = AsyncMock(return_value=b"")
    bucket.upload = AsyncMock()
    return bucket


@pytest.fixture
def mock_client(mock_bucket):
    """Mock async Supabase client."""
    client = MagicMock()
    client.storage.from_.return_value = mock_bucket
    return client


@pytest.fixture
def storage_sync(tmp_data_dir, mock_client):
    """StorageSync with mocked client."""
    sync = StorageSync("https://test.supabase.co", "test-key", data_dir=tmp_data_dir)
    sync._client = mock_client
    return sync


# -- hydrate_user --


@pytest.mark.asyncio
async def test_hydrate_user_downloads_files(storage_sync, mock_bucket, tmp_data_dir):
    """Files end up at correct local paths."""
    mock_bucket.list.side_effect = [
        # First call: list users/user-1/
        [
            {"name": "skills", "id": None},  # directory
            {"name": "prefs.json", "id": "abc123"},  # file
        ],
        # Second call: list users/user-1/skills/
        [
            {"name": "SKILL.md", "id": "def456"},
        ],
    ]
    mock_bucket.download.side_effect = [
        b'{"theme": "dark"}',
        b"# My Skill",
    ]

    user_dir = await storage_sync.hydrate_user("user-1")

    assert user_dir == tmp_data_dir / "sandboxes" / "user-1"
    assert (user_dir / "prefs.json").read_bytes() == b'{"theme": "dark"}'
    assert (user_dir / "skills" / "SKILL.md").read_bytes() == b"# My Skill"


@pytest.mark.asyncio
async def test_hydrate_user_creates_directories(storage_sync, mock_bucket, tmp_data_dir):
    """Parent directories are created as needed."""
    mock_bucket.list.side_effect = [
        [{"name": "deep", "id": None}],
        [{"name": "nested", "id": None}],
        [{"name": "file.txt", "id": "abc"}],
    ]
    mock_bucket.download.return_value = b"content"

    user_dir = await storage_sync.hydrate_user("user-2")

    assert (user_dir / "deep" / "nested" / "file.txt").exists()
    assert (user_dir / "deep" / "nested" / "file.txt").read_bytes() == b"content"


@pytest.mark.asyncio
async def test_hydrate_user_skips_populated_dir(storage_sync, mock_bucket, tmp_data_dir):
    """No-ops when directory already has content."""
    user_dir = tmp_data_dir / "sandboxes" / "user-3"
    user_dir.mkdir(parents=True)
    (user_dir / "existing.txt").write_text("already here")

    result = await storage_sync.hydrate_user("user-3")

    assert result == user_dir
    mock_bucket.list.assert_not_called()
    mock_bucket.download.assert_not_called()


@pytest.mark.asyncio
async def test_hydrate_user_creates_empty_dir_for_new_user(storage_sync, mock_bucket, tmp_data_dir):
    """Empty dir when Storage has no files for this user."""
    mock_bucket.list.return_value = []  # no files in Storage

    user_dir = await storage_sync.hydrate_user("new-user")

    assert user_dir.exists()
    assert user_dir.is_dir()
    assert list(user_dir.iterdir()) == []


# -- pull_system --


@pytest.mark.asyncio
async def test_pull_system_downloads_files(storage_sync, mock_bucket, tmp_data_dir):
    """Files end up at correct system paths."""
    mock_bucket.list.side_effect = [
        [
            {"name": "skills", "id": None},
        ],
        [
            {"name": "clarity-soul", "id": None},
        ],
        [
            {"name": "SKILL.md", "id": "abc"},
        ],
    ]
    mock_bucket.download.return_value = b"# Soul text"

    await storage_sync.pull_system()

    system_dir = tmp_data_dir / "config" / "system"
    assert (system_dir / "skills" / "clarity-soul" / "SKILL.md").read_bytes() == b"# Soul text"


@pytest.mark.asyncio
async def test_pull_system_overwrites_existing(storage_sync, mock_bucket, tmp_data_dir):
    """Overwrites existing files, doesn't skip."""
    system_dir = tmp_data_dir / "config" / "system"
    system_dir.mkdir(parents=True)
    target = system_dir / "config.json"
    target.write_text("old content")

    mock_bucket.list.return_value = [{"name": "config.json", "id": "abc"}]
    mock_bucket.download.return_value = b"new content"

    await storage_sync.pull_system()

    assert target.read_bytes() == b"new content"


# -- sync_file --


@pytest.mark.asyncio
async def test_sync_file_uploads(storage_sync, mock_bucket, tmp_data_dir):
    """Correct Storage path and upsert semantics."""
    user_dir = tmp_data_dir / "sandboxes" / "user-1"
    user_dir.mkdir(parents=True)
    (user_dir / "notes.md").write_text("hello")

    await storage_sync.sync_file("user-1", "notes.md")

    mock_bucket.upload.assert_called_once_with(
        path="users/user-1/notes.md",
        file=b"hello",
        file_options={"upsert": "true"},
    )


@pytest.mark.asyncio
async def test_sync_file_logs_on_failure(storage_sync, mock_bucket, tmp_data_dir, caplog):
    """Logs WARNING but doesn't raise on failure."""
    user_dir = tmp_data_dir / "sandboxes" / "user-1"
    user_dir.mkdir(parents=True)
    (user_dir / "notes.md").write_text("hello")

    mock_bucket.upload.side_effect = Exception("network error")

    with caplog.at_level(logging.WARNING):
        await storage_sync.sync_file("user-1", "notes.md")  # should not raise

    assert "Failed to sync" in caplog.text


@pytest.mark.asyncio
async def test_sync_file_correct_bucket(storage_sync, mock_client, mock_bucket, tmp_data_dir):
    """Uses the 'config' bucket."""
    user_dir = tmp_data_dir / "sandboxes" / "user-1"
    user_dir.mkdir(parents=True)
    (user_dir / "test.txt").write_text("data")

    await storage_sync.sync_file("user-1", "test.txt")

    mock_client.storage.from_.assert_called_with(BUCKET)


# -- _list_all_files --


@pytest.mark.asyncio
async def test_list_all_files_recursive(storage_sync, mock_bucket):
    """Recursively walks directories to find all files."""
    mock_bucket.list.side_effect = [
        # Root level
        [
            {"name": "file1.md", "id": "a"},
            {"name": "subdir", "id": None},
        ],
        # subdir level
        [
            {"name": "file2.md", "id": "b"},
        ],
    ]

    files = await storage_sync._list_all_files("prefix/")

    assert sorted(files) == ["prefix/file1.md", "prefix/subdir/file2.md"]


# -- init and client creation --


@pytest.mark.asyncio
async def test_ensure_client_creates_once(tmp_data_dir):
    """Client is created lazily and reused."""
    sync = StorageSync("https://test.supabase.co", "test-key", data_dir=tmp_data_dir)
    mock_client = MagicMock()

    with patch("chatServer.services.storage_sync.acreate_client", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_client

        client1 = await sync._ensure_client()
        client2 = await sync._ensure_client()

        assert client1 is mock_client
        assert client2 is mock_client
        mock_create.assert_called_once_with("https://test.supabase.co", "test-key")
