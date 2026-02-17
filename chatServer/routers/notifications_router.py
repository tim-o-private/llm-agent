"""
Notifications router.

Provides API endpoints for:
- Listing notifications (with unread filter)
- Getting unread count (for polling)
- Marking notifications as read
- Marking all as read
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from ..database.supabase_client import get_supabase_client
    from ..dependencies.auth import get_current_user
    from ..services.notification_service import NotificationService
except ImportError:
    from database.supabase_client import get_supabase_client
    from dependencies.auth import get_current_user
    from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# =============================================================================
# Response Models
# =============================================================================


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    category: str
    metadata: Dict[str, Any] = {}
    read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    count: int


class MarkReadResponse(BaseModel):
    success: bool


class MarkAllReadResponse(BaseModel):
    success: bool
    count: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """List notifications for the current user."""
    service = NotificationService(db)
    notifications = await service.get_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=min(limit, 100),  # Cap at 100
        offset=offset,
    )
    return notifications


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Get count of unread notifications. Used for polling."""
    service = NotificationService(db)
    count = await service.get_unread_count(user_id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    success = await service.mark_read(user_id, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or could not be updated")
    return MarkReadResponse(success=True)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Mark all notifications as read for the current user."""
    service = NotificationService(db)
    count = await service.mark_all_read(user_id)
    return MarkAllReadResponse(success=True, count=count)
