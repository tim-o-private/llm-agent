"""Integration tests for VaultTokenService with live database connections.

These tests verify Row-Level Security (RLS) policies are working correctly
by using actual database connections and inserting test data.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator

import jwt
import pytest
from psycopg_pool import AsyncConnectionPool

from chatServer.database.user_context import with_user_context
from chatServer.services.vault_token_service import VaultTokenService


class TestVaultTokenServiceIntegration:
    """Integration tests using live database connections."""

    @pytest.fixture(scope="function")
    async def db_pool(self) -> AsyncGenerator[AsyncConnectionPool, None]:
        """Create a database connection pool for testing."""
        # Get connection params from environment
        db_user = os.getenv("SUPABASE_DB_USER")
        db_password = os.getenv("SUPABASE_DB_PASSWORD")
        db_host = os.getenv("SUPABASE_DB_HOST")
        db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
        db_port = os.getenv("SUPABASE_DB_PORT", "5432")

        if not all([db_user, db_password, db_host]):
            pytest.skip("Database credentials not available for integration tests")

        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        pool = AsyncConnectionPool(
            conninfo=connection_string,
            min_size=1,
            max_size=3,
            timeout=30.0,
            kwargs={
                "connect_timeout": 10.0,
                "application_name": "vault-token-integration-test",
            }
        )

        try:
            await pool.open()
            yield pool
        finally:
            await pool.close()

    @pytest.fixture
    async def test_users(self, db_pool: AsyncConnectionPool) -> tuple[str, str]:
        """Create two test users in auth.users table."""
        user_a_id = str(uuid.uuid4())
        user_b_id = str(uuid.uuid4())

        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                # Insert test users into auth.users table
                await cur.execute("""
                    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                    VALUES
                        (%s, %s, 'dummy_password', NOW(), NOW(), NOW()),
                        (%s, %s, 'dummy_password', NOW(), NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (
                    user_a_id, f"user_a_{user_a_id[:8]}@test.com",
                    user_b_id, f"user_b_{user_b_id[:8]}@test.com"
                ))
                await conn.commit()

        yield user_a_id, user_b_id

        # Cleanup: Remove test users and their connections
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                # Delete connections first (due to foreign key)
                await cur.execute("""
                    DELETE FROM public.external_api_connections
                    WHERE user_id IN (%s, %s)
                """, (user_a_id, user_b_id))

                # Delete test users
                await cur.execute("""
                    DELETE FROM auth.users
                    WHERE id IN (%s, %s)
                """, (user_a_id, user_b_id))
                await conn.commit()

    def _create_jwt_token(self, user_id: str) -> str:
        """Create a JWT token for user impersonation."""
        # Get JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            pytest.skip("SUPABASE_JWT_SECRET not available for JWT token generation")

        # Create JWT payload
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        # Generate JWT token
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        return token

    @pytest.fixture
    async def vault_service_for_user(self, db_pool: AsyncConnectionPool):
        """Factory to create VaultTokenService for a specific user using authenticated role."""
        def _create_service_for_user(user_id: str):
            # Create an async context manager that provides a connection with authenticated role
            class VaultServiceConnectionManager:
                def __init__(self, pool: AsyncConnectionPool, user_id: str):
                    self.pool = pool
                    self.user_id = user_id
                    self.conn = None
                    self.original_role = None

                async def __aenter__(self):
                    # Get a service role connection from the pool
                    self.conn = await self.pool.getconn()

                    async with self.conn.cursor() as cur:
                        # Store the original role
                        await cur.execute("SELECT current_user")
                        self.original_role = (await cur.fetchone())[0]

                        # Switch to authenticated role
                        await cur.execute("SET ROLE authenticated")

                        # Set the JWT context that Supabase RLS recognizes
                        await cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (
                            f'{{"sub": "{self.user_id}", "role": "authenticated", "aud": "authenticated"}}',
                        ))
                        await cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (self.user_id,))
                        await cur.execute("SELECT set_config('request.jwt.claim.role', %s, true)", ('authenticated',))

                        # Verify that auth.uid() returns the correct user
                        await cur.execute("SELECT auth.uid()")
                        auth_uid_result = await cur.fetchone()

                        if not auth_uid_result or str(auth_uid_result[0]) != self.user_id:
                            raise Exception(f"Failed to set JWT context: auth.uid() returned {auth_uid_result[0]}, expected {self.user_id}")

                        # Verify we're now running as authenticated role
                        await cur.execute("SELECT current_user")
                        current_role = (await cur.fetchone())[0]
                        if current_role != 'authenticated':
                            raise Exception(f"Failed to switch to authenticated role: current_user is {current_role}")

                    # Return VaultTokenService with the authenticated role connection
                    return VaultTokenService(self.conn)

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self.conn:
                        try:
                            # Reset to original role before returning connection to pool
                            async with self.conn.cursor() as cur:
                                await cur.execute(f"SET ROLE {self.original_role}")
                        except Exception:
                            pass  # Ignore errors during cleanup
                        finally:
                            await self.pool.putconn(self.conn)

            return VaultServiceConnectionManager(db_pool, user_id)

        return _create_service_for_user

    @pytest.mark.asyncio
    async def test_rls_with_vault_tokens(
        self,
        db_pool: AsyncConnectionPool,
        test_users: tuple[str, str],
        vault_service_for_user
    ):
        """Test RLS works correctly when using vault-stored tokens."""
        user_a_id, user_b_id = test_users

        # Store tokens for User A
        tokens_a = {
            'access_token': 'user_a_vault_access_token',
            'refresh_token': 'user_a_vault_refresh_token'
        }

        async with vault_service_for_user(user_a_id) as service_a:
            success_a = await service_a.store_tokens(
                user_a_id,
                'gmail',
                tokens_a['access_token'],
                tokens_a['refresh_token'],
                scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                service_user_id='vault_google_user_a',
                service_user_email='vault_user_a@gmail.com',
                expires_at=datetime.now() + timedelta(hours=1)
            )
            assert success_a is not None  # store_tokens returns connection data, not boolean

        # Store tokens for User B
        tokens_b = {
            'access_token': 'user_b_vault_access_token',
            'refresh_token': 'user_b_vault_refresh_token'
        }

        async with vault_service_for_user(user_b_id) as service_b:
            success_b = await service_b.store_tokens(
                user_b_id,
                'gmail',
                tokens_b['access_token'],
                tokens_b['refresh_token'],
                scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                service_user_id='vault_google_user_b',
                service_user_email='vault_user_b@gmail.com',
                expires_at=datetime.now() + timedelta(hours=1)
            )
            assert success_b is not None  # store_tokens returns connection data, not boolean

        # Test 1: User A can retrieve their own tokens
        async with vault_service_for_user(user_a_id) as service_a:
            retrieved_tokens_a = await service_a.get_tokens(user_a_id, 'gmail')
            assert retrieved_tokens_a[0] == 'user_a_vault_access_token'  # access_token
            assert retrieved_tokens_a[1] == 'user_a_vault_refresh_token'  # refresh_token

        # Test 2: User B can retrieve their own tokens
        async with vault_service_for_user(user_b_id) as service_b:
            retrieved_tokens_b = await service_b.get_tokens(user_b_id, 'gmail')
            assert retrieved_tokens_b[0] == 'user_b_vault_access_token'  # access_token
            assert retrieved_tokens_b[1] == 'user_b_vault_refresh_token'  # refresh_token

        # Test 3: User A cannot retrieve User B's tokens (should raise ValueError)
        async with vault_service_for_user(user_a_id) as service_a:
            with pytest.raises(ValueError, match="No gmail connection found"):
                await service_a.get_tokens(user_b_id, 'gmail')

        # Test 4: User B cannot retrieve User A's tokens (should raise ValueError)
        async with vault_service_for_user(user_b_id) as service_b:
            with pytest.raises(ValueError, match="No gmail connection found"):
                await service_b.get_tokens(user_a_id, 'gmail')

        # Test 5: User A cannot update User B's tokens
        async with vault_service_for_user(user_a_id) as service_a:
            update_success_a_to_b = await service_a.update_access_token(
                user_b_id, 'gmail', 'malicious_token'
            )
            assert update_success_a_to_b is False  # Should fail due to RLS

        # Test 6: User B cannot update User A's tokens
        async with vault_service_for_user(user_b_id) as service_b:
            update_success_b_to_a = await service_b.update_access_token(
                user_a_id, 'gmail', 'malicious_token'
            )
            assert update_success_b_to_a is False  # Should fail due to RLS

        # Test 7: User A cannot revoke User B's tokens
        async with vault_service_for_user(user_a_id) as service_a:
            revoke_success_a_to_b = await service_a.revoke_tokens(user_b_id, 'gmail')
            assert revoke_success_a_to_b is False  # Should fail due to RLS

        # Test 8: User B cannot revoke User A's tokens
        async with vault_service_for_user(user_b_id) as service_b:
            revoke_success_b_to_a = await service_b.revoke_tokens(user_a_id, 'gmail')
            assert revoke_success_b_to_a is False  # Should fail due to RLS

        # Verify tokens are still intact after attempted cross-user operations
        async with vault_service_for_user(user_a_id) as service_a:
            final_tokens_a = await service_a.get_tokens(user_a_id, 'gmail')
            assert final_tokens_a[0] == 'user_a_vault_access_token'  # access_token

        async with vault_service_for_user(user_b_id) as service_b:
            final_tokens_b = await service_b.get_tokens(user_b_id, 'gmail')
            assert final_tokens_b[0] == 'user_b_vault_access_token'  # access_token

    @pytest.mark.asyncio
    async def test_direct_database_query_bypasses_rls_for_verification(
        self,
        db_pool: AsyncConnectionPool,
        test_users: tuple[str, str]
    ):
        """Test that direct database queries (as superuser) can see all data, bypassing RLS."""
        user_a_id, user_b_id = test_users

        # Store test data using the vault service (proper way)

        # Store tokens for User A
        async with db_pool.connection() as conn:
            async with with_user_context(conn, user_a_id) as user_conn:
                async with user_conn.cursor() as cur:
                    result_a = await cur.execute(
                        "SELECT store_oauth_tokens(%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_a_id, 'gmail', 'user_a_access_token', 'user_a_refresh_token',
                         None, ['https://www.googleapis.com/auth/gmail.readonly'],
                         'google_user_a', 'user_a@gmail.com')
                    )
                    result_a_data = await cur.fetchone()
                    assert result_a_data[0]['success'] is True

        # Store tokens for User B
        async with db_pool.connection() as conn:
            async with with_user_context(conn, user_b_id) as user_conn:
                async with user_conn.cursor() as cur:
                    result_b = await cur.execute(
                        "SELECT store_oauth_tokens(%s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_b_id, 'gmail', 'user_b_access_token', 'user_b_refresh_token',
                         None, ['https://www.googleapis.com/auth/gmail.readonly'],
                         'google_user_b', 'user_b@gmail.com')
                    )
                    result_b_data = await cur.fetchone()
                    assert result_b_data[0]['success'] is True

        # Direct database query as superuser (bypasses RLS)
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT user_id, service_name, service_user_email
                    FROM external_api_connections
                    WHERE service_name = 'gmail'
                    ORDER BY service_user_email
                """)
                all_connections = await cur.fetchall()

                # Should see both users' connections (RLS bypassed)
                assert len(all_connections) == 2

                # Verify both users' data is visible
                user_emails = [conn[2] for conn in all_connections]
                assert 'user_a@gmail.com' in user_emails
                assert 'user_b@gmail.com' in user_emails

                # Verify user IDs are correct
                user_ids = [str(conn[0]) for conn in all_connections]
                assert user_a_id in user_ids
                assert user_b_id in user_ids

    @pytest.mark.asyncio
    async def test_debug_auth_uid(
        self,
        db_pool: AsyncConnectionPool,
        test_users: tuple[str, str],
        vault_service_for_user
    ):
        """Debug test to check what auth.uid() returns."""
        user_a_id, user_b_id = test_users

        # Test what auth.uid() returns without setting context
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT auth.uid()")
                result = await cur.fetchone()
                print(f"auth.uid() without context: {result}")

        # Test what auth.uid() returns with our context setting
        async with vault_service_for_user(user_a_id) as conn_a:
            async with conn_a.cursor() as cur:
                await cur.execute("SELECT auth.uid()")
                result = await cur.fetchone()
                print(f"auth.uid() with User A context: {result}")
                print(f"Expected User A ID: {user_a_id}")

                # Also check what our JWT claims setting returns
                await cur.execute("SELECT current_setting('request.jwt.claims', true)")
                jwt_result = await cur.fetchone()
                print(f"JWT claims setting: {jwt_result}")

        # Test with User B
        async with vault_service_for_user(user_b_id) as conn_b:
            async with conn_b.cursor() as cur:
                await cur.execute("SELECT auth.uid()")
                result = await cur.fetchone()
                print(f"auth.uid() with User B context: {result}")
                print(f"Expected User B ID: {user_b_id}")

    @pytest.mark.asyncio
    async def test_debug_rls_status(
        self,
        db_pool: AsyncConnectionPool
    ):
        """Debug test to check RLS status and database role."""
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                # Check what role we're connecting as
                await cur.execute("SELECT current_user, session_user")
                user_result = await cur.fetchone()
                print(f"Current user: {user_result[0]}, Session user: {user_result[1]}")

                # Check if we're a superuser
                await cur.execute("SELECT usesuper FROM pg_user WHERE usename = current_user")
                super_result = await cur.fetchone()
                print(f"Is superuser: {super_result[0] if super_result else 'Unknown'}")

                # Check if RLS is enabled on the table
                await cur.execute("""
                    SELECT relname, relrowsecurity
                    FROM pg_class
                    WHERE relname = 'external_api_connections'
                """)
                rls_result = await cur.fetchone()
                print(f"Table: {rls_result[0]}, RLS enabled: {rls_result[1]}" if rls_result else "Table not found")

                # Check RLS policies
                await cur.execute("""
                    SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
                    FROM pg_policies
                    WHERE tablename = 'external_api_connections'
                """)
                policies = await cur.fetchall()
                print(f"RLS Policies ({len(policies)} found):")
                for policy in policies:
                    print(f"  - {policy[2]}: {policy[5]} for {policy[4]}")
                    print(f"    Qual: {policy[6]}")
                    print(f"    With Check: {policy[7]}")

    @pytest.mark.asyncio
    async def test_comprehensive_rls_debug(
        self,
        db_pool: AsyncConnectionPool,
        test_users: tuple[str, str],
        vault_service_for_user
    ):
        """Comprehensive test to debug RLS behavior step by step."""
        user_a_id, user_b_id = test_users

        # Store tokens for both users using the vault service
        async with vault_service_for_user(user_a_id) as service_a:
            connection_a = await service_a.store_tokens(
                user_a_id,
                'gmail',
                'debug_access_token_a',
                'debug_refresh_token_a',
                scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                service_user_id='debug_user_a',
                service_user_email='debug_a@gmail.com'
            )
            connection_a_id = connection_a['connection_id']

        async with vault_service_for_user(user_b_id) as service_b:
            connection_b = await service_b.store_tokens(
                user_b_id,
                'gmail',
                'debug_access_token_b',
                'debug_refresh_token_b',
                scopes=['https://www.googleapis.com/auth/gmail.readonly'],
                service_user_id='debug_user_b',
                service_user_email='debug_b@gmail.com'
            )
            connection_b_id = connection_b['connection_id']

        # Test 1: User A can access their own tokens
        async with vault_service_for_user(user_a_id) as service_a:
            user_a_tokens = await service_a.get_tokens(user_a_id, 'gmail')
            assert user_a_tokens is not None
            assert user_a_tokens['access_token'] == 'debug_access_token_a'
            assert user_a_tokens['refresh_token'] == 'debug_refresh_token_a'

        # Test 2: User B can access their own tokens
        async with vault_service_for_user(user_b_id) as service_b:
            user_b_tokens = await service_b.get_tokens(user_b_id, 'gmail')
            assert user_b_tokens is not None
            assert user_b_tokens['access_token'] == 'debug_access_token_b'
            assert user_b_tokens['refresh_token'] == 'debug_refresh_token_b'

        # Test 3: Cross-user access should be blocked
        async with vault_service_for_user(user_a_id) as service_a:
            user_b_tokens_from_a = await service_a.get_tokens(user_b_id, 'gmail')
            assert user_b_tokens_from_a is None, "User A should not be able to access User B's tokens"

        async with vault_service_for_user(user_b_id) as service_b:
            user_a_tokens_from_b = await service_b.get_tokens(user_a_id, 'gmail')
            assert user_a_tokens_from_b is None, "User B should not be able to access User A's tokens"

        # Test 4: Verify data exists in database (superuser view)
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT user_id, service_name, service_user_email
                    FROM external_api_connections
                    WHERE service_name = 'gmail' AND service_user_email LIKE 'debug_%'
                    ORDER BY service_user_email
                """)
                all_connections = await cur.fetchall()

                assert len(all_connections) == 2, f"Expected 2 connections, found {len(all_connections)}"

                user_emails = [conn[2] for conn in all_connections]
                assert 'debug_a@gmail.com' in user_emails
                assert 'debug_b@gmail.com' in user_emails
