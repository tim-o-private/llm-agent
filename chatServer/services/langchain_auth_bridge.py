"""Authentication bridge between Supabase Vault and LangChain Google services.

Thin wrapper over GoogleCredentialService. Kept for backward compatibility
with integration tests. New code should use GoogleCredentialService directly.
"""

import json
import logging
import os
import tempfile
from typing import List, Optional, Tuple

import psycopg
from google.oauth2.credentials import Credentials

from ..database.connection import get_db_connection
from .google_credential_service import get_google_credential_service

logger = logging.getLogger(__name__)


class VaultToLangChainCredentialAdapter:
    """Converts Vault OAuth tokens to LangChain-compatible credentials.

    Delegates to GoogleCredentialService for token fetch, refresh, and persist.
    Retains temp-file creation for LangChain's file-based credential system.
    """

    def __init__(self, db_connection: Optional[psycopg.AsyncConnection] = None):
        self.db_connection = db_connection
        self._temp_files = []

    async def _get_db_connection(self) -> psycopg.AsyncConnection:
        if self.db_connection:
            return self.db_connection
        async for db_conn in get_db_connection():
            return db_conn

    async def create_google_credentials(
        self,
        user_id: str,
        service_name: str = 'gmail',
        scopes: Optional[List[str]] = None
    ) -> Credentials:
        """Create Google OAuth2 credentials from existing Vault tokens.

        Delegates to GoogleCredentialService for the full lifecycle.
        """
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/gmail.readonly']

        service = get_google_credential_service()
        return await service.get_credentials(
            user_id=user_id,
            service_name=service_name,
            scopes=scopes,
        )

    async def fetch_or_refresh_gmail_credentials(self, user_id: str) -> Credentials:
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='gmail',
            scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        )

    async def fetch_or_refresh_calendar_credentials(self, user_id: str) -> Credentials:
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='google_calendar',
            scopes=['https://www.googleapis.com/auth/calendar.readonly'],
        )

    async def create_temp_credential_files(
        self,
        user_id: str,
        service_name: str = 'gmail',
        scopes: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """Create temporary credential files for LangChain (fallback method)."""
        try:
            credentials = await self.create_google_credentials(user_id, service_name, scopes)

            token_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(token_data, f, indent=2)
                token_file = f.name
                self._temp_files.append(token_file)

            client_secrets = {
                "installed": {
                    "client_id": credentials.client_id,
                    "client_secret": credentials.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(client_secrets, f, indent=2)
                secrets_file = f.name
                self._temp_files.append(secrets_file)

            return token_file, secrets_file

        except Exception as e:
            self.cleanup_temp_files()
            raise RuntimeError(f"Failed to create credential files: {e}")

    def cleanup_temp_files(self):
        for file_path in self._temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")
        self._temp_files.clear()

    def __del__(self):
        self.cleanup_temp_files()


async def create_auth_bridge(db_connection: Optional[psycopg.AsyncConnection] = None) -> VaultToLangChainCredentialAdapter:  # noqa: E501
    return VaultToLangChainCredentialAdapter(db_connection)
