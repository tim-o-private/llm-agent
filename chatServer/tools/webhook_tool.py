"""Generic webhook tool for making HTTP requests."""

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from .registry import register_tool_type

logger = logging.getLogger(__name__)


class WebhookToolInput(BaseModel):
    """Input schema for WebhookTool -- accepts arbitrary payload fields."""

    model_config = ConfigDict(extra="allow")

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Payload data to send with the webhook request.",
    )


@register_tool_type("WebhookTool")
class WebhookTool(BaseTool):
    """Make HTTP requests to configured endpoints."""

    name: str = "webhook"
    description: str = (
        "Make an HTTP request to a configured endpoint. "
        "The URL, method, headers, and timeout are set in the tool configuration."
    )
    args_schema: Type[BaseModel] = WebhookToolInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def __init__(self, config: dict | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._config = config or {}
        # Support individual config keys from kwargs (loader compatibility)
        for key in ("url", "method", "headers", "payload_schema", "timeout"):
            if key in kwargs and key not in self._config:
                self._config[key] = kwargs[key]

    @property
    def url(self) -> str:
        return self._config.get("url", "")

    @property
    def method(self) -> str:
        return self._config.get("method", "GET").upper()

    @property
    def headers(self) -> dict[str, str]:
        return self._config.get("headers", {}) or {}

    @property
    def payload_schema(self) -> Optional[dict]:
        return self._config.get("payload_schema")

    @property
    def timeout(self) -> float:
        return self._config.get("timeout", 30)

    def _run(self, payload: dict[str, Any] | None = None) -> str:
        return "WebhookTool requires async execution. Use _arun."

    async def _arun(self, payload: dict[str, Any] | None = None) -> str:
        try:
            # Validate payload against schema if provided
            if self.payload_schema and payload is not None:
                validation_error = self._validate_payload(payload, self.payload_schema)
                if validation_error:
                    return validation_error

            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.method == "GET":
                    response = await client.get(
                        self.url, headers=self.headers, params=payload or None
                    )
                elif self.method in ("POST", "PUT", "PATCH"):
                    response = await client.request(
                        self.method,
                        self.url,
                        headers=self.headers,
                        json=payload or None,
                    )
                elif self.method == "DELETE":
                    response = await client.delete(
                        self.url, headers=self.headers, params=payload or None
                    )
                else:
                    return f"Unsupported HTTP method: {self.method}"

                # Try to return JSON, fallback to text
                try:
                    return str(response.json())
                except Exception:
                    return response.text

        except httpx.TimeoutException as e:
            logger.error("Webhook timeout to %s: %s", self.url, e)
            return f"Webhook request timed out after {self.timeout}s: {e}"
        except httpx.HTTPStatusError as e:
            logger.error("Webhook HTTP error to %s: %s", self.url, e)
            return f"Webhook HTTP error: {e}"
        except httpx.RequestError as e:
            logger.error("Webhook request error to %s: %s", self.url, e)
            return f"Webhook request failed: {e}"
        except Exception as e:
            logger.error("Webhook unexpected error to %s: %s", self.url, e)
            return f"Webhook unexpected error: {e}"

    def _validate_payload(self, payload: dict, schema: dict) -> Optional[str]:
        """Basic type checking against a simple payload schema.

        Schema format: {"field_name": {"type": "str", "required": True}}
        """
        for field_name, field_rules in schema.items():
            if not isinstance(field_rules, dict):
                continue
            required = field_rules.get("required", False)
            expected_type = field_rules.get("type", "any")
            if required and field_name not in payload:
                return f"Missing required field: {field_name}"
            if field_name in payload and expected_type != "any":
                value = payload[field_name]
                type_map = {
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                }
                expected_python_type = type_map.get(expected_type)
                if expected_python_type and not isinstance(value, expected_python_type):
                    return (
                        f"Field '{field_name}' must be of type {expected_type}, "
                        f"got {type(value).__name__}"
                    )
        return None
