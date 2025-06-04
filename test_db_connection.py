#!/usr/bin/env python3
"""Test script to check database connection to running dev server."""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

from tests.helpers.gmail_integration_helper import GmailIntegrationTestHelper

async def test_connection():
    """Test connection to dev server database pool."""
    print("🔍 Testing connection to dev server database pool...")
    
    helper = GmailIntegrationTestHelper('test_user')
    
    try:
        db_conn = await helper._get_db_connection()
        print(f"✅ Successfully connected to dev server database pool!")
        print(f"   Connection type: {type(db_conn)}")
        
        # Test a simple query
        async with db_conn.cursor() as cur:
            await cur.execute("SELECT 1 as test")
            result = await cur.fetchone()
            print(f"   Test query result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print(f"   Error type: {type(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1) 