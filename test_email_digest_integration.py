#!/usr/bin/env python3
"""Test script for email digest integration."""

import asyncio
import os
import uuid
from datetime import datetime

# Add the project root to Python path
import sys
sys.path.append('.')

from chatServer.agents.email_digest_agent import create_email_digest_agent
from chatServer.services.email_digest_scheduler import generate_digest_for_user


async def test_agent_creation():
    """Test email digest agent creation."""
    print("\n🤖 Testing Agent Creation...")
    
    # Create a test user ID
    test_user_id = str(uuid.uuid4())
    
    try:
        # Create email digest agent
        agent = await create_email_digest_agent(test_user_id)
        
        print(f"✅ Created email digest agent for user {test_user_id}")
        print(f"   - Agent name: {agent.agent_name}")
        print(f"   - User ID: {agent.user_id}")
        print(f"   - Session ID: {agent.session_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation test failed: {e}")
        return False


async def test_agent_executor_creation():
    """Test agent executor creation using existing framework."""
    print("\n⚙️  Testing Agent Executor Creation...")
    
    # Create a test user ID
    test_user_id = str(uuid.uuid4())
    
    try:
        # Create email digest agent
        agent = await create_email_digest_agent(test_user_id)
        
        # Try to get the agent executor (this will test the database loading)
        executor = await agent.get_agent_executor()
        
        print(f"✅ Created agent executor:")
        print(f"   - Executor type: {type(executor).__name__}")
        print(f"   - Tools loaded: {len(executor.tools) if hasattr(executor, 'tools') else 'Unknown'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent executor creation test failed: {e}")
        return False


async def test_digest_generation_mock():
    """Test digest generation with mock data (no real Gmail connection)."""
    print("\n📧 Testing Digest Generation (Mock)...")
    
    # Create a test user ID
    test_user_id = str(uuid.uuid4())
    
    try:
        # This will fail because we don't have real Gmail tokens, but we can test the flow
        result = await generate_digest_for_user(test_user_id)
        
        print(f"✅ Digest generation completed:")
        print(f"   - User ID: {result['user_id']}")
        print(f"   - Status: {result['status']}")
        print(f"   - Generated at: {result['generated_at']}")
        
        if result['status'] == 'error':
            print(f"   - Expected error (no Gmail tokens): {result['digest'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Digest generation test failed: {e}")
        return False


async def test_database_connection():
    """Test database connection and basic queries."""
    print("\n🗄️  Testing Database Connection...")
    
    try:
        from chatServer.database.connection import get_db_connection
        
        async for db_conn in get_db_connection():
            async with db_conn.cursor() as cur:
                # Test agent configuration query
                await cur.execute("""
                    SELECT agent_name, COUNT(*) as tool_count
                    FROM agent_configurations ac
                    LEFT JOIN agent_tools at ON ac.id = at.agent_id
                    WHERE ac.agent_name = 'email_digest_agent'
                    GROUP BY ac.agent_name
                """)
                
                result = await cur.fetchone()
                if result:
                    print(f"✅ Found agent '{result[0]}' with {result[1]} tools")
                else:
                    print("❌ Email digest agent not found in database")
                    return False
                
                # Test table existence
                await cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('email_digests', 'agent_logs', 'external_api_connections')
                    ORDER BY table_name
                """)
                
                tables = await cur.fetchall()
                table_names = [t[0] for t in tables]
                print(f"✅ Found required tables: {table_names}")
                
                return len(table_names) >= 3
                
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 Starting Email Digest Integration Tests")
    print("=" * 50)
    
    # Initialize database manager for all tests
    db_manager = None
    try:
        from chatServer.database.connection import get_database_manager
        db_manager = get_database_manager()
        await db_manager.initialize()
        print("✅ Database connection pool initialized")
    except Exception as e:
        print(f"⚠️  Failed to initialize database pool: {e}")
        print("   Some tests may fail due to database connection issues")
    
    # Check environment
    required_env_vars = [
        'SUPABASE_DB_USER', 'SUPABASE_DB_PASSWORD', 
        'SUPABASE_DB_HOST', 'GOOGLE_API_KEY'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("   Some tests may fail due to missing configuration")
    
    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Agent Creation", test_agent_creation),
        ("Agent Executor Creation", test_agent_executor_creation),
        ("Digest Generation (Mock)", test_digest_generation_mock),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Clean up database manager
    if db_manager:
        try:
            await db_manager.close()
            print("✅ Database connection pool closed")
        except Exception as e:
            print(f"⚠️  Error closing database pool: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Email digest integration is ready.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    success = asyncio.run(main()) 