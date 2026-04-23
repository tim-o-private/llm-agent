"""Unit tests for VaultService.find_backlinks — SPEC-047 FU-2.

Tests the backlinks computation: finding wikilinks, excluding system dirs,
handling aliases, and ignoring non-md files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chatServer.services.vault_service import VaultService

USER_A = "11111111-1111-1111-1111-111111111111"


def _make_service(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


# ---------------------------------------------------------------------------
# Basic backlink detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finds_simple_wikilink(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "meeting.md").write_text("# Meeting notes")
    (user_root / "index.md").write_text("See [[meeting]] for details")

    result = await svc.find_backlinks(USER_A, "meeting.md")
    assert len(result) == 1
    assert result[0]["path"] == "index.md"
    assert result[0]["name"] == "index.md"


@pytest.mark.asyncio
async def test_finds_alias_wikilink(tmp_path):
    """Matches [[meeting|Meeting Notes]] syntax."""
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "meeting.md").write_text("# Meeting")
    (user_root / "daily.md").write_text("Check [[meeting|Meeting Notes]] today")

    result = await svc.find_backlinks(USER_A, "meeting.md")
    assert len(result) == 1
    assert result[0]["path"] == "daily.md"


@pytest.mark.asyncio
async def test_finds_multiple_backlinks(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "a.md").write_text("Link to [[target]]")
    (user_root / "b.md").write_text("Also references [[target|alias]]")
    (user_root / "c.md").write_text("No link here")

    result = await svc.find_backlinks(USER_A, "target.md")
    paths = [r["path"] for r in result]
    assert "a.md" in paths
    assert "b.md" in paths
    assert "c.md" not in paths
    assert len(result) == 2


@pytest.mark.asyncio
async def test_backlinks_in_subdirectory(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "notes").mkdir()
    (user_root / "notes" / "meeting.md").write_text("# Meeting")
    (user_root / "notes" / "summary.md").write_text("See [[meeting]]")

    result = await svc.find_backlinks(USER_A, "notes/meeting.md")
    assert len(result) == 1
    assert result[0]["path"] == "notes/summary.md"


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_excludes_self(tmp_path):
    """A file should not appear as its own backlink."""
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "self-ref.md").write_text("Links to [[self-ref]] itself")

    result = await svc.find_backlinks(USER_A, "self-ref.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_activity_dir(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "_activity").mkdir()
    (user_root / "_activity" / "log.md").write_text("[[target]]")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_runs_dir(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "_runs").mkdir()
    (user_root / "_runs" / "run.md").write_text("[[target]]")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_workflows_dir(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "_workflows").mkdir()
    (user_root / "_workflows" / "flow.md").write_text("[[target]]")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_hidden_files(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / ".hidden.md").write_text("[[target]]")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_non_md_files(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "notes.txt").write_text("[[target]]")
    (user_root / "data.json").write_text('{"link": "[[target]]"}')

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_excludes_symlinks(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    real = user_root / "real.md"
    real.write_text("[[target]]")
    (user_root / "link.md").symlink_to(real)

    result = await svc.find_backlinks(USER_A, "target.md")
    # Only real.md, not the symlink
    assert len(result) == 1
    assert result[0]["path"] == "real.md"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_vault(tmp_path):
    svc = _make_service(tmp_path)
    _prep_user(tmp_path, USER_A)

    result = await svc.find_backlinks(USER_A, "nonexistent.md")
    assert result == []


@pytest.mark.asyncio
async def test_no_vault_directory(tmp_path):
    """User root doesn't exist — returns empty without error."""
    svc = _make_service(tmp_path)
    result = await svc.find_backlinks(USER_A, "file.md")
    assert result == []


@pytest.mark.asyncio
async def test_file_with_no_links(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "other.md").write_text("No wikilinks here")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert result == []


@pytest.mark.asyncio
async def test_results_sorted_alphabetically(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    (user_root / "z.md").write_text("[[target]]")
    (user_root / "a.md").write_text("[[target]]")
    (user_root / "m.md").write_text("[[target]]")

    result = await svc.find_backlinks(USER_A, "target.md")
    paths = [r["path"] for r in result]
    assert paths == ["a.md", "m.md", "z.md"]


@pytest.mark.asyncio
async def test_handles_broken_encoding(tmp_path):
    """Files with bad encoding should be read with errors='replace', not crash."""
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "target.md").write_text("# Target")
    bad_file = user_root / "bad.md"
    bad_file.write_bytes(b"[[target]] \xff\xfe broken")

    result = await svc.find_backlinks(USER_A, "target.md")
    assert len(result) == 1
    assert result[0]["path"] == "bad.md"


@pytest.mark.asyncio
async def test_does_not_match_partial_stem(tmp_path):
    """[[meet]] should NOT match meeting.md."""
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "meeting.md").write_text("# Meeting")
    (user_root / "other.md").write_text("See [[meet]] for info")

    result = await svc.find_backlinks(USER_A, "meeting.md")
    assert result == []
