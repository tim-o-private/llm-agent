"""Config service — Supabase Storage with overlay resolution.

Reads config files from a Supabase Storage bucket with two layers:
  - /system/...  — read-only defaults (deployed as code)
  - /users/{user_id}/... — per-user mutable overrides

Overlay resolution: user path wins over system path.
Simple dict cache with invalidate-on-write (no TTL complexity).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from storage3.exceptions import StorageApiError

logger = logging.getLogger(__name__)

# Simple in-memory cache: (full_path) -> content string
_cache: Dict[str, Optional[str]] = {}

# Sentinel to distinguish "cached as None" from "not in cache"
_MISSING = object()


def _validate_path(path: str) -> None:
    """Reject path traversal attempts."""
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Invalid config path (traversal attempt): {path}")


class ConfigService:
    """Reads/writes config files from Supabase Storage with overlay resolution."""

    BUCKET = "config"

    def __init__(self, supabase_client: Any):
        """Initialize with an async Supabase client (service_role)."""
        self._client = supabase_client
        self._storage = supabase_client.storage

    def _bucket(self):
        """Get the bucket proxy for the config bucket."""
        return self._storage.from_(self.BUCKET)

    async def read(self, path: str, user_id: str) -> Optional[str]:
        """Read with overlay: user path -> system fallback."""
        content, _ = await self.read_with_source(path, user_id)
        return content

    async def read_with_source(self, path: str, user_id: str) -> Tuple[Optional[str], str]:
        """Read with overlay, returning (content, source).

        source is "user", "system", or "none".
        """
        _validate_path(path)

        # Try user path first
        user_full = f"users/{user_id}/{path}"
        content = await self._download(user_full)
        if content is not None:
            return content, "user"

        # Fall back to system path
        system_full = f"system/{path}"
        content = await self._download(system_full)
        if content is not None:
            return content, "system"

        return None, "none"

    async def write(self, path: str, user_id: str, content: str) -> None:
        """Write to user config layer. Invalidates cache."""
        _validate_path(path)
        user_full = f"users/{user_id}/{path}"

        bucket = self._bucket()
        await asyncio.to_thread(
            bucket.upload,
            path=user_full,
            file=content.encode("utf-8"),
            file_options={"content-type": self._content_type(path), "upsert": "true"},
        )

        # Bust cache for this path and the overlay key
        _cache.pop(user_full, None)
        logger.info("Config written: %s", user_full)

    async def write_system(self, path: str, content: str) -> None:
        """Write to system config layer (for seeding). Invalidates cache."""
        _validate_path(path)
        system_full = f"system/{path}"

        bucket = self._bucket()
        await asyncio.to_thread(
            bucket.upload,
            path=system_full,
            file=content.encode("utf-8"),
            file_options={"content-type": self._content_type(path), "upsert": "true"},
        )

        _cache.pop(system_full, None)
        logger.info("System config written: %s", system_full)

    async def list_paths(self, prefix: str, user_id: str) -> List[str]:
        """Merged listing — user paths shadow system paths with same relative name."""
        _validate_path(prefix)

        user_prefix = f"users/{user_id}/{prefix}"
        system_prefix = f"system/{prefix}"

        user_files = await self._list_files(user_prefix)
        system_files = await self._list_files(system_prefix)

        # Merge: user shadows system
        # Strip the layer prefix to get relative paths
        user_relative = {f.removeprefix(user_prefix) for f in user_files}
        system_relative = {f.removeprefix(system_prefix) for f in system_files}
        all_relative = user_relative | system_relative

        return sorted(f"{prefix}{rel}" for rel in all_relative)

    async def ensure_bucket(self) -> None:
        """Create the config bucket if it doesn't exist."""
        try:
            self._storage.get_bucket(self.BUCKET)
            logger.info("Config bucket already exists")
        except StorageApiError:
            self._storage.create_bucket(
                self.BUCKET,
                options={
                    "public": False,
                    "file_size_limit": 1048576,
                    "allowed_mime_types": ["text/plain", "text/markdown", "application/json"],
                },
            )
            logger.info("Created config bucket")

    def invalidate(self, path: str, user_id: str) -> None:
        """Invalidate cache for a specific user+path."""
        user_full = f"users/{user_id}/{path}"
        _cache.pop(user_full, None)

    def invalidate_all(self) -> None:
        """Clear entire config cache."""
        _cache.clear()

    # -- Internal helpers --

    async def _download(self, full_path: str) -> Optional[str]:
        """Download a file, returning None for 404. Caches results."""
        cached = _cache.get(full_path, _MISSING)
        if cached is not _MISSING:
            return cached

        try:
            bucket = self._bucket()
            data: bytes = await asyncio.to_thread(bucket.download, full_path)
            content = data.decode("utf-8")
            _cache[full_path] = content
            return content
        except StorageApiError as e:
            if "not found" in str(e).lower() or (hasattr(e, "status") and e.status == 404):
                _cache[full_path] = None
                return None
            logger.warning("Storage error downloading %s: %s", full_path, e)
            raise
        except Exception as e:
            logger.warning("Unexpected error downloading %s: %s", full_path, e)
            raise

    async def _list_files(self, prefix: str) -> List[str]:
        """List files under a prefix in the bucket."""
        try:
            # Split prefix into folder path and name prefix for Supabase list API
            # The list API takes a path (folder) and returns items in it
            bucket = self._bucket()
            items = await asyncio.to_thread(bucket.list, path=prefix)
            return [f"{prefix}{item['name']}" for item in items if item.get("name")]
        except StorageApiError as e:
            if "not found" in str(e).lower() or (hasattr(e, "status") and e.status == 404):
                return []
            logger.warning("Storage error listing %s: %s", prefix, e)
            raise
        except Exception as e:
            logger.warning("Unexpected error listing %s: %s", prefix, e)
            raise

    @staticmethod
    def _content_type(path: str) -> str:
        if path.endswith(".json"):
            return "application/json"
        if path.endswith(".md"):
            return "text/markdown"
        return "text/plain"


# -- Global instance management --

_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """Get the global ConfigService instance."""
    global _config_service
    if _config_service is None:
        raise RuntimeError("ConfigService not initialized. Call initialize_config_service() first.")
    return _config_service


async def initialize_config_service() -> None:
    """Initialize the global ConfigService from the Supabase manager."""
    global _config_service

    from ..database.supabase_client import get_supabase_manager

    manager = get_supabase_manager()
    await manager.ensure_initialized()
    client = manager.get_client()

    _config_service = ConfigService(client)
    await _config_service.ensure_bucket()
    logger.info("ConfigService initialized")


async def shutdown_config_service() -> None:
    """Shut down the ConfigService."""
    global _config_service
    if _config_service:
        _config_service.invalidate_all()
        _config_service = None
        logger.info("ConfigService shut down")
