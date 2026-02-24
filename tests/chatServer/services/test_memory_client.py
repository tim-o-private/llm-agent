"""Tests for MemoryClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from chatServer.services.memory_client import MemoryClient


@pytest.fixture
def client():
    return MemoryClient(
        base_url="https://memory.example.com",
        backend_key="test-backend-key",
        user_id="user-123",
    )


def _mock_http(response):
    """Create a mock httpx.AsyncClient context manager."""
    mock = AsyncMock()
    mock.post.return_value = response
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


def _ok_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


class TestCallTool:
    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, client):
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_http(_ok_response({"id": "mem-1"}))

            await client.call_tool("store_memory", {"text": "hello", "scope": "global"})

            mock_http = mock_cls.return_value
            payload = mock_http.post.call_args.kwargs["json"]
            assert payload == {"tool_name": "store_memory", "arguments": {"text": "hello", "scope": "global"}}

    @pytest.mark.asyncio
    async def test_sends_correct_headers(self, client):
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_http(_ok_response({}))

            await client.call_tool("search", {"query": "test"})

            mock_http = mock_cls.return_value
            headers = mock_http.post.call_args.kwargs["headers"]
            assert headers["X-Backend-Key"] == "test-backend-key"
            assert headers["X-User-Id"] == "user-123"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_posts_to_api_tools_call_endpoint(self, client):
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_http(_ok_response({}))

            await client.call_tool("search", {"query": "test"})

            url = mock_cls.return_value.post.call_args.args[0]
            assert url == "https://memory.example.com/api/tools/call"

    @pytest.mark.asyncio
    async def test_returns_json_response_directly(self, client):
        data = {"memories": [{"id": "mem-1", "text": "hello"}]}
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_http(_ok_response(data))
            result = await client.call_tool("search", {"query": "test"})
            assert result == data

    @pytest.mark.asyncio
    async def test_returns_list_response(self, client):
        data = [{"id": "mem-1"}, {"id": "mem-2"}]
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_http(_ok_response(data))
            result = await client.call_tool("list_entities", {})
            assert result == data

    @pytest.mark.asyncio
    async def test_connection_error_raises_runtime_error(self, client):
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.side_effect = httpx.ConnectError("Connection refused")
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="Memory server unavailable"):
                await client.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_http_error_raises_runtime_error(self, client):
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            resp = MagicMock()
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=MagicMock(status_code=500),
            )
            mock_http.post.return_value = resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="Memory server unavailable"):
                await client.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_base_url(self):
        c = MemoryClient(base_url="https://memory.example.com/", backend_key="k", user_id="u")
        assert c.base_url == "https://memory.example.com"
