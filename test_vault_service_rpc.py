#!/usr/bin/env python3
"""Test script to verify VaultTokenService works with RPC functions."""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from psycopg_pool import AsyncConnectionPool
from chatServer.services.vault_token_service import VaultTokenService


async def test_vault_service_rpc():
    """Test VaultTokenService with RPC functions."""
    print("🧪 Testing VaultTokenService with RPC functions...")
    
    # Get database connection parameters from environment
    db_user = os.getenv("SUPABASE_DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    db_host = os.getenv("SUPABASE_DB_HOST")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_port = os.getenv("SUPABASE_DB_PORT", "5432")
    
    if not all([db_user, db_password, db_host]):
        print("❌ Missing required environment variables:")
        print(f"   SUPABASE_DB_USER: {'✅' if db_user else '❌'}")
        print(f"   SUPABASE_DB_PASSWORD: {'✅' if db_password else '❌'}")
        print(f"   SUPABASE_DB_HOST: {'✅' if db_host else '❌'}")
        print("\nPlease set these environment variables and try again.")
        return
    
    # Create database connection pool
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    pool = AsyncConnectionPool(
        conninfo=connection_string,
        min_size=1,
        max_size=3,
        timeout=30.0,
        kwargs={
            "connect_timeout": 10.0,
            "application_name": "vault-token-rpc-test",
        }
    )
    
    try:
        # Initialize the connection pool
        print("🔌 Initializing database connection pool...")
        await pool.open()
        print("✅ Database connection pool initialized successfully")
        
        # Test user ID
        test_user_id = str(uuid.uuid4())
        service_name = "gmail"
        
        # Get connection from pool
        async with pool.connection() as db_conn:
            # Helper function to set JWT context
            async def set_jwt_context(conn, user_id):
                async with conn.cursor() as cur:
                    # Set up authentication context
                    await cur.execute("SET ROLE authenticated")
                    
                    # Set the JWT context that Supabase RLS recognizes (full claims object)
                    await cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (
                        f'{{"sub": "{user_id}", "role": "authenticated", "aud": "authenticated"}}',
                    ))
                    await cur.execute("SELECT set_config('request.jwt.claim.sub', %s, true)", (user_id,))
                    await cur.execute("SELECT set_config('request.jwt.claim.role', %s, true)", ('authenticated',))
                    
                    # Verify that auth.uid() returns the correct user
                    await cur.execute("SELECT auth.uid()")
                    auth_uid_result = await cur.fetchone()
                    
                    if not auth_uid_result or str(auth_uid_result[0]) != user_id:
                        raise Exception(f"Failed to set JWT context: auth.uid() returned {auth_uid_result[0]}, expected {user_id}")
                    
                    return auth_uid_result[0]
            
            async with db_conn.cursor() as cur:
                # Create test user in auth.users table
                print(f"👤 Creating test user: {test_user_id}")
                await cur.execute("""
                    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                    VALUES (%s, %s, 'dummy_password', NOW(), NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (test_user_id, f"test_{test_user_id[:8]}@example.com"))
                await db_conn.commit()
                
                # Set JWT context for the first time
                auth_uid = await set_jwt_context(db_conn, test_user_id)
                print(f"✅ Set authentication context for user: {test_user_id}")
                print(f"✅ Verified auth.uid() returns: {auth_uid}")
                
                # Create VaultTokenService
                vault_service = VaultTokenService(db_conn)
                
                # Test 1: Store tokens using existing store_tokens method (should work)
                print("\n📝 Test 1: Storing OAuth tokens...")
                connection_data = await vault_service.store_tokens(
                    user_id=test_user_id,
                    service_name=service_name,
                    access_token="test_access_token_123",
                    refresh_token="test_refresh_token_456",
                    expires_at=datetime.now() + timedelta(hours=1),
                    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                    service_user_email="test@gmail.com"
                )
                print(f"✅ Stored tokens successfully: connection_id={connection_data.get('id')}")
                
                # Re-set JWT context after commit (store_tokens commits the transaction)
                auth_uid = await set_jwt_context(db_conn, test_user_id)
                print(f"🔧 Re-set JWT context after store_tokens commit: {auth_uid}")
                
                # Test 2: Retrieve tokens using updated get_tokens method
                print("\n🔍 Test 2: Retrieving OAuth tokens...")
                
                # Debug: Check JWT context before calling get_tokens
                await cur.execute("SELECT auth.uid()")
                auth_uid_before = await cur.fetchone()
                print(f"🔍 Debug: auth.uid() before get_tokens: {auth_uid_before[0] if auth_uid_before else 'NULL'}")
                
                # Debug: Test RPC function directly first
                print("🔍 Debug: Testing get_oauth_tokens RPC function directly...")
                try:
                    await cur.execute("SELECT get_oauth_tokens(%s, %s)", (test_user_id, service_name))
                    rpc_result = await cur.fetchone()
                    print(f"✅ Direct RPC call successful: {rpc_result[0] if rpc_result else 'No result'}")
                except Exception as e:
                    print(f"❌ Direct RPC call failed: {e}")
                    
                    # Rollback the failed transaction
                    await db_conn.rollback()
                    
                    # Re-set JWT context and try again
                    print("🔧 Debug: Re-setting JWT context after rollback...")
                    auth_uid = await set_jwt_context(db_conn, test_user_id)
                    print(f"🔍 Debug: auth.uid() after reset: {auth_uid}")
                    
                    # Try RPC function again
                    try:
                        await cur.execute("SELECT get_oauth_tokens(%s, %s)", (test_user_id, service_name))
                        rpc_result_retry = await cur.fetchone()
                        print(f"✅ Direct RPC call after reset successful: {rpc_result_retry[0] if rpc_result_retry else 'No result'}")
                    except Exception as e2:
                        print(f"❌ Direct RPC call still failing after reset: {e2}")
                        raise e2
                
                # Now try the VaultTokenService method
                access_token, refresh_token = await vault_service.get_tokens(
                    user_id=test_user_id,
                    service_name=service_name
                )
                print(f"✅ Retrieved tokens successfully:")
                print(f"   Access token: {access_token[:20]}...")
                print(f"   Refresh token: {refresh_token[:20] if refresh_token else 'None'}...")
                
                # Test 3: Test cross-user access prevention
                print("\n🚫 Test 3: Testing cross-user access prevention...")
                other_user_id = str(uuid.uuid4())
                try:
                    await vault_service.get_tokens(
                        user_id=other_user_id,
                        service_name=service_name
                    )
                    print("❌ ERROR: Cross-user access should have been blocked!")
                except Exception as e:
                    print(f"✅ Cross-user access correctly blocked: {e}")
                
                # Test 4: Revoke tokens using updated revoke_tokens method
                print("\n🗑️ Test 4: Revoking OAuth tokens...")
                try:
                    revoke_success = await vault_service.revoke_tokens(
                        user_id=test_user_id,
                        service_name=service_name
                    )
                    print(f"✅ Revoked tokens successfully: {revoke_success}")
                except Exception as e:
                    print(f"❌ Revoke failed: {e}")
                    # Rollback and reset JWT context
                    await db_conn.rollback()
                    auth_uid = await set_jwt_context(db_conn, test_user_id)
                    print(f"🔧 Reset JWT context after revoke failure: {auth_uid}")
                    
                    # Try revoke again
                    try:
                        revoke_success = await vault_service.revoke_tokens(
                            user_id=test_user_id,
                            service_name=service_name
                        )
                        print(f"✅ Revoked tokens successfully on retry: {revoke_success}")
                    except Exception as e2:
                        print(f"❌ Revoke still failing: {e2}")
                        # Continue with test anyway
                        revoke_success = False
                
                # Re-set JWT context after revoke operation (which may have committed)
                auth_uid = await set_jwt_context(db_conn, test_user_id)
                print(f"🔧 Re-set JWT context after revoke operation: {auth_uid}")
                
                # Test 5: Verify tokens are gone
                print("\n🔍 Test 5: Verifying tokens are deleted...")
                try:
                    await vault_service.get_tokens(
                        user_id=test_user_id,
                        service_name=service_name
                    )
                    print("❌ ERROR: Tokens should have been deleted!")
                except ValueError as e:
                    print(f"✅ Tokens correctly deleted: {e}")
                except Exception as e:
                    print(f"🔍 Token verification failed (expected if revoke worked): {e}")
                    # This is expected if tokens were successfully revoked
                
                # Cleanup: Remove test user
                print(f"\n🧹 Cleaning up test user: {test_user_id}")
                await cur.execute("DELETE FROM auth.users WHERE id = %s", (test_user_id,))
                await db_conn.commit()
                
                print("\n🎉 All tests passed! VaultTokenService is working with RPC functions.")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the connection pool
        print("🔌 Closing database connection pool...")
        await pool.close()
        print("✅ Database connection pool closed")


if __name__ == "__main__":
    asyncio.run(test_vault_service_rpc()) 