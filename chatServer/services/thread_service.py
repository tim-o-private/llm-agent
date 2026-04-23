"""ThreadService — thread-doc operations on top of VaultService.

Thread-docs are plain markdown files with YAML frontmatter living under
``_threads/`` in the user's vault. This service handles creation, status
transitions, listing, and updates — all I/O goes through VaultService so
the security boundary (``_resolve``) is never bypassed.

SPEC-054 AC-01 through AC-03.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import yaml
from fastapi import HTTPException

from ..lib.slugify import slugify
from .vault_service import VaultService

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Status lifecycle (SPEC-054 §1):
#   active  --> watching / paused / completed / archived
#   watching --> active / paused / completed / archived
#   paused  --> active / watching / archived
#   completed --> archived
#   archived  --> active  (unarchive)
VALID_TRANSITIONS: dict[str, set[str]] = {
    "active": {"watching", "paused", "completed", "archived"},
    "watching": {"active", "paused", "completed", "archived"},
    "paused": {"active", "watching", "archived"},
    "completed": {"archived"},
    "archived": {"active"},
}

ALL_STATUSES = {"active", "watching", "paused", "completed", "archived"}


class ThreadService:
    """Thread-doc CRUD on top of VaultService."""

    def __init__(self, vault: VaultService):
        self._vault = vault

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_thread(
        self,
        user_id: str,
        title: str,
        trigger: str,
        initiated_by: str = "agent",
        goal: str = "",
    ) -> str:
        """Create a thread-doc under ``_threads/``. Returns vault-relative path.

        If a file with the same date-slug already exists, appends a numeric
        suffix (``-2``, ``-3``, ...) to avoid collisions.
        """
        slug = slugify(title)
        if not slug:
            slug = "untitled"
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base_filename = f"{date_prefix}-{slug}.md"
        rel_path = f"_threads/{base_filename}"

        # Handle filename collisions
        stat = await self._vault.stat_file(user_id, rel_path)
        if stat is not None:
            counter = 2
            while True:
                candidate = f"_threads/{date_prefix}-{slug}-{counter}.md"
                if await self._vault.stat_file(user_id, candidate) is None:
                    rel_path = candidate
                    break
                counter += 1

        now = datetime.now(timezone.utc).isoformat()
        frontmatter = {
            "doc_type": "thread",
            "title": title,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "initiated_by": initiated_by,
            "trigger": trigger,
            "tags": [],
            "next_action": None,
            "next_action_at": None,
            "blocked_on": None,
        }
        body_sections = (
            f"## Goal\n{goal}\n\n"
            "## Plan\n\n"
            "## Progress\n\n"
            "## Findings\n\n"
            "## Open Questions\n\n"
            "## Notes\n"
        )
        content = _serialize_frontmatter_doc(frontmatter, body_sections)
        await self._vault.update_body(user_id, rel_path, content)
        return rel_path

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def change_status(
        self, user_id: str, rel_path: str, new_status: str
    ) -> None:
        """Validate and apply a status transition. Raises 422 on invalid."""
        if new_status not in ALL_STATUSES:
            raise HTTPException(422, f"Unknown status: {new_status}")

        content = await self._vault.read_file(user_id, rel_path)
        fm, body = _parse_frontmatter(content)
        current = fm.get("status")

        if current not in VALID_TRANSITIONS:
            raise HTTPException(
                422, f"Thread has unknown current status: {current}"
            )

        if new_status not in VALID_TRANSITIONS[current]:
            raise HTTPException(
                422, f"Invalid transition: {current} -> {new_status}"
            )

        fm["status"] = new_status
        fm["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._vault.update_body(
            user_id, rel_path, _serialize_frontmatter_doc(fm, body)
        )

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_active_threads(self, user_id: str) -> list[dict]:
        """Return frontmatter summaries for active/watching/blocked threads.

        Walks ``_threads/``, reads frontmatter from each ``.md`` file, and
        returns threads whose status is ``active``, ``watching``, or
        ``active`` with ``blocked_on`` set.
        """
        threads_dir = "_threads"
        try:
            entries = await self._vault.list_folder(user_id, threads_dir)
        except HTTPException:
            # _threads/ doesn't exist yet — no threads
            return []

        results: list[dict] = []
        for entry in entries:
            if entry.type != "file" or not entry.name.endswith(".md"):
                continue
            try:
                content = await self._vault.read_file(user_id, entry.path)
                fm, _ = _parse_frontmatter(content)
                status = fm.get("status", "")
                if status in ("active", "watching"):
                    results.append({
                        "path": entry.path,
                        "title": fm.get("title", ""),
                        "status": status,
                        "next_action": fm.get("next_action"),
                        "blocked_on": fm.get("blocked_on"),
                        "created_at": fm.get("created_at", ""),
                        "updated_at": fm.get("updated_at", ""),
                    })
            except Exception:
                logger.warning(
                    "Failed to read thread-doc %s for user %s",
                    entry.path,
                    user_id,
                    exc_info=True,
                )
        return results

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_thread(
        self,
        user_id: str,
        rel_path: str,
        updates: dict[str, Any],
    ) -> None:
        """Update frontmatter fields and optionally append to Progress.

        ``updates`` may include ``next_action``, ``blocked_on``, and
        ``progress_line`` (appended to ## Progress as a timestamped bullet).
        """
        content = await self._vault.read_file(user_id, rel_path)
        fm, body = _parse_frontmatter(content)

        for key in ("next_action", "blocked_on", "next_action_at", "tags"):
            if key in updates:
                fm[key] = updates[key]

        fm["updated_at"] = datetime.now(timezone.utc).isoformat()

        if "progress_line" in updates:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            line = f"- {ts}: {updates['progress_line']}"
            body = _prepend_to_section(body, "Progress", line)

        await self._vault.update_body(
            user_id, rel_path, _serialize_frontmatter_doc(fm, body)
        )


# ---- Frontmatter helpers ------------------------------------------------


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split a markdown document into (frontmatter_dict, body_str)."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1))
        if not isinstance(fm, dict):
            fm = {}
    except yaml.YAMLError:
        fm = {}
    body = content[match.end():].lstrip("\n")
    return fm, body


def _serialize_frontmatter_doc(fm: dict, body: str) -> str:
    """Render frontmatter dict + body back to a markdown document."""
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---\n\n{body}"


def _prepend_to_section(body: str, section_name: str, line: str) -> str:
    """Prepend a line after the ``## <section>`` heading (most-recent-first).

    If the section doesn't exist, append it at the end.
    """
    pattern = re.compile(
        rf"^(## {re.escape(section_name)}\s*\n)", re.MULTILINE
    )
    match = pattern.search(body)
    if match:
        insert_at = match.end()
        return body[:insert_at] + line + "\n" + body[insert_at:]
    # Section not found — append
    return body.rstrip("\n") + f"\n\n## {section_name}\n{line}\n"
