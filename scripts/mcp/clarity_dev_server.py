#!/usr/bin/env python3
"""
MCP Server for local Clarity dev access.

Provides chat_with_clarity tool so agents can send messages to the running
chatServer and verify tool integrations end-to-end without human relay.

Auth: signs in via Supabase email/password using CLARITY_DEV_USERNAME and
CLARITY_DEV_PASSWORD to get a real JWT for the test user. Falls back to
HS256 JWT minting if credentials aren't set.
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from dotenv import load_dotenv
from jose import jwt
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# Load .env so the server works standalone (not just when launched by Claude)
load_dotenv()

CHAT_API_URL = "http://localhost:3001/api/chat"
DEFAULT_AGENT_NAME = "clarity"

# Cached auth state (refreshed when expired)
_cached_token: Optional[str] = None
_cached_token_expiry: Optional[datetime] = None

mcp = FastMCP("clarity_dev_mcp")


def _sign_in_dev_user() -> str:
    """Sign in as the dev test user via Supabase GoTrue and return the access token."""
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    email = os.environ.get("CLARITY_DEV_USERNAME", "")
    password = os.environ.get("CLARITY_DEV_PASSWORD", "")

    if not all([supabase_url, anon_key, email, password]):
        raise RuntimeError(
            "SUPABASE_URL, SUPABASE_ANON_KEY, CLARITY_DEV_USERNAME, and "
            "CLARITY_DEV_PASSWORD must all be set in .env"
        )

    resp = httpx.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        timeout=10.0,
    )
    if resp.status_code != 200:
        detail = resp.text[:500]
        raise RuntimeError(f"Supabase sign-in failed ({resp.status_code}): {detail}")

    data = resp.json()
    return data["access_token"]


def _mint_dev_jwt() -> str:
    """Mint an HS256 JWT for the configured dev user (legacy fallback)."""
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    user_id = os.environ.get("CLARITY_DEV_USER_ID")

    if not secret:
        raise RuntimeError("SUPABASE_JWT_SECRET is not set in the environment")
    if not user_id:
        raise RuntimeError("CLARITY_DEV_USER_ID is not set in the environment")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _get_dev_token() -> str:
    """Get a dev JWT, preferring email/password auth, falling back to HS256 minting."""
    global _cached_token, _cached_token_expiry

    now = datetime.now(timezone.utc)
    if _cached_token and _cached_token_expiry and now < _cached_token_expiry:
        return _cached_token

    # Try email/password sign-in first
    if os.environ.get("CLARITY_DEV_USERNAME") and os.environ.get("CLARITY_DEV_PASSWORD"):
        token = _sign_in_dev_user()
        _cached_token = token
        _cached_token_expiry = now + timedelta(minutes=50)  # Supabase tokens last 1h
        return token

    # Fall back to HS256 minting
    return _mint_dev_jwt()


def _handle_error(e: Exception) -> str:
    """Return actionable error messages."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        try:
            detail = e.response.json().get("detail", e.response.text)
        except Exception:
            detail = e.response.text
        if status == 401:
            return (
                f"Error: Unauthorized (401). Check that SUPABASE_JWT_SECRET matches "
                f"the running server and CLARITY_DEV_USER_ID is a valid Supabase user UUID. "
                f"Detail: {detail}"
            )
        if status == 422:
            return f"Error: Validation error (422). Check agent_name and session_id. Detail: {detail}"
        return f"Error: HTTP {status}. Detail: {detail}"
    if isinstance(e, httpx.ConnectError):
        return (
            "Error: Could not connect to localhost:3001. "
            "Is the chatServer running? Start it with: pnpm dev:chatServer"
        )
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out after 30s. The server may be overloaded."
    if isinstance(e, RuntimeError):
        return f"Error: Configuration problem — {e}"
    return f"Error: {type(e).__name__}: {e}"


class ChatInput(BaseModel):
    """Input model for chat_with_clarity."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(
        ...,
        description="Message to send to the Clarity agent",
        min_length=1,
        max_length=4000,
    )
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Chat session UUID. If omitted, a new UUID is generated. "
            "Re-use the same session_id across calls to maintain conversation history."
        ),
    )
    agent_name: Optional[str] = Field(
        default=DEFAULT_AGENT_NAME,
        description="Agent name to target (default: 'clarity')",
        min_length=1,
        max_length=100,
    )


@mcp.tool(
    name="chat_with_clarity",
    annotations={
        "title": "Chat with Clarity (local dev)",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def chat_with_clarity(params: ChatInput) -> str:
    """Send a message to the locally running Clarity chatServer and return the agent's response.

    Use this to verify tool integrations end-to-end, check that agent responses match
    spec, or debug agent behaviour without human relay.

    Requires the chatServer to be running on localhost:3001.
    Authenticates as the dev test user via CLARITY_DEV_USERNAME/PASSWORD,
    falling back to HS256 JWT if credentials aren't configured.

    Args:
        params (ChatInput): Validated input containing:
            - message (str): The message to send (1-4000 chars)
            - session_id (Optional[str]): Session UUID for multi-turn conversations.
              Omit to start a fresh session.
            - agent_name (Optional[str]): Target agent (default: 'clarity')

    Returns:
        str: JSON with the agent response, e.g.:
            {
                "session_id": "...",
                "response": "Hello! How can I help?",
                "tool_name": null,
                "tool_input": null,
                "error": null
            }
        On failure, returns "Error: <actionable description>".

    Examples:
        - Verify a new feature: chat_with_clarity(message="list my tasks")
        - Multi-turn: use the same session_id across calls
        - Test tool integration: chat_with_clarity(message="search my emails for receipts")
    """
    try:
        token = _get_dev_token()
    except RuntimeError as e:
        return _handle_error(e)

    session_id = params.session_id or str(uuid.uuid4())

    payload = {
        "message": params.message,
        "session_id": session_id,
        "agent_name": params.agent_name or DEFAULT_AGENT_NAME,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                CHAT_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    mcp.run()
