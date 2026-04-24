"""Integration tests for /api/vault/threads/* — auth, cross-user, status transitions.

Wires the real thread_router against a real VaultService backed by tmp_path.
Auth goes through dependency_overrides.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.thread_router import router
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
    app.include_router(router)
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
    async def test_list_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        # No auth override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads")
        assert r.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_status_change_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/threads/test-thread/status",
                json={"status": "watching"},
            )
        assert r.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestListThreads:
    @pytest.mark.asyncio
    async def test_empty_list(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads")
        assert r.status_code == 200
        assert r.json()["threads"] == []

    @pytest.mark.asyncio
    async def test_list_returns_active_threads(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)

        # Create a thread directly via service
        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        await svc.create_thread(TEST_USER_A, "My Thread", "test trigger")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads")
        assert r.status_code == 200
        threads = r.json()["threads"]
        assert len(threads) == 1
        assert threads[0]["title"] == "My Thread"
        assert threads[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_status_filter(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)

        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        await svc.create_thread(TEST_USER_A, "Active One", "test")
        p2 = await svc.create_thread(TEST_USER_A, "Watching One", "test")
        await svc.change_status(TEST_USER_A, p2, "watching")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads", params={"status": "watching"})
        assert r.status_code == 200
        threads = r.json()["threads"]
        assert len(threads) == 1
        assert threads[0]["title"] == "Watching One"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class TestGetThread:
    @pytest.mark.asyncio
    async def test_read_existing_thread(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)

        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        rel_path = await svc.create_thread(TEST_USER_A, "Read Me", "test")
        # Extract the slug from _threads/YYYY-MM-DD-read-me.md
        slug = rel_path.replace("_threads/", "").replace(".md", "")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get(f"/api/vault/threads/{slug}")
        assert r.status_code == 200
        assert "Read Me" in r.json()["content"]

    @pytest.mark.asyncio
    async def test_read_nonexistent_returns_404(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads/nonexistent")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Status change
# ---------------------------------------------------------------------------


class TestChangeStatus:
    @pytest.mark.asyncio
    async def test_valid_transition(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)

        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        rel_path = await svc.create_thread(TEST_USER_A, "Status Test", "test")
        slug = rel_path.replace("_threads/", "").replace(".md", "")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                f"/api/vault/threads/{slug}/status",
                json={"status": "watching"},
            )
        assert r.status_code == 200
        assert r.json()["status"] == "watching"

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_422(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        vault = _make_vault(tmp_path)

        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        rel_path = await svc.create_thread(TEST_USER_A, "Invalid Trans", "test")
        # Set to completed
        content = await vault.read_file(TEST_USER_A, rel_path)
        content = content.replace("status: active", "status: completed")
        await vault.update_body(TEST_USER_A, rel_path, content)

        slug = rel_path.replace("_threads/", "").replace(".md", "")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                f"/api/vault/threads/{slug}/status",
                json={"status": "active"},
            )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_user_b_cannot_see_user_a_threads(self, tmp_path):
        _prep_user(tmp_path, TEST_USER_A)
        _prep_user(tmp_path, TEST_USER_B)
        vault = _make_vault(tmp_path)

        from chatServer.services.thread_service import ThreadService
        svc = ThreadService(vault)
        await svc.create_thread(TEST_USER_A, "Secret Thread", "private")

        # User B sees empty list
        app = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/threads")
        assert r.status_code == 200
        assert r.json()["threads"] == []
