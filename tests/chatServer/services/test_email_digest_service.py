"""Tests for EmailDigestService LTM integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.email_digest_service import EmailDigestService

_BUILD_AGENT = "chatServer.services.email_digest_service.build_deep_agent"


def _mock_agent(response_text="Digest content"):
    """Return a mock Deep Agent whose ainvoke() yields response_text."""
    agent = MagicMock()
    last_msg = MagicMock()
    last_msg.content = response_text
    agent.ainvoke = AsyncMock(return_value={"messages": [last_msg]})
    return agent


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
        "chatServer.database.supabase_client.create_system_client",
        new_callable=AsyncMock,
        return_value=mock_db,
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
        "chatServer.database.supabase_client.create_system_client",
        new_callable=AsyncMock,
        return_value=mock_db,
    ):
        result = await service._load_ltm("user-123", "email_digest_agent")

    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_prepends_ltm_to_prompt(service):
    """When LTM exists, it is prepended to the digest prompt."""
    mock_agent = _mock_agent("Digest content")

    with patch(
        _BUILD_AGENT,
        new_callable=AsyncMock,
        return_value=mock_agent,
    ), patch.object(
        service, "_load_ltm", return_value="User prefers concise summaries"
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    # Verify the prompt passed to agent.ainvoke() included LTM context
    invoke_arg = mock_agent.ainvoke.call_args[0][0]
    prompt_text = invoke_arg["messages"][0]["content"]
    assert "User context (from memory):" in prompt_text
    assert "User prefers concise summaries" in prompt_text


@pytest.mark.asyncio
async def test_generate_digest_works_without_ltm(service):
    """When no LTM exists, the digest still generates normally."""
    mock_agent = _mock_agent("Digest content")

    with patch(
        _BUILD_AGENT,
        new_callable=AsyncMock,
        return_value=mock_agent,
    ), patch.object(
        service, "_load_ltm", return_value=None
    ), patch.object(
        service, "_store_digest_result", return_value=True
    ):
        result = await service.generate_digest(hours_back=24)

    assert result["success"] is True
    invoke_arg = mock_agent.ainvoke.call_args[0][0]
    prompt_text = invoke_arg["messages"][0]["content"]
    assert "User context (from memory):" not in prompt_text
    assert "email digest" in prompt_text.lower()
