import logging
import os
import unittest
import uuid
from contextlib import AsyncExitStack  # Import AsyncExitStack
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig  # For type hinting if needed by Fake
from langchain_postgres import PostgresChatMessageHistory  # Import for spec

from chatServer.main import (  # Import get_db_connection for override key and get_agent_loader
    app,
    get_agent_loader,
    get_db_connection,
)
from src.core.agents.customizable_agent import CustomizableAgentExecutor

TEST_USER_ID = "test-user-123"
MOCK_JWT_SECRET = "test-super-secret-key-for-testing-only"
MOCK_JWT_PAYLOAD = {"sub": TEST_USER_ID, "aud": "authenticated"}

def create_mock_jwt(payload: Dict[str, Any] = MOCK_JWT_PAYLOAD, secret: str = MOCK_JWT_SECRET, algorithm: str = "HS256") -> str:  # noqa: E501
    return f"mock_jwt_for_{payload.get('sub', 'unknown_user')}"

# Define a Fake CustomizableAgentExecutor for testing
class FakeCustomizableAgentExecutor(CustomizableAgentExecutor):
    # Allow extra fields for our test attributes
    model_config = {"extra": "allow"}

    def __init__(self, **kwargs): # Accept any kwargs to be flexible
        # Create a minimal Runnable agent that satisfies Pydantic validation
        from langchain_core.runnables import RunnableLambda

        # Create a simple runnable that just returns a mock response
        def mock_agent_function(inputs):
            return {"output": "Mocked agent response"}

        mock_agent_runnable = RunnableLambda(mock_agent_function)

        # Initialize with the valid runnable agent first
        super().__init__(agent=mock_agent_runnable, tools=[])

        # Now set our test-specific attributes using object.__setattr__ to bypass Pydantic
        object.__setattr__(self, 'mock_ainvoke_result', {"output": "Mocked AI response from FakeExecutor"})
        object.__setattr__(self, 'ainvoke_call_history', [])

    async def ainvoke(self, inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        # First call the parent's ainvoke to ensure chat_history is added
        # But we don't want to actually execute the agent, so we'll intercept before super().ainvoke
        if "chat_history" not in inputs:
            inputs["chat_history"] = []

        # Simulate loading existing chat history from memory if the executor has memory
        if hasattr(self, 'memory') and self.memory is not None:
            try:
                # Try to load existing messages from the memory's chat_memory
                if hasattr(self.memory, 'chat_memory') and hasattr(self.memory.chat_memory, 'aget_messages'):
                    existing_messages = await self.memory.chat_memory.aget_messages()
                    if existing_messages:
                        inputs["chat_history"] = existing_messages
            except Exception:
                # If memory loading fails, just use empty chat_history
                pass

        # Record the call with the processed inputs (including chat_history)
        self.ainvoke_call_history.append(inputs.copy())

        # Simulate the behavior of the actual ainvoke if needed for specific tests
        if hasattr(self, '_custom_ainvoke_side_effect') and self._custom_ainvoke_side_effect:
            if isinstance(self._custom_ainvoke_side_effect, Exception):
                raise self._custom_ainvoke_side_effect
            return self._custom_ainvoke_side_effect(inputs)
        return self.mock_ainvoke_result

    # Add other methods/attributes if main.py checks for them on the agent_executor instance

class TestChatEndpoint(unittest.IsolatedAsyncioTestCase):
    async def mock_db_connection_generator(self): # Define it as a method or static method
        yield self.mock_db_conn_instance

    async def asyncSetUp(self):
        self.stack = AsyncExitStack()

        # Mock lifespan dependencies to avoid real DB/Telegram/cache initialization
        self._lifespan_patches = []

        # Mock database manager
        mock_db_manager = AsyncMock()
        p1 = patch('chatServer.database.connection.get_database_manager', return_value=mock_db_manager)

        # Mock supabase manager
        mock_supabase_manager = AsyncMock()
        mock_supabase_manager.get_client.return_value = MagicMock()
        p2 = patch('chatServer.database.supabase_client.get_supabase_manager', return_value=mock_supabase_manager)

        # Mock tool cache
        p3 = patch('chatServer.services.tool_cache_service.initialize_tool_cache', new_callable=AsyncMock)
        p4 = patch('chatServer.services.tool_cache_service.shutdown_tool_cache', new_callable=AsyncMock)

        # Mock agent config cache
        p3a = patch('chatServer.services.agent_config_cache_service.initialize_agent_config_cache', new_callable=AsyncMock)  # noqa: E501
        p4a = patch('chatServer.services.agent_config_cache_service.shutdown_agent_config_cache', new_callable=AsyncMock)  # noqa: E501

        # Mock user instructions cache
        p3b = patch('chatServer.services.user_instructions_cache_service.initialize_user_instructions_cache', new_callable=AsyncMock)  # noqa: E501
        p4b = patch('chatServer.services.user_instructions_cache_service.shutdown_user_instructions_cache', new_callable=AsyncMock)  # noqa: E501

        # Mock background task service
        mock_bg_service = MagicMock()
        mock_bg_service.stop_background_tasks = AsyncMock()
        p5 = patch('chatServer.services.background_tasks.get_background_task_service', return_value=mock_bg_service)

        for p in [p1, p2, p3, p4, p3a, p4a, p3b, p4b, p5]:
            self._lifespan_patches.append(p)
            p.start()

        # Ensure telegram_bot_token is None so telegram init is skipped
        from chatServer.config.settings import get_settings
        self._settings = get_settings()
        self._orig_telegram_token = self._settings.telegram_bot_token
        self._settings.telegram_bot_token = None

        self.app_lifespan_context = await self.stack.enter_async_context(app.router.lifespan_context(app))

        self.patcher_os_environ = patch.dict(os.environ, {
            "SUPABASE_JWT_SECRET": MOCK_JWT_SECRET
        })
        self.patcher_os_environ.start()
        self.addAsyncCleanup(self.patcher_os_environ.stop)

        # Mock for the database connection instance that will be yielded
        self.mock_db_conn_instance = AsyncMock()

        # Override the get_db_connection dependency
        app.dependency_overrides[get_db_connection] = self.mock_db_connection_generator

        # Create a mock agent loader module
        self.mock_agent_loader = MagicMock(spec=['load_agent_executor'])
        self.fake_agent_executor_instance = FakeCustomizableAgentExecutor()
        self.mock_agent_loader.load_agent_executor.return_value = self.fake_agent_executor_instance

        # Override the get_agent_loader dependency
        app.dependency_overrides[get_agent_loader] = lambda: self.mock_agent_loader

        self.client = TestClient(app)

        # Patch PostgresChatMessageHistory class and its instance
        self.patch_chat_message_history_class = patch('chatServer.services.chat.PostgresChatMessageHistory', autospec=True)  # noqa: E501
        self.mock_postgres_chat_history_class = self.patch_chat_message_history_class.start() # This is the mock of the CLASS  # noqa: E501
        self.addAsyncCleanup(self.patch_chat_message_history_class.stop)

        # Create an instance mock that *is an instance of* PostgresChatMessageHistory (due to autospec on class)
        # or by explicit spec here.
        self.mock_chat_history_instance = MagicMock(spec_set=PostgresChatMessageHistory) # Use spec_set for stricter instance checking  # noqa: E501
        self.mock_chat_history_instance.aget_messages = AsyncMock(return_value=[])
        self.mock_chat_history_instance.aadd_messages = AsyncMock()
        # Ensure the mocked CLASS returns our mocked INSTANCE
        self.mock_postgres_chat_history_class.return_value = self.mock_chat_history_instance

        self.patch_jwt_decode = patch('jose.jwt.decode')
        self.mock_jwt_decode = self.patch_jwt_decode.start()
        self.addAsyncCleanup(self.patch_jwt_decode.stop)
        self.mock_jwt_decode.return_value = MOCK_JWT_PAYLOAD

        from chatServer import main as chat_main_module
        if hasattr(chat_main_module, 'AGENT_EXECUTOR_CACHE'):
            chat_main_module.AGENT_EXECUTOR_CACHE.clear()

        # Reset the global chat service instance to ensure fresh state
        import chatServer.services.chat
        chatServer.services.chat._chat_service = None

        # Removed the direct patch of get_db_connection, using dependency_overrides instead

        self.test_session_id = str(uuid.uuid4())
        self.auth_headers = {"Authorization": f"Bearer {create_mock_jwt()}"}

    async def asyncTearDown(self):
        # Clean up dependency overrides
        app.dependency_overrides.pop(get_db_connection, None)
        app.dependency_overrides.pop(get_agent_loader, None)

        await self.stack.aclose()

        # Stop lifespan patches
        for p in self._lifespan_patches:
            p.stop()

        # Restore telegram token
        self._settings.telegram_bot_token = self._orig_telegram_token

    # Test methods remain synchronous as TestClient makes synchronous calls
    def test_chat_new_session_cache_miss(self):
        agent_name = "test_agent_new"
        message = "Hello, new agent!"

        # Reset ainvoke result for this specific test if needed, or set a default in Fake's init
        object.__setattr__(self.fake_agent_executor_instance, 'mock_ainvoke_result', {"output": "Mocked AI response"})
        object.__setattr__(self.fake_agent_executor_instance, 'ainvoke_call_history', [])

        # Ensure the cache is empty before the test
        from chatServer import main as chat_main_module
        chat_main_module.AGENT_EXECUTOR_CACHE.clear()

        response = self.client.post(
            "/api/chat",
            headers=self.auth_headers,
            json={"agent_name": agent_name, "message": message, "session_id": self.test_session_id}
        )

        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertEqual(data["session_id"], self.test_session_id)
        self.assertEqual(data["response"], "Mocked AI response")

        self.mock_agent_loader.load_agent_executor.assert_called_once_with(
            user_id=TEST_USER_ID,
            agent_name=agent_name,
            session_id=self.test_session_id,
            log_level=logging.INFO
        )

        self.mock_postgres_chat_history_class.assert_called_once()
        args, kwargs = self.mock_postgres_chat_history_class.call_args
        self.assertEqual(args[0], "chat_message_history")
        self.assertEqual(args[1], self.test_session_id)
        # The async_connection argument for PostgresChatMessageHistory would come from the get_db_connection dependency.
        # We need to ensure the mock_db_conn_instance is what's passed.
        # This depends on how the dependency injection provides the connection.
        # If get_db_connection is a context manager, its __aenter__ result is used.
        # If it's a simple async def, its return value is used.
        # Given the mock setup for get_db_connection_dependency, it provides an async generator.
        # FastAPI will iterate this once to get the value.
        self.assertEqual(kwargs.get('async_connection'), self.mock_db_conn_instance)

        # The cache will store the FakeCustomizableAgentExecutor instance
        # Note: With ChatService, the cache is managed by the service, so we check if it was populated
        cached_item = chat_main_module.AGENT_EXECUTOR_CACHE.get((TEST_USER_ID, agent_name))
        # The ChatService should have cached the executor after loading it
        self.assertIsNotNone(cached_item, "Agent executor should be cached after first load")

        self.assertEqual(len(self.fake_agent_executor_instance.ainvoke_call_history), 1)
        ainvoke_call_args = self.fake_agent_executor_instance.ainvoke_call_history[0]
        self.assertEqual(ainvoke_call_args["input"], message)
        self.assertIn("chat_history", ainvoke_call_args)

        # Note: aadd_messages is not called because our FakeCustomizableAgentExecutor
        # doesn't go through the full agent execution path that would trigger memory saving
        # self.mock_chat_history_instance.aadd_messages.assert_called_once()

    def test_chat_existing_session_cache_hit(self):
        agent_name = "test_agent_cached"
        message = "Hello again, cached agent!"

        from chatServer import main as chat_main_module
        # Use the Fake executor for caching as well
        cached_fake_executor = FakeCustomizableAgentExecutor()
        object.__setattr__(cached_fake_executor, 'mock_ainvoke_result', {"output": "Cached AI response"})
        object.__setattr__(cached_fake_executor, 'ainvoke_call_history', [])

        # Set up existing messages that should be loaded from memory
        existing_messages = [
            HumanMessage(content="First message"),
            AIMessage(content="First AI reply")
        ]

        # Update the mock to return existing messages for this test
        self.mock_chat_history_instance.aget_messages = AsyncMock(return_value=existing_messages)

        # Create a mock memory object that the cached executor will use
        mock_memory = MagicMock()
        mock_memory.chat_memory = self.mock_chat_history_instance
        object.__setattr__(cached_fake_executor, 'memory', mock_memory)

        # Pre-populate the cache with our cached executor
        chat_main_module.AGENT_EXECUTOR_CACHE[(TEST_USER_ID, agent_name)] = cached_fake_executor

        response = self.client.post(
            "/api/chat",
            headers=self.auth_headers,
            json={"agent_name": agent_name, "message": message, "session_id": self.test_session_id}
        )

        self.assertEqual(response.status_code, 200, response.json())
        data = response.json()
        self.assertEqual(data["response"], "Cached AI response")

        # Verify that the agent loader was not called (cache hit)
        self.mock_agent_loader.load_agent_executor.assert_not_called()

        # Verify that the cached executor was used
        self.assertEqual(len(cached_fake_executor.ainvoke_call_history), 1)
        ainvoke_call_args = cached_fake_executor.ainvoke_call_history[0]
        self.assertEqual(ainvoke_call_args["input"], message)
        self.assertEqual(len(ainvoke_call_args["chat_history"]), len(existing_messages))
        for i, msg in enumerate(existing_messages):
            self.assertEqual(ainvoke_call_args["chat_history"][i].content, msg.content)
            self.assertEqual(ainvoke_call_args["chat_history"][i].type, msg.type)

    def test_chat_missing_session_id(self):
        response = self.client.post(
            "/api/chat",
            headers=self.auth_headers,
            json={"agent_name": "test_agent", "message": "This will fail"}
        )
        self.assertEqual(response.status_code, 422)

    def test_chat_agent_load_failure(self):
        self.mock_agent_loader.load_agent_executor.side_effect = Exception("Failed to load agent")
        # Reset ainvoke result for this specific test if needed, or set a default in Fake's init
        self.fake_agent_executor_instance.mock_ainvoke_result = {"output": "Mocked AI response"}

        response = self.client.post(
            "/api/chat",
            headers=self.auth_headers,
            json={"agent_name": "failing_agent", "message": "test", "session_id": self.test_session_id}
        )
        self.assertEqual(response.status_code, 500, response.json())
        data = response.json()
        self.assertIn("Could not load agent", data["detail"])
        self.assertIn("Failed to load agent", data["detail"])

    def test_chat_agent_ainvoke_failure(self):
        # Configure the fake_agent_executor_instance (returned by the loader) to raise an error
        self.fake_agent_executor_instance._custom_ainvoke_side_effect = Exception("Agent execution error")
        self.fake_agent_executor_instance.ainvoke_call_history = []

        response = self.client.post(
            "/api/chat",
            headers=self.auth_headers,
            json={"agent_name": "erroring_agent", "message": "test", "session_id": self.test_session_id}
        )
        self.assertEqual(response.status_code, 200) # Endpoint is expected to return 200 with error in body
        data = response.json()
        self.assertEqual(data["response"], "An error occurred processing your request.")
        self.assertIn("Agent execution error", data["error"])

if __name__ == '__main__':
    unittest.main()
