"""Helper functions for Gmail integration testing."""

import uuid
from typing import Any, Optional

import psycopg

from chatServer.config.settings import get_settings
from src.core.agent_loader_db import load_agent_executor_db


class GmailIntegrationTestHelper:
    """Helper class for Gmail integration testing."""

    def __init__(self, test_user_id: Optional[str] = None):
        # Generate a proper UUID for the test user if not provided
        if test_user_id is None or not self._is_valid_uuid(test_user_id):
            self.test_user_id = str(uuid.uuid4())
        else:
            self.test_user_id = test_user_id

        self._db_connection = None
        self._settings = get_settings()
        self._user_created = False

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

    async def _get_db_connection(self):
        """Get database connection for testing (creates own connection)."""
        if self._db_connection is None:
            try:
                # Create our own connection using the same settings as the dev server
                conn_str = self._settings.database_url
                self._db_connection = await psycopg.AsyncConnection.connect(
                    conn_str,
                    connect_timeout=10
                )
                print("✅ Created test database connection")
            except Exception as e:
                raise RuntimeError(f"Failed to create test database connection: {e}")

        return self._db_connection

    async def _ensure_test_user_exists(self):
        """Ensure test user exists in auth.users table."""
        if self._user_created:
            return

        db_conn = await self._get_db_connection()
        async with db_conn.cursor() as cur:
            # Check if user exists
            await cur.execute(
                "SELECT id FROM auth.users WHERE id = %s",
                (self.test_user_id,)
            )

            if await cur.fetchone() is None:
                # Create test user
                await cur.execute("""
                    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                    VALUES (%s, %s, 'dummy_password', NOW(), NOW(), NOW())
                """, (
                    self.test_user_id,
                    f"test_user_{self.test_user_id[:8]}@gmail-integration-test.com"
                ))
                print(f"✅ Created test user: {self.test_user_id}")
                self._user_created = True

    async def setup_test_oauth_tokens(self,
                                    access_token: str = "test_access_token",
                                    refresh_token: str = "test_refresh_token") -> None:
        """Set up test OAuth tokens in vault using the same path as Gmail tools."""
        # Ensure test user exists first
        await self._ensure_test_user_exists()

        # Import VaultTokenService here to avoid circular imports
        from chatServer.services.vault_token_service import VaultTokenService

        db_conn = await self._get_db_connection()
        vault_service = VaultTokenService(db_conn)
        await vault_service.store_tokens(
            user_id=self.test_user_id,
            service_name="gmail",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=None,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            service_user_email="test@gmail.com"
        )
        print(f"✅ Stored test OAuth tokens for user: {self.test_user_id}")

    async def cleanup_test_tokens(self) -> None:
        """Clean up test tokens and test user."""
        try:
            # Import VaultTokenService here to avoid circular imports
            from chatServer.services.vault_token_service import VaultTokenService

            db_conn = await self._get_db_connection()
            vault_service = VaultTokenService(db_conn)
            await vault_service.revoke_tokens(
                user_id=self.test_user_id,
                service_name="gmail"
            )
            print(f"✅ Cleaned up OAuth tokens for user: {self.test_user_id}")

            # Clean up test user if we created it
            if self._user_created:
                async with db_conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM auth.users WHERE id = %s",
                        (self.test_user_id,)
                    )
                    print(f"✅ Cleaned up test user: {self.test_user_id}")

        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

    async def create_test_agent(self) -> Any:
        """Create test agent with Gmail tools."""
        # load_agent_executor_db is synchronous, not async
        agent = load_agent_executor_db(
            agent_name="test_email_digest_agent",
            user_id=self.test_user_id,
            session_id=f"test_session_{self.test_user_id}"
        )

        # Verify the agent has the required methods
        if not hasattr(agent, 'ainvoke'):
            raise RuntimeError(f"Loaded agent {type(agent)} does not have ainvoke method")

        return agent

    async def execute_gmail_digest(self,
                                 agent: Any,
                                 hours_back: int = 24,
                                 max_threads: int = 10) -> str:
        """Execute Gmail digest via agent."""
        query = f"Generate an email digest for the last {hours_back} hours, max {max_threads} threads"
        result = await agent.ainvoke({"input": query})
        return result.get("output", str(result))

    async def execute_gmail_search(self,
                                 agent: Any,
                                 search_query: str = "is:unread") -> str:
        """Execute Gmail search via agent."""
        query = f"Search my Gmail for: {search_query}"
        result = await agent.ainvoke({"input": query})
        return result.get("output", str(result))

    async def close(self):
        """Clean up resources."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
