#!/usr/bin/env python3
"""Test script to verify agent loading with normalized schema."""

import sys
import uuid
sys.path.append('.')

from src.core.agent_loader_db import load_agent_executor_db

def test_agent_loading():
    """Test loading the test_email_digest_agent with normalized schema."""
    try:
        print("🔄 Testing agent loading with normalized schema...")
        
        agent_executor = load_agent_executor_db(
            agent_name='test_email_digest_agent',
            user_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4())
        )
        
        print(f"✅ Agent loaded successfully!")
        print(f"✅ Number of tools: {len(agent_executor.tools)}")
        
        # Verify expected tools are present
        tool_names = [tool.name for tool in agent_executor.tools]
        expected_tools = ['gmail_digest', 'gmail_search']
        
        for expected_tool in expected_tools:
            if expected_tool in tool_names:
                print(f"✅ Tool '{expected_tool}' found")
            else:
                print(f"❌ Tool '{expected_tool}' missing")
        
        # Show all loaded tools
        print("\n📋 All loaded tools:")
        for tool in agent_executor.tools:
            print(f"  - {tool.name} ({type(tool).__name__})")
        
        print("\n🎉 Normalized schema test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_loading()
    sys.exit(0 if success else 1) 