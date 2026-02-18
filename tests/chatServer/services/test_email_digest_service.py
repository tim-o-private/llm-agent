"""Tests for EmailDigestService LTM integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.email_digest_service import EmailDigestService


@pytest.fixture
def service():
    return EmailDigestService(user_id="user-123", context="scheduled")


@pytest.mark.asyncio
async def test_load_ltm_returns_notes(service):
    """_load_ltm returns notes when they exist."""
    mock_result = MagicMock()
    mock_result.data = {"notes": "User cares about Q1 launch"}

    mock_db = MagicMock()
    chain = mock_db.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

    with patch(
        "chatServer.services.email_digest_service.create_client",
        return_value=mock_db,
    ), patch.dict(
        "os.environ",
        {"VITE_SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "key"},
    ):
        result = await service._load_ltm("user-123", "email_digest_agent")

    assert result == "User cares about Q1 launch"


@pytest.mark.asyncio
async def test_load_ltm_returns_none_on_missing(service):
    """_load_ltm returns None when no notes exist."""
    mock_result = MagicMock()
    mock_result.data = None

    mock_db = MagicMock()
    chain = mock_db.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

    with patch(
        "chatServer.services.email_digest_service.create_client",
        return_value=mock_db,
    ), patch.dict(
        "os.environ",
        {"VITE_SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "key"},
    ):
        result = await service._load_ltm("user-123", "email_digest_agent")

    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_prepends_ltm_to_prompt(service):
    """When LTM exists, it is prepended to the digest prompt."""
    mock_executor = MagicMock()
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Digest content"})

    with patch(
        "chatServer.services.email_digest_service.load_agent_executor_db",
        return_value=mock_executor,
    ), patch.object(
        service, "_load_ltm", return_value="User prefers concise summaries"
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    # Verify the prompt included LTM context
    call_args = mock_executor.ainvoke.call_args[0][0]
    assert "User context (from memory):" in call_args["input"]
    assert "User prefers concise summaries" in call_args["input"]


@pytest.mark.asyncio
async def test_generate_digest_works_without_ltm(service):
    """When no LTM exists, the digest still generates normally."""
    mock_executor = MagicMock()
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Digest content"})

    with patch(
        "chatServer.services.email_digest_service.load_agent_executor_db",
        return_value=mock_executor,
    ), patch.object(
        service, "_load_ltm", return_value=None
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    call_args = mock_executor.ainvoke.call_args[0][0]
    assert "User context (from memory):" not in call_args["input"]
    assert "email digest" in call_args["input"].lower()
