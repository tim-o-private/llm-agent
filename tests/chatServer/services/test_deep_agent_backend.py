"""Unit tests for ClarityBackend — BackendProtocol over ConfigService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.sandbox.security_boundary import ModificationPolicy, SecurityBoundary
from chatServer.services.deep_agent_backend import ClarityBackend, _run_async


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def user_id() -> str:
    return "user-123"


@pytest.fixture()
def config_service():
    svc = MagicMock()
    svc.read = AsyncMock(return_value="line1\nline2\nline3\n")
    svc.write = AsyncMock(return_value=None)
    svc.list_paths = AsyncMock(return_value=["skills/soul/SKILL.md", "skills/soul/notes.txt"])
    return svc


@pytest.fixture()
def permissive_boundary():
    """SecurityBoundary that allows /user/skills/** writes."""
    policy = ModificationPolicy(
        immutable_paths=["/system/**"],
        mutable_paths=["/user/**"],
        elevated_review=[],
    )
    return SecurityBoundary(policy=policy)


@pytest.fixture()
def restrictive_boundary():
    """SecurityBoundary that only allows /user/workflows/** writes."""
    policy = ModificationPolicy(
        immutable_paths=["/system/**"],
        mutable_paths=["/user/workflows/**"],
        elevated_review=[],
    )
    return SecurityBoundary(policy=policy)


@pytest.fixture()
def self_improvement_service():
    svc = MagicMock()
    svc.propose_change = AsyncMock(return_value=MagicMock())
    return svc


@pytest.fixture()
def backend(config_service, permissive_boundary, user_id):
    return ClarityBackend(
        config_service=config_service,
        user_id=user_id,
        security_boundary=permissive_boundary,
    )


@pytest.fixture()
def backend_with_si(config_service, permissive_boundary, user_id, self_improvement_service):
    return ClarityBackend(
        config_service=config_service,
        user_id=user_id,
        security_boundary=permissive_boundary,
        self_improvement_service=self_improvement_service,
    )


# ---------------------------------------------------------------------------
# read()
# ---------------------------------------------------------------------------


def test_read_returns_content(backend, config_service, user_id):
    result = backend.read("/skills/soul/SKILL.md")

    config_service.read.assert_called_once_with("skills/soul/SKILL.md", user_id)
    assert result.error is None
    assert result.file_data is not None
    assert "line1" in result.file_data["content"]
    assert result.file_data["encoding"] == "utf-8"


def test_read_strips_leading_slash(backend, config_service, user_id):
    backend.read("/skills/soul/SKILL.md")
    # Must NOT pass the leading slash to ConfigService (it rejects them)
    config_service.read.assert_called_once_with("skills/soul/SKILL.md", user_id)


def test_read_overlay_user_over_system(config_service, permissive_boundary, user_id):
    """ConfigService handles overlay — verify backend calls read() with correct path."""
    config_service.read = AsyncMock(return_value="user content")
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.read("/skills/soul/SKILL.md")
    config_service.read.assert_called_once_with("skills/soul/SKILL.md", user_id)
    assert result.file_data["content"] == "user content"


def test_read_file_not_found(config_service, permissive_boundary, user_id):
    config_service.read = AsyncMock(return_value=None)
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.read("/skills/missing.md")
    assert result.error is not None
    assert "file_not_found" in result.error
    assert result.file_data is None


def test_read_applies_offset_and_limit(config_service, permissive_boundary, user_id):
    config_service.read = AsyncMock(return_value="a\nb\nc\nd\ne\n")
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.read("/f.md", offset=1, limit=2)
    assert result.error is None
    # Lines b and c (0-indexed offset=1, limit=2)
    lines = result.file_data["content"].splitlines()
    assert lines == ["b", "c"]


# ---------------------------------------------------------------------------
# write()
# ---------------------------------------------------------------------------


def test_write_to_user_namespace(backend, config_service, user_id):
    result = backend.write("/skills/soul/SKILL.md", "new content")

    config_service.write.assert_called_once_with("skills/soul/SKILL.md", user_id, "new content")
    assert result.error is None
    assert result.path == "/skills/soul/SKILL.md"


def test_write_strips_leading_slash(backend, config_service, user_id):
    backend.write("/skills/soul/notes.txt", "content")
    config_service.write.assert_called_once_with("skills/soul/notes.txt", user_id, "content")


def test_write_to_system_namespace_rejected(config_service, user_id):
    """Paths that map to /system/ are immutable — write must be rejected."""
    # Default policy: /system/** is immutable
    boundary = SecurityBoundary()
    b = ClarityBackend(config_service, user_id, boundary)
    # /system/ paths are immutable by default; our mapping sends user paths to /user/,
    # but we can directly test by using a policy that classifies /user/skills/ as immutable
    policy = ModificationPolicy(
        immutable_paths=["/user/skills/**"],
        mutable_paths=[],
        elevated_review=[],
    )
    b2 = ClarityBackend(config_service, user_id, SecurityBoundary(policy))
    result = b2.write("/skills/soul/SKILL.md", "hacked")
    assert result.error is not None
    assert "immutable" in result.error
    config_service.write.assert_not_called()


def test_write_unknown_path_rejected(config_service, user_id):
    """Unknown paths (not in mutable_paths) are also rejected."""
    policy = ModificationPolicy(
        immutable_paths=["/system/**"],
        mutable_paths=["/user/workflows/**"],  # skills NOT listed
        elevated_review=[],
    )
    b = ClarityBackend(config_service, user_id, SecurityBoundary(policy))
    result = b.write("/skills/soul/SKILL.md", "content")
    assert result.error is not None
    assert "unknown" in result.error
    config_service.write.assert_not_called()


def test_write_triggers_self_improvement(
    backend_with_si, config_service, self_improvement_service, user_id
):
    backend_with_si.write("/skills/soul/SKILL.md", "updated")

    self_improvement_service.propose_change.assert_called_once()
    call_kwargs = self_improvement_service.propose_change.call_args
    assert call_kwargs.kwargs["user_id"] == user_id
    assert call_kwargs.kwargs["file_path"] == "/user/skills/soul/SKILL.md"
    assert call_kwargs.kwargs["content"] == "updated"


def test_write_without_self_improvement(backend, config_service, user_id):
    """Works correctly when self_improvement_service is None."""
    result = backend.write("/skills/soul/SKILL.md", "content")
    assert result.error is None
    config_service.write.assert_called_once()


def test_write_si_failure_does_not_fail_write(
    config_service, permissive_boundary, user_id, self_improvement_service
):
    """If propose_change raises, the write result is still success."""
    self_improvement_service.propose_change = AsyncMock(side_effect=RuntimeError("oops"))
    b = ClarityBackend(config_service, user_id, permissive_boundary, self_improvement_service)
    result = b.write("/skills/soul/SKILL.md", "content")
    assert result.error is None  # write succeeded even though SI failed
    assert result.path == "/skills/soul/SKILL.md"


# ---------------------------------------------------------------------------
# edit()
# ---------------------------------------------------------------------------


def test_edit_applies_replacement(backend, config_service, user_id):
    config_service.read = AsyncMock(return_value="hello world\n")
    result = backend.edit("/skills/soul/SKILL.md", "world", "there")

    assert result.error is None
    assert result.occurrences == 1
    config_service.write.assert_called_once_with(
        "skills/soul/SKILL.md", user_id, "hello there\n"
    )


def test_edit_replace_all(backend, config_service, user_id):
    config_service.read = AsyncMock(return_value="x x x\n")
    result = backend.edit("/skills/soul/SKILL.md", "x", "y", replace_all=True)

    assert result.error is None
    assert result.occurrences == 3
    written_content = config_service.write.call_args.args[2]
    assert written_content == "y y y\n"


def test_edit_to_system_rejected(config_service, user_id):
    policy = ModificationPolicy(
        immutable_paths=["/user/skills/**"],
        mutable_paths=[],
        elevated_review=[],
    )
    b = ClarityBackend(config_service, user_id, SecurityBoundary(policy))
    result = b.edit("/skills/soul/SKILL.md", "old", "new")
    assert result.error is not None
    assert "immutable" in result.error
    config_service.write.assert_not_called()


def test_edit_string_not_found(backend, config_service, user_id):
    config_service.read = AsyncMock(return_value="hello world\n")
    result = backend.edit("/f.md", "missing_string", "replacement")
    assert result.error is not None
    assert "not found" in result.error


def test_edit_file_not_found(backend, config_service, user_id):
    config_service.read = AsyncMock(return_value=None)
    result = backend.edit("/missing.md", "old", "new")
    assert result.error is not None
    assert "file_not_found" in result.error


def test_edit_triggers_self_improvement(
    backend_with_si, config_service, self_improvement_service, user_id
):
    config_service.read = AsyncMock(return_value="old content\n")
    backend_with_si.edit("/skills/soul/SKILL.md", "old", "new")
    self_improvement_service.propose_change.assert_called_once()


# ---------------------------------------------------------------------------
# ls()
# ---------------------------------------------------------------------------


def test_ls_merges_namespaces(backend, config_service, user_id):
    """ls() calls ConfigService.list_paths and maps results to display paths."""
    result = backend.ls("/skills/")
    config_service.list_paths.assert_called_once_with("skills/", user_id)
    assert result.error is None
    assert len(result.entries) == 2
    paths = [e["path"] for e in result.entries]
    assert "/skills/soul/SKILL.md" in paths
    assert "/skills/soul/notes.txt" in paths


def test_ls_strips_leading_slash(backend, config_service, user_id):
    backend.ls("/skills/soul/")
    config_service.list_paths.assert_called_once_with("skills/soul/", user_id)


def test_ls_empty_directory(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(return_value=[])
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.ls("/nonexistent/")
    assert result.error is None
    assert result.entries == []


# ---------------------------------------------------------------------------
# grep()
# ---------------------------------------------------------------------------


def test_grep_searches_content(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(return_value=["skills/soul/SKILL.md"])
    config_service.read = AsyncMock(return_value="line with TODO here\nno match\n")
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.grep("TODO")
    assert result.error is None
    assert len(result.matches) == 1
    assert result.matches[0]["line"] == 1
    assert "TODO" in result.matches[0]["text"]
    assert result.matches[0]["path"] == "/skills/soul/SKILL.md"


def test_grep_no_matches(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(return_value=["skills/soul/SKILL.md"])
    config_service.read = AsyncMock(return_value="no match here\n")
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.grep("FIXME")
    assert result.error is None
    assert result.matches == []


def test_grep_glob_filter(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(
        return_value=["skills/soul/SKILL.md", "skills/soul/notes.txt"]
    )
    config_service.read = AsyncMock(return_value="pattern here\n")
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.grep("pattern", glob="*.md")
    # Only SKILL.md matches the *.md glob
    paths = [m["path"] for m in result.matches]
    assert "/skills/soul/SKILL.md" in paths
    assert not any("notes.txt" in p for p in paths)


# ---------------------------------------------------------------------------
# glob()
# ---------------------------------------------------------------------------


def test_glob_filters_filenames(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(
        return_value=["skills/soul/SKILL.md", "skills/soul/notes.txt", "skills/tools/SKILL.md"]
    )
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.glob("SKILL.md")
    assert result.error is None
    matched_paths = [e["path"] for e in result.matches]
    assert "/skills/soul/SKILL.md" in matched_paths
    assert "/skills/tools/SKILL.md" in matched_paths
    assert not any("notes.txt" in p for p in matched_paths)


def test_glob_wildcard_pattern(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(
        return_value=["skills/soul/SKILL.md", "skills/soul/notes.txt"]
    )
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.glob("*.txt")
    paths = [e["path"] for e in result.matches]
    assert "/skills/soul/notes.txt" in paths
    assert not any(".md" in p for p in paths)


def test_glob_no_matches(config_service, permissive_boundary, user_id):
    config_service.list_paths = AsyncMock(return_value=["skills/soul/SKILL.md"])
    b = ClarityBackend(config_service, user_id, permissive_boundary)
    result = b.glob("*.json")
    assert result.error is None
    assert result.matches == []


# ---------------------------------------------------------------------------
# Path stripping
# ---------------------------------------------------------------------------


def test_path_stripping_read(backend, config_service, user_id):
    """All path consumers strip the leading slash before calling ConfigService."""
    backend.read("///triple/leading/slash.md")
    config_service.read.assert_called_once_with("triple/leading/slash.md", user_id)


def test_path_stripping_write(backend, config_service, user_id):
    backend.write("///skills/soul/SKILL.md", "content")
    config_service.write.assert_called_once_with("skills/soul/SKILL.md", user_id, "content")


def test_path_stripping_ls(backend, config_service, user_id):
    backend.ls("///skills/")
    config_service.list_paths.assert_called_once_with("skills/", user_id)
