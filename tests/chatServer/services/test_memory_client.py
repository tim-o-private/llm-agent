"""Tests for MemoryClient."""

import json
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


class TestCallTool:
    @pytest.mark.asyncio
    async def test_sends_correct_jsonrpc_payload(self, client):
        """Verify JSON-RPC payload structure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"content": [{"type": "text", "text": '{"id": "mem-1"}'}]}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            await client.call_tool("store_memory", {"text": "hello", "scope": "global"})

            mock_http.post.assert_called_once()
            call_kwargs = mock_http.post.call_args
            payload = call_kwargs.kwargs["json"]
            assert payload["jsonrpc"] == "2.0"
            assert payload["method"] == "tools/call"
            assert payload["params"]["name"] == "store_memory"
            assert payload["params"]["arguments"] == {"text": "hello", "scope": "global"}

    @pytest.mark.asyncio
    async def test_sends_correct_headers(self, client):
        """Verify auth headers are sent."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"content": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            await client.call_tool("search", {"query": "test"})

            call_kwargs = mock_http.post.call_args
            headers = call_kwargs.kwargs["headers"]
            assert headers["X-Backend-Key"] == "test-backend-key"
            assert headers["X-User-Id"] == "user-123"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_posts_to_correct_url(self, client):
        """Verify URL construction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"content": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            await client.call_tool("search", {"query": "test"})

            url = mock_http.post.call_args.args[0]
            assert url == "https://memory.example.com/mcp"

    @pytest.mark.asyncio
    async def test_parses_json_text_response(self, client):
        """Verify JSON parsing from MCP text content."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"content": [{"type": "text", "text": '{"memories": [{"id": 1}]}'}]}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.call_tool("search", {"query": "test"})
            assert result == {"memories": [{"id": 1}]}

    @pytest.mark.asyncio
    async def test_returns_plain_text_as_dict(self, client):
        """Non-JSON text content wrapped in {text: ...}."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {"content": [{"type": "text", "text": "Memory stored successfully"}]}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.call_tool("store_memory", {"text": "hi"})
            assert result == {"text": "Memory stored successfully"}

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty_dict(self, client):
        """Empty MCP content returns {}."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {"content": []}}
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.call_tool("search", {"query": "nothing"})
            assert result == {}

    @pytest.mark.asyncio
    async def test_connection_error_raises_runtime_error(self, client):
        """Network errors raise RuntimeError."""
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.side_effect = httpx.ConnectError("Connection refused")
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="Memory server unavailable"):
                await client.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_non_200_raises_runtime_error(self, client):
        """HTTP error status raises RuntimeError."""
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
            )
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="Memory server unavailable"):
                await client.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_malformed_json_response_raises_runtime_error(self, client):
        """Invalid JSON body raises RuntimeError."""
        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json.side_effect = json.JSONDecodeError("bad", "", 0)
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="invalid JSON"):
                await client.call_tool("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_mcp_error_response_raises_runtime_error(self, client):
        """MCP error in response body raises RuntimeError."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"code": -32600, "message": "Invalid request"}}
        mock_response.raise_for_status = MagicMock()

        with patch("chatServer.services.memory_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_response
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="Memory server error"):
                await client.call_tool("search", {"query": "test"})
