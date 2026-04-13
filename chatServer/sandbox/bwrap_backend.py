"""BwrapBackend — BaseSandbox subclass using bubblewrap for OS-level isolation.

Implements ``execute()``, ``upload_files()``, ``download_files()``, and the
``id`` property. All 6 ``BackendProtocol`` file operations (ls, read, write,
edit, grep, glob) are inherited from ``BaseSandbox`` and run shell commands
inside the bwrap namespace via ``execute()``.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox

logger = logging.getLogger(__name__)

_MAX_OUTPUT_BYTES = 1_048_576  # 1 MB
_DEFAULT_TIMEOUT = 120  # seconds


class BwrapBackend(BaseSandbox):
    """Per-user bubblewrap sandbox backend.

    Each ``execute()`` call spawns a fresh bwrap namespace with:

    - ``/system`` — read-only system config (skills, templates)
    - ``/user``   — read-write user config (preferences, notes)
    - ``/usr``, ``/bin``, ``/lib`` — read-only host system dirs (python3, coreutils)

    File operations are provided by ``BaseSandbox`` via shell commands.
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

    # -- abstract implementations ------------------------------------------

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Run *command* inside a fresh bwrap namespace.

        Uses ``subprocess.run()`` synchronously. ``BaseSandbox.aexecute()``
        calls this via ``asyncio.to_thread()``.
        """
        effective_timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
        bwrap_args = self._build_bwrap_args() + ["--", "/bin/sh", "-c", command]

        try:
            result = subprocess.run(  # noqa: S603 — bwrap invocation, command is sandboxed
                bwrap_args,
                capture_output=True,
                timeout=effective_timeout,
                text=True,
            )
        except FileNotFoundError:
            return ExecuteResponse(output="bwrap not found", exit_code=-1)
        except subprocess.TimeoutExpired:
            return ExecuteResponse(output="[timed out]", exit_code=-1)

        combined = result.stdout + result.stderr
        truncated = len(combined.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        if truncated:
            combined = combined.encode("utf-8", errors="replace")[:_MAX_OUTPUT_BYTES].decode(
                "utf-8", errors="replace"
            )

        return ExecuteResponse(
            output=combined,
            exit_code=result.returncode,
            truncated=truncated,
        )

    def upload_files(
        self, files: list[tuple[str, bytes]]
    ) -> list[FileUploadResponse]:
        """Write files directly to the host filesystem (bind-mounted into namespace)."""
        responses: list[FileUploadResponse] = []
        for sandbox_path, content in files:
            host_path = self._resolve_upload_path(sandbox_path)
            if host_path is None:
                responses.append(
                    FileUploadResponse(path=sandbox_path, error="permission_denied")
                )
                continue
            try:
                host_path.parent.mkdir(parents=True, exist_ok=True)
                host_path.write_bytes(content)
                responses.append(FileUploadResponse(path=sandbox_path))
            except OSError as exc:
                responses.append(
                    FileUploadResponse(path=sandbox_path, error=str(exc))
                )
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Read files from the host filesystem."""
        responses: list[FileDownloadResponse] = []
        for sandbox_path in paths:
            host_path = self._resolve_download_path(sandbox_path)
            if host_path is None:
                responses.append(
                    FileDownloadResponse(path=sandbox_path, error="invalid_path")
                )
                continue
            try:
                content = host_path.read_bytes()
                responses.append(
                    FileDownloadResponse(path=sandbox_path, content=content)
                )
            except FileNotFoundError:
                responses.append(
                    FileDownloadResponse(path=sandbox_path, error="file_not_found")
                )
            except OSError as exc:
                responses.append(
                    FileDownloadResponse(path=sandbox_path, error=str(exc))
                )
        return responses

    @property
    def id(self) -> str:
        """Deterministic identifier based on user_dir path."""
        return f"bwrap:{self._user_dir}"

    # -- internal ----------------------------------------------------------

    def _build_bwrap_args(self) -> list[str]:
        args = [
            self._bwrap_path,
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind", str(self._system_dir), "/system",
            "--bind", str(self._user_dir), "/user",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib",
        ]
        if Path("/lib64").exists():
            args.extend(["--ro-bind", "/lib64", "/lib64"])
        args.extend([
            "--tmpfs", "/tmp",
            "--dev", "/dev",
            "--proc", "/proc",
            "--chdir", "/user",
        ])
        return args

    def _resolve_upload_path(self, sandbox_path: str) -> Path | None:
        """Map a sandbox path to a host path for uploads.

        Only ``/user/...`` paths are writable. ``/system/...`` is read-only.
        Paths under ``/tmp/`` are mapped to a ``.tmp`` subdirectory of
        ``user_dir`` for ``BaseSandbox._edit_via_upload`` temp-file support.
        """
        if sandbox_path.startswith("/user/"):
            relative = sandbox_path[len("/user/"):]
            return self._user_dir / relative
        if sandbox_path == "/user":
            return self._user_dir
        # /tmp paths used by BaseSandbox._edit_via_upload
        if sandbox_path.startswith("/tmp/"):
            relative = sandbox_path[len("/tmp/"):]
            return self._user_dir / ".tmp" / relative
        # /system is read-only — reject uploads
        return None

    def _resolve_download_path(self, sandbox_path: str) -> Path | None:
        """Map a sandbox path to a host path for downloads."""
        if sandbox_path.startswith("/user/"):
            relative = sandbox_path[len("/user/"):]
            return self._user_dir / relative
        if sandbox_path.startswith("/system/"):
            relative = sandbox_path[len("/system/"):]
            return self._system_dir / relative
        return None
