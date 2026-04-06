"""GitTracker — manages the git repo in a user's /user/ directory."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_AUTHOR = "Clarity Agent <agent@clarity.app>"


@dataclass
class CommitInfo:
    """Lightweight representation of a git commit."""

    sha: str
    message: str
    timestamp: str = ""
    files: list[str] | None = None


class GitTracker:
    """Thin async wrapper around git CLI for sandbox user directories.

    All operations target a specific *user_dir* and run via
    ``asyncio.create_subprocess_exec``.
    """

    def __init__(self, user_dir: Path) -> None:
        self._user_dir = user_dir

    # -- public API -----------------------------------------------------------

    async def commit(self, message: str) -> CommitInfo | None:
        """Stage all changes and commit.  Returns CommitInfo or None if nothing to commit."""
        await self._run("git", "add", "-A")
        rc, stdout, _ = await self._run(
            "git", "diff", "--cached", "--quiet",
        )
        if rc == 0:
            # Nothing staged
            return None

        await self._run(
            "git", "commit",
            "-m", message,
            "--author", _AUTHOR,
        )
        return await self._head_commit()

    async def log(self, limit: int = 20) -> list[CommitInfo]:
        """Return recent commits (newest first)."""
        rc, stdout, _ = await self._run(
            "git", "log",
            f"--max-count={limit}",
            "--format=%H|%s|%aI",
        )
        if rc != 0 or not stdout.strip():
            return []

        commits: list[CommitInfo] = []
        for line in stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append(CommitInfo(sha=parts[0], message=parts[1], timestamp=parts[2]))
        return commits

    async def diff(self, commit_hash: str | None = None) -> str:
        """Show diff for *commit_hash* (default: last commit vs its parent)."""
        if commit_hash:
            _, stdout, _ = await self._run("git", "diff", f"{commit_hash}~1", commit_hash)
        else:
            _, stdout, _ = await self._run("git", "diff", "HEAD~1", "HEAD")
        return stdout

    async def diff_files(self, commit_hash: str | None = None) -> list[str]:
        """Return list of files changed in *commit_hash* (default: last commit)."""
        if commit_hash:
            _, stdout, _ = await self._run("git", "diff", "--name-only", f"{commit_hash}~1", commit_hash)
        else:
            _, stdout, _ = await self._run("git", "diff", "--name-only", "HEAD~1", "HEAD")
        return [f for f in stdout.strip().splitlines() if f]

    async def revert(self, commit_hash: str) -> CommitInfo | None:
        """Revert a specific commit. Returns the revert commit or None on failure."""
        rc, _, stderr = await self._run("git", "revert", "--no-edit", commit_hash)
        if rc != 0:
            logger.error("git revert failed for %s: %s", commit_hash, stderr)
            return None
        return await self._head_commit()

    async def get_head_sha(self) -> str | None:
        """Return the SHA of HEAD, or None if no commits."""
        rc, stdout, _ = await self._run("git", "rev-parse", "HEAD")
        if rc != 0:
            return None
        return stdout.strip()

    async def get_changelog(self, since: str | None = None) -> str:
        """Human-readable changelog.  Optionally since a commit SHA."""
        if since:
            rc, stdout, _ = await self._run(
                "git", "log",
                f"{since}..HEAD",
                "--format=- %s (%h, %ar)",
            )
        else:
            rc, stdout, _ = await self._run(
                "git", "log",
                "--max-count=50",
                "--format=- %s (%h, %ar)",
            )
        if rc != 0:
            return ""
        return stdout.strip()

    # -- internals ------------------------------------------------------------

    async def _head_commit(self) -> CommitInfo | None:
        rc, stdout, _ = await self._run("git", "log", "-1", "--format=%H|%s|%aI")
        if rc != 0 or not stdout.strip():
            return None
        parts = stdout.strip().split("|", 2)
        if len(parts) == 3:
            return CommitInfo(sha=parts[0], message=parts[1], timestamp=parts[2])
        return None

    async def _run(self, *args: str) -> tuple[int, str, str]:
        """Run a git command in the user directory.

        Uses create_subprocess_exec (not shell) to avoid injection.
        """
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(self._user_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={
                "GIT_AUTHOR_NAME": "Clarity Agent",
                "GIT_AUTHOR_EMAIL": "agent@clarity.app",
                "GIT_COMMITTER_NAME": "Clarity Agent",
                "GIT_COMMITTER_EMAIL": "agent@clarity.app",
                "HOME": str(self._user_dir),
                "PATH": "/usr/bin:/bin",
            },
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        )
