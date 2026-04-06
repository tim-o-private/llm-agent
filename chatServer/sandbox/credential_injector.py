"""CredentialInjector — injects OAuth tokens as subprocess env vars."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Mapping of provider name → env-var prefix for tokens.
_PROVIDER_ENV_MAP: dict[str, str] = {
    "google": "GOOGLE",
    "gmail": "GOOGLE",
    "google_calendar": "GOOGLE_CALENDAR",
}


class CredentialInjector:
    """Reads OAuth tokens from ``external_api_connections`` and produces
    a dict of environment variables suitable for passing to
    :pymethod:`BwrapSandbox.execute`.

    Tokens never touch the filesystem — they exist only in the subprocess
    environment for the duration of the command.
    """

    def __init__(self, db_client: Any) -> None:
        self._db = db_client

    async def get_env_for_tool(
        self,
        user_id: str,
        provider: str,
    ) -> dict[str, str]:
        """Return env-var dict with tokens for *provider*.

        Returns an empty dict when no connection is found — the caller
        decides whether that's an error.
        """
        try:
            result = (
                await self._db.table("external_api_connections")
                .select("access_token, refresh_token")
                .eq("user_id", user_id)
                .eq("provider", provider)
                .eq("status", "active")
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning("Failed to query credentials for %s/%s", user_id, provider, exc_info=True)
            return {}

        if not result.data:
            return {}

        row = result.data[0]
        prefix = _PROVIDER_ENV_MAP.get(provider, provider.upper())
        env: dict[str, str] = {}

        if row.get("access_token"):
            env[f"{prefix}_ACCESS_TOKEN"] = row["access_token"]
        if row.get("refresh_token"):
            env[f"{prefix}_REFRESH_TOKEN"] = row["refresh_token"]

        return env
