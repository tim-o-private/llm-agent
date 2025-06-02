"""Authentication bridge between Supabase Vault and LangChain Google services."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-5-authentication-bridge
# @rules memory-bank/rules/agent-rules.json#agent-003

import tempfile
import json
import os
import logging
from typing import Tuple, Optional, List
from google.oauth2.credentials import Credentials
from chatServer.services.vault_token_service import VaultTokenService

logger = logging.getLogger(__name__)


class VaultToLangChainCredentialAdapter:
    """Converts Vault OAuth tokens to LangChain-compatible credentials.
    
    This adapter bridges the gap between Supabase Vault's encrypted token storage
    and LangChain's file-based credential system for Google services (Gmail, Calendar, Drive, etc.).
    """
    
    def __init__(self, vault_service: VaultTokenService):
        """Initialize the credential adapter.
        
        Args:
            vault_service: VaultTokenService instance for token retrieval
        """
        self.vault_service = vault_service
        self._temp_files = []  # Track temp files for cleanup
    
    async def create_google_credentials(
        self, 
        user_id: str, 
        service_name: str = 'google',
        scopes: Optional[List[str]] = None
    ) -> Credentials:
        """Create Google OAuth2 credentials from Vault tokens.
        
        Args:
            user_id: User ID to retrieve tokens for
            service_name: Service name in vault (e.g., 'google', 'gmail', 'google_calendar')
            scopes: OAuth scopes to include (defaults to readonly Gmail)
            
        Returns:
            Google OAuth2 Credentials object
            
        Raises:
            RuntimeError: If credentials cannot be created
        """
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        
        try:
            logger.info(f"Creating Google credentials for user {user_id}, service {service_name}")
            
            # Get tokens from Vault
            access_token, refresh_token = await self.vault_service.get_tokens(
                user_id, service_name
            )
            
            if not access_token:
                raise RuntimeError(f"No {service_name} access token found for user {user_id}")
            
            # Get Google OAuth client credentials from environment
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise RuntimeError(
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
            
            logger.info(f"Successfully created Google credentials for user {user_id}, service {service_name}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to create Google credentials for user {user_id}, service {service_name}: {e}")
            raise RuntimeError(f"Google authentication failed: {e}")
    
    async def create_gmail_credentials(self, user_id: str) -> Credentials:
        """Create Gmail-specific credentials (convenience method).
        
        Args:
            user_id: User ID to retrieve tokens for
            
        Returns:
            Google OAuth2 Credentials object with Gmail scopes
        """
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='gmail',
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
    
    async def create_calendar_credentials(self, user_id: str) -> Credentials:
        """Create Google Calendar-specific credentials (convenience method).
        
        Args:
            user_id: User ID to retrieve tokens for
            
        Returns:
            Google OAuth2 Credentials object with Calendar scopes
        """
        return await self.create_google_credentials(
            user_id=user_id,
            service_name='google_calendar',
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
    
    async def create_temp_credential_files(
        self, 
        user_id: str, 
        service_name: str = 'google',
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