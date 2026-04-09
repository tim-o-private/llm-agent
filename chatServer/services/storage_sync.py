"""StorageSync -- thin Supabase Storage utility for sandbox file hydration.

Downloads config from Supabase Storage to local disk (hydrate/pull) and
uploads changed files back (sync). No overlay logic, no caching.
"""

import logging
from pathlib import Path

from supabase import acreate_client

logger = logging.getLogger(__name__)

BUCKET = "config"


class StorageSync:
    """Thin Supabase Storage utility for hydrating and syncing sandbox files."""

    def __init__(self, supabase_url: str, supabase_key: str, data_dir: Path = Path("/data")):
        self._url = supabase_url
        self._key = supabase_key
        self._data_dir = data_dir
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            self._client = await acreate_client(self._url, self._key)
        return self._client

    async def _list_all_files(self, prefix: str) -> list[str]:
        """Recursively list all file paths under *prefix* in the config bucket."""
        client = await self._ensure_client()
        bucket = client.storage.from_(BUCKET)
        result: list[str] = []
        stack = [prefix]
        while stack:
            current = stack.pop()
            try:
                items = await bucket.list(path=current)
            except Exception:
                logger.warning("Failed to list %s", current, exc_info=True)
                continue
            for item in items:
                name = item.get("name", "")
                if not name:
                    continue
                full = f"{current}{name}" if current.endswith("/") else f"{current}/{name}"
                if item.get("id") is None:
                    # Directory -- recurse
                    stack.append(full + "/")
                else:
                    result.append(full)
        return result

    async def hydrate_user(self, user_id: str) -> Path:
        """Download user files from Storage to local sandbox dir.

        No-ops if target directory already has content (local disk is
        source of truth once populated).

        Returns the path to the user's sandbox directory.
        """
        user_dir = self._data_dir / "sandboxes" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        if any(user_dir.iterdir()):
            logger.info("User dir already populated, skipping hydration: %s", user_dir)
            return user_dir

        prefix = f"users/{user_id}/"
        files = await self._list_all_files(prefix)
        client = await self._ensure_client()
        bucket = client.storage.from_(BUCKET)

        for storage_path in files:
            relative = storage_path.removeprefix(prefix)
            local_path = user_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = await bucket.download(storage_path)
                local_path.write_bytes(data)
                logger.debug("Downloaded %s -> %s", storage_path, local_path)
            except Exception:
                logger.warning("Failed to download %s", storage_path, exc_info=True)

        logger.info("Hydrated %d files for user %s", len(files), user_id)
        return user_dir

    async def pull_system(self) -> None:
        """Download system config from Storage to local config dir.

        Overwrites existing files (Storage is authoritative for system config).
        """
        system_dir = self._data_dir / "config" / "system"
        system_dir.mkdir(parents=True, exist_ok=True)

        prefix = "system/"
        files = await self._list_all_files(prefix)
        client = await self._ensure_client()
        bucket = client.storage.from_(BUCKET)

        for storage_path in files:
            relative = storage_path.removeprefix(prefix)
            local_path = system_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                data = await bucket.download(storage_path)
                local_path.write_bytes(data)
                logger.debug("Downloaded %s -> %s", storage_path, local_path)
            except Exception:
                logger.warning("Failed to download %s", storage_path, exc_info=True)

        logger.info("Pulled %d system config files", len(files))

    async def sync_file(self, user_id: str, relative_path: str) -> None:
        """Upload a single changed file back to Storage.

        Fire-and-forget: logs WARNING on failure but never raises.
        """
        local_path = self._data_dir / "sandboxes" / user_id / relative_path
        storage_path = f"users/{user_id}/{relative_path}"
        try:
            client = await self._ensure_client()
            bucket = client.storage.from_(BUCKET)
            data = local_path.read_bytes()
            await bucket.upload(
                path=storage_path,
                file=data,
                file_options={"upsert": "true"},
            )
            logger.info("Synced %s -> %s", local_path, storage_path)
        except Exception:
            logger.warning("Failed to sync %s to Storage", relative_path, exc_info=True)
