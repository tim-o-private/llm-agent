import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import uuid

# Assuming main.py is in chatServer directory, adjust import path as necessary
# This might require adding chatServer's parent to PYTHONPATH for tests to run
from chatServer.main import app, serialize_message_for_cache, deserialize_message_from_cache, server_session_cache
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

class TestChatAPILogic(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Clear server_session_cache before each test
        server_session_cache.clear()

        # Mock dependencies of the /api/chat endpoint
        self.mock_get_agent_config = patch('chatServer.main.get_agent_config').start()
        self.mock_load_agent_executor = patch('chatServer.main.load_agent_executor').start()
        self.mock_prompt_manager_service_get = patch('chatServer.main.prompt_manager_service.get_active_customizations_for_agent').start()

        # Configure default mock returns
        self.mock_get_agent_config.return_value = MagicMock() # Simulate a valid agent config
        self.mock_agent_executor_instance = MagicMock()
        self.mock_agent_executor_instance.ainvoke = AsyncMock(return_value={"output": "Mocked AI response"})
        self.mock_load_agent_executor.return_value = self.mock_agent_executor_instance
        self.mock_prompt_manager_service_get.return_value = None # No custom instructions by default
        
        # Mock JWT authentication (get_current_user dependency)
        # This assumes get_current_user is used as a dependency in your endpoint
        # and that it relies on request.state.user_id being set by some middleware.
        # A more direct way might be to patch get_current_user itself if it's complex.
        # For now, we'll simulate a valid token and user_id via a simplified patch
        # or by ensuring the TestClient can pass headers.

        # We need a way to simulate an authenticated user for the TestClient.
        # The simplest is to patch the `get_current_user` dependency if it's directly used by endpoint.
        # If auth is via request.state.user_id, we might need a middleware patch or helper.
        # Let's assume for now we can patch the underlying auth mechanism if needed,
        # or that tests run with a simplified auth for /api/chat.
        # For this example, we will assume get_current_user is patched if it's a direct FastAPI dependency.
        # If it's based on request.headers, we set it in TestClient calls.
        self.test_user_id = "test-user-id-123"
        # This is a common way to provide a fake token for testing purposes.
        # The actual JWT validation logic is assumed to be tested elsewhere or mocked robustly.
        self.fake_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQtMTIzIn0.faketokenpart"
        self.auth_headers = {"Authorization": f"Bearer {self.fake_jwt_token}"}
        
        # Patch the get_current_user dependency for all tests in this class
        self.get_current_user_patcher = patch('chatServer.main.get_current_user')
        self.mock_get_current_user = self.get_current_user_patcher.start()
        self.mock_get_current_user.return_value = self.test_user_id

    def tearDown(self):
        patch.stopall()
        self.get_current_user_patcher.stop()

    def test_chat_new_session(self):
        agent_id = "test_agent"
        message = "Hello, agent!"
        
        response = self.client.post(
            "/api/chat", 
            json={"agent_id": agent_id, "message": message},
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data['session_id'])
        self.assertEqual(data['response'], "Mocked AI response")
        self.assertTrue(data['session_id'] in server_session_cache) # Verify session is cached
        self.assertEqual(len(server_session_cache[data['session_id']]), 2) # Human msg + AI msg

    def test_chat_existing_session_uses_cache(self):
        agent_id = "test_agent"
        session_id = str(uuid.uuid4())
        initial_human_msg = HumanMessage(content="First message")
        initial_ai_msg = AIMessage(content="First AI response")
        server_session_cache[session_id] = [
            serialize_message_for_cache(initial_human_msg),
            serialize_message_for_cache(initial_ai_msg)
        ]

        new_message = "Second message"
        response = self.client.post(
            "/api/chat", 
            json={"agent_id": agent_id, "message": new_message, "session_id": session_id},
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['session_id'], session_id)
        self.assertEqual(len(server_session_cache[session_id]), 4) # 2 initial + 2 new

        # Verify that agent was called with reconstructed history
        call_args = self.mock_agent_executor_instance.ainvoke.call_args
        self.assertIsNotNone(call_args)
        invoked_history = call_args[0][0]['chat_history'] # First arg of first call, then 'chat_history' key
        self.assertEqual(len(invoked_history), 2)
        self.assertIsInstance(invoked_history[0], HumanMessage)
        self.assertEqual(invoked_history[0].content, initial_human_msg.content)
        self.assertIsInstance(invoked_history[1], AIMessage)
        self.assertEqual(invoked_history[1].content, initial_ai_msg.content)

    def test_cache_trimming(self):
        # This test will depend on MAX_CACHE_HISTORY_LENGTH in main.py
        from chatServer.main import MAX_CACHE_HISTORY_LENGTH
        agent_id = "test_agent"
        session_id = str(uuid.uuid4())
        
        # Populate cache beyond MAX_CACHE_HISTORY_LENGTH
        initial_messages = []
        for i in range(MAX_CACHE_HISTORY_LENGTH + 5):
            initial_messages.append(serialize_message_for_cache(HumanMessage(content=f"Old msg {i}")))
            initial_messages.append(serialize_message_for_cache(AIMessage(content=f"Old AI resp {i}")))
        server_session_cache[session_id] = initial_messages
        
        # Send a new message that will trigger cache update and trimming
        response = self.client.post(
            "/api/chat", 
            json={"agent_id": agent_id, "message": "New message", "session_id": session_id},
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(server_session_cache[session_id]), MAX_CACHE_HISTORY_LENGTH)

    def test_message_serialization_deserialization(self):
        human_msg = HumanMessage(content="Hello", additional_kwargs={"user": "test"})
        ai_msg = AIMessage(content="Hi", additional_kwargs={"confidence": 0.9}, tool_calls=[{"name": "search", "args": {"query": "weather"}, "id": "tool_123"}])
        tool_msg = ToolMessage(content="Sunny", tool_call_id="tool_123", name="search")

        serialized_human = serialize_message_for_cache(human_msg)
        serialized_ai = serialize_message_for_cache(ai_msg)
        serialized_tool = serialize_message_for_cache(tool_msg)

        self.assertEqual(serialized_human['type'], 'human')
        self.assertEqual(serialized_ai['type'], 'ai')
        self.assertEqual(serialized_tool['type'], 'tool')

        deserialized_human = deserialize_message_from_cache(serialized_human)
        deserialized_ai = deserialize_message_from_cache(serialized_ai)
        deserialized_tool = deserialize_message_from_cache(serialized_tool)

        self.assertIsInstance(deserialized_human, HumanMessage)
        self.assertEqual(deserialized_human.content, human_msg.content)
        self.assertEqual(deserialized_human.additional_kwargs, human_msg.additional_kwargs)

        self.assertIsInstance(deserialized_ai, AIMessage)
        self.assertEqual(deserialized_ai.content, ai_msg.content)
        self.assertEqual(deserialized_ai.additional_kwargs, ai_msg.additional_kwargs)
        self.assertEqual(len(deserialized_ai.tool_calls), 1)
        self.assertEqual(deserialized_ai.tool_calls[0]['id'], "tool_123")

        self.assertIsInstance(deserialized_tool, ToolMessage)
        self.assertEqual(deserialized_tool.content, tool_msg.content)
        self.assertEqual(deserialized_tool.tool_call_id, tool_msg.tool_call_id)
        self.assertEqual(deserialized_tool.name, tool_msg.name)

    def test_archive_messages_endpoint_placeholder(self):
        # This is just to ensure the endpoint exists and returns success for now
        # Actual DB interaction would need more involved mocking or a test DB.
        session_id = str(uuid.uuid4())
        payload = {
            "session_id": session_id,
            "messages_batch": [serialize_message_for_cache(HumanMessage(content="Msg 1"))]
        }
        response = self.client.post("/api/chat/session/archive_messages", json=payload, headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

if __name__ == '__main__':
    unittest.main() 