"""
Telegram integration router.

Provides:
- Webhook endpoint for Telegram updates
- Account linking endpoints (generate token, check status, unlink)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

try:
    from ..channels.telegram_bot import get_telegram_bot_service
    from ..database.supabase_client import get_supabase_client
    from ..dependencies.auth import get_current_user
    from ..services.telegram_linking_service import (
        create_linking_token,
        get_telegram_status,
        unlink_telegram_account,
    )
except ImportError:
    from channels.telegram_bot import get_telegram_bot_service
    from database.supabase_client import get_supabase_client
    from dependencies.auth import get_current_user
    from services.telegram_linking_service import (
        create_linking_token,
        get_telegram_status,
        unlink_telegram_account,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


# =============================================================================
# Response Models
# =============================================================================


class LinkTokenResponse(BaseModel):
    token: str
    bot_username: str


class TelegramStatusResponse(BaseModel):
    linked: bool
    linked_at: str | None = None
    linked_session_id: str | None = None


class UnlinkResponse(BaseModel):
    success: bool


# =============================================================================
# Webhook Endpoint (called by Telegram)
# =============================================================================


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receive updates from Telegram.

    This endpoint is called by Telegram when users send messages
    or interact with inline keyboards. No auth required — Telegram
    validates via the webhook secret.
    """
    bot_service = get_telegram_bot_service()
    if not bot_service:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    data = await request.json()
    await bot_service.process_update(data)
    return {"ok": True}


# =============================================================================
# Linking Endpoints (called by frontend)
# =============================================================================


@router.get("/link-token", response_model=LinkTokenResponse)
async def get_link_token(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """
    Generate a one-time linking token.

    The user sends this token to the Telegram bot via /start <token>.
    Token expires after 10 minutes.
    """
    bot_service = get_telegram_bot_service()
    if not bot_service:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    token = await create_linking_token(db, user_id)

    # Get bot username for display
    try:
        bot_info = await bot_service.bot.get_me()
        bot_username = bot_info.username or "your_bot"
    except Exception:
        bot_username = "your_bot"

    return LinkTokenResponse(token=token, bot_username=bot_username)


@router.get("/status", response_model=TelegramStatusResponse)
async def get_status(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Check if user has Telegram linked."""
    status = await get_telegram_status(db, user_id)
    return TelegramStatusResponse(**status)


@router.post("/unlink", response_model=UnlinkResponse)
async def unlink(
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    """Unlink Telegram account."""
    success = await unlink_telegram_account(db, user_id)
    return UnlinkResponse(success=success)
