"""ConfigHydrator — downloads user config from Supabase Storage to local disk."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Subdirectories to create in a fresh user tree.
_USER_TREE_DIRS = ["agents", "workflows", "preferences", "memory"]


class ConfigHydrator:
    """Hydrates a user's local config tree from Supabase Storage.

    Called on first provision when the user directory does not yet exist.
    After hydration an initial git commit records the state.
    """

    def __init__(self, config_service) -> None:  # noqa: ANN001 — avoid circular import
        self._config_service = config_service

    async def hydrate(self, user_id: str, user_dir: Path) -> None:
        """Download user config files and initialise a git repo.

        Raises on Storage unavailability so the caller can degrade
        gracefully.
        """
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create canonical subdirectories
        for subdir in _USER_TREE_DIRS:
            (user_dir / subdir).mkdir(exist_ok=True)

        # Pull files from Supabase Storage
        await self._download_files(user_id, user_dir)

        # Write .gitignore
        gitignore = user_dir / ".gitignore"
        gitignore.write_text("/tmp/\n*.pyc\n__pycache__/\n")

        # Initialise git repo + first commit
        await self._git_init(user_dir)

        logger.info("Hydrated user tree for %s at %s", user_id, user_dir)

    # -- internals ---------------------------------------------------------

    async def _download_files(self, user_id: str, user_dir: Path) -> None:
        """Fetch user-layer files from ConfigService."""
        try:
            paths = await self._config_service.list_paths("", user_id)
        except Exception:
            logger.warning("Could not list config paths for %s — empty tree", user_id)
            return

        for rel_path in paths:
            try:
                content = await self._config_service.read(rel_path, user_id)
                if content is not None:
                    local_path = user_dir / rel_path
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_text(content)
            except Exception:
                logger.warning("Failed to download %s for %s", rel_path, user_id, exc_info=True)

    async def _git_init(self, user_dir: Path) -> None:
        """``git init`` + initial commit in *user_dir*."""
        cmds = [
            ["git", "init"],
            ["git", "add", "-A"],
            ["git", "commit", "-m", "Initial hydration from Supabase Storage", "--allow-empty"],
        ]
        for cmd in cmds:
            proc = await asyncio.create_subprocess_exec(  # noqa: S603 — git init in controlled dir
                *cmd,
                cwd=str(user_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                logger.warning("git command failed in %s: %s (rc=%d)", user_dir, cmd, proc.returncode)
