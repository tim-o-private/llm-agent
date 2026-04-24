"""Integration tests for /api/vault/entities/* — index, search, auth, cross-user.

Wires the real entity_router + vault_router against a real VaultService
backed by tmp_path. Auth goes through dependency_overrides.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.entity_router import get_entity_service, router as entity_router
from chatServer.routers.vault_router import get_vault_service
from chatServer.services.entity_service import EntityService
from chatServer.services.vault_service import VaultService

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


def _make_vault(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _build_app(user_id: str, vault: VaultService) -> FastAPI:
    app = FastAPI()
    app.include_router(entity_router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_vault_service] = lambda: vault
    return app


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


def _write_entity(
    user_root: Path, entity_type: str, slug: str, content: str
) -> None:
    path = user_root / "entities" / entity_type / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    @pytest.mark.asyncio
    async def test_index_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(entity_router)
        app.dependency_overrides[get_vault_service] = lambda: vault
        # No auth override — should get 401/403
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/index")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Entity index
# ---------------------------------------------------------------------------


class TestEntityIndex:
    @pytest.mark.asyncio
    async def test_empty_vault(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/index")
        assert r.status_code == 200
        data = r.json()
        assert data["entities"] == []

    @pytest.mark.asyncio
    async def test_returns_entities(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_entity(
            user_root,
            "people",
            "alice",
            "---\nentity_type: person\nname: Alice Chen\naliases:\n  - alice@co.com\n---\n",
        )
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/index")
        assert r.status_code == 200
        entities = r.json()["entities"]
        assert len(entities) == 1
        assert entities[0]["slug"] == "alice"
        assert entities[0]["name"] == "Alice Chen"
        assert entities[0]["entity_type"] == "person"
        assert entities[0]["path"] == "entities/people/alice.md"
        assert "alice@co.com" in entities[0]["aliases"]

    @pytest.mark.asyncio
    async def test_filter_by_type(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\n---\n",
        )
        _write_entity(
            user_root, "companies", "acme",
            "---\nentity_type: company\nname: Acme\n---\n",
        )
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/index", params={"entity_type": "people"})
        assert r.status_code == 200
        entities = r.json()["entities"]
        assert len(entities) == 1
        assert entities[0]["entity_type"] == "person"


# ---------------------------------------------------------------------------
# Entity search
# ---------------------------------------------------------------------------


class TestEntitySearch:
    @pytest.mark.asyncio
    async def test_search_by_name(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice Chen\n---\n",
        )
        _write_entity(
            user_root, "people", "bob",
            "---\nentity_type: person\nname: Bob Smith\n---\n",
        )
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/search", params={"q": "alice"})
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["name"] == "Alice Chen"


# ---------------------------------------------------------------------------
# Cross-user isolation (AC-23)
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_user_a_cannot_see_user_b_entities(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)
        user_b_root = _prep_user(tmp_path, TEST_USER_B)

        _write_entity(
            user_b_root, "people", "secret",
            "---\nentity_type: person\nname: Secret Person\n---\n",
        )

        # User A should not see User B's entities
        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/entities/index")
        assert r.status_code == 200
        assert r.json()["entities"] == []
