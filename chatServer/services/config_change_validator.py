"""ConfigChangeSafetyValidator — pre-execution validation for config_change proposals.

Blocks unsafe self-modification before the user ever sees the approval card
(AC-13). Two categories of checks:

1. Protected paths: files under security/auth/activity directories cannot be
   modified via config_change proposals.
2. Blocked content patterns: proposed content that would weaken safety
   constraints (removing approval gates, enabling auto-approve, granting
   destructive tools) is rejected.

The validator runs at two points:
- Before card creation (OrchestrationService) — prevents unsafe proposals
  from entering the approval lane.
- Before execution (ConfigChangeExecutor, SPEC-052) — defense-in-depth.
"""

from __future__ import annotations

import re


class ConfigChangeSafetyValidator:
    """Validates proposed config changes before creation or execution."""

    PROTECTED_PATHS: list[str] = [
        "system/security/",
        "system/auth/",
        "_activity/",
    ]

    BLOCKED_CONTENT_PATTERNS: list[str] = [
        r"default_gate_policy:\s*none",
        r"approval_tier:\s*(auto|none)",
        r"tools:\s*\[.*delete_file.*\]",
    ]

    def validate(
        self, file_path: str, proposed_content: str
    ) -> tuple[bool, str | None]:
        """Validate a proposed config change.

        Returns ``(True, None)`` if safe, or ``(False, reason)`` if blocked.
        """
        # 1. Protected path check
        for prefix in self.PROTECTED_PATHS:
            if file_path.startswith(prefix):
                return (
                    False,
                    f"Cannot modify protected path: {prefix}",
                )

        # 2. Blocked content pattern check
        for pattern in self.BLOCKED_CONTENT_PATTERNS:
            if re.search(pattern, proposed_content, re.IGNORECASE):
                return (
                    False,
                    f"Proposed content matches blocked pattern: {pattern}",
                )

        return True, None
