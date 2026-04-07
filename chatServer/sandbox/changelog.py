"""ChangelogService — formatted changelog from sandbox git history.

Provides human-readable summaries of self-modifications, accessible
via conversation ("what have you changed recently?") and future
file browser (Phase 4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .git_tracker import CommitInfo, GitTracker

logger = logging.getLogger(__name__)


@dataclass
class ChangelogEntry:
    """A single changelog entry with category."""

    sha: str
    message: str
    timestamp: str
    category: str  # "prompt", "preference", "workflow", "memory", "other"


class ChangelogService:
    """Provides formatted changelog from git history in the user sandbox."""

    def __init__(self, git_tracker: GitTracker) -> None:
        self._git = git_tracker

    async def get_changelog(
        self,
        user_id: str,
        since: str | None = None,
        limit: int = 50,
    ) -> str:
        """Return markdown-formatted changelog.

        Args:
            user_id: The user whose changelog to retrieve.
            since: Optional commit SHA to start from.
            limit: Max number of entries.

        Returns:
            Markdown-formatted changelog grouped by category.
        """
        if since:
            raw = await self._git.get_changelog(since=since)
        else:
            commits = await self._git.log(limit=limit)
            if not commits:
                return "No changes recorded yet."
            raw = None  # We'll format from commits directly

        if raw is not None:
            return self._format_raw_changelog(raw)

        commits = await self._git.log(limit=limit)
        if not commits:
            return "No changes recorded yet."

        entries = [self._categorize_commit(c) for c in commits]
        return self._format_grouped(entries)

    async def get_change_detail(self, sha: str) -> dict[str, Any]:
        """Get detail for a specific change: message + diff.

        Returns dict with 'message', 'diff', 'files' keys.
        """
        commits = await self._git.log(limit=100)
        commit = next((c for c in commits if c.sha.startswith(sha)), None)

        message = commit.message if commit else "Unknown commit"
        diff = await self._git.diff(sha)
        files = await self._git.diff_files(sha)

        return {
            "sha": sha,
            "message": message,
            "diff": diff,
            "files": files,
        }

    async def get_recent_summary(self, days: int = 30) -> str:
        """Get a summary of recent changes for conversational access."""
        commits = await self._git.log(limit=100)
        if not commits:
            return "I haven't made any changes to my configuration yet."

        entries = [self._categorize_commit(c) for c in commits]

        # Count by category
        counts: dict[str, int] = {}
        for entry in entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1

        parts = []
        for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
            label = self._category_label(cat)
            parts.append(f"- **{label}**: {count} change{'s' if count != 1 else ''}")

        total = len(entries)
        header = f"I've made **{total} change{'s' if total != 1 else ''}** to my configuration:\n"
        return header + "\n".join(parts)

    def _categorize_commit(self, commit: CommitInfo) -> ChangelogEntry:
        """Categorize a commit based on its message and files."""
        msg = commit.message.lower()
        category = "other"

        if any(kw in msg for kw in ["prompt", "soul", "instruction", "personality"]):
            category = "prompt"
        elif any(kw in msg for kw in ["preference", "setting", "config"]):
            category = "preference"
        elif any(kw in msg for kw in ["workflow", "template", "schedule"]):
            category = "workflow"
        elif any(kw in msg for kw in ["memory", "observation"]):
            category = "memory"

        return ChangelogEntry(
            sha=commit.sha,
            message=commit.message,
            timestamp=commit.timestamp,
            category=category,
        )

    def _format_grouped(self, entries: list[ChangelogEntry]) -> str:
        """Format entries grouped by category."""
        if not entries:
            return "No changes recorded."

        groups: dict[str, list[ChangelogEntry]] = {}
        for entry in entries:
            groups.setdefault(entry.category, []).append(entry)

        lines = ["# Configuration Changelog\n"]
        for cat in ["prompt", "preference", "workflow", "memory", "other"]:
            group = groups.get(cat, [])
            if not group:
                continue
            lines.append(f"\n## {self._category_label(cat)}\n")
            for entry in group:
                short_sha = entry.sha[:8]
                lines.append(f"- {entry.message} (`{short_sha}`)")

        return "\n".join(lines)

    def _format_raw_changelog(self, raw: str) -> str:
        """Format raw git log output into markdown."""
        if not raw.strip():
            return "No changes in this period."
        return f"# Configuration Changelog\n\n{raw}"

    @staticmethod
    def _category_label(category: str) -> str:
        """Human-readable label for a category."""
        return {
            "prompt": "Prompt Changes",
            "preference": "Preference Changes",
            "workflow": "Workflow Changes",
            "memory": "Memory Updates",
            "other": "Other Changes",
        }.get(category, category.title())
