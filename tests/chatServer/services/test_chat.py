"""Unit tests for chat service."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from langchain_core.chat_history import BaseChatMessageHistory

from chatServer.models.chat import ChatRequest, ChatResponse
from chatServer.services.chat import AsyncConversationBufferWindowMemory, ChatService, get_chat_service


class MockChatMessageHistory(BaseChatMessageHistory):
    """Mock chat message history for testing."""

    def __init__(self):
        self.messages = []
        self.aget_messages = AsyncMock(return_value=[])

    def add_message(self, message):
        self.messages.append(message)

    def clear(self):
        self.messages.clear()


# Async tests using pytest directly (not unittest.TestCase)
@pytest.mark.asyncio
async def test_async_memory_aload_memory_variables_with_messages():
    """Test async loading of memory variables with messages."""
    mock_chat_memory = MockChatMessageHistory()
    memory = AsyncConversationBufferWindowMemory(
        chat_memory=mock_chat_memory,
        k=5,
        return_messages=True,
        memory_key="chat_history",
        input_key="input"
    )

    mock_messages = [MagicMock(), MagicMock(), MagicMock()]
    mock_chat_memory.aget_messages = AsyncMock(return_value=mock_messages)

    result = await memory.aload_memory_variables({})

    assert result["chat_history"] == mock_messages
    mock_chat_memory.aget_messages.assert_called_once()


@pytest.mark.asyncio
async def test_async_memory_aload_memory_variables_with_window_limit():
    """Test async loading with window limit applied."""
    mock_chat_memory = MockChatMessageHistory()
    memory = AsyncConversationBufferWindowMemory(
        chat_memory=mock_chat_memory,
        k=5,
        return_messages=True,
        memory_key="chat_history",
        input_key="input"
    )

    # Create 12 messages (6 pairs)
    mock_messages = [MagicMock() for _ in range(12)]
    mock_chat_memory.aget_messages = AsyncMock(return_value=mock_messages)

    # k=5 means last 10 messages (5*2)
    result = await memory.aload_memory_variables({})

    # Should get last 10 messages
    assert len(result["chat_history"]) == 10
    assert result["chat_history"] == mock_messages[-10:]


class TestAsyncConversationBufferWindowMemory(unittest.TestCase):
    """Test cases for AsyncConversationBufferWindowMemory class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_chat_memory = MockChatMessageHistory()
        self.memory = AsyncConversationBufferWindowMemory(
            chat_memory=self.mock_chat_memory,
            k=5,
            return_messages=True,
            memory_key="chat_history",
            input_key="input"
        )

    def test_messages_to_string(self):
        """Test converting messages to string format."""
        mock_messages = [MagicMock(), MagicMock()]

        with patch('langchain.schema.get_buffer_string') as mock_get_buffer:
            mock_get_buffer.return_value = "formatted string"

            result = self.memory.messages_to_string(mock_messages)

            self.assertEqual(result, "formatted string")
            mock_get_buffer.assert_called_once_with(
                mock_messages,
                human_prefix=self.memory.human_prefix,
                ai_prefix=self.memory.ai_prefix
            )


class TestChatService(unittest.TestCase):
    """Test cases for ChatService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = {}
        self.service = ChatService(self.mock_cache)

    def test_chat_service_initialization(self):
        """Test ChatService initialization."""
        self.assertEqual(self.service.agent_executor_cache, self.mock_cache)

    @patch('chatServer.services.chat.PostgresChatMessageHistory')
    @patch('chatServer.services.chat.AsyncConversationBufferWindowMemory')
    def test_create_chat_memory(self, mock_memory_class, mock_history_class):
        """Test creating chat memory."""
        mock_pg_connection = MagicMock()
        mock_history = MagicMock()
        mock_memory = MagicMock()
        mock_history_class.return_value = mock_history
        mock_memory_class.return_value = mock_memory

        result = self.service.create_chat_memory("session123", mock_pg_connection)

        mock_history_class.assert_called_once_with(
            "chat_message_history",  # CHAT_MESSAGE_HISTORY_TABLE_NAME
            "session123",
            async_connection=mock_pg_connection
        )
        mock_memory_class.assert_called_once_with(
            chat_memory=mock_history,
            k=50,
            return_messages=True,
            memory_key="chat_history",
            input_key="input"
        )
        self.assertEqual(result, mock_memory)

    def test_get_or_load_agent_executor_cache_hit(self):
        """Test getting agent executor from cache (cache hit)."""
        mock_executor = MagicMock()
        mock_executor.ainvoke = MagicMock()
        mock_executor.memory = MagicMock()
        mock_memory = MagicMock()

        cache_key = ("user123", "agent1")
        self.mock_cache[cache_key] = mock_executor

        result = self.service.get_or_load_agent_executor(
            user_id="user123",
            agent_name="agent1",
            session_id="session123",
            agent_loader_module=MagicMock(),
            memory=mock_memory
        )

        self.assertEqual(result, mock_executor)
        self.assertEqual(mock_executor.memory, mock_memory)

    def test_get_or_load_agent_executor_cache_miss(self):
        """Test loading new agent executor (cache miss)."""
        mock_executor = MagicMock()
        mock_executor.ainvoke = MagicMock()
        mock_executor.memory = MagicMock()
        mock_memory = MagicMock()
        mock_loader = MagicMock()
        mock_loader.load_agent_executor.return_value = mock_executor

        result = self.service.get_or_load_agent_executor(
            user_id="user123",
            agent_name="agent1",
            session_id="session123",
            agent_loader_module=mock_loader,
            memory=mock_memory
        )

        self.assertEqual(result, mock_executor)
        self.assertEqual(mock_executor.memory, mock_memory)
        self.assertIn(("user123", "agent1"), self.mock_cache)
        mock_loader.load_agent_executor.assert_called_once()

    def test_get_or_load_agent_executor_invalid_interface(self):
        """Test error when agent executor has invalid interface."""
        mock_executor = MagicMock()
        # Remove required attributes to simulate invalid interface
        del mock_executor.ainvoke
        mock_loader = MagicMock()
        mock_loader.load_agent_executor.return_value = mock_executor

        with self.assertRaises(HTTPException) as context:
            self.service.get_or_load_agent_executor(
                user_id="user123",
                agent_name="agent1",
                session_id="session123",
                agent_loader_module=mock_loader,
                memory=MagicMock()
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Agent loading failed", context.exception.detail)

    def test_get_or_load_agent_executor_loading_error(self):
        """Test error during agent loading."""
        mock_loader = MagicMock()
        mock_loader.load_agent_executor.side_effect = Exception("Loading failed")

        with self.assertRaises(HTTPException) as context:
            self.service.get_or_load_agent_executor(
                user_id="user123",
                agent_name="agent1",
                session_id="session123",
                agent_loader_module=mock_loader,
                memory=MagicMock()
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Could not load agent", context.exception.detail)

    def test_extract_tool_info_no_steps(self):
        """Test extracting tool info when no intermediate steps."""
        response_data = {"output": "response"}

        tool_name, tool_input = self.service.extract_tool_info(response_data)

        self.assertIsNone(tool_name)
        self.assertIsNone(tool_input)

    def test_extract_tool_info_with_steps(self):
        """Test extracting tool info with intermediate steps."""
        mock_action = MagicMock()
        mock_action.tool = "web_search"
        mock_action.tool_input = {"query": "test"}
        mock_observation = "observation"

        response_data = {
            "output": "response",
            "intermediate_steps": [(mock_action, mock_observation)]
        }

        tool_name, tool_input = self.service.extract_tool_info(response_data)

        self.assertEqual(tool_name, "web_search")
        self.assertEqual(tool_input, {"query": "test"})

    def test_extract_tool_info_invalid_steps(self):
        """Test extracting tool info with invalid intermediate steps."""
        response_data = {
            "output": "response",
            "intermediate_steps": ["invalid_step"]
        }

        tool_name, tool_input = self.service.extract_tool_info(response_data)

        self.assertIsNone(tool_name)
        self.assertIsNone(tool_input)


class TestChatServiceAsync:
    """Async test cases for ChatService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_cache = {}
        self.service = ChatService(self.mock_cache)

    @pytest.mark.asyncio
    async def test_process_chat_missing_session_id(self):
        """Test processing chat with missing session ID."""
        chat_input = ChatRequest(
            agent_name="agent1",
            message="Hello",
            session_id=""
        )

        with pytest.raises(HTTPException) as exc_info:
            await self.service.process_chat(
                chat_input=chat_input,
                user_id="user123",
                pg_connection=MagicMock(),
                agent_loader_module=MagicMock(),
                request=MagicMock()
            )

        assert exc_info.value.status_code == 400
        assert "session_id is required" in exc_info.value.detail

    @patch('chatServer.services.chat.ChatService.create_chat_memory')
    @patch('chatServer.services.chat.ChatService.get_or_load_agent_executor')
    @pytest.mark.asyncio
    async def test_process_chat_success(self, mock_get_executor, mock_create_memory):
        """Test successful chat processing."""
        chat_input = ChatRequest(
            agent_name="agent1",
            message="Hello",
            session_id="session123"
        )

        mock_memory = MagicMock()
        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Hello back!"})

        mock_create_memory.return_value = mock_memory
        mock_get_executor.return_value = mock_executor

        result = await self.service.process_chat(
            chat_input=chat_input,
            user_id="user123",
            pg_connection=MagicMock(),
            agent_loader_module=MagicMock(),
            request=MagicMock()
        )

        assert isinstance(result, ChatResponse)
        assert result.session_id == "session123"
        assert result.response == "Hello back!"
        assert result.error is None

    @patch('chatServer.services.chat.ChatService.create_chat_memory')
    @patch('chatServer.services.chat.ChatService.get_or_load_agent_executor')
    @pytest.mark.asyncio
    async def test_process_chat_agent_execution_error(self, mock_get_executor, mock_create_memory):
        """Test chat processing with agent execution error."""
        chat_input = ChatRequest(
            agent_name="agent1",
            message="Hello",
            session_id="session123"
        )

        mock_memory = MagicMock()
        mock_executor = MagicMock()
        mock_executor.ainvoke = AsyncMock(side_effect=Exception("Agent failed"))

        mock_create_memory.return_value = mock_memory
        mock_get_executor.return_value = mock_executor

        result = await self.service.process_chat(
            chat_input=chat_input,
            user_id="user123",
            pg_connection=MagicMock(),
            agent_loader_module=MagicMock(),
            request=MagicMock()
        )

        assert isinstance(result, ChatResponse)
        assert result.session_id == "session123"
        assert "error occurred processing" in result.response
        assert "Agent failed" in result.error


class TestChatServiceGlobal(unittest.TestCase):
    """Test cases for global chat service functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global instance
        import chatServer.services.chat
        chatServer.services.chat._chat_service = None

    def test_get_chat_service_creates_instance(self):
        """Test that get_chat_service creates a new instance."""
        mock_cache = {}
        service = get_chat_service(mock_cache)
        self.assertIsInstance(service, ChatService)
        self.assertEqual(service.agent_executor_cache, mock_cache)

    def test_get_chat_service_returns_same_instance(self):
        """Test that get_chat_service returns the same instance."""
        mock_cache = {}
        service1 = get_chat_service(mock_cache)
        service2 = get_chat_service(mock_cache)
        self.assertIs(service1, service2)


if __name__ == "__main__":
    unittest.main()
