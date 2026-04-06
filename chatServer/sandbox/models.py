"""Sandbox data models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class SandboxStatus(str, enum.Enum):
    """Lifecycle status of a sandbox instance."""

    PROVISIONING = "provisioning"
    ACTIVE = "active"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    ERROR = "error"


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for the sandbox subsystem."""

    enabled: bool = False
    base_path: Path = field(default_factory=lambda: Path("/data/sandboxes"))
    system_path: Path = field(default_factory=lambda: Path("/data/sandbox-system"))
    bwrap_binary: str = "bwrap"

    @property
    def users_path(self) -> Path:
        return self.base_path / "users"

    @property
    def tools_path(self) -> Path:
        return self.base_path / "tools"


@dataclass
class CommandResult:
    """Result of a command executed inside a sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
