import os
import logging
from core.agent_loader_db import load_agent_executor_db

def test_agent_executor_db():
    # Set these to match an agent and user in your DB
    agent_name = os.getenv("TEST_AGENT_NAME", "your_agent_name")
    user_id = os.getenv("TEST_USER_ID", "test_user")
    session_id = "test_session"

    print(f"Testing DB agent loader for agent: {agent_name}, user: {user_id}")

    try:
        executor = load_agent_executor_db(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            log_level=logging.DEBUG
        )
    except Exception as e:
        print(f"FAILED to load agent executor: {e}")
        raise

    print("Loaded agent executor:", executor)
    print("Loaded tools:")
    for tool in executor.tools:
        print(f"  - Tool: {tool.name} (type: {type(tool).__name__})")
        # Optionally, try to call a simple method if available
        if hasattr(tool, "_run"):
            try:
                # This is just a dry run; adjust arguments as needed for your tools
                result = tool._run(operation="read", agent_id=agent_name)
                print(f"    _run() result: {result}")
            except Exception as tool_exc:
                print(f"    _run() failed: {tool_exc}")

    print("DB agent loader test completed successfully.")

if __name__ == "__main__":
    test_agent_executor_db() 