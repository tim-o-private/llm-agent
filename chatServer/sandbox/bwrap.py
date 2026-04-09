"""BwrapSandbox — creates and manages a bubblewrap namespace for a user."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from .models import CommandResult

logger = logging.getLogger(__name__)

# Output truncation limit per stream (1 MB).
_MAX_OUTPUT_BYTES = 1_048_576
_TRUNCATED_MARKER = "\n[truncated]"
_MAX_TIMEOUT = 300.0


def _truncate(text: str) -> str:
    """Truncate output to the byte limit, appending a marker if needed."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return text
    truncated = encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return truncated + _TRUNCATED_MARKER


class BwrapSandbox:
    """Per-user bubblewrap namespace sandbox.

    Each ``execute()`` call spawns a fresh bwrap process sharing the same
    bind-mount layout — per-command isolation with a persistent user tree.
    """

    def __init__(
        self,
        user_dir: Path,
        system_dir: Path,
        bwrap_path: str = "bwrap",
    ) -> None:
        self._user_dir = user_dir
        self._system_dir = system_dir
        self._bwrap_path = bwrap_path

    # -- lifecycle ---------------------------------------------------------

    async def create(self) -> BwrapSandbox:
        """Validate prerequisites and prepare the sandbox for use."""
        bwrap = Path(self._bwrap_path)
        if not bwrap.exists():
            raise FileNotFoundError(f"bwrap binary not found: {self._bwrap_path}")
        if not os.access(bwrap, os.X_OK):
            raise PermissionError(f"bwrap binary not executable: {self._bwrap_path}")
        return self

    async def destroy(self) -> None:
        """Release any resources held by this sandbox.

        The user directory on disk is NOT deleted — it persists for the
        next session.
        """
        logger.info("Sandbox destroyed for user_dir=%s", self._user_dir)

    # -- command execution -------------------------------------------------

    async def execute(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
        cwd: str = "/user",
    ) -> CommandResult:
        """Run *command* inside a fresh bwrap namespace.

        Parameters
        ----------
        command:
            Shell command string passed to ``/bin/sh -c``.
        env:
            Extra environment variables merged into the subprocess env.
            Used for credential injection — tokens are per-invocation,
            never written to disk.
        timeout:
            Maximum wall-clock seconds.  Capped at 300 s.
        cwd:
            Working directory inside the namespace (default ``/user``).
        """
        timeout = min(timeout, _MAX_TIMEOUT)

        bwrap_args = self._build_bwrap_args(cwd) + ["--", "/bin/sh", "-c", command]

        proc_env = {**os.environ}
        if env:
            proc_env.update(env)

        proc = await asyncio.create_subprocess_exec(  # noqa: S603 — bwrap invocation, command is sandboxed
            *bwrap_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=proc_env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )
            return CommandResult(
                stdout=_truncate(stdout_bytes.decode("utf-8", errors="replace")),
                stderr=_truncate(stderr_bytes.decode("utf-8", errors="replace")),
                exit_code=proc.returncode or 0,
                timed_out=False,
            )
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            return CommandResult(
                stdout="",
                stderr="[timed out]",
                exit_code=-1,
                timed_out=True,
            )

    # -- internal ----------------------------------------------------------

    def _build_bwrap_args(self, cwd: str) -> list[str]:
        return [
            self._bwrap_path,
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind", str(self._system_dir), "/system",
            "--bind", str(self._user_dir), "/user",
            "--tmpfs", "/tmp",
            "--dev", "/dev",
            "--proc", "/proc",
            "--chdir", cwd,
        ]
