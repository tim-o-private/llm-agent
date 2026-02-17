"""Unit tests for chat models."""

import unittest

from pydantic import ValidationError

from chatServer.models.chat import ChatRequest, ChatResponse


class TestChatRequest(unittest.TestCase):
    """Test cases for ChatRequest model."""

    def test_valid_chat_request(self):
        """Test creating a valid ChatRequest."""
        data = {
            "agent_name": "test_agent",
            "message": "Hello, world!",
            "session_id": "session-123"
        }
        request = ChatRequest(**data)

        self.assertEqual(request.agent_name, "test_agent")
        self.assertEqual(request.message, "Hello, world!")
        self.assertEqual(request.session_id, "session-123")

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing agent_name
        with self.assertRaises(ValidationError):
            ChatRequest(message="Hello", session_id="session-123")

        # Missing message
        with self.assertRaises(ValidationError):
            ChatRequest(agent_name="test_agent", session_id="session-123")

        # Missing session_id
        with self.assertRaises(ValidationError):
            ChatRequest(agent_name="test_agent", message="Hello")

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        # Empty strings should be allowed but might not be desirable
        request = ChatRequest(
            agent_name="",
            message="",
            session_id=""
        )
        self.assertEqual(request.agent_name, "")
        self.assertEqual(request.message, "")
        self.assertEqual(request.session_id, "")


class TestChatResponse(unittest.TestCase):
    """Test cases for ChatResponse model."""

    def test_minimal_chat_response(self):
        """Test creating a minimal ChatResponse."""
        response = ChatResponse(
            session_id="session-123",
            response="Hello back!"
        )

        self.assertEqual(response.session_id, "session-123")
        self.assertEqual(response.response, "Hello back!")
        self.assertIsNone(response.tool_name)
        self.assertIsNone(response.tool_input)
        self.assertIsNone(response.error)

    def test_full_chat_response(self):
        """Test creating a ChatResponse with all fields."""
        tool_input = {"param1": "value1", "param2": 42}
        response = ChatResponse(
            session_id="session-123",
            response="Tool executed successfully",
            tool_name="test_tool",
            tool_input=tool_input,
            error=None
        )

        self.assertEqual(response.session_id, "session-123")
        self.assertEqual(response.response, "Tool executed successfully")
        self.assertEqual(response.tool_name, "test_tool")
        self.assertEqual(response.tool_input, tool_input)
        self.assertIsNone(response.error)

    def test_error_response(self):
        """Test creating a ChatResponse with an error."""
        response = ChatResponse(
            session_id="session-123",
            response="An error occurred",
            error="Something went wrong"
        )

        self.assertEqual(response.session_id, "session-123")
        self.assertEqual(response.response, "An error occurred")
        self.assertEqual(response.error, "Something went wrong")
        self.assertIsNone(response.tool_name)
        self.assertIsNone(response.tool_input)

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing session_id
        with self.assertRaises(ValidationError):
            ChatResponse(response="Hello back!")

        # Missing response
        with self.assertRaises(ValidationError):
            ChatResponse(session_id="session-123")


if __name__ == '__main__':
    unittest.main()
