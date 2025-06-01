"""Integration tests for VaultTokenService with live database connections.

These tests verify Row-Level Security (RLS) policies are working correctly
by using actual database connections and inserting test data.
"""

import pytest
import asyncio
import uuid
import os
import jwt
from datetime import datetime, timedelta
from typing import AsyncGenerator

import psycopg
from psycopg_pool import AsyncConnectionPool

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
        """Factory to create VaultTokenService for a specific user."""
        def _create_service_for_user(user_id: str):
            # Create an async context manager that provides a connection with proper user context
            class UserConnectionManager:
                def __init__(self, pool: AsyncConnectionPool, user_id: str):
                    self.pool = pool
                    self.user_id = user_id
                    self.conn = None
                
                async def __aenter__(self):
                    self.conn = await self.pool.getconn()
                    
                    # Switch to authenticated role and set user context
                    # This is the key to making RLS work properly
                    async with self.conn.cursor() as cur:
                        # Switch from postgres role to authenticated role
                        await cur.execute("SET ROLE authenticated")
                        
                        # Set JWT claims that RLS policies use
                        await cur.execute("SELECT set_config('request.jwt.claims', %s, true)", 
                                        (f'{{"sub": "{self.user_id}", "role": "authenticated"}}',))
                        await cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", 
                                        (self.user_id,))
                        
                        # Verify the role switch worked
                        await cur.execute("SELECT current_user")
                        current_role = await cur.fetchone()
                        print(f"Switched to role: {current_role[0]}")
                        
                        # Verify auth.uid() now returns the correct user
                        await cur.execute("SELECT auth.uid()")
                        auth_uid = await cur.fetchone()
                        print(f"auth.uid() after role switch: {auth_uid[0]}")
                        
                    return self.conn
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self.conn:
                        # Reset role back to original before returning connection to pool
                        try:
                            async with self.conn.cursor() as cur:
                                await cur.execute("RESET ROLE")
                        except Exception as e:
                            print(f"Warning: Failed to reset role: {e}")
                        await self.pool.putconn(self.conn)
            
            return UserConnectionManager(db_pool, user_id)
        
        return _create_service_for_user

    @pytest.mark.asyncio
    async def test_rls_prevents_cross_user_access(
        self, 
        db_pool: AsyncConnectionPool, 
        test_users: tuple[str, str],
        vault_service_for_user
    ):
        """Test that User A cannot access User B's OAuth tokens due to RLS."""
        user_a_id, user_b_id = test_users
        
        # Create test data directly in database (bypassing RLS for setup)
        connection_a_id = str(uuid.uuid4())
        connection_b_id = str(uuid.uuid4())
        
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                # Insert test connections for both users (as superuser, bypassing RLS)
                await cur.execute("""
                    INSERT INTO public.external_api_connections 
                    (id, user_id, service_name, access_token, refresh_token, scopes, 
                     service_user_id, service_user_email, token_expires_at, is_active)
                    VALUES 
                        (%s, %s, 'gmail', 'user_a_access_token', 'user_a_refresh_token', 
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'google_user_a', 'user_a@gmail.com', %s, true),
                        (%s, %s, 'gmail', 'user_b_access_token', 'user_b_refresh_token',
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'google_user_b', 'user_b@gmail.com', %s, true)
                """, (
                    connection_a_id, user_a_id, datetime.now() + timedelta(hours=1),
                    connection_b_id, user_b_id, datetime.now() + timedelta(hours=1)
                ))
                await conn.commit()

        # Test 1: User A can access their own connection
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            user_a_connections = await service_a.list_user_connections(user_a_id)
            assert len(user_a_connections) == 1
            assert str(user_a_connections[0]['id']) == connection_a_id
            assert user_a_connections[0]['service_user_email'] == 'user_a@gmail.com'

        # Test 2: User B can access their own connection  
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            user_b_connections = await service_b.list_user_connections(user_b_id)
            assert len(user_b_connections) == 1
            assert str(user_b_connections[0]['id']) == connection_b_id
            assert user_b_connections[0]['service_user_email'] == 'user_b@gmail.com'

        # Test 3: User A cannot access User B's connections
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            user_a_trying_b = await service_a.list_user_connections(user_b_id)
            assert len(user_a_trying_b) == 0  # RLS should prevent access

        # Test 4: User B cannot access User A's connections
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            user_b_trying_a = await service_b.list_user_connections(user_a_id)
            assert len(user_b_trying_a) == 0  # RLS should prevent access

        # Test 5: User A cannot get User B's connection info
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            user_a_trying_b_info = await service_a.get_connection_info(user_b_id, 'gmail')
            assert user_a_trying_b_info is None  # RLS should prevent access

        # Test 6: User B cannot get User A's connection info
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            user_b_trying_a_info = await service_b.get_connection_info(user_a_id, 'gmail')
            assert user_b_trying_a_info is None  # RLS should prevent access

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
        
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
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
        
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
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
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            retrieved_tokens_a = await service_a.get_tokens(user_a_id, 'gmail')
            assert retrieved_tokens_a[0] == 'user_a_vault_access_token'  # access_token
            assert retrieved_tokens_a[1] == 'user_a_vault_refresh_token'  # refresh_token

        # Test 2: User B can retrieve their own tokens
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            retrieved_tokens_b = await service_b.get_tokens(user_b_id, 'gmail')
            assert retrieved_tokens_b[0] == 'user_b_vault_access_token'  # access_token
            assert retrieved_tokens_b[1] == 'user_b_vault_refresh_token'  # refresh_token

        # Test 3: User A cannot retrieve User B's tokens (should raise ValueError)
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            with pytest.raises(ValueError, match="No gmail connection found"):
                await service_a.get_tokens(user_b_id, 'gmail')

        # Test 4: User B cannot retrieve User A's tokens (should raise ValueError)
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            with pytest.raises(ValueError, match="No gmail connection found"):
                await service_b.get_tokens(user_a_id, 'gmail')

        # Test 5: User A cannot update User B's tokens
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            update_success_a_to_b = await service_a.update_access_token(
                user_b_id, 'gmail', 'malicious_token'
            )
            assert update_success_a_to_b is False  # Should fail due to RLS

        # Test 6: User B cannot update User A's tokens
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            update_success_b_to_a = await service_b.update_access_token(
                user_a_id, 'gmail', 'malicious_token'
            )
            assert update_success_b_to_a is False  # Should fail due to RLS

        # Test 7: User A cannot revoke User B's tokens
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            revoke_success_a_to_b = await service_a.revoke_tokens(user_b_id, 'gmail')
            assert revoke_success_a_to_b is False  # Should fail due to RLS

        # Test 8: User B cannot revoke User A's tokens
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            revoke_success_b_to_a = await service_b.revoke_tokens(user_a_id, 'gmail')
            assert revoke_success_b_to_a is False  # Should fail due to RLS

        # Verify tokens are still intact after attempted cross-user operations
        async with vault_service_for_user(user_a_id) as conn_a:
            service_a = VaultTokenService(conn_a)
            final_tokens_a = await service_a.get_tokens(user_a_id, 'gmail')
            assert final_tokens_a[0] == 'user_a_vault_access_token'  # access_token
        
        async with vault_service_for_user(user_b_id) as conn_b:
            service_b = VaultTokenService(conn_b)
            final_tokens_b = await service_b.get_tokens(user_b_id, 'gmail')
            assert final_tokens_b[0] == 'user_b_vault_access_token'  # access_token

    @pytest.mark.asyncio
    async def test_direct_database_query_bypasses_rls_for_verification(
        self, 
        db_pool: AsyncConnectionPool, 
        test_users: tuple[str, str]
    ):
        """Verify that our test data exists by querying directly (bypassing RLS)."""
        user_a_id, user_b_id = test_users
        
        # Insert test data
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO public.external_api_connections 
                    (user_id, service_name, access_token, scopes, service_user_email, is_active)
                    VALUES 
                        (%s, 'gmail', 'direct_test_token_a', 
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'direct_a@test.com', true),
                        (%s, 'gmail', 'direct_test_token_b',
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'direct_b@test.com', true)
                """, (user_a_id, user_b_id))
                await conn.commit()

        # Query directly without RLS context (as superuser)
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT user_id, service_user_email, access_token 
                    FROM public.external_api_connections 
                    WHERE user_id IN (%s, %s)
                    ORDER BY service_user_email
                """, (user_a_id, user_b_id))
                
                results = await cur.fetchall()
                assert len(results) == 2
                
                # Verify both records exist
                user_emails = [row[1] for row in results]
                assert 'direct_a@test.com' in user_emails
                assert 'direct_b@test.com' in user_emails
                
                # Verify tokens are different
                tokens = [row[2] for row in results]
                assert 'direct_test_token_a' in tokens
                assert 'direct_test_token_b' in tokens

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
        
        # Create test data directly in database (bypassing RLS for setup)
        connection_a_id = str(uuid.uuid4())
        connection_b_id = str(uuid.uuid4())
        
        async with db_pool.connection() as conn:
            async with conn.cursor() as cur:
                # Insert test connections for both users (as superuser, bypassing RLS)
                await cur.execute("""
                    INSERT INTO public.external_api_connections 
                    (id, user_id, service_name, access_token, refresh_token, scopes, 
                     service_user_id, service_user_email, token_expires_at, is_active)
                    VALUES 
                        (%s, %s, 'gmail', 'user_a_access_token', 'user_a_refresh_token', 
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'google_user_a', 'user_a@gmail.com', %s, true),
                        (%s, %s, 'gmail', 'user_b_access_token', 'user_b_refresh_token',
                         ARRAY['https://www.googleapis.com/auth/gmail.readonly'], 
                         'google_user_b', 'user_b@gmail.com', %s, true)
                """, (
                    connection_a_id, user_a_id, datetime.now() + timedelta(hours=1),
                    connection_b_id, user_b_id, datetime.now() + timedelta(hours=1)
                ))
                await conn.commit()
                print(f"Inserted test data: User A ({user_a_id}) -> {connection_a_id}, User B ({user_b_id}) -> {connection_b_id}")

        # Test User A context
        print(f"\n=== Testing User A Context ===")
        async with vault_service_for_user(user_a_id) as conn_a:
            async with conn_a.cursor() as cur:
                # Check auth.uid() in this context
                await cur.execute("SELECT auth.uid()")
                auth_uid_result = await cur.fetchone()
                print(f"auth.uid() in User A context: {auth_uid_result[0]}")
                
                # Query for User A's own connections
                await cur.execute("""
                    SELECT id, user_id, service_user_email, auth.uid() = user_id as rls_match
                    FROM public.external_api_connections 
                    WHERE user_id = %s
                """, (user_a_id,))
                user_a_own = await cur.fetchall()
                print(f"User A querying own connections: {len(user_a_own)} results")
                for row in user_a_own:
                    print(f"  - ID: {row[0]}, User: {row[1]}, Email: {row[2]}, RLS Match: {row[3]}")
                
                # Query for User B's connections (should be blocked by RLS)
                await cur.execute("""
                    SELECT id, user_id, service_user_email, auth.uid() = user_id as rls_match
                    FROM public.external_api_connections 
                    WHERE user_id = %s
                """, (user_b_id,))
                user_a_trying_b = await cur.fetchall()
                print(f"User A querying User B's connections: {len(user_a_trying_b)} results")
                for row in user_a_trying_b:
                    print(f"  - ID: {row[0]}, User: {row[1]}, Email: {row[2]}, RLS Match: {row[3]}")
                
                # Query all connections (should only see User A's due to RLS)
                await cur.execute("""
                    SELECT id, user_id, service_user_email, auth.uid() = user_id as rls_match
                    FROM public.external_api_connections 
                """)
                all_from_a = await cur.fetchall()
                print(f"User A querying all connections: {len(all_from_a)} results")
                for row in all_from_a:
                    print(f"  - ID: {row[0]}, User: {row[1]}, Email: {row[2]}, RLS Match: {row[3]}")

        # Test User B context
        print(f"\n=== Testing User B Context ===")
        async with vault_service_for_user(user_b_id) as conn_b:
            async with conn_b.cursor() as cur:
                # Check auth.uid() in this context
                await cur.execute("SELECT auth.uid()")
                auth_uid_result = await cur.fetchone()
                print(f"auth.uid() in User B context: {auth_uid_result[0]}")
                
                # Query all connections (should only see User B's due to RLS)
                await cur.execute("""
                    SELECT id, user_id, service_user_email, auth.uid() = user_id as rls_match
                    FROM public.external_api_connections 
                """)
                all_from_b = await cur.fetchall()
                print(f"User B querying all connections: {len(all_from_b)} results")
                for row in all_from_b:
                    print(f"  - ID: {row[0]}, User: {row[1]}, Email: {row[2]}, RLS Match: {row[3]}") 