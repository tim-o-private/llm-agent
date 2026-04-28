"""Unified Google OAuth credential management.

Single service for all Google integrations (Gmail, Calendar, Drive, etc.).
Handles token fetch, expiry detection, refresh, vault persist, and
ReauthRequiredError on irrecoverable failures.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials

from ..exceptions import ReauthRequiredError

logger = logging.getLogger(__name__)

EXPIRY_BUFFER = timedelta(minutes=5)


class GoogleCredentialService:
    """Fetch, refresh, and persist Google OAuth credentials."""

    async def get_credentials(
        self,
        user_id: str,
        service_name: str,
        connection_id: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ) -> Credentials:
        """Return valid Google credentials, refreshing if needed.

        Args:
            user_id: Clarity user ID.
            service_name: 'gmail' or 'google_calendar'.
            connection_id: Specific connection UUID (multi-account).
            scopes: OAuth scopes for the Credentials object.

        Raises:
            ReauthRequiredError: Token is dead and user must reconnect.
            ValueError: No connection found for user/service.
        """
        token_data = await self._fetch_token_data(user_id, service_name, connection_id)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        account_email = token_data.get("service_user_email")
        cid = token_data.get("connection_id") or connection_id

        if not access_token:
            raise ReauthRequiredError(
                service_name,
                f"No access token for {account_email or service_name}. "
                "Please reconnect in Settings > Integrations.",
            )

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "Google OAuth configuration missing (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)"
            )

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )

        if self._needs_refresh(credentials, token_data):
            if not refresh_token:
                raise ReauthRequiredError(
                    service_name,
                    f"Token expired for {account_email or service_name} and no refresh token available. "
                    "Please reconnect in Settings > Integrations.",
                )
            await self._refresh(credentials, user_id, service_name, cid, account_email)

        return credentials

    async def get_all_credentials(
        self,
        user_id: str,
        service_name: str,
        scopes: Optional[list[str]] = None,
    ) -> list[tuple[Credentials, dict]]:
        """Return credentials for ALL connections of a service.

        Returns list of (Credentials, token_data) tuples. Skips connections
        that fail to refresh (logs warning) so one bad account doesn't
        block the others.
        """
        all_token_data = await self._fetch_all_token_data(user_id, service_name)
        results = []
        for token_data in all_token_data:
            try:
                cid = token_data.get("connection_id")
                creds = await self.get_credentials(
                    user_id, service_name, connection_id=cid, scopes=scopes,
                )
                results.append((creds, token_data))
            except (ReauthRequiredError, ValueError) as exc:
                email = token_data.get("service_user_email", "unknown")
                logger.warning("Skipping %s account %s: %s", service_name, email, exc)
        return results

    # -- Token fetch ----------------------------------------------------------

    async def _fetch_token_data(
        self, user_id: str, service_name: str, connection_id: Optional[str],
    ) -> dict:
        from ..database.supabase_client import create_system_client

        client = await create_system_client()
        params = {"p_user_id": user_id, "p_service_name": service_name}
        if connection_id:
            params["p_connection_id"] = connection_id

        result = await client.rpc("get_oauth_tokens_for_scheduler", params).execute()

        if not result.data:
            raise ValueError(
                f"No {service_name} connection found for user {user_id}. "
                "Please connect in Settings > Integrations."
            )

        data = result.data
        if isinstance(data, list):
            if connection_id:
                for item in data:
                    if str(item.get("connection_id")) == str(connection_id):
                        return item
                return data[0]
            return data[0]
        return data

    async def _fetch_all_token_data(
        self, user_id: str, service_name: str,
    ) -> list[dict]:
        from ..database.supabase_client import create_system_client

        client = await create_system_client()
        result = await client.rpc("get_oauth_tokens_for_scheduler", {
            "p_user_id": user_id,
            "p_service_name": service_name,
        }).execute()

        if not result.data:
            return []

        data = result.data
        if isinstance(data, list):
            return data
        return [data]

    # -- Expiry detection -----------------------------------------------------

    def _needs_refresh(self, credentials: Credentials, token_data: dict) -> bool:
        expires_at_str = token_data.get("expires_at")
        if expires_at_str:
            try:
                if isinstance(expires_at_str, str):
                    expires_at = datetime.fromisoformat(
                        expires_at_str.replace("Z", "+00:00")
                    )
                else:
                    expires_at = expires_at_str
                if datetime.now(timezone.utc) + EXPIRY_BUFFER > expires_at:
                    return True
            except (ValueError, TypeError):
                pass

        if credentials.expired:
            return True

        return False

    # -- Refresh + persist ----------------------------------------------------

    async def _refresh(
        self,
        credentials: Credentials,
        user_id: str,
        service_name: str,
        connection_id: Optional[str],
        account_email: Optional[str],
    ) -> None:
        label = account_email or service_name
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: credentials.refresh(GoogleAuthRequest())
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if "invalid_grant" in error_msg:
                raise ReauthRequiredError(
                    service_name,
                    f"Refresh token revoked for {label}. "
                    "Please reconnect in Settings > Integrations.",
                ) from exc
            if "unauthorized" in error_msg:
                raise ReauthRequiredError(
                    service_name,
                    f"Authentication failed for {label}. "
                    "Please reconnect in Settings > Integrations.",
                ) from exc
            raise ReauthRequiredError(
                service_name,
                f"Token refresh failed for {label}: {exc}. "
                "Please reconnect in Settings > Integrations.",
            ) from exc

        if not credentials.token:
            raise ReauthRequiredError(
                service_name,
                f"Token refresh returned no access token for {label}. "
                "Please reconnect in Settings > Integrations.",
            )

        if connection_id:
            await self._persist_refreshed_token(
                connection_id, credentials.token, credentials.expiry,
            )

        logger.info("Refreshed %s token for %s", service_name, label)

    async def _persist_refreshed_token(
        self,
        connection_id: str,
        new_token: str,
        new_expiry: Optional[datetime],
    ) -> None:
        try:
            from ..database.supabase_client import create_system_client

            client = await create_system_client()

            conn = await client.table("external_api_connections").select(
                "user_id, service_name, service_user_id"
            ).eq("id", connection_id).execute()

            if not conn.data or not conn.data[0]:
                logger.error("Connection %s not found for token persist", connection_id)
                return

            row = conn.data[0]
            service_user_id = row.get("service_user_id") or "default"
            secret_name = f"{row['user_id']}_{row['service_name']}_{service_user_id}_access"

            await client.rpc("store_secret", {
                "p_secret": new_token,
                "p_name": secret_name,
                "p_description": f"Access token for {row['service_name']}",
            }).execute()

            update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
            if new_expiry:
                if isinstance(new_expiry, datetime):
                    update_data["token_expires_at"] = new_expiry.isoformat()
                else:
                    update_data["token_expires_at"] = str(new_expiry)

            await client.table("external_api_connections").update(
                update_data
            ).eq("id", connection_id).execute()

        except Exception as exc:
            logger.error("Failed to persist refreshed token for %s: %s", connection_id, exc)


_service: Optional[GoogleCredentialService] = None


def get_google_credential_service() -> GoogleCredentialService:
    global _service
    if _service is None:
        _service = GoogleCredentialService()
    return _service
