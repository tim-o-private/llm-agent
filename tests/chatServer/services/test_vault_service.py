"""Unit tests for VaultService — the filesystem chokepoint.

``_resolve`` is security-critical. The negative matrix in this file is
non-negotiable: ``..`` segments, absolute paths, null bytes, and symlink
components must all raise HTTPException(403).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from chatServer.services.vault_service import VaultService

USER_A = "11111111-1111-1111-1111-111111111111"
USER_B = "22222222-2222-2222-2222-222222222222"


def _make_service(tmp_path: Path, sync=None) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=sync, data_dir=tmp_path)


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


# ---------------------------------------------------------------------------
# AC-22 — negative matrix for _resolve
# ---------------------------------------------------------------------------


class TestResolveRejectsTraversal:
    """AC-22: ``_resolve`` rejects any path that escapes the user sandbox."""

    def test_dotdot_escapes_single_level(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "../other/secret")
        assert exc.value.status_code == 403

    def test_dotdot_nested(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "subdir/../../etc/passwd")
        assert exc.value.status_code == 403

    def test_dotdot_alone(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "..")
        assert exc.value.status_code == 403

    def test_absolute_path_rejected(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "/etc/passwd")
        assert exc.value.status_code == 403

    def test_absolute_path_inside_vault_rejected(self, tmp_path):
        """Even an absolute path that would land inside the vault is rejected."""
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, str(user_root / "today.md"))
        assert exc.value.status_code == 403

    def test_null_byte_rejected(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "today.md\x00.bak")
        assert exc.value.status_code == 403

    def test_empty_string_rejected(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException):
            svc._resolve(USER_A, "")

    def test_current_dir_rejected(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException):
            svc._resolve(USER_A, ".")

    def test_symlink_component_rejected(self, tmp_path):
        """A symlink anywhere on the path rejects the whole resolve."""
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        # Create a symlink pointing outside the vault.
        target = tmp_path / "outside"
        target.mkdir()
        (target / "secret.md").write_text("pwn")
        link = user_root / "link"
        link.symlink_to(target)

        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, "link/secret.md")
        assert exc.value.status_code == 403

    def test_symlink_pointing_into_vault_rejected(self, tmp_path):
        """Even a symlink pointing *inside* the vault is rejected — tamper signal."""
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        real = user_root / "real.md"
        real.write_text("ok")
        link = user_root / "alias.md"
        link.symlink_to(real)

        with pytest.raises(HTTPException):
            svc._resolve(USER_A, "alias.md")

    def test_cross_user_rejected(self, tmp_path):
        """User A cannot traverse into User B's sandbox."""
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        _prep_user(tmp_path, USER_B)
        with pytest.raises(HTTPException) as exc:
            svc._resolve(USER_A, f"../{USER_B}/today.md")
        assert exc.value.status_code == 403

    def test_backslash_segments_rejected_via_dotdot(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        # Backslashes are not separators on POSIX, so they don't escape on
        # their own — but doubled dots in a single part still caught.
        with pytest.raises(HTTPException):
            svc._resolve(USER_A, "a/../../escape")


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------


class TestResolveAcceptsValidPaths:
    def test_plain_filename(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        assert svc._resolve(USER_A, "today.md") == user_root / "today.md"

    def test_nested_path(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        assert svc._resolve(USER_A, "notes/2026-04-20.md") == user_root / "notes" / "2026-04-20.md"

    def test_current_dir_in_middle(self, tmp_path):
        """A leading single-dot segment in an otherwise-safe path is fine
        after Path normalization (the inner-resolved path still lands inside)."""
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        # Path("./a.md").parts == ("a.md",) — no "." in parts
        assert svc._resolve(USER_A, "./a.md") == user_root / "a.md"


# ---------------------------------------------------------------------------
# read_file / update_body / sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_file_roundtrip(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "today.md").write_text("hello")
    assert await svc.read_file(USER_A, "today.md") == "hello"


@pytest.mark.asyncio
async def test_read_file_404_when_missing(tmp_path):
    svc = _make_service(tmp_path)
    _prep_user(tmp_path, USER_A)
    with pytest.raises(HTTPException) as exc:
        await svc.read_file(USER_A, "today.md")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_body_writes_file_and_schedules_sync(tmp_path):
    sync = MagicMock()
    sync.sync_file = AsyncMock(return_value=None)
    svc = _make_service(tmp_path, sync=sync)
    _prep_user(tmp_path, USER_A)

    mtime = await svc.update_body(USER_A, "today.md", "new body")

    assert (tmp_path / "sandboxes" / USER_A / "today.md").read_text() == "new body"
    assert isinstance(mtime, float)
    # Let any scheduled tasks run.
    import asyncio as _a
    await _a.sleep(0)
    sync.sync_file.assert_awaited()


@pytest.mark.asyncio
async def test_update_body_if_match_conflict(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    file_path = user_root / "today.md"
    file_path.write_text("original")
    actual_mtime = file_path.stat().st_mtime

    stale = actual_mtime - 10.0
    with pytest.raises(HTTPException) as exc:
        await svc.update_body(USER_A, "today.md", "new", expected_mtime=stale)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_body_rejects_oversize(tmp_path):
    svc = _make_service(tmp_path)
    _prep_user(tmp_path, USER_A)
    huge = "x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc:
        await svc.update_body(USER_A, "today.md", huge)
    assert exc.value.status_code == 413


# ---------------------------------------------------------------------------
# seed_if_missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_if_missing_copies_template(tmp_path):
    svc = _make_service(tmp_path)
    _prep_user(tmp_path, USER_A)
    (tmp_path / "config" / "system" / "templates" / "today.md").write_text("# seed")

    await svc.seed_if_missing(USER_A, "today.md", "templates/today.md")

    assert (tmp_path / "sandboxes" / USER_A / "today.md").read_text() == "# seed"


@pytest.mark.asyncio
async def test_seed_if_missing_noop_when_exists(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "today.md").write_text("existing")
    (tmp_path / "config" / "system" / "templates" / "today.md").write_text("seed")

    await svc.seed_if_missing(USER_A, "today.md", "templates/today.md")

    assert (user_root / "today.md").read_text() == "existing"


@pytest.mark.asyncio
async def test_seed_if_missing_missing_template_is_silent(tmp_path):
    svc = _make_service(tmp_path)
    _prep_user(tmp_path, USER_A)

    # Should not raise; just log.
    await svc.seed_if_missing(USER_A, "today.md", "templates/missing.md")
    assert not (tmp_path / "sandboxes" / USER_A / "today.md").exists()


# ---------------------------------------------------------------------------
# list_recent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_recent_excludes_today_and_system_dirs(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "today.md").write_text("t")
    (user_root / "a.md").write_text("a")
    (user_root / "b.md").write_text("b")

    # _workflows and _activity dirs should be skipped.
    (user_root / "_workflows").mkdir()
    (user_root / "_workflows" / "x.md").write_text("x")
    (user_root / "_activity").mkdir()
    (user_root / "_activity" / "y.md").write_text("y")

    # Stagger mtimes for determinism.
    os.utime(user_root / "a.md", (100, 100))
    os.utime(user_root / "b.md", (200, 200))

    entries = await svc.list_recent(USER_A, limit=10)
    paths = [e.path for e in entries]
    assert "today.md" not in paths
    assert "_workflows/x.md" not in paths
    assert "_activity/y.md" not in paths
    assert "b.md" in paths and "a.md" in paths
    # Most-recent first.
    assert paths.index("b.md") < paths.index("a.md")


@pytest.mark.asyncio
async def test_list_recent_empty_when_sandbox_missing(tmp_path):
    svc = _make_service(tmp_path)
    # Don't create USER_A sandbox.
    assert await svc.list_recent(USER_A) == []


@pytest.mark.asyncio
async def test_list_recent_ignores_symlinks(tmp_path):
    svc = _make_service(tmp_path)
    user_root = _prep_user(tmp_path, USER_A)
    (user_root / "a.md").write_text("a")
    (user_root / "link.md").symlink_to(user_root / "a.md")

    entries = await svc.list_recent(USER_A, limit=10)
    paths = [e.path for e in entries]
    assert "link.md" not in paths
    assert "a.md" in paths
