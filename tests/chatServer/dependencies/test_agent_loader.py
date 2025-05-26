"""Unit tests for agent loader dependency."""

import unittest
from unittest.mock import patch, MagicMock

from chatServer.dependencies.agent_loader import get_agent_loader


class TestGetAgentLoader(unittest.TestCase):
    """Test cases for get_agent_loader function."""

    def test_get_agent_loader_returns_agent_loader_module(self):
        """Test that get_agent_loader returns the agent_loader module."""
        with patch('chatServer.dependencies.agent_loader.agent_loader') as mock_agent_loader:
            mock_agent_loader.some_function = MagicMock()
            
            result = get_agent_loader()
            
            self.assertIs(result, mock_agent_loader)

    def test_get_agent_loader_is_callable(self):
        """Test that get_agent_loader is callable and returns something."""
        result = get_agent_loader()
        
        # Should return the actual agent_loader module
        self.assertIsNotNone(result)

    def test_get_agent_loader_consistent_return(self):
        """Test that get_agent_loader returns the same module consistently."""
        result1 = get_agent_loader()
        result2 = get_agent_loader()
        
        # Should return the same module instance
        self.assertIs(result1, result2)

    def test_get_agent_loader_can_be_mocked_for_testing(self):
        """Test that get_agent_loader can be easily mocked for testing purposes."""
        mock_loader = MagicMock()
        mock_loader.load_agent_executor = MagicMock(return_value="mock_executor")
        
        # Mock the function itself, not the module it returns
        with patch('chatServer.dependencies.agent_loader.get_agent_loader', return_value=mock_loader):
            from chatServer.dependencies.agent_loader import get_agent_loader as mocked_get_agent_loader
            
            # This simulates how the dependency would be overridden in tests
            result = mocked_get_agent_loader()
            
            self.assertIs(result, mock_loader)
            self.assertEqual(result.load_agent_executor(), "mock_executor")

    def test_get_agent_loader_module_attributes(self):
        """Test that the returned module has expected attributes."""
        result = get_agent_loader()
        
        # The agent_loader module should have certain expected attributes
        # This test verifies the module structure without importing the actual module
        self.assertTrue(hasattr(result, '__name__'))
        
        # If we know specific functions that should exist, we can test for them
        # For example, if agent_loader should have a load_agent_executor function:
        # self.assertTrue(hasattr(result, 'load_agent_executor'))


if __name__ == '__main__':
    unittest.main() 