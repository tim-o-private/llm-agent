"""Unit tests for SearchWebTool."""

from unittest.mock import AsyncMock, patch

import pytest

from chatServer.tools.web_search_tool import SearchWebTool


@pytest.fixture
def tool():
    return SearchWebTool(user_id="user-123")


class TestSearchWebToolArun:
    @pytest.mark.asyncio
    async def test_arun_happy_path_returns_formatted_output(self, tool):
        results = [
            {"title": "First Result", "url": "https://example.com/1", "snippet": "A great snippet"},
            {"title": "Second Result", "url": "https://example.com/2", "snippet": "Another snippet"},
        ]
        with patch("chatServer.tools.web_search_tool.WebSearchService") as mock_svc_cls:
            mock_svc_cls.return_value.search = AsyncMock(return_value=results)
            output = await tool._arun(query="test query")

        assert "1." in output
        assert "2." in output
        assert "First Result" in output
        assert "https://example.com/1" in output
        assert "A great snippet" in output
        assert "Second Result" in output

    @pytest.mark.asyncio
    async def test_arun_no_results_returns_message(self, tool):
        with patch("chatServer.tools.web_search_tool.WebSearchService") as mock_svc_cls:
            mock_svc_cls.return_value.search = AsyncMock(return_value=[])
            output = await tool._arun(query="obscure query")

        assert "No results found" in output

    @pytest.mark.asyncio
    async def test_arun_network_error_returns_friendly_message(self, tool):
        with patch("chatServer.tools.web_search_tool.WebSearchService") as mock_svc_cls:
            mock_svc_cls.return_value.search = AsyncMock(side_effect=Exception("connection refused"))
            output = await tool._arun(query="test query")

        assert "temporarily unavailable" in output

    @pytest.mark.asyncio
    async def test_arun_value_error_returns_invalid_query(self, tool):
        with patch("chatServer.tools.web_search_tool.WebSearchService") as mock_svc_cls:
            mock_svc_cls.return_value.search = AsyncMock(side_effect=ValueError("query too long"))
            output = await tool._arun(query="x" * 501)

        assert "Invalid search query" in output


class TestSearchWebToolPromptSection:
    def test_prompt_section_returns_guidance(self):
        result = SearchWebTool.prompt_section("web")
        assert result is not None
        assert "search_web" in result

    def test_prompt_section_same_for_all_channels(self):
        web = SearchWebTool.prompt_section("web")
        telegram = SearchWebTool.prompt_section("telegram")
        scheduled = SearchWebTool.prompt_section("scheduled")
        assert web == telegram == scheduled
