"""
Chat history router.

Provides API endpoints for:
- Listing chat sessions (with optional channel filter)
- Fetching messages for a session (with cursor pagination)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

try:
    from ..database.supabase_client import get_supabase_client
    from ..dependencies.auth import get_current_user
    from ..services.chat_history_service import ChatHistoryService
except ImportError:
    from database.supabase_client import get_supabase_client
    from dependencies.auth import get_current_user
    from services.chat_history_service import ChatHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat-history"])


# =============================================================================
# Response Models
# =============================================================================


class SessionResponse(BaseModel):
    id: str
    user_id: str
    chat_id: Optional[str] = None
    agent_name: str
    channel: str
    session_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    session_id: str
    message: Dict[str, Any]
    created_at: datetime


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    channel: Optional[str] = Query(None, description="Filter by channel: web, telegram, scheduled"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """List chat sessions for the current user."""
    service = ChatHistoryService(db)
    sessions = await service.get_sessions(
        user_id=user_id,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None, description="Cursor: return messages before this ID"),
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Fetch messages for a specific session with cursor-based pagination."""
    service = ChatHistoryService(db)
    messages = await service.get_session_messages(
        session_id=session_id,
        user_id=user_id,
        limit=limit,
        before_id=before_id,
    )
    return messages
