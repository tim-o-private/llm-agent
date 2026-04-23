"""Chat-related Pydantic models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    agent_name: str
    message: str
    session_id: str  # Added: session_id is now required
    scope: Optional[dict] = None  # SPEC-049: ChatScope serialized as dict


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
