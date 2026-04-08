"""Tests for EmailDigestService LTM integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.email_digest_service import EmailDigestService

_BUILD_HANDLER = "chatServer.services.email_digest_service.build_conversation_handler"


def _mock_handler(response_text="Digest content"):
    """Return a mock ConversationHandler whose run() yields response_text."""
    handler = MagicMock()
    run_result = MagicMock()
    run_result.response_text = response_text
    handler.run = AsyncMock(return_value=run_result)
    return handler


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
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "key"},
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
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "key"},
    ):
        result = await service._load_ltm("user-123", "email_digest_agent")

    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_prepends_ltm_to_prompt(service):
    """When LTM exists, it is prepended to the digest prompt."""
    mock_handler = _mock_handler("Digest content")

    with patch(
        _BUILD_HANDLER,
        new_callable=AsyncMock,
        return_value=mock_handler,
    ), patch.object(
        service, "_load_ltm", return_value="User prefers concise summaries"
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    # Verify the prompt passed to handler.run() included LTM context
    messages = mock_handler.run.call_args[0][0]
    prompt_text = messages[0]["content"]
    assert "User context (from memory):" in prompt_text
    assert "User prefers concise summaries" in prompt_text


@pytest.mark.asyncio
async def test_generate_digest_works_without_ltm(service):
    """When no LTM exists, the digest still generates normally."""
    mock_handler = _mock_handler("Digest content")

    with patch(
        _BUILD_HANDLER,
        new_callable=AsyncMock,
        return_value=mock_handler,
    ), patch.object(
        service, "_load_ltm", return_value=None
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    messages = mock_handler.run.call_args[0][0]
    prompt_text = messages[0]["content"]
    assert "User context (from memory):" not in prompt_text
    assert "email digest" in prompt_text.lower()
