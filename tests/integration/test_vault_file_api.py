"""Integration tests for PUT /api/vault/file — save round-trip, auth, mtime
conflict, size limit, path traversal, 404 on missing file.

These tests wire the real router against a real VaultService backed by
tmp_path. Auth goes through dependency_overrides.

See SPEC-047 AC-19, AC-23.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.vault_file_router import router as vault_file_router
from chatServer.routers.vault_router import get_vault_service
from chatServer.services.vault_service import VaultService

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


def _make_vault(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _build_app(user_id: str, vault: VaultService) -> FastAPI:
    app = FastAPI()
    app.include_router(vault_file_router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_vault_service] = lambda: vault
    return app


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    @pytest.mark.asyncio
    async def test_save_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(vault_file_router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        # No auth override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "test.md", "content": "x", "mtime": 0},
            )
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_backlinks_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(vault_file_router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "test.md"})
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/vault/file — save round-trip
# ---------------------------------------------------------------------------


class TestSaveFile:
    @pytest.mark.asyncio
    async def test_save_roundtrip(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        file_path = user_root / "test.md"
        file_path.write_text("original")
        mtime = file_path.stat().st_mtime

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "test.md", "content": "updated", "mtime": mtime},
            )
        assert r.status_code == 200
        body = r.json()
        assert "mtime" in body
        assert isinstance(body["mtime"], float)
        # Verify disk contents
        assert file_path.read_text() == "updated"

    @pytest.mark.asyncio
    async def test_save_409_stale_mtime(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        file_path = user_root / "test.md"
        file_path.write_text("original")
        stale_mtime = file_path.stat().st_mtime - 10.0

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "test.md", "content": "new", "mtime": stale_mtime},
            )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_save_413_oversized(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        file_path = user_root / "test.md"
        file_path.write_text("small")
        mtime = file_path.stat().st_mtime

        huge = "x" * (10 * 1024 * 1024 + 1)
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "test.md", "content": huge, "mtime": mtime},
            )
        assert r.status_code == 413

    @pytest.mark.asyncio
    async def test_save_403_path_traversal(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={
                    "path": "../../../etc/passwd",
                    "content": "x",
                    "mtime": 0,
                },
            )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_save_404_nonexistent_file(self, tmp_path):
        """PUT returns 404 for files that don't exist (no create-via-PUT)."""
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "new-file.md", "content": "x", "mtime": 0},
            )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_user_b_cannot_save_user_a_file(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        _prep_user(tmp_path, TEST_USER_B)
        (root_a / "secret.md").write_text("A's file")

        # User B tries to save to a path that only exists in A's sandbox
        app = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.put(
                "/api/vault/file",
                json={"path": "secret.md", "content": "pwned", "mtime": 0},
            )
        # 404 because secret.md doesn't exist in B's sandbox
        assert r.status_code == 404
        # A's file should be untouched
        assert (root_a / "secret.md").read_text() == "A's file"
