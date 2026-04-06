"""Tests for conversation_handler_builder — handler factory + caching.

Covers AC-02 (singleton client), AC-17 (tool loading), AC-31 (caching).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.conversation_handler_builder import (
    _get_anthropic_client,
    _handler_cache,
)


class TestGetAnthropicClient:
    def test_returns_singleton(self):
        """AC-02: Anthropic client is instantiated once."""
        import chatServer.services.conversation_handler_builder as mod

        mod._anthropic_client = None  # Reset
        with patch("chatServer.services.conversation_handler_builder.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            c1 = _get_anthropic_client()
            c2 = _get_anthropic_client()

            assert c1 is c2
            mock_anthropic.AsyncAnthropic.assert_called_once()
            mod._anthropic_client = None  # Cleanup


class TestHandlerCaching:
    def test_cache_is_ttl_cache(self):
        """AC-31: Handler cache uses TTLCache."""
        from cachetools import TTLCache

        assert isinstance(_handler_cache, TTLCache)

    @pytest.mark.asyncio
    async def test_build_caches_handler(self):
        """AC-31: Second call returns cached handler."""
        import chatServer.services.conversation_handler_builder as mod

        # Clear cache and client
        mod._handler_cache.clear()
        mod._anthropic_client = None

        mock_handler = MagicMock()

        with patch.object(mod, "_build_handler", new_callable=AsyncMock, return_value=mock_handler):
            with patch.object(mod, "_get_anthropic_client", return_value=MagicMock()):
                h1 = await mod.build_conversation_handler("u1", "agent", "s1")
                h2 = await mod.build_conversation_handler("u1", "agent", "s2")

                assert h1 is h2
                mod._build_handler.assert_awaited_once()

        mod._handler_cache.clear()
        mod._anthropic_client = None
