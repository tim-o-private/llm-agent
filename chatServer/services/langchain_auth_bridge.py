"""Authentication bridge between Supabase Vault and LangChain Google services."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-5-authentication-bridge
# @rules memory-bank/rules/agent-rules.json#agent-003

import tempfile
import json
import os
import logging
from typing import Tuple, Optional, List
from google.oauth2.credentials import Credentials
import psycopg
from datetime import datetime

try:
    from ..database.connection import get_db_connection
except ImportError:
    from chatServer.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class VaultToLangChainCredentialAdapter:
    """Converts Vault OAuth tokens to LangChain-compatible credentials.
    
    This adapter bridges the gap between Supabase Vault's encrypted token storage
    and LangChain's file-based credential system for Google services (Gmail, Calendar, Drive, etc.).
    
    Uses direct vault access via vault.decrypted_secrets for maximum security.
    """
    
    def __init__(self, db_connection: Optional[psycopg.AsyncConnection] = None):
        """Initialize the credential adapter.
        
        Args:
            db_connection: Optional database connection. If not provided, will get one from pool.
        """
        self.db_connection = db_connection
        self._temp_files = []  # Track temp files for cleanup
    
    async def _get_db_connection(self) -> psycopg.AsyncConnection:
        """Get database connection from pool if not provided."""
        if self.db_connection:
            return self.db_connection
        
        # Get connection from pool
        async for db_conn in get_db_connection():
            return db_conn
    
    async def _get_tokens_from_vault(self, user_id: str, service_name: str) -> Tuple[str, Optional[str]]:
        """Get decrypted tokens directly from vault.
        
        Args:
            user_id: User ID to retrieve tokens for
            service_name: Service name (gmail, google_calendar, slack)
            
        Returns:
            Tuple of (access_token, refresh_token). refresh_token may be None.
            
        Raises:
            ValueError: If no connection found for the user/service
            RuntimeError: If token retrieval fails
        """
        try:
            logger.debug(f"Retrieving tokens from vault for user {user_id} service {service_name}")
            
            db_conn = await self._get_db_connection()
            async with db_conn.cursor() as cur:
                # Get connection with secret IDs
                await cur.execute("""
                    SELECT access_token_secret_id, refresh_token_secret_id, is_active
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                connection_result = await cur.fetchone()
                if not connection_result:
                    raise ValueError(f"No {service_name} connection found for user {user_id}")
                
                access_token_secret_id, refresh_token_secret_id, is_active = connection_result
                
                if not is_active:
                    raise ValueError(f"{service_name} connection is inactive for user {user_id}")
                
                if not access_token_secret_id:
                    raise RuntimeError(f"No access token secret ID found for user {user_id} service {service_name}")
                
                # Get decrypted access token
                await cur.execute("""
                    SELECT decrypted_secret 
                    FROM vault.decrypted_secrets 
                    WHERE id = %s
                """, (access_token_secret_id,))
                
                access_result = await cur.fetchone()
                if not access_result or not access_result[0]:
                    raise RuntimeError(f"Failed to decrypt access token for user {user_id} service {service_name}")
                
                access_token = access_result[0]
                
                # Get decrypted refresh token if available
                refresh_token = None
                if refresh_token_secret_id:
                    await cur.execute("""
                        SELECT decrypted_secret 
                        FROM vault.decrypted_secrets 
                        WHERE id = %s
                    """, (refresh_token_secret_id,))
                    
                    refresh_result = await cur.fetchone()
                    if refresh_result and refresh_result[0]:
                        refresh_token = refresh_result[0]
                
                logger.debug(f"Successfully retrieved tokens from vault for user {user_id} service {service_name}")
                return access_token, refresh_token
            
        except ValueError:
            # Re-raise ValueError as-is (expected errors)
            raise
        except Exception as e:
            logger.error(f"Error retrieving tokens from vault for user {user_id} service {service_name}: {e}")
            raise RuntimeError(f"Failed to retrieve OAuth tokens from vault: {e}")

    async def create_google_credentials(
        self, 
        user_id: str, 
        service_name: str = 'gmail',
        scopes: Optional[List[str]] = None
    ) -> Credentials:
        """Create Google OAuth2 credentials from existing Vault tokens.
        
        IMPORTANT: This method only works if the user has already completed the OAuth flow
        via the UI (Integrations.tsx). It cannot create new credentials - only retrieve
        and refresh existing ones.
        
        Args:
            user_id: User ID to retrieve tokens for
            service_name: Service name in vault (gmail, google_calendar, slack)
            scopes: OAuth scopes to include (defaults to readonly Gmail)
            
        Returns:
            Google OAuth2 Credentials object (with refreshed tokens if needed)
            
        Raises:
            ValueError: If no OAuth connection exists for this user/service
            RuntimeError: If credentials cannot be created or refreshed
        """
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        
        try:
            logger.info(f"Creating Google credentials for user {user_id}, service {service_name}")
            
            # Get tokens from Vault (this will fail if no OAuth flow was completed)
            access_token, refresh_token = await self._get_tokens_from_vault(user_id, service_name)
            
            if not access_token:
                raise RuntimeError(f"No {service_name} access token found for user {user_id}")
            
            # Get Google OAuth client credentials from environment
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise RuntimeError(
                    "Google OAuth configuration missing. Please contact support - "
                    "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables required"
                )
            
            # Create Google credentials object
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes
            )
            
            # Check if token needs refresh and refresh if necessary
            if credentials.expired and credentials.refresh_token:
                logger.info(f"Access token expired for user {user_id}, service {service_name}. Attempting refresh...")
                await self._refresh_credentials(user_id, service_name, credentials)
            elif credentials.expired:
                raise RuntimeError(
                    f"Access token expired and no refresh token available. "
                    f"Please reconnect your {service_name} account in Settings > Integrations."
                )
            
            logger.info(f"Successfully created Google credentials for user {user_id}, service {service_name}")
            return credentials
            
        except ValueError as e:
            # Re-raise ValueError with clearer message about OAuth requirement
            raise ValueError(f"No OAuth connection found. User must complete OAuth flow via UI first: {e}")
        except Exception as e:
            logger.error(f"Failed to create Google credentials for user {user_id}, service {service_name}: {e}")
            raise RuntimeError(f"Google authentication failed: {e}")
    
    async def _refresh_credentials(self, user_id: str, service_name: str, credentials: Credentials) -> None:
        """Refresh expired credentials and update vault storage.
        
        Args:
            user_id: User ID
            service_name: Service name
            credentials: Credentials object to refresh (modified in place)
            
        Raises:
            RuntimeError: If refresh fails
        """
        try:
            logger.info(f"Refreshing credentials for user {user_id}, service {service_name}")
            
            # Use Google's refresh mechanism
            from google.auth.transport.requests import Request
            import asyncio
            
            # Google's refresh is synchronous, so we run it in a thread
            def refresh_sync():
                request = Request()
                credentials.refresh(request)
            
            # Run the synchronous refresh in a thread pool
            await asyncio.get_event_loop().run_in_executor(None, refresh_sync)
            
            if not credentials.token:
                raise RuntimeError(
                    f"Token refresh failed - no new access token received. "
                    f"Please reconnect your {service_name} account in Settings > Integrations."
                )
            
            # Update the vault with the new access token
            await self._update_access_token_in_vault(user_id, service_name, credentials.token, credentials.expiry)
            
            logger.info(f"Successfully refreshed credentials for user {user_id}, service {service_name}")
            
        except Exception as e:
            logger.error(f"Failed to refresh credentials for user {user_id}, service {service_name}: {e}")
            error_msg = str(e)
            if "invalid_grant" in error_msg.lower():
                raise RuntimeError(
                    f"Refresh token is invalid or expired. "
                    f"Please reconnect your {service_name} account in Settings > Integrations."
                )
            elif "unauthorized" in error_msg.lower():
                raise RuntimeError(
                    f"Authentication failed during token refresh. "
                    f"Please reconnect your {service_name} account in Settings > Integrations."
                )
            else:
                raise RuntimeError(f"Token refresh failed: {error_msg}")
    
    async def _update_access_token_in_vault(self, user_id: str, service_name: str, new_access_token: str, expires_at: Optional[datetime] = None) -> None:
        """Update access token in vault after refresh.
        
        Args:
            user_id: User ID
            service_name: Service name
            new_access_token: New access token
            expires_at: Token expiration time
        """
        try:
            db_conn = await self._get_db_connection()
            async with db_conn.cursor() as cur:
                # Get current connection to find the access token secret ID
                await cur.execute("""
                    SELECT access_token_secret_id 
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                connection_result = await cur.fetchone()
                if not connection_result:
                    raise RuntimeError(f"No connection found for user {user_id} service {service_name}")
                
                access_token_secret_id = connection_result[0]
                if not access_token_secret_id:
                    raise RuntimeError(f"No access token secret ID found for user {user_id} service {service_name}")
                
                # Update the vault secret with the new token
                await cur.execute(
                    "SELECT vault.update_secret(%s, %s)",
                    (access_token_secret_id, new_access_token)
                )
                
                # Update the connection record with new expiration time if provided
                if expires_at:
                    await cur.execute("""
                        UPDATE external_api_connections 
                        SET token_expires_at = %s, updated_at = %s
                        WHERE user_id = %s AND service_name = %s
                    """, (expires_at, datetime.now(), user_id, service_name))
                
                logger.debug(f"Successfully updated access token in vault for user {user_id} service {service_name}")
                
        except Exception as e:
            logger.error(f"Error updating access token in vault for user {user_id} service {service_name}: {e}")
            raise
    
    async def fetch_or_refresh_gmail_credentials(self, user_id: str) -> Credentials:
        """Fetch or refresh Gmail-specific credentials (convenience method).
        
        Args:
            user_id: User ID to retrieve tokens for
            
        Returns:
            Google OAuth2 Credentials object with Gmail scopes
            
        Raises:
            ValueError: If no OAuth connection exists for this user
            RuntimeError: If credentials cannot be fetched or refreshed
        """
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='gmail',
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
    
    async def fetch_or_refresh_calendar_credentials(self, user_id: str) -> Credentials:
        """Fetch or refresh Google Calendar-specific credentials (convenience method).
        
        Args:
            user_id: User ID to retrieve tokens for
            
        Returns:
            Google OAuth2 Credentials object with Calendar scopes
            
        Raises:
            ValueError: If no OAuth connection exists for this user
            RuntimeError: If credentials cannot be fetched or refreshed
        """
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='google_calendar',
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
    
    async def create_temp_credential_files(
        self, 
        user_id: str, 
        service_name: str = 'gmail',
        scopes: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """Create temporary credential files for LangChain (fallback method).
        
        This method creates temporary JSON files that LangChain can use directly.
        Files are automatically tracked for cleanup.
        
        Args:
            user_id: User ID to retrieve tokens for
            service_name: Service name in vault
            scopes: OAuth scopes to include
            
        Returns:
            Tuple of (token_file_path, client_secrets_file_path)
            
        Raises:
            RuntimeError: If credential files cannot be created
        """
        try:
            logger.info(f"Creating temporary credential files for user {user_id}, service {service_name}")
            
            # Get credentials object first
            credentials = await self.create_google_credentials(user_id, service_name, scopes)
            
            # Create temporary token file
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
            
            # Create client secrets file
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
            
            logger.info(f"Created temporary credential files: token={token_file}, secrets={secrets_file}")
            return token_file, secrets_file
            
        except Exception as e:
            logger.error(f"Failed to create temporary credential files for user {user_id}, service {service_name}: {e}")
            # Clean up any files that were created
            self.cleanup_temp_files()
            raise RuntimeError(f"Failed to create credential files: {e}")
    
    def cleanup_temp_files(self):
        """Clean up temporary credential files."""
        for file_path in self._temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {e}")
        
        self._temp_files.clear()
    
    def __del__(self):
        """Ensure temp files are cleaned up when adapter is destroyed."""
        self.cleanup_temp_files()


# Factory function for creating adapter instances
async def create_auth_bridge(db_connection: Optional[psycopg.AsyncConnection] = None) -> VaultToLangChainCredentialAdapter:
    """Create a VaultToLangChainCredentialAdapter instance.
    
    Args:
        db_connection: Optional database connection. If not provided, will get one from pool.
        
    Returns:
        VaultToLangChainCredentialAdapter instance
    """
    return VaultToLangChainCredentialAdapter(db_connection) 