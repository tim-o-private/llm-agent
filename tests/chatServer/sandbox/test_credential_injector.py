"""Tests for CredentialInjector — OAuth token injection as env vars."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.sandbox.credential_injector import CredentialInjector


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def injector(mock_db):
    return CredentialInjector(mock_db)


def _mock_query_chain(db, data):
    """Build a chained Supabase query mock returning *data*."""
    result = MagicMock()
    result.data = data

    chain = AsyncMock()
    chain.execute = AsyncMock(return_value=result)

    limit_mock = MagicMock(return_value=chain)
    eq3 = MagicMock(return_value=MagicMock(limit=limit_mock))
    eq2 = MagicMock(return_value=MagicMock(eq=eq3))
    eq1 = MagicMock(return_value=MagicMock(eq=eq2))
    select = MagicMock(return_value=MagicMock(eq=eq1))
    table = MagicMock(return_value=MagicMock(select=select))
    db.table = table


class TestGetEnvForTool:
    @pytest.mark.asyncio
    async def test_returns_tokens_for_google(self, mock_db, injector):
        _mock_query_chain(mock_db, [
            {"access_token": "at_123", "refresh_token": "rt_456"},
        ])

        env = await injector.get_env_for_tool("user-1", "google")

        assert env["GOOGLE_ACCESS_TOKEN"] == "at_123"
        assert env["GOOGLE_REFRESH_TOKEN"] == "rt_456"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_connection(self, mock_db, injector):
        _mock_query_chain(mock_db, [])

        env = await injector.get_env_for_tool("user-1", "google")

        assert env == {}

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self, mock_db, injector):
        mock_db.table.side_effect = Exception("DB down")

        env = await injector.get_env_for_tool("user-1", "google")

        assert env == {}

    @pytest.mark.asyncio
    async def test_omits_missing_refresh_token(self, mock_db, injector):
        _mock_query_chain(mock_db, [
            {"access_token": "at_123", "refresh_token": None},
        ])

        env = await injector.get_env_for_tool("user-1", "google")

        assert "GOOGLE_ACCESS_TOKEN" in env
        assert "GOOGLE_REFRESH_TOKEN" not in env

    @pytest.mark.asyncio
    async def test_gmail_maps_to_google_prefix(self, mock_db, injector):
        _mock_query_chain(mock_db, [
            {"access_token": "at_gmail", "refresh_token": "rt_gmail"},
        ])

        env = await injector.get_env_for_tool("user-1", "gmail")

        assert env["GOOGLE_ACCESS_TOKEN"] == "at_gmail"
        assert env["GOOGLE_REFRESH_TOKEN"] == "rt_gmail"

    @pytest.mark.asyncio
    async def test_unknown_provider_uses_uppercase_name(self, mock_db, injector):
        _mock_query_chain(mock_db, [
            {"access_token": "at_slack", "refresh_token": None},
        ])

        env = await injector.get_env_for_tool("user-1", "slack")

        assert env["SLACK_ACCESS_TOKEN"] == "at_slack"
