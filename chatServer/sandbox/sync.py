"""SyncService — syncs sandbox /user/ changes to Supabase Storage."""

from __future__ import annotations

import logging
from pathlib import Path

from .git_tracker import GitTracker
from .security_boundary import SecurityBoundary

logger = logging.getLogger(__name__)


class SyncService:
    """Syncs changed files from the sandbox git repo back to Supabase Storage.

    Called after every approved commit to keep Storage in sync with
    the on-disk user tree.
    """

    def __init__(
        self,
        security_boundary: SecurityBoundary,
        config_service=None,  # noqa: ANN001 — ConfigService, optional
    ) -> None:
        self._boundary = security_boundary
        self._config_service = config_service

    async def sync_to_storage(
        self,
        user_id: str,
        git_tracker: GitTracker,
        user_dir: Path,
        commit_hash: str | None = None,
    ) -> list[str]:
        """Sync changed files from *commit_hash* to Supabase Storage.

        Returns list of successfully synced file paths.
        """
        if not self._config_service:
            logger.warning("No ConfigService — skipping sync for user %s", user_id)
            return []

        changed_files = await git_tracker.diff_files(commit_hash)
        synced: list[str] = []

        for rel_path in changed_files:
            sandbox_path = f"/user/{rel_path}"

            # Security check: only sync mutable paths
            if not self._boundary.validate_write(sandbox_path):
                logger.error(
                    "Refusing to sync immutable path %s for user %s",
                    sandbox_path,
                    user_id,
                )
                continue

            local_file = user_dir / rel_path
            if not local_file.exists():
                # File was deleted — remove from storage
                try:
                    await self._config_service.delete(rel_path, user_id)
                    synced.append(rel_path)
                    logger.debug("Deleted %s from storage for user %s", rel_path, user_id)
                except Exception:
                    logger.warning("Failed to delete %s from storage", rel_path, exc_info=True)
                continue

            try:
                content = local_file.read_text(encoding="utf-8")
                await self._config_service.write(rel_path, user_id, content)
                synced.append(rel_path)
                logger.debug("Synced %s to storage for user %s", rel_path, user_id)
            except Exception:
                logger.warning("Failed to sync %s to storage", rel_path, exc_info=True)

        return synced
