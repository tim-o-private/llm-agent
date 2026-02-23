"""Async HTTP client for min-memory MCP server."""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MemoryClient:
    """Client for min-memory server using MCP JSON-RPC over HTTP."""

    def __init__(self, base_url: str, backend_key: str, user_id: str):
        self.base_url = base_url.rstrip("/")
        self.backend_key = backend_key
        self.user_id = user_id

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | list:
        """Call a min-memory tool via MCP JSON-RPC.

        Returns parsed JSON from the tool's text response.
        Raises RuntimeError on communication or parsing errors.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Backend-Key": self.backend_key,
            "X-User-Id": self.user_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.base_url}/mcp", json=payload, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Memory server request failed: %s", e)
            raise RuntimeError(f"Memory server unavailable: {e}") from e

        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Memory server returned invalid JSON: {e}") from e

        if "error" in body:
            raise RuntimeError(f"Memory server error: {body['error']}")

        # MCP response: {"result": {"content": [{"type": "text", "text": "..."}]}}
        content = body.get("result", {}).get("content", [])
        if not content:
            return {}

        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            # Some tools return plain text, not JSON
            return {"text": text}
