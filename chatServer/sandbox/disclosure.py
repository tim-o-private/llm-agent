"""DisclosureModel — trust-tier-based notification formatting for config changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TrustTier = Literal["inform", "recommend", "act"]


@dataclass
class ChangeDescription:
    """Describes a single config change for disclosure."""

    file_path: str
    action: str  # "created", "updated", "deleted"
    summary: str  # human-readable diff summary
    commit_sha: str


class DisclosureModel:
    """Formats change notifications according to the user's trust tier.

    Inform  — full transparency for every change.
    Recommend — aggregated summary.
    Act     — silent; periodic digest only.
    """

    def format_change_notification(
        self,
        change: ChangeDescription,
        trust_tier: TrustTier,
    ) -> str | None:
        """Format a notification body, or None if the tier suppresses it."""
        if trust_tier == "act":
            return None

        if trust_tier == "recommend":
            return self._format_recommend(change)

        return self._format_inform(change)

    def format_aggregated_notification(
        self,
        changes: list[ChangeDescription],
        trust_tier: TrustTier,
    ) -> str | None:
        """Format an aggregated notification for multiple changes."""
        if trust_tier == "act":
            return None

        if not changes:
            return None

        if trust_tier == "recommend":
            n = len(changes)
            areas = {self._area_name(c.file_path) for c in changes}
            areas_str = ", ".join(sorted(areas))
            return (
                f"I made {n} adjustment{'s' if n != 1 else ''} "
                f"to how I handle your {areas_str}."
            )

        # Inform — list each change
        lines = ["I updated my configuration:\n"]
        for c in changes:
            lines.append(f"- **{c.file_path}** ({c.action}): {c.summary}")
        return "\n".join(lines)

    def format_digest(self, changes: list[ChangeDescription]) -> str:
        """Format a periodic digest for Act-tier users."""
        if not changes:
            return "No configuration changes in this period."

        lines = [f"**Configuration changelog** ({len(changes)} change{'s' if len(changes) != 1 else ''}):\n"]
        for c in changes:
            lines.append(f"- **{c.file_path}** ({c.action}): {c.summary} [`{c.commit_sha[:8]}`]")
        return "\n".join(lines)

    # -- internals ------------------------------------------------------------

    def _format_inform(self, change: ChangeDescription) -> str:
        return (
            f"I {change.action} **{change.file_path}**:\n\n"
            f"{change.summary}\n\n"
            f"Commit: `{change.commit_sha[:8]}`"
        )

    def _format_recommend(self, change: ChangeDescription) -> str:
        area = self._area_name(change.file_path)
        return (
            f"I adjusted how I handle your {area}. "
            f"Let me know if that feels off."
        )

    @staticmethod
    def _area_name(file_path: str) -> str:
        """Extract a human-readable area name from a sandbox path."""
        parts = file_path.strip("/").split("/")
        # /user/preferences/scheduling.yaml -> "scheduling"
        # /user/agent/style_overrides.md -> "style"
        if len(parts) >= 2:
            return parts[1]  # e.g. "agent", "preferences", "workflows"
        return "configuration"
