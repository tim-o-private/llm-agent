"""Unit tests for FileContextService — SPEC-047 FU-2.

Tests suggest card state transitions, activity_log emission, and file
context composition. Uses mock DB clients (no real Supabase).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from chatServer.services.file_context_service import FileContextService

USER_A = "user-a"
CARD_ID = "card-001"


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_user_client(select_rows=None):
    """Return a mock UserScopedClient with chainable query methods."""
    client = MagicMock()

    def table(_name):
        tbl = MagicMock()
        chain = MagicMock()

        # Make every chained method return the same chain
        for method in ("select", "eq", "order", "limit", "update"):
            getattr(chain, method, None)
            setattr(chain, method, MagicMock(return_value=chain))

        chain.execute = AsyncMock(
            return_value=MagicMock(data=select_rows or [])
        )
        tbl.select = MagicMock(return_value=chain)
        tbl.update = MagicMock(return_value=chain)

        # Wire eq, order, limit on tbl itself for direct chaining
        tbl.eq = MagicMock(return_value=chain)
        tbl.order = MagicMock(return_value=chain)
        tbl.limit = MagicMock(return_value=chain)

        return tbl

    client.table = MagicMock(side_effect=table)
    return client


def _mock_system_client():
    """Return a mock SystemClient whose insert echoes the payload."""
    client = MagicMock()

    def table(_name):
        tbl = MagicMock()
        insert_chain = MagicMock()
        insert_chain.execute = AsyncMock(
            return_value=MagicMock(data=[{"id": "activity-1"}])
        )
        tbl.insert = MagicMock(return_value=insert_chain)
        return tbl

    client.table = MagicMock(side_effect=table)
    return client


def _pending_card(**overrides):
    """Return a dict representing a pending suggest card row."""
    card = {
        "id": CARD_ID,
        "user_id": USER_A,
        "file_path": "notes/meeting.md",
        "target_line": 5,
        "label": "Clarity suggests",
        "body": "You should add a summary section",
        "suggested_text": "## Summary\n\nKey takeaways from the meeting.",
        "status": "pending",
        "created_at": "2026-04-21T10:00:00Z",
        "decided_at": None,
    }
    card.update(overrides)
    return card


# ---------------------------------------------------------------------------
# get_file_context
# ---------------------------------------------------------------------------


class TestGetFileContext:
    @pytest.mark.asyncio
    async def test_returns_null_summary(self):
        user = _mock_user_client(select_rows=[])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        result = await svc.get_file_context(USER_A, "notes/meeting.md")
        assert result["summary"] is None

    @pytest.mark.asyncio
    async def test_returns_suggest_cards_and_activity(self):
        card = _pending_card()
        activity = {"id": "act-1", "action": "edited file", "status": "done"}
        user = _mock_user_client(select_rows=[card])
        # Override second table call to return activity
        call_count = {"n": 0}
        original_table = user.table.side_effect

        def table_dispatch(name):
            call_count["n"] += 1
            tbl = original_table(name)
            if call_count["n"] > 1:
                # Second table call is for activity_log
                chain = MagicMock()
                for method in ("select", "eq", "order", "limit"):
                    setattr(chain, method, MagicMock(return_value=chain))
                chain.execute = AsyncMock(
                    return_value=MagicMock(data=[activity])
                )
                tbl.select = MagicMock(return_value=chain)
            return tbl

        user.table.side_effect = table_dispatch

        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        result = await svc.get_file_context(USER_A, "notes/meeting.md")
        assert isinstance(result["suggest_cards"], list)
        assert isinstance(result["activity"], list)

    @pytest.mark.asyncio
    async def test_requires_user_client(self):
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=None)
        with pytest.raises(RuntimeError, match="user_client required"):
            await svc.get_file_context(USER_A, "notes/meeting.md")


# ---------------------------------------------------------------------------
# accept_suggest_card
# ---------------------------------------------------------------------------


class TestAcceptSuggestCard:
    @pytest.mark.asyncio
    async def test_accept_returns_text_and_target_line(self):
        card = _pending_card()
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=_mock_system_client(),
        ):
            result = await svc.accept_suggest_card(USER_A, CARD_ID)

        assert result["text"] == card["suggested_text"]
        assert result["target_line"] == card["target_line"]

    @pytest.mark.asyncio
    async def test_accept_404_when_card_not_found(self):
        user = _mock_user_client(select_rows=[])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with pytest.raises(HTTPException) as exc:
            await svc.accept_suggest_card(USER_A, "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_409_when_already_accepted(self):
        card = _pending_card(status="accepted")
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with pytest.raises(HTTPException) as exc:
            await svc.accept_suggest_card(USER_A, CARD_ID)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_accept_409_when_already_dismissed(self):
        card = _pending_card(status="dismissed")
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with pytest.raises(HTTPException) as exc:
            await svc.accept_suggest_card(USER_A, CARD_ID)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_accept_emits_activity_log(self):
        card = _pending_card()
        user = _mock_user_client(select_rows=[card])
        mock_system = _mock_system_client()
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=mock_system,
        ):
            await svc.accept_suggest_card(USER_A, CARD_ID)

        # Verify activity_log insert was called
        mock_system.table.assert_called_with("activity_log")

    @pytest.mark.asyncio
    async def test_accept_handles_null_suggested_text(self):
        """Informational cards have no suggested_text."""
        card = _pending_card(suggested_text=None)
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=_mock_system_client(),
        ):
            result = await svc.accept_suggest_card(USER_A, CARD_ID)

        assert result["text"] is None
        assert result["target_line"] == 5

    @pytest.mark.asyncio
    async def test_accept_requires_user_client(self):
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=None)
        with pytest.raises(RuntimeError, match="user_client required"):
            await svc.accept_suggest_card(USER_A, CARD_ID)


# ---------------------------------------------------------------------------
# dismiss_suggest_card
# ---------------------------------------------------------------------------


class TestDismissSuggestCard:
    @pytest.mark.asyncio
    async def test_dismiss_returns_none(self):
        card = _pending_card()
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=_mock_system_client(),
        ):
            result = await svc.dismiss_suggest_card(USER_A, CARD_ID)

        assert result is None

    @pytest.mark.asyncio
    async def test_dismiss_404_when_card_not_found(self):
        user = _mock_user_client(select_rows=[])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with pytest.raises(HTTPException) as exc:
            await svc.dismiss_suggest_card(USER_A, "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_dismiss_409_when_already_dismissed(self):
        card = _pending_card(status="dismissed")
        user = _mock_user_client(select_rows=[card])
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with pytest.raises(HTTPException) as exc:
            await svc.dismiss_suggest_card(USER_A, CARD_ID)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_dismiss_emits_activity_log(self):
        card = _pending_card()
        user = _mock_user_client(select_rows=[card])
        mock_system = _mock_system_client()
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=user)

        with patch(
            "chatServer.database.supabase_client.create_system_client",
            new_callable=AsyncMock,
            return_value=mock_system,
        ):
            await svc.dismiss_suggest_card(USER_A, CARD_ID)

        mock_system.table.assert_called_with("activity_log")

    @pytest.mark.asyncio
    async def test_dismiss_requires_user_client(self):
        vault = MagicMock()
        svc = FileContextService(vault_service=vault, user_client=None)
        with pytest.raises(RuntimeError, match="user_client required"):
            await svc.dismiss_suggest_card(USER_A, CARD_ID)


# ---------------------------------------------------------------------------
# get_backlinks (delegation)
# ---------------------------------------------------------------------------


class TestGetBacklinks:
    @pytest.mark.asyncio
    async def test_delegates_to_vault_service(self):
        vault = MagicMock()
        vault.find_backlinks = AsyncMock(
            return_value=[{"path": "index.md", "name": "index.md"}]
        )
        svc = FileContextService(vault_service=vault)

        result = await svc.get_backlinks(USER_A, "meeting.md")
        assert result == [{"path": "index.md", "name": "index.md"}]
        vault.find_backlinks.assert_awaited_once_with(USER_A, "meeting.md")
