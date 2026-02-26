"""Unit tests for WebSearchService — both DDG and Tavily providers."""

import os
from unittest.mock import MagicMock, patch

import pytest

from chatServer.services.web_search_service import WebSearchService


class TestWebSearchServiceDDG:
    @pytest.mark.asyncio
    async def test_ddg_search_returns_normalized_results(self):
        raw = [{"title": "T", "href": "U", "body": "S"}]
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = raw
        with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
            service = WebSearchService(provider="duckduckgo")
            results = await service.search("test query")
        assert results == [{"title": "T", "url": "U", "snippet": "S"}]

    @pytest.mark.asyncio
    async def test_ddg_network_error_propagates(self):
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = Exception("network failure")
        with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
            service = WebSearchService(provider="duckduckgo")
            with pytest.raises(Exception, match="network failure"):
                await service.search("test query")

    @pytest.mark.asyncio
    async def test_max_results_capped_at_10(self):
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = []
        with patch("duckduckgo_search.DDGS", return_value=mock_ddgs):
            service = WebSearchService(provider="duckduckgo")
            await service.search("test query", max_results=20)
            mock_ddgs.text.assert_called_once_with("test query", max_results=10)


class TestWebSearchServiceTavily:
    @pytest.mark.asyncio
    async def test_tavily_search_returns_normalized_results(self):
        raw = {"results": [{"title": "T", "url": "U", "content": "S"}]}
        mock_client = MagicMock()
        mock_client.search.return_value = raw
        with patch("tavily.TavilyClient", return_value=mock_client):
            with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
                service = WebSearchService(provider="tavily")
                results = await service.search("test query")
        assert results == [{"title": "T", "url": "U", "snippet": "S"}]

    @pytest.mark.asyncio
    async def test_tavily_missing_api_key_raises_runtime_error(self):
        os.environ.pop("TAVILY_API_KEY", None)
        service = WebSearchService(provider="tavily")
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
            await service.search("test query")

    @pytest.mark.asyncio
    async def test_tavily_network_error_propagates(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("tavily down")
        with patch("tavily.TavilyClient", return_value=mock_client):
            with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}):
                service = WebSearchService(provider="tavily")
                with pytest.raises(Exception, match="tavily down"):
                    await service.search("test query")


class TestWebSearchServiceValidation:
    @pytest.mark.asyncio
    async def test_empty_query_raises_value_error(self):
        service = WebSearchService(provider="duckduckgo")
        with pytest.raises(ValueError, match="empty"):
            await service.search("")

    @pytest.mark.asyncio
    async def test_whitespace_query_raises_value_error(self):
        service = WebSearchService(provider="duckduckgo")
        with pytest.raises(ValueError, match="empty"):
            await service.search("   ")

    @pytest.mark.asyncio
    async def test_query_over_500_chars_raises_value_error(self):
        service = WebSearchService(provider="duckduckgo")
        with pytest.raises(ValueError, match="500"):
            await service.search("x" * 501)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown search provider"):
            WebSearchService(provider="invalid")
