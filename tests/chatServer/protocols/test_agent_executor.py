"""Unit tests for agent executor protocol."""

import unittest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock

from chatServer.protocols.agent_executor import AgentExecutorProtocol


class MockAgentExecutor:
    """Mock implementation of AgentExecutorProtocol for testing."""
    
    def __init__(self):
        self.memory = "mock_memory"
    
    async def ainvoke(self, inputs: Dict[str, Any], config: Optional[Any] = None) -> Dict[str, Any]:
        """Mock implementation of ainvoke."""
        return {"output": f"Processed: {inputs.get('input', 'no input')}"}


class InvalidAgentExecutor:
    """Invalid implementation missing required methods."""
    
    def __init__(self):
        self.memory = "mock_memory"
    
    # Missing ainvoke method


class TestAgentExecutorProtocol(unittest.TestCase):
    """Test cases for AgentExecutorProtocol."""

    def test_protocol_exists(self):
        """Test that the protocol exists and can be imported."""
        # Check that the protocol exists
        self.assertIsNotNone(AgentExecutorProtocol)
        self.assertTrue(hasattr(AgentExecutorProtocol, '__annotations__'))

    def test_valid_implementation(self):
        """Test that a valid implementation satisfies the protocol."""
        executor = MockAgentExecutor()
        
        # Check that it has the required attributes
        self.assertTrue(hasattr(executor, 'memory'))
        self.assertTrue(hasattr(executor, 'ainvoke'))
        self.assertTrue(callable(executor.ainvoke))
        
        # Check memory attribute
        self.assertEqual(executor.memory, "mock_memory")

    def test_protocol_checking(self):
        """Test protocol checking with isinstance-like behavior."""
        valid_executor = MockAgentExecutor()
        invalid_executor = InvalidAgentExecutor()
        
        # Valid executor should have all required methods
        self.assertTrue(hasattr(valid_executor, 'memory'))
        self.assertTrue(hasattr(valid_executor, 'ainvoke'))
        self.assertTrue(callable(valid_executor.ainvoke))
        
        # Invalid executor is missing ainvoke
        self.assertTrue(hasattr(invalid_executor, 'memory'))
        self.assertFalse(hasattr(invalid_executor, 'ainvoke'))

    def test_memory_attribute(self):
        """Test that the memory attribute can hold various types."""
        executor = MockAgentExecutor()
        
        # Test with string
        executor.memory = "string_memory"
        self.assertEqual(executor.memory, "string_memory")
        
        # Test with dict
        memory_dict = {"type": "buffer", "size": 100}
        executor.memory = memory_dict
        self.assertEqual(executor.memory, memory_dict)
        
        # Test with None
        executor.memory = None
        self.assertIsNone(executor.memory)
        
        # Test with mock object
        mock_memory = AsyncMock()
        executor.memory = mock_memory
        self.assertEqual(executor.memory, mock_memory)

    def test_protocol_documentation(self):
        """Test that the protocol has proper documentation."""
        # Check class docstring
        self.assertIsNotNone(AgentExecutorProtocol.__doc__)
        self.assertIn("Protocol defining the interface", AgentExecutorProtocol.__doc__)
        
        # Check method docstring
        self.assertIsNotNone(AgentExecutorProtocol.ainvoke.__doc__)
        self.assertIn("Asynchronously invoke", AgentExecutorProtocol.ainvoke.__doc__)


class TestProtocolCompliance(unittest.IsolatedAsyncioTestCase):
    """Test protocol compliance with async methods."""

    async def test_ainvoke_method(self):
        """Test that the ainvoke method works as expected."""
        executor = MockAgentExecutor()
        
        # Test basic invocation
        result = await executor.ainvoke({"input": "test message"})
        self.assertEqual(result, {"output": "Processed: test message"})
        
        # Test with config parameter
        result = await executor.ainvoke(
            {"input": "test message"}, 
            config={"some": "config"}
        )
        self.assertEqual(result, {"output": "Processed: test message"})
        
        # Test with empty inputs
        result = await executor.ainvoke({})
        self.assertEqual(result, {"output": "Processed: no input"})

    async def test_ainvoke_return_type(self):
        """Test that ainvoke returns the expected type."""
        executor = MockAgentExecutor()
        
        result = await executor.ainvoke({"input": "test"})
        
        # Should return a dictionary
        self.assertIsInstance(result, dict)
        self.assertIn("output", result)
        self.assertIsInstance(result["output"], str)

    async def test_async_ainvoke_compliance(self):
        """Test that ainvoke is properly async."""
        executor = MockAgentExecutor()
        
        # Should be awaitable
        result = await executor.ainvoke({"input": "async test"})
        self.assertIsInstance(result, dict)
        
        # Should work with asyncio
        import asyncio
        task = asyncio.create_task(executor.ainvoke({"input": "task test"}))
        result = await task
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main() 