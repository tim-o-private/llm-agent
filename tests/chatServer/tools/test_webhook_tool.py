"""Tests for WebhookTool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from chatServer.tools.webhook_tool import WebhookTool


def _mock_httpx_client(response=None, side_effect=None):
    """Build a mock httpx.AsyncClient that acts as an async context manager."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=response, side_effect=side_effect)
    mock_client.request = AsyncMock(return_value=response, side_effect=side_effect)
    mock_client.delete = AsyncMock(return_value=response, side_effect=side_effect)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestWebhookToolInit:
    """Tests for WebhookTool construction and properties."""

    def test_webhook_tool_init_with_config(self):
        """Constructor accepts and stores config."""
        config = {"url": "https://example.com/webhook", "method": "POST"}
        tool = WebhookTool(config=config, user_id="user-1")
        assert tool._config == config

    def test_webhook_tool_get_properties(self):
        """url, method, headers, timeout, payload_schema read from config."""
        config = {
            "url": "https://example.com/webhook",
            "method": "post",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 10,
            "payload_schema": {"field": {"type": "str", "required": True}},
        }
        tool = WebhookTool(config=config, user_id="user-1")
        assert tool.url == "https://example.com/webhook"
        assert tool.method == "POST"
        assert tool.headers == {"Authorization": "Bearer token"}
        assert tool.timeout == 10
        assert tool.payload_schema == {"field": {"type": "str", "required": True}}


class TestWebhookToolArun:
    """Tests for WebhookTool._arun async execution."""

    async def test_webhook_tool_arun_get(self):
        """Mock GET request and verify response text is returned."""
        tool = WebhookTool(
            config={"url": "https://example.com/api", "method": "GET"},
            user_id="user-1",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_client = _mock_httpx_client(response=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool._arun(payload={"key": "value"})

        assert result == str({"status": "ok"})
        mock_client.get.assert_awaited_once_with(
            "https://example.com/api",
            headers={},
            params={"key": "value"},
        )

    async def test_webhook_tool_arun_post_json(self):
        """Mock POST request with JSON payload."""
        tool = WebhookTool(
            config={"url": "https://example.com/api", "method": "POST"},
            user_id="user-1",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123"}
        mock_client = _mock_httpx_client(response=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool._arun(payload={"name": "test"})

        assert result == str({"id": "123"})
        mock_client.request.assert_awaited_once_with(
            "POST",
            "https://example.com/api",
            headers={},
            json={"name": "test"},
        )

    async def test_webhook_tool_arun_timeout(self):
        """Mock TimeoutException and verify error message returned."""
        tool = WebhookTool(
            config={"url": "https://example.com/api", "method": "GET", "timeout": 5},
            user_id="user-1",
        )
        mock_client = _mock_httpx_client(side_effect=httpx.TimeoutException("Request timed out"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool._arun()

        assert "timed out" in result
        assert "5s" in result

    async def test_webhook_tool_arun_http_error(self):
        """Mock HTTPStatusError and verify error message returned."""
        tool = WebhookTool(
            config={"url": "https://example.com/api", "method": "GET"},
            user_id="user-1",
        )
        error = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(),
        )
        mock_client = _mock_httpx_client(side_effect=error)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await tool._arun()

        assert "HTTP error" in result

    async def test_webhook_tool_payload_validation(self):
        """Provide payload_schema and verify validation errors for invalid payloads."""
        config = {
            "url": "https://example.com/api",
            "method": "POST",
            "payload_schema": {
                "name": {"type": "str", "required": True},
                "count": {"type": "int", "required": True},
            },
        }
        tool = WebhookTool(config=config, user_id="user-1")

        # Missing required field
        result = await tool._arun(payload={"name": "test"})
        assert "Missing required field: count" in result

        # Wrong type
        result = await tool._arun(payload={"name": "test", "count": "not_an_int"})
        assert "Field 'count' must be of type int" in result
