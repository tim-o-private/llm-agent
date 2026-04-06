"""Tests for ConfigService — overlay resolution, caching, path protection."""

from unittest.mock import MagicMock

import pytest

from chatServer.services.config_service import ConfigService, _cache, _validate_path


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the module-level cache before each test."""
    _cache.clear()
    yield
    _cache.clear()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with storage bucket proxy."""
    client = MagicMock()
    bucket_proxy = MagicMock()
    client.storage.from_.return_value = bucket_proxy
    client.storage.get_bucket = MagicMock()
    client.storage.create_bucket = MagicMock()
    return client, bucket_proxy


@pytest.fixture
def config_service(mock_supabase):
    client, _ = mock_supabase
    return ConfigService(client)


# -- Path validation --

def test_validate_path_rejects_traversal():
    with pytest.raises(ValueError, match="traversal"):
        _validate_path("../etc/passwd")


def test_validate_path_rejects_double_dot_in_middle():
    with pytest.raises(ValueError, match="traversal"):
        _validate_path("agents/../secrets/key")


def test_validate_path_rejects_leading_slash():
    with pytest.raises(ValueError, match="traversal"):
        _validate_path("/etc/passwd")


def test_validate_path_accepts_normal_paths():
    _validate_path("agents/clarity/soul.md")
    _validate_path("agent/instructions.md")
    _validate_path("agents/clarity/identity.json")


# -- Overlay resolution --

@pytest.mark.asyncio
async def test_read_returns_user_file_when_both_exist(config_service, mock_supabase):
    """User layer wins over system layer."""
    _, bucket = mock_supabase

    def download_side_effect(path):
        if path == "users/user-1/agents/clarity/soul.md":
            return b"user soul"
        if path == "system/agents/clarity/soul.md":
            return b"system soul"
        raise Exception("unexpected path")

    bucket.download.side_effect = download_side_effect

    result = await config_service.read("agents/clarity/soul.md", "user-1")
    assert result == "user soul"


@pytest.mark.asyncio
async def test_read_falls_back_to_system_when_no_user_file(config_service, mock_supabase):
    """Falls back to system layer when user file doesn't exist."""
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase

    def download_side_effect(path):
        if path.startswith("users/"):
            raise StorageApiError("Object not found", "not_found", 404)
        if path == "system/agents/clarity/soul.md":
            return b"system soul"
        raise Exception("unexpected path")

    bucket.download.side_effect = download_side_effect

    result = await config_service.read("agents/clarity/soul.md", "user-1")
    assert result == "system soul"


@pytest.mark.asyncio
async def test_read_returns_none_when_neither_exists(config_service, mock_supabase):
    """Returns None when neither user nor system file exists."""
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase
    bucket.download.side_effect = StorageApiError("Object not found", "not_found", 404)

    result = await config_service.read("agents/clarity/soul.md", "user-1")
    assert result is None


@pytest.mark.asyncio
async def test_read_with_source_user(config_service, mock_supabase):
    _, bucket = mock_supabase
    bucket.download.return_value = b"user content"

    content, source = await config_service.read_with_source("agents/clarity/soul.md", "user-1")
    assert content == "user content"
    assert source == "user"


@pytest.mark.asyncio
async def test_read_with_source_system(config_service, mock_supabase):
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase

    def download_side_effect(path):
        if path.startswith("users/"):
            raise StorageApiError("Object not found", "not_found", 404)
        return b"system content"

    bucket.download.side_effect = download_side_effect

    content, source = await config_service.read_with_source("agents/clarity/soul.md", "user-1")
    assert content == "system content"
    assert source == "system"


@pytest.mark.asyncio
async def test_read_with_source_none(config_service, mock_supabase):
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase
    bucket.download.side_effect = StorageApiError("Object not found", "not_found", 404)

    content, source = await config_service.read_with_source("agents/clarity/soul.md", "user-1")
    assert content is None
    assert source == "none"


# -- Write --

@pytest.mark.asyncio
async def test_write_uploads_to_user_path(config_service, mock_supabase):
    _, bucket = mock_supabase

    await config_service.write("agent/instructions.md", "user-1", "my instructions")

    bucket.upload.assert_called_once_with(
        path="users/user-1/agent/instructions.md",
        file=b"my instructions",
        file_options={"content-type": "text/markdown", "upsert": "true"},
    )


@pytest.mark.asyncio
async def test_write_invalidates_cache(config_service, mock_supabase):
    """Writing busts the cache for that path."""
    _, bucket = mock_supabase

    # Prime cache
    _cache["users/user-1/agent/instructions.md"] = "old instructions"

    await config_service.write("agent/instructions.md", "user-1", "new instructions")

    assert "users/user-1/agent/instructions.md" not in _cache


@pytest.mark.asyncio
async def test_write_rejects_path_traversal(config_service):
    with pytest.raises(ValueError, match="traversal"):
        await config_service.write("../secret", "user-1", "evil")


# -- Write system --

@pytest.mark.asyncio
async def test_write_system_uploads_to_system_path(config_service, mock_supabase):
    _, bucket = mock_supabase

    await config_service.write_system("agents/clarity/soul.md", "# Soul text")

    bucket.upload.assert_called_once_with(
        path="system/agents/clarity/soul.md",
        file=b"# Soul text",
        file_options={"content-type": "text/markdown", "upsert": "true"},
    )


# -- Caching --

@pytest.mark.asyncio
async def test_download_caches_result(config_service, mock_supabase):
    """Second read for same path hits cache, not storage."""
    _, bucket = mock_supabase
    bucket.download.return_value = b"cached content"

    result1 = await config_service.read("agents/clarity/soul.md", "user-1")
    result2 = await config_service.read("agents/clarity/soul.md", "user-1")

    assert result1 == result2 == "cached content"
    # download called once for user path (first call), then cached
    assert bucket.download.call_count == 1


@pytest.mark.asyncio
async def test_download_caches_none_for_404(config_service, mock_supabase):
    """404 results are cached as None to avoid repeated lookups."""
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase
    bucket.download.side_effect = StorageApiError("Object not found", "not_found", 404)

    result1 = await config_service.read("nonexistent.md", "user-1")
    result2 = await config_service.read("nonexistent.md", "user-1")

    assert result1 is None
    assert result2 is None
    # download called twice for first call (user + system), then both cached
    assert bucket.download.call_count == 2


# -- Cache invalidation --

def test_invalidate_clears_user_path(config_service):
    _cache["users/user-1/agent/instructions.md"] = "old"
    _cache["system/agents/clarity/soul.md"] = "system soul"

    config_service.invalidate("agent/instructions.md", "user-1")

    assert "users/user-1/agent/instructions.md" not in _cache
    assert "system/agents/clarity/soul.md" in _cache


def test_invalidate_all_clears_everything(config_service):
    _cache["users/user-1/agent/instructions.md"] = "old"
    _cache["system/agents/clarity/soul.md"] = "system"

    config_service.invalidate_all()

    assert len(_cache) == 0


# -- Error handling --

@pytest.mark.asyncio
async def test_download_reraises_non_404_storage_errors(config_service, mock_supabase):
    """Non-404 StorageApiErrors are re-raised, not swallowed."""
    from storage3.exceptions import StorageApiError

    _, bucket = mock_supabase
    bucket.download.side_effect = StorageApiError("Permission denied", "forbidden", 403)

    with pytest.raises(StorageApiError):
        await config_service._download("system/agents/clarity/soul.md")


@pytest.mark.asyncio
async def test_download_reraises_unexpected_errors(config_service, mock_supabase):
    """Non-storage exceptions are re-raised."""
    _, bucket = mock_supabase
    bucket.download.side_effect = ConnectionError("network failure")

    with pytest.raises(ConnectionError):
        await config_service._download("system/agents/clarity/soul.md")


# -- Ensure bucket --

@pytest.mark.asyncio
async def test_ensure_bucket_creates_when_not_exists(config_service, mock_supabase):
    from storage3.exceptions import StorageApiError

    client, _ = mock_supabase
    client.storage.get_bucket.side_effect = StorageApiError("not found", "not_found", 404)

    await config_service.ensure_bucket()

    client.storage.create_bucket.assert_called_once_with(
        "config",
        options={
            "public": False,
            "file_size_limit": 1048576,
            "allowed_mime_types": ["text/plain", "text/markdown", "application/json"],
        },
    )


@pytest.mark.asyncio
async def test_ensure_bucket_noop_when_exists(config_service, mock_supabase):
    client, _ = mock_supabase
    client.storage.get_bucket.return_value = {"id": "config", "name": "config"}

    await config_service.ensure_bucket()

    client.storage.create_bucket.assert_not_called()


# -- Content type --

def test_content_type_json():
    assert ConfigService._content_type("identity.json") == "application/json"


def test_content_type_markdown():
    assert ConfigService._content_type("soul.md") == "text/markdown"


def test_content_type_plain():
    assert ConfigService._content_type("config.txt") == "text/plain"
    assert ConfigService._content_type("config.yaml") == "text/plain"


# -- List paths --

@pytest.mark.asyncio
async def test_list_paths_merges_user_and_system(config_service, mock_supabase):
    """User paths shadow system paths; unique paths from both appear."""
    _, bucket = mock_supabase

    def list_side_effect(path=None):
        if path and path.startswith("users/"):
            return [{"name": "soul.md"}, {"name": "custom.md"}]
        if path and path.startswith("system/"):
            return [{"name": "soul.md"}, {"name": "identity.json"}]
        return []

    bucket.list.side_effect = list_side_effect

    paths = await config_service.list_paths("agents/clarity/", "user-1")

    assert sorted(paths) == [
        "agents/clarity/custom.md",
        "agents/clarity/identity.json",
        "agents/clarity/soul.md",
    ]


# -- Global instance management --

@pytest.mark.asyncio
async def test_get_config_service_raises_before_init():
    import chatServer.services.config_service as mod
    from chatServer.services.config_service import get_config_service
    original = mod._config_service
    mod._config_service = None

    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            get_config_service()
    finally:
        mod._config_service = original
