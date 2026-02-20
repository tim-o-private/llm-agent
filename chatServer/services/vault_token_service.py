"""Vault Token Service for secure OAuth token management using Supabase Vault."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg

from ..config.constants import DEFAULT_LOG_LEVEL
from ..database.connection import get_db_connection

logger = logging.getLogger(__name__)


class VaultTokenService:
    """Service for managing OAuth tokens using Supabase Vault.

    Provides secure storage and retrieval of OAuth access and refresh tokens
    using Supabase Vault's authenticated encryption with associated data (AEAD).
    Supports both user context (UI) and scheduler context (background tasks).
    """

    def __init__(self, db_connection: psycopg.AsyncConnection, context: str = "user"):
        """Initialize the vault token service.

        Args:
            db_connection: PostgreSQL async connection from the connection pool
            context: Execution context - "user" for UI operations, "scheduler" for background tasks
        """
        self.db = db_connection
        self.context = context

        if context not in ["user", "scheduler"]:
            raise ValueError(f"Invalid context: {context}. Must be 'user' or 'scheduler'")

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
        """Store OAuth tokens securely using Supabase Vault.

        Note: Token storage always uses the user context RPC function regardless of service context,
        as storage operations are typically initiated by user authentication flows.

        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service (gmail, google_calendar, slack)
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_at: When the access token expires (optional)
            scopes: List of OAuth scopes granted (optional)
            service_user_id: User ID on the external service (optional)
            service_user_email: User email on the external service (optional)

        Returns:
            Dictionary containing the stored connection record

        Raises:
            Exception: If token storage fails
        """
        try:
            logger.info(f"Storing tokens for user {user_id} service {service_name}")

            async with self.db.cursor() as cur:
                # Use the RPC function to store tokens securely
                await cur.execute("""
                    SELECT store_oauth_tokens(
                        %s::UUID, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    user_id, service_name, access_token, refresh_token,
                    expires_at, scopes or [], service_user_id, service_user_email
                ))

                rpc_result = await cur.fetchone()
                if not rpc_result or not rpc_result[0]:
                    raise Exception("RPC function returned no result")

                result_json = rpc_result[0]
                if not result_json.get('success'):
                    raise Exception(f"RPC function failed: {result_json}")

                # Get the full connection record
                connection_id = result_json.get('connection_id')
                if not connection_id:
                    raise Exception("No connection ID returned from RPC function")

                # Fetch the complete connection record
                await cur.execute("""
                    SELECT * FROM external_api_connections
                    WHERE id = %s AND user_id = %s
                """, (connection_id, user_id))

                connection_result = await cur.fetchone()
                if not connection_result:
                    raise Exception("Failed to retrieve stored connection record")

                # Convert row to dictionary
                columns = [desc[0] for desc in cur.description]
                connection_data = dict(zip(columns, connection_result))

                # Commit the transaction so changes are visible to other connections
                await self.db.commit()

                logger.info(f"Successfully stored tokens for user {user_id} service {service_name}")
                return connection_data

        except Exception as e:
            # Rollback on error
            await self.db.rollback()
            logger.error(f"Error storing tokens for user {user_id} service {service_name}: {e}")
            raise Exception(f"Failed to store OAuth tokens: {e}")

    async def get_tokens(self, user_id: str, service_name: str) -> Tuple[str, Optional[str]]:
        """Retrieve OAuth tokens for a service connection.

        Uses the appropriate RPC function based on the service context:
        - User context: get_oauth_tokens (requires auth.uid())
        - Scheduler context: get_oauth_tokens_for_scheduler (requires postgres user)

        Args:
            user_id: User ID from auth.users
            service_name: Name of the external service (e.g., 'gmail', 'slack')

        Returns:
            Tuple of (access_token, refresh_token). refresh_token may be None.

        Raises:
            ValueError: If no connection found or tokens invalid
            Exception: For other errors
        """
        try:
            logger.debug(f"Retrieving tokens for user {user_id} service {service_name} (context: {self.context})")

            async with self.db.cursor() as cur:
                # Use appropriate RPC function based on context
                if self.context == "scheduler":
                    # Scheduler context - use scheduler-specific function
                    await cur.execute("""
                        SELECT get_oauth_tokens_for_scheduler(%s, %s)
                    """, (user_id, service_name))
                else:
                    # User context - use standard function with auth.uid()
                    await cur.execute("""
                        SELECT get_oauth_tokens(%s, %s)
                    """, (user_id, service_name))

                result = await cur.fetchone()
                if not result or not result[0]:
                    raise ValueError(f"No OAuth connection found for user {user_id} service {service_name}")

                token_data = result[0]  # This is the JSON result from the RPC function

                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token')

                if not access_token:
                    raise ValueError(f"No valid access token found for user {user_id} service {service_name}")

                logger.debug(f"Successfully retrieved tokens for user {user_id} service {service_name} (context: {self.context})")
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

                # Commit the transaction so changes are visible to other connections
                await self.db.commit()

                logger.info(f"Successfully updated access token for user {user_id} service {service_name}")
                return True

        except Exception as e:
            # Rollback on error
            await self.db.rollback()
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
                # Use RPC function to revoke tokens with proper security context
                await cur.execute("""
                    SELECT revoke_oauth_tokens(%s, %s)
                """, (user_id, service_name))

                result = await cur.fetchone()
                if not result or not result[0]:
                    logger.error(f"Failed to revoke tokens for user {user_id} service {service_name}")
                    return False

                # Commit the transaction so changes are visible to other connections
                await self.db.commit()

                logger.info(f"Successfully revoked tokens for user {user_id} service {service_name}")
                return True

        except Exception as e:
            # Rollback on error
            await self.db.rollback()
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
    """FastAPI dependency to get a VaultTokenService instance for user context.

    Args:
        db_conn: Database connection from the connection pool

    Returns:
        VaultTokenService instance configured for user context
    """
    return VaultTokenService(db_conn, context="user")


# Scheduler dependency function
async def get_vault_token_service_for_scheduler(db_conn: psycopg.AsyncConnection) -> VaultTokenService:
    """Get a VaultTokenService instance for scheduler context.

    This should be used by background services that run as the postgres user
    and need to access OAuth tokens for scheduled operations.

    Args:
        db_conn: Database connection from the connection pool (should be postgres user)

    Returns:
        VaultTokenService instance configured for scheduler context
    """
    return VaultTokenService(db_conn, context="scheduler")
