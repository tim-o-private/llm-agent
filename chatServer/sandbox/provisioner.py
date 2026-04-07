"""SandboxProvisioner — manages per-user sandbox lifecycle."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .bwrap import BwrapSandbox
from .hydrator import ConfigHydrator
from .models import SandboxConfig

logger = logging.getLogger(__name__)


class SandboxNotAvailableError(Exception):
    """Raised when sandbox functionality is disabled or unavailable."""


class SandboxProvisioner:
    """Provisions, caches, and tears down per-user bwrap sandboxes.

    Only one sandbox per user is active at a time.  ``get_or_create``
    returns the cached instance if one exists.
    """

    def __init__(
        self,
        config: SandboxConfig,
        config_service=None,  # noqa: ANN001 — ConfigService, optional to avoid circular import
    ) -> None:
        self._config = config
        self._active: dict[str, BwrapSandbox] = {}
        self._lock = asyncio.Lock()
        self._hydrator = ConfigHydrator(config_service) if config_service else None

    # -- public API --------------------------------------------------------

    async def provision(self, user_id: str) -> BwrapSandbox:
        """Create a new sandbox for *user_id*.

        * Creates the user directory if it doesn't exist.
        * Hydrates from ConfigService on first provision.
        * Initialises a git repo in the user directory.
        * Validates bwrap and returns a ready-to-use sandbox.
        """
        if not self._config.enabled:
            raise SandboxNotAvailableError("Sandbox functionality is disabled (BWRAP_ENABLED=false)")

        async with self._lock:
            user_dir = self._config.users_path / user_id
            system_dir = self._config.system_path
            tools_dir = self._config.tools_path

            # Hydrate on first provision
            if not user_dir.exists() and self._hydrator:
                await self._hydrator.hydrate(user_id, user_dir)
            elif not user_dir.exists():
                # No hydrator — just create the bare directory + git init
                user_dir.mkdir(parents=True, exist_ok=True)
                await self._bare_git_init(user_dir)

            sandbox = BwrapSandbox(
                user_dir=user_dir,
                system_dir=system_dir,
                tools_dir=tools_dir,
                bwrap_path=self._config.bwrap_binary,
            )
            await sandbox.create()
            self._active[user_id] = sandbox
            logger.info("Provisioned sandbox for user %s", user_id)
            return sandbox

    async def get_or_create(self, user_id: str) -> BwrapSandbox:
        """Return existing sandbox or provision a new one."""
        if user_id in self._active:
            return self._active[user_id]
        return await self.provision(user_id)

    async def destroy(self, user_id: str) -> None:
        """Tear down sandbox for *user_id*.

        The user directory on disk is NOT deleted.
        """
        async with self._lock:
            sandbox = self._active.pop(user_id, None)
            if sandbox:
                await sandbox.destroy()
                logger.info("Destroyed sandbox for user %s", user_id)

    async def destroy_all(self) -> None:
        """Tear down all active sandboxes (shutdown hook)."""
        user_ids = list(self._active.keys())
        for uid in user_ids:
            await self.destroy(uid)

    async def verify_user_repos(self) -> list[str]:
        """Scan existing user dirs and verify git integrity.

        Returns a list of user_ids with corrupted repos.
        """
        corrupted: list[str] = []
        users_dir = self._config.users_path
        if not users_dir.exists():
            return corrupted

        for entry in users_dir.iterdir():
            if not entry.is_dir():
                continue
            git_dir = entry / ".git"
            if not git_dir.exists():
                continue
            proc = await asyncio.create_subprocess_exec(  # noqa: S603 — git fsck in user dir
                "git", "fsck", "--quick",
                cwd=str(entry),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    "Corrupted git repo for user %s: %s",
                    entry.name,
                    stderr_bytes.decode("utf-8", errors="replace"),
                )
                corrupted.append(entry.name)

        return corrupted

    @property
    def active_sandboxes(self) -> dict[str, BwrapSandbox]:
        """Read-only view of currently active sandboxes."""
        return dict(self._active)

    # -- internals ---------------------------------------------------------

    def get_user_dir(self, user_id: str) -> Path:
        """Return the local directory for a user's sandbox tree."""
        return self._config.users_path / user_id

    @staticmethod
    async def _bare_git_init(user_dir: Path) -> None:
        gitignore = user_dir / ".gitignore"
        gitignore.write_text("/tmp/\n*.pyc\n__pycache__/\n")

        cmds = [
            ["git", "init"],
            ["git", "add", "-A"],
            ["git", "commit", "-m", "Initial empty sandbox", "--allow-empty"],
        ]
        for cmd in cmds:
            proc = await asyncio.create_subprocess_exec(  # noqa: S603 — git init in controlled dir
                *cmd,
                cwd=str(user_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()


# -- Global instance management --

_provisioner: Optional[SandboxProvisioner] = None


def get_provisioner() -> SandboxProvisioner:
    """Get the global SandboxProvisioner instance."""
    global _provisioner
    if _provisioner is None:
        raise RuntimeError(
            "SandboxProvisioner not initialized. Call initialize_provisioner() first."
        )
    return _provisioner


def initialize_provisioner(
    config_service=None,  # noqa: ANN001 — ConfigService, avoids circular import
) -> None:
    """Initialize the global SandboxProvisioner from settings."""
    global _provisioner
    from pathlib import Path as _Path  # noqa: PLC0415 — lazy import to avoid circular

    from ..config.settings import get_settings
    from .models import SandboxConfig

    settings = get_settings()
    config = SandboxConfig(
        enabled=settings.sandbox_enabled,
        base_path=_Path(settings.sandbox_base_path),
        system_path=_Path(settings.sandbox_system_path),
        bwrap_binary=settings.bwrap_binary,
    )
    _provisioner = SandboxProvisioner(config, config_service=config_service)
    logger.info("SandboxProvisioner initialized (enabled=%s)", config.enabled)


async def shutdown_provisioner() -> None:
    """Shut down the global SandboxProvisioner, destroying all active sandboxes."""
    global _provisioner
    if _provisioner:
        await _provisioner.destroy_all()
        _provisioner = None
        logger.info("SandboxProvisioner shut down")
