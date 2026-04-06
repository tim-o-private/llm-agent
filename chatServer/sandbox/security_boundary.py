"""SecurityBoundary — application-level defense-in-depth for sandbox paths.

The primary enforcement is the kernel-level read-only bind mount on /system/.
This class provides a second validation layer plus audit logging.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal

logger = logging.getLogger(__name__)

PathClass = Literal["immutable", "mutable", "unknown"]


@dataclass(frozen=True)
class ModificationPolicy:
    """Parsed modification_policy.yaml content."""

    immutable_paths: list[str] = field(default_factory=lambda: ["/system/**"])
    mutable_paths: list[str] = field(
        default_factory=lambda: [
            "/user/agent/**",
            "/user/workflows/**",
            "/user/preferences/**",
            "/user/memory/**",
            "/user/schedules/**",
        ],
    )
    elevated_review: list[str] = field(
        default_factory=lambda: ["/user/workflows/**"],
    )


_DEFAULTS = ModificationPolicy()


def load_policy(data: dict | None = None) -> ModificationPolicy:
    """Create a ModificationPolicy from a parsed YAML dict (or defaults)."""
    if not data:
        return ModificationPolicy()
    return ModificationPolicy(
        immutable_paths=data.get("immutable_paths", _DEFAULTS.immutable_paths),
        mutable_paths=data.get("mutable_paths", _DEFAULTS.mutable_paths),
        elevated_review=data.get("elevated_review", _DEFAULTS.elevated_review),
    )


class SecurityBoundary:
    """Classifies sandbox paths and validates write operations.

    Defence-in-depth: bwrap enforces read-only at the kernel level;
    this class provides application-level checks and audit trails.
    """

    def __init__(self, policy: ModificationPolicy | None = None) -> None:
        self._policy = policy or ModificationPolicy()

    @property
    def policy(self) -> ModificationPolicy:
        return self._policy

    def classify_path(self, path: str) -> PathClass:
        """Classify *path* as immutable, mutable, or unknown.

        The path should be absolute within the sandbox namespace
        (e.g. ``/system/security/tool_allowlist.yaml``).
        """
        normalised = str(PurePosixPath(path))

        for pattern in self._policy.immutable_paths:
            if fnmatch.fnmatch(normalised, pattern):
                return "immutable"

        for pattern in self._policy.mutable_paths:
            if fnmatch.fnmatch(normalised, pattern):
                return "mutable"

        return "unknown"

    def validate_write(self, path: str) -> bool:
        """Return True if writing to *path* is allowed.

        Writes to immutable or unknown paths are rejected.
        """
        classification = self.classify_path(path)
        if classification != "mutable":
            logger.warning(
                "Write rejected — path %s classified as %s",
                path,
                classification,
            )
            return False
        return True

    def requires_elevated_review(self, path: str) -> bool:
        """Return True if *path* matches an elevated-review glob."""
        normalised = str(PurePosixPath(path))
        return any(
            fnmatch.fnmatch(normalised, pattern)
            for pattern in self._policy.elevated_review
        )
