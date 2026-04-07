"""Local protocol stubs for deepagents.backends.protocol.

TODO (SPEC-043): Replace with direct imports from deepagents once the langchain
1.x migration is complete.  deepagents>=0.5.0 requires langchain>=1.2.15, which
is incompatible with the AgentExecutor usage in
src/core/agents/customizable_agent.py (removed in langchain 1.x).

These stubs mirror the real types exactly so that ClarityBackend works both
before and after the migration.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import NotRequired, TypedDict

# ---------------------------------------------------------------------------
# Shared type aliases
# ---------------------------------------------------------------------------


class FileInfo(TypedDict):
    """Structured file listing info."""

    path: str
    is_dir: NotRequired[bool]
    size: NotRequired[int]
    modified_at: NotRequired[str]


class GrepMatch(TypedDict):
    """A single match from a grep search."""

    path: str
    line: int
    text: str


class FileData(TypedDict):
    """Data structure for storing file contents with metadata."""

    content: str
    encoding: str
    created_at: NotRequired[str]
    modified_at: NotRequired[str]


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ReadResult:
    error: str | None = None
    file_data: FileData | None = None


@dataclass
class WriteResult:
    error: str | None = None
    path: str | None = None


@dataclass
class EditResult:
    error: str | None = None
    path: str | None = None
    occurrences: int | None = None


@dataclass
class LsResult:
    error: str | None = None
    entries: list[FileInfo] | None = None


@dataclass
class GrepResult:
    error: str | None = None
    matches: list[GrepMatch] | None = None


@dataclass
class GlobResult:
    error: str | None = None
    matches: list[FileInfo] | None = None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class BackendProtocol(abc.ABC):  # noqa: B024
    """Minimal stub mirroring deepagents.backends.protocol.BackendProtocol."""

    def ls(self, path: str) -> LsResult:  # noqa: D102
        raise NotImplementedError

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:  # noqa: D102
        raise NotImplementedError

    def write(self, file_path: str, content: str) -> WriteResult:  # noqa: D102
        raise NotImplementedError

    def edit(  # noqa: D102
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,  # noqa: FBT001, FBT002
    ) -> EditResult:
        raise NotImplementedError

    def grep(  # noqa: D102
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        raise NotImplementedError

    def glob(self, pattern: str, path: str = "/") -> GlobResult:  # noqa: D102
        raise NotImplementedError
