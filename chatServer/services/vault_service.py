"""VaultService — filesystem chokepoint for the per-user vault.

Every web-side read/write to ``/data/sandboxes/{user_id}/`` goes through
this class. ``_resolve`` is the entire security boundary — a bug here
leaks cross-user data. See SPEC-045 §"Access Control Model".
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Hard cap on today.md writes (AC/edge case).
_MAX_WRITE_BYTES = 10 * 1024 * 1024

# Directories excluded from list_recent by default.
_DEFAULT_RECENT_EXCLUDES = ("_workflows", "_activity", "_runs")

# Directories excluded from tree/folder listings (dot-files handled separately).
_TREE_EXCLUDES = {"_activity", "_runs"}

# Safety cap on recursive tree depth.
_MAX_TREE_DEPTH = 10


@dataclass
class RecentEntry:
    path: str
    updated_at: str


@dataclass
class TreeNode:
    """A file or folder in the vault tree."""

    name: str
    path: str  # relative to user root, posix separators
    type: str  # "file" | "folder"
    mtime: str  # ISO 8601
    size: int
    children: list["TreeNode"] | None = None


@dataclass
class FolderEntry:
    """A single entry in a flat folder listing."""

    name: str
    path: str
    type: str  # "file" | "folder"
    mtime: str
    size: int


class VaultService:
    """Read/write scoped to ``/data/sandboxes/{user_id}/``."""

    def __init__(
        self,
        storage_sync,
        data_dir: Path = Path("/data"),
    ):
        self._sync = storage_sync
        self._data_dir = Path(data_dir)
        self._root = self._data_dir / "sandboxes"
        self._system = self._data_dir / "config" / "system"

    def _user_root(self, user_id: str) -> Path:
        return (self._root / user_id).resolve(strict=False)

    def _resolve(self, user_id: str, rel_path: str) -> Path:
        """Resolve ``rel_path`` against the user's vault root.

        Raises ``HTTPException(403)`` on any escape attempt.
        """
        if not isinstance(rel_path, str):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if rel_path == "" or rel_path == ".":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if "\x00" in rel_path:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if os.path.isabs(rel_path):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        # Component-level pre-check (before any filesystem touch). Reject any
        # literal ".." segment; absolute markers; and empty segments from
        # doubled separators.
        parts = Path(rel_path).parts
        for seg in parts:
            if seg in ("..", ""):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        user_root = self._user_root(user_id)
        candidate = (user_root / rel_path).resolve(strict=False)

        # Containment — post-resolution check catches anything the component
        # pre-check missed (e.g. exotic encodings).
        try:
            candidate.relative_to(user_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
            ) from exc

        # Symlink guard — walk each component of the *input* path (pre-
        # resolution). If any component is a symlink, reject. Even a symlink
        # pointing inside the vault is rejected, because agents should not be
        # creating symlinks and the presence of one indicates tampering.
        probe = user_root
        for seg in parts:
            probe = probe / seg
            if probe.is_symlink():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        return candidate

    async def read_file(self, user_id: str, rel_path: str) -> str:
        path = self._resolve(user_id, rel_path)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        return path.read_text()

    async def stat_file(self, user_id: str, rel_path: str) -> Optional[os.stat_result]:
        path = self._resolve(user_id, rel_path)
        if not path.exists():
            return None
        return path.stat()

    async def update_body(
        self,
        user_id: str,
        rel_path: str,
        new_body: str,
        expected_mtime: Optional[float] = None,
    ) -> float:
        """Write ``new_body`` to ``rel_path``; fire-and-forget sync to Storage.

        If ``expected_mtime`` is provided and the on-disk mtime differs, raise
        409 (per Technical Approach §1 — last-write-wins + If-Match).
        Returns the new mtime as a float.
        """
        path = self._resolve(user_id, rel_path)

        encoded = new_body.encode("utf-8")
        if len(encoded) > _MAX_WRITE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File too large",
            )

        if expected_mtime is not None and path.exists():
            current_mtime = path.stat().st_mtime
            # Tolerate float rounding to millisecond precision.
            if abs(current_mtime - expected_mtime) > 0.001:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="File modified since last read",
                )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
        new_mtime = path.stat().st_mtime

        # Fire-and-forget sync to Supabase Storage. Never raise.
        if self._sync is not None:
            try:
                asyncio.create_task(self._sync.sync_file(user_id, rel_path))
            except Exception:  # pragma: no cover — sync is best-effort
                logger.warning("Failed to schedule sync_file for %s", rel_path)

        return new_mtime

    async def seed_if_missing(
        self,
        user_id: str,
        rel_path: str,
        template_rel: str,
    ) -> None:
        """Copy ``{system}/{template_rel}`` → ``{user}/{rel_path}`` if missing."""
        path = self._resolve(user_id, rel_path)
        if path.exists():
            return
        src = (self._system / template_rel).resolve(strict=False)
        # Containment check on the system side too (template_rel is trusted
        # internal input, but cheap to enforce).
        try:
            src.relative_to(self._system.resolve(strict=False))
        except ValueError:
            logger.warning("Template %s escapes system dir; skipping seed", template_rel)
            return
        if not src.exists() or not src.is_file():
            logger.warning("Seed template not found: %s", src)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, path)
        logger.info("Seeded %s for user %s from %s", rel_path, user_id, src)
        if self._sync is not None:
            try:
                asyncio.create_task(self._sync.sync_file(user_id, rel_path))
            except Exception:  # pragma: no cover
                pass

    async def list_recent(
        self,
        user_id: str,
        limit: int = 10,
        exclude: Optional[list[str]] = None,
    ) -> list[RecentEntry]:
        """Return recently-modified files under the user's vault.

        Filters out ``today.md`` and default excluded dirs. Ignores hidden
        files. Resolves paths relative to the user root.
        """
        user_root = self._user_root(user_id)
        if not user_root.exists():
            return []

        excludes = set(exclude) if exclude is not None else set(_DEFAULT_RECENT_EXCLUDES)
        return await asyncio.to_thread(self._walk_recent, user_root, excludes, limit)

    @staticmethod
    def _walk_recent(
        user_root: Path, excludes: set[str], limit: int
    ) -> list[RecentEntry]:
        results: list[tuple[float, str]] = []
        for dirpath, dirnames, filenames in os.walk(user_root, followlinks=False):
            try:
                rel_dir = Path(dirpath).relative_to(user_root)
            except ValueError:
                continue
            rel_dir_parts = rel_dir.parts
            if rel_dir_parts and rel_dir_parts[0] in excludes:
                dirnames[:] = []
                continue
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".")
                and not (not rel_dir_parts and d in excludes)
            ]
            for fname in filenames:
                if fname.startswith("."):
                    continue
                full = Path(dirpath) / fname
                if full.is_symlink():
                    continue
                rel = full.relative_to(user_root).as_posix()
                if rel == "today.md":
                    continue
                try:
                    mtime = full.stat().st_mtime
                except OSError:
                    continue
                results.append((mtime, rel))

        results.sort(key=lambda item: item[0], reverse=True)
        return [
            RecentEntry(
                path=rel,
                updated_at=datetime.fromtimestamp(mtime, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            )
            for mtime, rel in results[:limit]
        ]

    # ------------------------------------------------------------------
    # Tree / folder listing (SPEC-046 FU-1)
    # ------------------------------------------------------------------

    async def list_tree(self, user_id: str) -> list[TreeNode]:
        """Return a recursive tree of the user's vault.

        Excludes dot-files, ``_activity/``, and ``_runs/`` directories.
        Delegates to a thread to avoid blocking the event loop on large vaults.
        """
        user_root = self._user_root(user_id)
        if not user_root.exists():
            return []
        return await asyncio.to_thread(
            self._build_tree, user_root, user_root, depth=0
        )

    @staticmethod
    def _mtime_iso(path: Path) -> str:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        return (
            datetime.fromtimestamp(mtime, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _file_size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    @classmethod
    def _build_tree(
        cls, user_root: Path, current: Path, depth: int
    ) -> list[TreeNode]:
        if depth > _MAX_TREE_DEPTH:
            return []

        nodes: list[TreeNode] = []
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            return []

        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_symlink():
                continue

            rel = entry.relative_to(user_root).as_posix()

            if entry.is_dir():
                # Skip excluded top-level dirs
                top_level_name = Path(rel).parts[0] if Path(rel).parts else ""
                if top_level_name in _TREE_EXCLUDES:
                    continue
                children = cls._build_tree(user_root, entry, depth + 1)
                nodes.append(
                    TreeNode(
                        name=entry.name,
                        path=rel,
                        type="folder",
                        mtime=cls._mtime_iso(entry),
                        size=0,
                        children=children,
                    )
                )
            elif entry.is_file():
                nodes.append(
                    TreeNode(
                        name=entry.name,
                        path=rel,
                        type="file",
                        mtime=cls._mtime_iso(entry),
                        size=cls._file_size(entry),
                    )
                )
        return nodes

    async def list_folder(
        self, user_id: str, rel_path: str
    ) -> list[FolderEntry]:
        """Return a flat (one-level) listing of a vault folder.

        ``rel_path`` can be empty or ``""`` for the root. Otherwise it goes
        through ``_resolve`` for safety.
        """
        user_root = self._user_root(user_id)

        if not rel_path or rel_path in ("", "."):
            target = user_root
        else:
            target = self._resolve(user_id, rel_path)

        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if not target.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        return await asyncio.to_thread(self._list_dir, user_root, target)

    @classmethod
    def _list_dir(cls, user_root: Path, target: Path) -> list[FolderEntry]:
        entries: list[FolderEntry] = []
        try:
            items = sorted(target.iterdir(), key=lambda p: p.name)
        except OSError:
            return []

        for item in items:
            if item.name.startswith("."):
                continue
            if item.is_symlink():
                continue

            rel = item.relative_to(user_root).as_posix()

            # Skip excluded top-level dirs
            top_level_name = Path(rel).parts[0] if Path(rel).parts else ""
            if item.is_dir() and top_level_name in _TREE_EXCLUDES:
                continue

            entry_type = "folder" if item.is_dir() else "file"
            entries.append(
                FolderEntry(
                    name=item.name,
                    path=rel,
                    type=entry_type,
                    mtime=cls._mtime_iso(item),
                    size=cls._file_size(item) if item.is_file() else 0,
                )
            )
        return entries
