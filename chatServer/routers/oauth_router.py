"""Router for standalone Google OAuth flow (multi-Gmail account support)."""

import logging
import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse

from ..dependencies.auth import get_current_user
from ..services.oauth_service import OAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])


def _get_oauth_service() -> OAuthService:
    """Create OAuthService with a service-role Supabase client.

    TODO: SPEC-017 — OAuthService uses sync Supabase client for Google OAuth
    callback handling (no auth context). Migrate when sync SystemClient is available.
    """
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase configuration missing",
        )

    client = create_client(supabase_url, supabase_key)
    return OAuthService(client)


@router.get("/gmail/connect")
async def initiate_gmail_connect(
    user_id: str = Depends(get_current_user),
    oauth_service: OAuthService = Depends(_get_oauth_service),
):
    """Initiate OAuth flow for connecting an additional Gmail account.

    Returns the Google OAuth consent URL as JSON. The frontend fetches this
    with an Authorization header, then navigates the browser to the URL.
    """
    try:
        auth_url = await oauth_service.create_gmail_auth_url(user_id)
        return JSONResponse(content={"auth_url": auth_url})
    except RuntimeError as e:
        logger.error(f"Failed to initiate Gmail OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/gmail/callback")
async def gmail_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    oauth_service: OAuthService = Depends(_get_oauth_service),
):
    """Handle OAuth callback from Google.

    Validates state, exchanges code for tokens, stores tokens, and redirects
    to the frontend with success/error status.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    result = await oauth_service.handle_gmail_callback(code, state)

    if result.status == "success":
        redirect_url = (
            f"{frontend_url}/auth/callback"
            f"?service=gmail&source=standalone&status=success"
        )
    else:
        error_msg = quote(result.error_message or "Unknown error")
        redirect_url = (
            f"{frontend_url}/auth/callback"
            f"?service=gmail&source=standalone&status=error"
            f"&error_message={error_msg}"
        )

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
