import asyncio
from ai.agent_orchestrator import AgentOrchestrator
from chat_types.chat import ChatResponse, AgentAction

async def test_simple():
    """Test with a simple mock response"""
    try:
        # Create a simple mock response
        response = ChatResponse(
            message="Hello! I'm working correctly through the router.",
            actions=[
                AgentAction(
                    type="response",
                    data={"message": "Router test successful"},
                    status="completed"
                )
            ],
            metadata={
                "agent_name": "test",
                "session_id": "test-session",
                "user_id": "test-user",
                "timestamp": "2025-01-30T00:00:00Z",
                "success": True
            }
        )
        print("Mock response created successfully")
        print("Message:", response.message)
        print("Actions:", len(response.actions))
        return response
    except Exception as e:
        print("Error creating mock response:", str(e))
        import traceback
        traceback.print_exc()

async def test_orchestrator():
    """Test the actual orchestrator with a timeout"""
    orchestrator = AgentOrchestrator("test-user")
    try:
        # Test with a timeout
        response = await asyncio.wait_for(
            orchestrator.process_message("Hello", "test-session"),
            timeout=10.0  # 10 second timeout
        )
        print("Orchestrator Success:", response.message[:100])
        print("Actions:", len(response.actions))
        return response
    except asyncio.TimeoutError:
        print("Orchestrator timed out after 10 seconds")
        return None
    except Exception as e:
        print("Orchestrator Error:", str(e))
        return None

async def main():
    print("=== Testing Mock Response ===")
    await test_simple()
    
    print("\n=== Testing Orchestrator ===")
    await test_orchestrator()

if __name__ == "__main__":
    asyncio.run(main()) 