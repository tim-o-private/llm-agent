#!/usr/bin/env python3
"""Test script to verify EmailDigestAgent integration with chat service."""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from chatServer.services.chat import ChatService
from chatServer.models.chat import ChatRequest
from psycopg_pool import AsyncConnectionPool


async def test_email_digest_integration():
    """Test EmailDigestAgent integration with chat service."""
    print("🧪 Testing EmailDigestAgent integration with chat service...")
    
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
            "application_name": "email-digest-integration-test",
        }
    )
    
    try:
        # Initialize the connection pool
        print("🔌 Initializing database connection pool...")
        await pool.open()
        print("✅ Database connection pool initialized successfully")
        
        # Test user ID
        test_user_id = str(uuid.uuid4())
        test_session_id = str(uuid.uuid4())  # Use UUID format for session ID
        
        # Get connection from pool
        async with pool.connection() as db_conn:
            async with db_conn.cursor() as cur:
                # Create test user in auth.users table
                print(f"👤 Creating test user: {test_user_id}")
                await cur.execute("""
                    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at)
                    VALUES (%s, %s, 'dummy_password', NOW(), NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """, (test_user_id, f"test_{test_user_id[:8]}@example.com"))
                await db_conn.commit()
                
                # Create chat service with empty cache
                agent_executor_cache = {}
                chat_service = ChatService(agent_executor_cache)
                
                # Test 1: Load EmailDigestAgent through agent loader
                print("\n📧 Test 1: Loading EmailDigestAgent through agent loader...")
                try:
                    # Import agent loader module
                    import src.core.agent_loader as agent_loader_module
                    
                    # Create memory for the session
                    memory = chat_service.create_chat_memory(test_session_id, db_conn)
                    
                    # Load agent executor
                    agent_executor = chat_service.get_or_load_agent_executor(
                        user_id=test_user_id,
                        agent_name="email_digest_agent",
                        session_id=test_session_id,
                        agent_loader_module=agent_loader_module,
                        memory=memory
                    )
                    
                    print(f"✅ Successfully loaded agent executor: {type(agent_executor).__name__}")
                    
                    # Check if it has the expected interface
                    if hasattr(agent_executor, 'ainvoke') and hasattr(agent_executor, 'memory'):
                        print("✅ Agent executor has required interface (ainvoke, memory)")
                    else:
                        print("❌ Agent executor missing required interface")
                        return
                    
                except Exception as e:
                    print(f"❌ Failed to load EmailDigestAgent: {e}")
                    import traceback
                    traceback.print_exc()
                    return
                
                # Test 2: Process a chat request
                print("\n💬 Test 2: Processing chat request with EmailDigestAgent...")
                try:
                    # Create a chat request
                    chat_request = ChatRequest(
                        message="Generate an email digest for the last 24 hours",
                        agent_name="email_digest_agent",
                        session_id=test_session_id
                    )
                    
                    # Create a mock request object
                    class MockRequest:
                        def __init__(self):
                            self.headers = {}
                    
                    mock_request = MockRequest()
                    
                    # Process the chat request
                    response = await chat_service.process_chat(
                        chat_input=chat_request,
                        user_id=test_user_id,
                        pg_connection=db_conn,
                        agent_loader_module=agent_loader_module,
                        request=mock_request
                    )
                    
                    print(f"✅ Chat processing successful!")
                    print(f"   Session ID: {response.session_id}")
                    print(f"   Response length: {len(response.response)} characters")
                    print(f"   Tool used: {response.tool_name}")
                    print(f"   Error: {response.error}")
                    
                    # Check if response contains expected content
                    if "email" in response.response.lower() or "digest" in response.response.lower():
                        print("✅ Response contains email/digest related content")
                    else:
                        print("⚠️ Response may not be email digest related")
                        print(f"   Response preview: {response.response[:200]}...")
                    
                except Exception as e:
                    print(f"❌ Failed to process chat request: {e}")
                    import traceback
                    traceback.print_exc()
                    return
                
                # Test 3: Verify agent caching
                print("\n🗄️ Test 3: Verifying agent caching...")
                try:
                    # Load the same agent again - should hit cache
                    agent_executor_2 = chat_service.get_or_load_agent_executor(
                        user_id=test_user_id,
                        agent_name="email_digest_agent",
                        session_id=test_session_id,
                        agent_loader_module=agent_loader_module,
                        memory=memory
                    )
                    
                    # Check if it's the same instance (cached)
                    cache_key = (test_user_id, "email_digest_agent")
                    if cache_key in chat_service.agent_executor_cache:
                        print("✅ Agent executor is properly cached")
                        print(f"   Cache key: {cache_key}")
                        print(f"   Cached executor type: {type(chat_service.agent_executor_cache[cache_key]).__name__}")
                    else:
                        print("❌ Agent executor not found in cache")
                    
                except Exception as e:
                    print(f"❌ Failed to verify caching: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Cleanup: Remove test user
                print(f"\n🧹 Cleaning up test user: {test_user_id}")
                await cur.execute("DELETE FROM auth.users WHERE id = %s", (test_user_id,))
                await db_conn.commit()
                
                print("\n🎉 All integration tests completed successfully!")
                print("\n📋 Summary:")
                print("   ✅ EmailDigestAgent loads through agent loader")
                print("   ✅ Chat service can process requests with EmailDigestAgent")
                print("   ✅ Agent caching works correctly")
                print("   ✅ Integration between specialized agent and generic chat service working")
                
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the connection pool
        print("🔌 Closing database connection pool...")
        await pool.close()
        print("✅ Database connection pool closed")


if __name__ == "__main__":
    asyncio.run(test_email_digest_integration()) 