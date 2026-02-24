"""Async HTTP client for min-memory server."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MemoryClient:
    """Client for min-memory server using direct REST API."""

    def __init__(self, base_url: str, backend_key: str, user_id: str):
        self.base_url = base_url.rstrip("/")
        self.backend_key = backend_key
        self.user_id = user_id

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | list:
        """Call a min-memory tool via the direct REST endpoint.

        Returns parsed JSON from the tool response.
        Raises RuntimeError on communication or server errors.
        """
        payload = {"tool_name": tool_name, "arguments": arguments}
        headers = {
            "Content-Type": "application/json",
            "X-Backend-Key": self.backend_key,
            "X-User-Id": self.user_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self.base_url}/api/tools/call", json=payload, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Memory server request failed: %s", e)
            raise RuntimeError(f"Memory server unavailable: {e}") from e

        return resp.json()
