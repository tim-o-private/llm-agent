"""Database user context helper for setting auth.uid() in RPC functions."""

import logging

import psycopg

logger = logging.getLogger(__name__)


async def set_user_context(connection: psycopg.AsyncConnection, user_id: str) -> None:
    """Set user context on a database connection so auth.uid() returns the correct user.

    This is required when calling RPC functions that check auth.uid() for security.
    The connection should be a service role connection with proper permissions.

    Args:
        connection: PostgreSQL async connection (should be service role)
        user_id: User ID to set as the current authenticated user

    Raises:
        Exception: If setting user context fails
    """
    try:
        async with connection.cursor() as cur:
            # Set JWT claims that auth.uid() uses
            # This mimics what Supabase does when a user is authenticated
            jwt_claims = f'{{"sub": "{user_id}", "role": "authenticated", "aud": "authenticated"}}'

            await cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (jwt_claims,))
            await cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (user_id,))

            # Verify that auth.uid() now returns the correct user
            await cur.execute("SELECT auth.uid()")
            auth_uid_result = await cur.fetchone()

            if not auth_uid_result or str(auth_uid_result[0]) != user_id:
                raise Exception(f"Failed to set user context: auth.uid() returned {auth_uid_result[0]}, expected {user_id}")

            logger.debug(f"Successfully set user context for user {user_id}")

    except Exception as e:
        logger.error(f"Error setting user context for user {user_id}: {e}")
        raise Exception(f"Failed to set user context: {e}")


class UserContextConnection:
    """Context manager that provides a database connection with user context set.

    This is useful for calling RPC functions that check auth.uid() for security.
    """

    def __init__(self, connection: psycopg.AsyncConnection, user_id: str):
        """Initialize the context manager.

        Args:
            connection: PostgreSQL async connection (should be service role)
            user_id: User ID to set as the current authenticated user
        """
        self.connection = connection
        self.user_id = user_id
        self._context_set = False

    async def __aenter__(self) -> psycopg.AsyncConnection:
        """Enter the context and set user context."""
        await set_user_context(self.connection, self.user_id)
        self._context_set = True
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and optionally clean up."""
        # Note: We don't reset the context because the connection
        # will be returned to the pool and reset automatically
        pass


def with_user_context(connection: psycopg.AsyncConnection, user_id: str) -> UserContextConnection:
    """Create a context manager that sets user context on a database connection.

    Usage:
        async with with_user_context(conn, user_id) as user_conn:
            # Now auth.uid() will return user_id in RPC functions
            result = await user_conn.execute("SELECT some_rpc_function(%s)", (param,))

    Args:
        connection: PostgreSQL async connection (should be service role)
        user_id: User ID to set as the current authenticated user

    Returns:
        UserContextConnection context manager
    """
    return UserContextConnection(connection, user_id)
