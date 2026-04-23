"""Integration tests for GET /api/vault/backlinks — backlinks endpoint,
auth, cross-user isolation.

See SPEC-047 AC-20, AC-23.
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
    async def test_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(vault_file_router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "test.md"})
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/vault/backlinks
# ---------------------------------------------------------------------------


class TestBacklinks:
    @pytest.mark.asyncio
    async def test_returns_backlinks(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "target.md").write_text("# Target")
        (user_root / "linker.md").write_text("See [[target]] for info")
        (user_root / "other.md").write_text("No links")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "target.md"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["backlinks"]) == 1
        assert body["backlinks"][0]["path"] == "linker.md"
        assert body["backlinks"][0]["name"] == "linker.md"

    @pytest.mark.asyncio
    async def test_empty_vault_returns_empty_list(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "missing.md"})
        assert r.status_code == 200
        assert r.json()["backlinks"] == []

    @pytest.mark.asyncio
    async def test_handles_alias_syntax(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "meeting.md").write_text("# Meeting")
        (user_root / "index.md").write_text("Check [[meeting|Meeting Notes]]")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "meeting.md"})
        assert r.status_code == 200
        assert len(r.json()["backlinks"]) == 1


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_backlinks_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        root_b = _prep_user(tmp_path, TEST_USER_B)
        (root_a / "target.md").write_text("# A's target")
        (root_a / "linker.md").write_text("[[target]]")
        (root_b / "target.md").write_text("# B's target")
        # B has no linker

        # User A should see their own backlinks
        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "target.md"})
        assert r.status_code == 200
        assert len(r.json()["backlinks"]) == 1

        # User B should see no backlinks
        app_b = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app_b)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/backlinks", params={"path": "target.md"})
        assert r.status_code == 200
        assert len(r.json()["backlinks"]) == 0
