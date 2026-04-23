"""Integration tests for suggest card endpoints — accept, dismiss, activity_log.

These tests wire the router against a real VaultService (for path resolution)
and mock Supabase clients (for suggest_cards table). The suggest card
endpoints need DB access, so we override ``get_user_scoped_client`` with
mocks that simulate the suggest_cards table.

See SPEC-047 AC-22, AC-23.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.vault_file_router import router as vault_file_router
from chatServer.routers.vault_router import get_vault_service
from chatServer.services.vault_service import VaultService

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"
CARD_ID = "card-001"


def _make_vault(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _pending_card(**overrides):
    card = {
        "id": CARD_ID,
        "user_id": TEST_USER_A,
        "file_path": "notes/meeting.md",
        "target_line": 5,
        "label": "Clarity suggests",
        "body": "You should add a summary section",
        "suggested_text": "## Summary\n\nKey takeaways.",
        "status": "pending",
        "created_at": "2026-04-21T10:00:00Z",
        "decided_at": None,
    }
    card.update(overrides)
    return card


def _mock_user_client_with_card(card=None):
    """Build a mock UserScopedClient that returns the given card on select."""
    client = MagicMock()
    rows = [card] if card else []

    def table(_name):
        tbl = MagicMock()
        chain = MagicMock()
        for method in ("select", "eq", "order", "limit", "update"):
            setattr(chain, method, MagicMock(return_value=chain))
        chain.execute = AsyncMock(return_value=MagicMock(data=rows))
        tbl.select = MagicMock(return_value=chain)
        tbl.update = MagicMock(return_value=chain)
        tbl.eq = MagicMock(return_value=chain)
        return tbl

    client.table = MagicMock(side_effect=table)
    return client


def _mock_system_client():
    client = MagicMock()

    def table(_name):
        tbl = MagicMock()
        insert_chain = MagicMock()
        insert_chain.execute = AsyncMock(
            return_value=MagicMock(data=[{"id": "act-1"}])
        )
        tbl.insert = MagicMock(return_value=insert_chain)
        return tbl

    client.table = MagicMock(side_effect=table)
    return client


def _build_app(
    user_id: str,
    vault: VaultService,
    user_client=None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(vault_file_router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_vault_service] = lambda: vault
    if user_client is not None:
        app.dependency_overrides[get_user_scoped_client] = lambda: user_client
    return app


# ---------------------------------------------------------------------------
# POST /api/vault/file/suggest/{id}/accept
# ---------------------------------------------------------------------------


class TestAcceptSuggestCard:
    @pytest.mark.asyncio
    async def test_accept_returns_text_and_line(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _pending_card()
        user_client = _mock_user_client_with_card(card)

        app = _build_app(TEST_USER_A, vault, user_client)
        transport = ASGITransport(app=app)
        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=_mock_system_client(),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post(f"/api/vault/file/suggest/{CARD_ID}/accept")

        assert r.status_code == 200
        body = r.json()
        assert body["text"] == card["suggested_text"]
        assert body["target_line"] == card["target_line"]

    @pytest.mark.asyncio
    async def test_accept_404_missing_card(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_client = _mock_user_client_with_card(None)

        app = _build_app(TEST_USER_A, vault, user_client)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/file/suggest/nonexistent/accept")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_409_already_accepted(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _pending_card(status="accepted")
        user_client = _mock_user_client_with_card(card)

        app = _build_app(TEST_USER_A, vault, user_client)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(f"/api/vault/file/suggest/{CARD_ID}/accept")
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/vault/file/suggest/{id}/dismiss
# ---------------------------------------------------------------------------


class TestDismissSuggestCard:
    @pytest.mark.asyncio
    async def test_dismiss_returns_204(self, tmp_path):
        vault = _make_vault(tmp_path)
        card = _pending_card()
        user_client = _mock_user_client_with_card(card)

        app = _build_app(TEST_USER_A, vault, user_client)
        transport = ASGITransport(app=app)
        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=_mock_system_client(),
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post(f"/api/vault/file/suggest/{CARD_ID}/dismiss")

        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_dismiss_404_missing_card(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_client = _mock_user_client_with_card(None)

        app = _build_app(TEST_USER_A, vault, user_client)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/file/suggest/nonexistent/dismiss")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_user_b_cannot_accept_user_a_card(self, tmp_path):
        """User B's scoped client won't find User A's card."""
        vault = _make_vault(tmp_path)
        # Empty result for user B (card belongs to user A)
        user_client = _mock_user_client_with_card(None)

        app = _build_app(TEST_USER_B, vault, user_client)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(f"/api/vault/file/suggest/{CARD_ID}/accept")
        assert r.status_code == 404
