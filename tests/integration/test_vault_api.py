"""Integration tests for /api/vault/* — auth, path safety, cross-user isolation.

These tests wire the real router against a real VaultService backed by
tmp_path. Auth goes through dependency_overrides — unauthenticated
requests must reach a 401/403 path via the real ``get_current_user``
dependency when no override is supplied.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.vault_router import get_vault_service, router
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
    async def test_tree_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        # No auth override — should get 401/403
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_file_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "today.md"})
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_folder_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": ""})
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/vault/tree
# ---------------------------------------------------------------------------


class TestVaultTree:
    @pytest.mark.asyncio
    async def test_empty_vault(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code == 200
        assert r.json()["tree"] == []

    @pytest.mark.asyncio
    async def test_tree_returns_files_and_folders(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "today.md").write_text("# Today")
        (user_root / "notes").mkdir()
        (user_root / "notes" / "jan.md").write_text("jan")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code == 200
        tree = r.json()["tree"]
        names = [n["name"] for n in tree]
        assert "today.md" in names
        assert "notes" in names

        notes = [n for n in tree if n["name"] == "notes"][0]
        assert notes["type"] == "folder"
        assert len(notes["children"]) == 1
        assert notes["children"][0]["name"] == "jan.md"

    @pytest.mark.asyncio
    async def test_tree_excludes_hidden_and_system_dirs(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / ".hidden").write_text("x")
        (user_root / "_activity").mkdir()
        (user_root / "_activity" / "log.json").write_text("{}")
        (user_root / "_runs").mkdir()
        (user_root / "_runs" / "run.json").write_text("{}")
        (user_root / "visible.md").write_text("ok")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code == 200
        names = [n["name"] for n in r.json()["tree"]]
        assert ".hidden" not in names
        assert "_activity" not in names
        assert "_runs" not in names
        assert "visible.md" in names


# ---------------------------------------------------------------------------
# GET /api/vault/file
# ---------------------------------------------------------------------------


class TestVaultFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "today.md").write_text("# Hello")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "today.md"})
        assert r.status_code == 200
        body = r.json()
        assert body["content"] == "# Hello"
        assert body["size"] == len("# Hello")
        assert "T" in body["mtime"]

    @pytest.mark.asyncio
    async def test_read_missing_file_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "nope.md"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_path_traversal_403(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "../../../etc/passwd"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_absolute_path_403(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "/etc/passwd"})
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/vault/folder
# ---------------------------------------------------------------------------


class TestVaultFolder:
    @pytest.mark.asyncio
    async def test_root_listing(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "a.md").write_text("a")
        (user_root / "subdir").mkdir()

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": ""})
        assert r.status_code == 200
        names = [e["name"] for e in r.json()["entries"]]
        assert "a.md" in names
        assert "subdir" in names

    @pytest.mark.asyncio
    async def test_subfolder_listing(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        (user_root / "notes").mkdir()
        (user_root / "notes" / "jan.md").write_text("jan")

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": "notes"})
        assert r.status_code == 200
        entries = r.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["name"] == "jan.md"

    @pytest.mark.asyncio
    async def test_missing_folder_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": "nope"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_path_traversal_403(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": "../../etc"})
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_tree_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        root_b = _prep_user(tmp_path, TEST_USER_B)
        (root_a / "a_file.md").write_text("A's file")
        (root_b / "b_file.md").write_text("B's file")

        # User A should only see their own file
        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code == 200
        names = [n["name"] for n in r.json()["tree"]]
        assert "a_file.md" in names
        assert "b_file.md" not in names

        # User B should only see their own file
        app_b = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app_b)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/tree")
        assert r.status_code == 200
        names = [n["name"] for n in r.json()["tree"]]
        assert "b_file.md" in names
        assert "a_file.md" not in names

    @pytest.mark.asyncio
    async def test_file_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        root_b = _prep_user(tmp_path, TEST_USER_B)
        (root_a / "secret.md").write_text("A's secret")
        (root_b / "secret.md").write_text("B's secret")

        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/file", params={"path": "secret.md"})
        assert r.status_code == 200
        assert r.json()["content"] == "A's secret"

    @pytest.mark.asyncio
    async def test_folder_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        root_b = _prep_user(tmp_path, TEST_USER_B)
        (root_a / "a_only.md").write_text("A")
        (root_b / "b_only.md").write_text("B")

        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/folder", params={"path": ""})
        assert r.status_code == 200
        names = [e["name"] for e in r.json()["entries"]]
        assert "a_only.md" in names
        assert "b_only.md" not in names
