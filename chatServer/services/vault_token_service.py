"""Vault Token Service for secure OAuth token management using Supabase Vault."""

import logging
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import psycopg

try:
    from ..config.constants import DEFAULT_LOG_LEVEL
    from ..database.connection import get_db_connection
except ImportError:
    from chatServer.config.constants import DEFAULT_LOG_LEVEL
    from chatServer.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class VaultTokenService:
    """Service for managing OAuth tokens using Supabase Vault.
    
    Provides secure storage and retrieval of OAuth access and refresh tokens
    using Supabase Vault's authenticated encryption with associated data (AEAD).
    """
    
    def __init__(self, db_connection: psycopg.AsyncConnection):
        """Initialize the vault token service.
        
        Args:
            db_connection: PostgreSQL async connection from the connection pool
        """
        self.db = db_connection
    
    async def store_tokens(
        self, 
        user_id: str, 
        service_name: str,
        access_token: str, 
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None,
        service_user_id: Optional[str] = None,
        service_user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store OAuth tokens in Vault and save references in connections table.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service (gmail, google_calendar, slack)
            access_token: OAuth access token to encrypt and store
            refresh_token: OAuth refresh token to encrypt and store (optional)
            expires_at: When the access token expires (optional)
            scopes: List of OAuth scopes granted (optional)
            service_user_id: User ID from the external service (optional)
            service_user_email: User email from the external service (optional)
            
        Returns:
            Dictionary containing the created/updated connection record
            
        Raises:
            Exception: If token storage fails
        """
        try:
            logger.info(f"Storing tokens for user {user_id} service {service_name}")
            
            async with self.db.cursor() as cur:
                # Store access token in vault
                await cur.execute(
                    "SELECT vault.create_secret(%s, %s, %s)",
                    (
                        access_token,
                        f'{user_id}_{service_name}_access',
                        f'Access token for {service_name} - User {user_id}'
                    )
                )
                access_secret_result = await cur.fetchone()
                if not access_secret_result or not access_secret_result[0]:
                    raise Exception("Failed to create access token secret in vault")
                
                access_secret_id = access_secret_result[0]
                logger.debug(f"Created access token secret: {access_secret_id}")
                
                # Store refresh token in vault if provided
                refresh_secret_id = None
                if refresh_token:
                    await cur.execute(
                        "SELECT vault.create_secret(%s, %s, %s)",
                        (
                            refresh_token,
                            f'{user_id}_{service_name}_refresh',
                            f'Refresh token for {service_name} - User {user_id}'
                        )
                    )
                    refresh_secret_result = await cur.fetchone()
                    if not refresh_secret_result or not refresh_secret_result[0]:
                        raise Exception("Failed to create refresh token secret in vault")
                    
                    refresh_secret_id = refresh_secret_result[0]
                    logger.debug(f"Created refresh token secret: {refresh_secret_id}")
                
                # Upsert connection record (update if exists, insert if new)
                await cur.execute("""
                    INSERT INTO external_api_connections (
                        user_id, service_name, access_token_secret_id, refresh_token_secret_id,
                        token_expires_at, scopes, service_user_id, service_user_email, 
                        is_active, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, service_name) 
                    DO UPDATE SET
                        access_token_secret_id = EXCLUDED.access_token_secret_id,
                        refresh_token_secret_id = EXCLUDED.refresh_token_secret_id,
                        token_expires_at = EXCLUDED.token_expires_at,
                        scopes = EXCLUDED.scopes,
                        service_user_id = EXCLUDED.service_user_id,
                        service_user_email = EXCLUDED.service_user_email,
                        is_active = EXCLUDED.is_active,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                """, (
                    user_id, service_name, access_secret_id, refresh_secret_id,
                    expires_at, scopes or [], service_user_id, service_user_email,
                    True, datetime.now()
                ))
                
                connection_result = await cur.fetchone()
                if not connection_result:
                    raise Exception("Failed to store connection record")
                
                # Convert row to dictionary
                columns = [desc[0] for desc in cur.description]
                connection_data = dict(zip(columns, connection_result))
                
                logger.info(f"Successfully stored tokens for user {user_id} service {service_name}")
                return connection_data
            
        except Exception as e:
            logger.error(f"Error storing tokens for user {user_id} service {service_name}: {e}")
            raise Exception(f"Failed to store OAuth tokens: {e}")
    
    async def get_tokens(self, user_id: str, service_name: str) -> Tuple[str, Optional[str]]:
        """Retrieve and decrypt OAuth tokens for a user's service connection.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service
            
        Returns:
            Tuple of (access_token, refresh_token). refresh_token may be None.
            
        Raises:
            ValueError: If no connection found for the user/service
            Exception: If token retrieval fails
        """
        try:
            logger.debug(f"Retrieving tokens for user {user_id} service {service_name}")
            
            async with self.db.cursor() as cur:
                # Get decrypted tokens using the secure view
                await cur.execute("""
                    SELECT access_token, refresh_token, is_active
                    FROM user_api_tokens 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                result = await cur.fetchone()
                if not result:
                    raise ValueError(f"No {service_name} connection found for user {user_id}")
                
                access_token, refresh_token, is_active = result
                
                if not is_active:
                    raise ValueError(f"{service_name} connection is inactive for user {user_id}")
                
                if not access_token:
                    raise Exception(f"Access token not found for user {user_id} service {service_name}")
                
                logger.debug(f"Successfully retrieved tokens for user {user_id} service {service_name}")
                return access_token, refresh_token
            
        except ValueError:
            # Re-raise ValueError as-is (expected errors)
            raise
        except Exception as e:
            logger.error(f"Error retrieving tokens for user {user_id} service {service_name}: {e}")
            raise Exception(f"Failed to retrieve OAuth tokens: {e}")
    
    async def update_access_token(
        self, 
        user_id: str, 
        service_name: str,
        new_access_token: str, 
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Update access token after refresh.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service
            new_access_token: New access token to store
            expires_at: When the new token expires (optional)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating access token for user {user_id} service {service_name}")
            
            async with self.db.cursor() as cur:
                # Get current connection to find the access token secret ID
                await cur.execute("""
                    SELECT access_token_secret_id 
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                connection_result = await cur.fetchone()
                if not connection_result:
                    logger.error(f"No connection found for user {user_id} service {service_name}")
                    return False
                
                access_token_secret_id = connection_result[0]
                if not access_token_secret_id:
                    logger.error(f"No access token secret ID found for user {user_id} service {service_name}")
                    return False
                
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
                
                logger.info(f"Successfully updated access token for user {user_id} service {service_name}")
                return True
            
        except Exception as e:
            logger.error(f"Error updating access token for user {user_id} service {service_name}: {e}")
            return False
    
    async def revoke_tokens(self, user_id: str, service_name: str) -> bool:
        """Revoke and delete OAuth tokens for a service connection.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service
            
        Returns:
            True if revocation successful, False otherwise
        """
        try:
            logger.info(f"Revoking tokens for user {user_id} service {service_name}")
            
            async with self.db.cursor() as cur:
                # Get connection with secret IDs
                await cur.execute("""
                    SELECT access_token_secret_id, refresh_token_secret_id
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                connection_result = await cur.fetchone()
                if not connection_result:
                    logger.warning(f"No connection found for user {user_id} service {service_name}")
                    return True  # Already revoked/doesn't exist
                
                access_token_secret_id, refresh_token_secret_id = connection_result
                
                # Delete vault secrets
                if access_token_secret_id:
                    await cur.execute(
                        "DELETE FROM vault.secrets WHERE id = %s",
                        (access_token_secret_id,)
                    )
                
                if refresh_token_secret_id:
                    await cur.execute(
                        "DELETE FROM vault.secrets WHERE id = %s",
                        (refresh_token_secret_id,)
                    )
                
                # Delete the connection record
                await cur.execute("""
                    DELETE FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                logger.info(f"Successfully revoked tokens for user {user_id} service {service_name}")
                return True
            
        except Exception as e:
            logger.error(f"Error revoking tokens for user {user_id} service {service_name}: {e}")
            return False
    
    async def get_connection_info(self, user_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        """Get connection information without decrypting tokens.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service
            
        Returns:
            Dictionary with connection info (excluding tokens) or None if not found
        """
        try:
            async with self.db.cursor() as cur:
                await cur.execute("""
                    SELECT id, service_name, service_user_id, service_user_email,
                           scopes, token_expires_at, is_active, created_at, updated_at
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                result = await cur.fetchone()
                if not result:
                    return None
                
                # Convert row to dictionary
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, result))
            
        except Exception as e:
            logger.error(f"Error getting connection info for user {user_id} service {service_name}: {e}")
            return None
    
    async def list_user_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all active connections for a user.
        
        Args:
            user_id: User ID from auth.users
            
        Returns:
            List of connection dictionaries (excluding tokens)
        """
        try:
            async with self.db.cursor() as cur:
                await cur.execute("""
                    SELECT id, service_name, service_user_id, service_user_email,
                           scopes, token_expires_at, is_active, created_at, updated_at
                    FROM external_api_connections 
                    WHERE user_id = %s AND is_active = true
                """, (user_id,))
                
                results = await cur.fetchall()
                if not results:
                    return []
                
                # Convert rows to dictionaries
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            logger.error(f"Error listing connections for user {user_id}: {e}")
            return []
    
    async def check_token_expiry(self, user_id: str, service_name: str) -> Optional[datetime]:
        """Check when a token expires.
        
        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service
            
        Returns:
            Expiration datetime or None if no expiration set or connection not found
        """
        try:
            async with self.db.cursor() as cur:
                await cur.execute("""
                    SELECT token_expires_at
                    FROM external_api_connections 
                    WHERE user_id = %s AND service_name = %s
                """, (user_id, service_name))
                
                result = await cur.fetchone()
                if result and result[0]:
                    return result[0]  # PostgreSQL returns datetime objects directly
                
                return None
            
        except Exception as e:
            logger.error(f"Error checking token expiry for user {user_id} service {service_name}: {e}")
            return None


# FastAPI dependency function
async def get_vault_token_service(db_conn: psycopg.AsyncConnection = get_db_connection()) -> VaultTokenService:
    """FastAPI dependency to get a VaultTokenService instance.
    
    Args:
        db_conn: Database connection from the connection pool
        
    Returns:
        VaultTokenService instance
    """
    return VaultTokenService(db_conn) 