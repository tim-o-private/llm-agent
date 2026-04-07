"""ClarityBackend — BackendProtocol implementation backed by ConfigService.

Maps Deep Agents' virtual filesystem operations to Supabase Storage via
ConfigService, with user/system namespace isolation and security validation.

Namespace conventions
---------------------
Deep Agents sees:    /skills/clarity-soul/SKILL.md   (leading slash, no layer prefix)
ConfigService needs: skills/clarity-soul/SKILL.md    (no leading slash, no layer prefix)
SecurityBoundary:    /user/skills/clarity-soul/SKILL.md  (absolute sandbox namespace)

All writes go to the user layer; reads use overlay resolution (user overrides system).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import fnmatch
import logging
import re
from typing import Optional

try:
    # Prefer the real package when langchain has been migrated to 1.x.
    # TODO (SPEC-043): remove the fallback once the AgentExecutor migration lands.
    from deepagents.backends.protocol import (
        BackendProtocol,
        EditResult,
        FileInfo,
        GlobResult,
        GrepMatch,
        GrepResult,
        LsResult,
        ReadResult,
        WriteResult,
    )
except ImportError:
    from .deep_agent_backend_protocol import (  # type: ignore[assignment]
        BackendProtocol,
        EditResult,
        FileInfo,
        GlobResult,
        GrepMatch,
        GrepResult,
        LsResult,
        ReadResult,
        WriteResult,
    )

from ..sandbox.security_boundary import SecurityBoundary
from ..sandbox.self_improvement import SelfImprovementService
from .config_service import ConfigService

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync context, bridging event loops.

    When called from within an already-running event loop (e.g. inside a
    LangGraph node), spawns a fresh thread with its own loop to avoid the
    "cannot run nested event loop" error.  Outside an async context, falls
    back to the simpler asyncio.run().
    """
    try:
        asyncio.get_running_loop()
        # Inside a running loop — run in a dedicated thread with its own loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop — safe to call asyncio.run directly
        return asyncio.run(coro)


def _strip_leading_slash(path: str) -> str:
    """Strip leading slash before handing a path to ConfigService."""
    return path.lstrip("/")


def _to_security_path(config_path: str) -> str:
    """Map a config-relative path to the sandbox /user/... namespace.

    All writes from Deep Agents target the user layer, so we always map
    into /user/... for SecurityBoundary classification.
    """
    return f"/user/{config_path}"


def _to_display_path(config_path: str) -> str:
    """Add a leading slash for paths returned to the Deep Agent caller."""
    return f"/{config_path}" if not config_path.startswith("/") else config_path


class ClarityBackend(BackendProtocol):
    """BackendProtocol implementation backed by Supabase Storage via ConfigService.

    Provides Deep Agents with a virtual filesystem over the config storage layer.
    User skills and configs overlay system defaults (handled by ConfigService).
    Writes are validated through SecurityBoundary and optionally routed through
    SelfImprovementService for user-facing change proposals.
    """

    def __init__(
        self,
        config_service: ConfigService,
        user_id: str,
        security_boundary: SecurityBoundary,
        self_improvement_service: Optional[SelfImprovementService] = None,
    ) -> None:
        self._config = config_service
        self._user_id = user_id
        self._boundary = security_boundary
        self._si = self_improvement_service

    # -- BackendProtocol methods -------------------------------------------------

    def ls(self, path: str) -> LsResult:
        """List files under path. Merges user and system layers via ConfigService."""
        config_path = _strip_leading_slash(path)
        try:
            paths = _run_async(self._config.list_paths(config_path, self._user_id))
        except Exception as exc:
            logger.warning("ls failed for %s: %s", path, exc)
            return LsResult(error=str(exc))

        entries: list[FileInfo] = [
            FileInfo(
                path=_to_display_path(p),
                is_dir=p.endswith("/"),
                size=0,
            )
            for p in paths
        ]
        return LsResult(entries=entries)

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        """Read a file with overlay resolution (user layer overrides system layer)."""
        config_path = _strip_leading_slash(file_path)
        try:
            content = _run_async(self._config.read(config_path, self._user_id))
        except Exception as exc:
            logger.warning("read failed for %s: %s", file_path, exc)
            return ReadResult(error=str(exc))

        if content is None:
            return ReadResult(error=f"file_not_found: {file_path}")

        lines = content.splitlines(keepends=True)
        sliced = lines[offset : offset + limit]
        return ReadResult(file_data={"content": "".join(sliced), "encoding": "utf-8"})

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write to user config layer after SecurityBoundary validation."""
        config_path = _strip_leading_slash(file_path)
        security_path = _to_security_path(config_path)

        if not self._boundary.validate_write(security_path):
            classification = self._boundary.classify_path(security_path)
            return WriteResult(
                error=f"Cannot write to {file_path}: path classified as '{classification}'"
            )

        try:
            _run_async(self._config.write(config_path, self._user_id, content))
        except Exception as exc:
            logger.warning("write failed for %s: %s", file_path, exc)
            return WriteResult(error=str(exc))

        self._maybe_propose(file_path, security_path, content)
        return WriteResult(path=file_path)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,  # noqa: FBT001, FBT002
    ) -> EditResult:
        """Edit a file by replacing old_string with new_string (read-modify-write)."""
        config_path = _strip_leading_slash(file_path)
        security_path = _to_security_path(config_path)

        if not self._boundary.validate_write(security_path):
            classification = self._boundary.classify_path(security_path)
            return EditResult(
                error=f"Cannot edit {file_path}: path classified as '{classification}'"
            )

        try:
            content = _run_async(self._config.read(config_path, self._user_id))
        except Exception as exc:
            return EditResult(error=str(exc))

        if content is None:
            return EditResult(error=f"file_not_found: {file_path}")

        if old_string not in content:
            return EditResult(error=f"String not found in {file_path}")

        if replace_all:
            new_content = content.replace(old_string, new_string)
            occurrences = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            occurrences = 1

        try:
            _run_async(self._config.write(config_path, self._user_id, new_content))
        except Exception as exc:
            return EditResult(error=str(exc))

        self._maybe_propose(file_path, security_path, new_content)
        return EditResult(path=file_path, occurrences=occurrences)

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        """Search file contents for a pattern (substring match, not regex per protocol)."""
        search_path = _strip_leading_slash(path or "")
        try:
            all_paths = _run_async(self._config.list_paths(search_path, self._user_id))
        except Exception as exc:
            return GrepResult(error=str(exc))

        # Apply glob filter if provided
        if glob:
            all_paths = [p for p in all_paths if fnmatch.fnmatch(p, glob)]

        matches: list[GrepMatch] = []
        try:
            compiled = re.compile(re.escape(pattern))  # protocol says literal match
        except re.error as exc:
            return GrepResult(error=f"Invalid pattern: {exc}")

        for file_path in all_paths:
            config_path = _strip_leading_slash(file_path)
            try:
                content = _run_async(self._config.read(config_path, self._user_id))
            except Exception:
                continue
            if content is None:
                continue
            for line_num, line in enumerate(content.splitlines(), start=1):
                if compiled.search(line):
                    matches.append(
                        GrepMatch(
                            path=_to_display_path(file_path),
                            line=line_num,
                            text=line,
                        )
                    )

        return GrepResult(matches=matches)

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        """Return FileInfo entries for paths matching a glob pattern."""
        search_path = _strip_leading_slash(path)
        try:
            all_paths = _run_async(self._config.list_paths(search_path, self._user_id))
        except Exception as exc:
            return GlobResult(error=str(exc))

        matched: list[FileInfo] = [
            FileInfo(path=_to_display_path(p), is_dir=p.endswith("/"), size=0)
            for p in all_paths
            if fnmatch.fnmatch(p, pattern) or fnmatch.fnmatch(p.split("/")[-1], pattern)
        ]

        return GlobResult(matches=matched)

    # -- Internal helpers --------------------------------------------------------

    def _maybe_propose(self, file_path: str, security_path: str, content: str) -> None:
        """Fire-and-forget proposal to SelfImprovementService (if configured).

        Logs on failure but never raises — a write already succeeded at this point.
        """
        if self._si is None:
            return
        try:
            _run_async(
                self._si.propose_change(
                    user_id=self._user_id,
                    git_tracker=None,  # Not available in backend context
                    file_path=security_path,
                    content=content,
                    description=f"Agent wrote {file_path}",
                )
            )
        except Exception as exc:
            logger.warning(
                "SelfImprovementService.propose_change failed for %s: %s",
                file_path,
                exc,
            )
