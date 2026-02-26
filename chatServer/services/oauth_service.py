"""OAuth service for Gmail account connections and token storage."""

import base64
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from ..config.settings import get_settings

logger = logging.getLogger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


@dataclass
class OAuthResult:
    """Result of an OAuth callback."""

    status: str  # "success" or "error"
    error_message: Optional[str] = None
    connection_id: Optional[str] = None
    email: Optional[str] = None


def _encode_state(user_id: str, nonce: str) -> str:
    """Encode user_id and nonce into a base64url state parameter."""
    payload = json.dumps({"user_id": user_id, "nonce": nonce})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_state(state: str) -> dict:
    """Decode a base64url state parameter."""
    try:
        payload = base64.urlsafe_b64decode(state.encode()).decode()
        return json.loads(payload)
    except Exception:
        raise ValueError("Invalid OAuth state parameter")


class OAuthService:
    """Service for managing standalone Google OAuth flows."""

    def __init__(self, supabase_client):
        """Initialize with a Supabase service-role client."""
        self.supabase = supabase_client
        self.settings = get_settings()

    async def create_gmail_auth_url(self, user_id: str) -> str:
        """Generate Google OAuth URL with state parameter for CSRF protection.

        Args:
            user_id: The authenticated user's ID.

        Returns:
            Google OAuth authorization URL.
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        if not client_id:
            raise RuntimeError("GOOGLE_CLIENT_ID not configured")
        if not redirect_uri:
            raise RuntimeError("GOOGLE_REDIRECT_URI not configured")

        # Generate CSRF nonce
        nonce = secrets.token_urlsafe(32)

        # Store nonce in oauth_states table (service role bypasses RLS)
        self.supabase.table("oauth_states").insert({
            "nonce": nonce,
            "user_id": user_id,
        }).execute()

        # Build state parameter
        state = _encode_state(user_id, nonce)

        # Build Google OAuth URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "select_account consent",
            "state": state,
            "include_granted_scopes": "false",
        }

        from urllib.parse import urlencode

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        logger.info(f"Generated OAuth URL for user {user_id}")
        return auth_url

    async def handle_gmail_callback(self, code: str, state: str) -> OAuthResult:
        """Handle OAuth callback: validate state, exchange code, store tokens.

        Args:
            code: Authorization code from Google.
            state: State parameter for CSRF validation.

        Returns:
            OAuthResult with success/error status.
        """
        try:
            # 1. Decode and validate state
            state_payload = _decode_state(state)
            nonce = state_payload.get("nonce")
            user_id = state_payload.get("user_id")

            if not nonce or not user_id:
                return OAuthResult(status="error", error_message="Invalid state parameter")

            # 2. Validate nonce exists and is not expired
            result = self.supabase.table("oauth_states").select("*").eq(
                "nonce", nonce
            ).execute()

            if not result.data:
                return OAuthResult(status="error", error_message="Invalid or expired OAuth state. Please try again.")

            oauth_state = result.data[0]

            # Check expiry
            expires_at = datetime.fromisoformat(oauth_state["expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_at:
                # Clean up expired nonce
                self.supabase.table("oauth_states").delete().eq("nonce", nonce).execute()
                return OAuthResult(status="error", error_message="Authentication timed out. Please try again.")

            # Verify user_id matches
            if oauth_state["user_id"] != user_id:
                return OAuthResult(status="error", error_message="State mismatch")

            # 3. Delete nonce (single-use)
            self.supabase.table("oauth_states").delete().eq("nonce", nonce).execute()

            # 4. Exchange code for tokens
            token_data = await self._exchange_code_for_tokens(code)

            # 5. Get user info from Google
            google_user = await self._get_google_userinfo(token_data["access_token"])
            google_sub = google_user.get("sub")
            google_email = google_user.get("email")

            if not google_sub or not google_email:
                return OAuthResult(status="error", error_message="Failed to get Google account info")

            # 6. Check max-5 limit
            existing = self.supabase.table("external_api_connections").select("id").eq(
                "user_id", user_id
            ).eq("service_name", "gmail").eq("is_active", True).execute()

            if len(existing.data) >= 5:
                return OAuthResult(
                    status="error",
                    error_message="Maximum of 5 Gmail accounts reached. Please disconnect one first."
                )

            # 7. Check for duplicate
            duplicate = self.supabase.table("external_api_connections").select("id").eq(
                "user_id", user_id
            ).eq("service_name", "gmail").eq("service_user_id", google_sub).execute()

            if duplicate.data:
                return OAuthResult(
                    status="error",
                    error_message=f"Gmail account {google_email} is already connected."
                )

            # 8. Store tokens via RPC
            expires_at_str = None
            if token_data.get("expires_in"):
                from datetime import timedelta

                expires_at_dt = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
                expires_at_str = expires_at_dt.isoformat()

            store_result = self.supabase.rpc("store_oauth_tokens", {
                "p_user_id": user_id,
                "p_service_name": "gmail",
                "p_access_token": token_data["access_token"],
                "p_refresh_token": token_data.get("refresh_token"),
                "p_expires_at": expires_at_str,
                "p_scopes": GMAIL_SCOPES,
                "p_service_user_id": google_sub,
                "p_service_user_email": google_email,
            }).execute()

            if not store_result.data or not store_result.data.get("success"):
                error = store_result.data.get("error", "Unknown error") if store_result.data else "No response"
                return OAuthResult(status="error", error_message=f"Failed to store tokens: {error}")

            connection_id = store_result.data.get("connection_id")

            logger.info(f"Successfully connected Gmail account {google_email} for user {user_id}")

            # Enqueue email onboarding job
            self._enqueue_email_onboarding(user_id, str(connection_id))

            return OAuthResult(
                status="success",
                connection_id=str(connection_id),
                email=google_email,
            )

        except ValueError as e:
            logger.warning(f"OAuth callback validation error: {e}")
            return OAuthResult(status="error", error_message=str(e))
        except Exception as e:
            logger.error(f"OAuth callback failed: {e}", exc_info=True)
            return OAuthResult(status="error", error_message="Authentication failed. Please try again.")

    def _enqueue_email_onboarding(self, user_id: str, connection_id: str) -> None:
        """Insert an email_processing job so the job runner onboards this account."""
        try:
            self.supabase.table("jobs").insert({
                "user_id": user_id,
                "job_type": "email_processing",
                "input": {"connection_id": connection_id},
            }).execute()
            logger.info(f"Enqueued email_processing job for connection {connection_id}")
        except Exception as e:
            # Non-fatal — the account is connected, onboarding can be retried
            logger.error(f"Failed to enqueue email onboarding job: {e}")

    async def store_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        service_user_id: Optional[str] = None,
        service_user_email: Optional[str] = None,
    ) -> dict:
        """Store Gmail tokens via Vault RPC and enqueue onboarding job.

        Used by the first-account OAuth flow (Supabase provider auth).
        The RPC handles Vault encryption and connection upsert.
        """
        store_result = self.supabase.rpc("store_oauth_tokens", {
            "p_user_id": user_id,
            "p_service_name": "gmail",
            "p_access_token": access_token,
            "p_refresh_token": refresh_token,
            "p_expires_at": expires_at,
            "p_scopes": scopes or [],
            "p_service_user_id": service_user_id,
            "p_service_user_email": service_user_email,
        }).execute()

        result = store_result.data
        if not result or not result.get("success"):
            error = result.get("error", "Unknown error") if result else "No response"
            raise RuntimeError(f"Failed to store tokens: {error}")

        connection_id = result.get("connection_id")
        self._enqueue_email_onboarding(user_id, str(connection_id))

        return result

    async def _exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for tokens via Google's token endpoint."""
        import aiohttp

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"Token exchange failed ({resp.status}): {body}")
                return await resp.json()

    async def _get_google_userinfo(self, access_token: str) -> dict:
        """Get Google user info (sub, email) using the access token."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to get Google user info ({resp.status})")
                return await resp.json()
