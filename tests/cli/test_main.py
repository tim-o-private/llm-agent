import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import the CLI module directly
import cli.main 

@pytest.fixture
def runner():
    return CliRunner()

# Patch the classes used *within* the ask command AND the module-level instance
@patch('cli.main.ContextManager') 
@patch('cli.main.LLMInterface')
# Patch the specific config_loader instance in the cli.main module
@patch.object(cli.main, 'config_loader') 
def test_ask_command_success(MockConfigLoaderInstance, MockLLMInterfaceClass, MockContextManagerClass, runner):
    # ^ Renamed args for clarity: MockConfigLoaderInstance is the patched module-level object
    #   MockLLMInterfaceClass and MockContextManagerClass are the patched classes
    """Test the ask command runs and calls dependencies."""
    
    # Configure the mocked module-level config_loader instance
    MockConfigLoaderInstance.get.side_effect = lambda key, default=None: {
        'GOOGLE_API_KEY': 'fake-key', 
        'data.base_dir': './data'
    }.get(key, default)

    # Configure the mock instances returned WHEN the patched classes are instantiated
    mock_llm_instance = MockLLMInterfaceClass.return_value
    mock_llm_instance.generate_text.return_value = "Mock LLM Response"
    
    mock_context_instance = MockContextManagerClass.return_value
    # Ensure the mock returns the expected tuple for unpacking
    mock_context_instance.get_context.return_value = ({'global': {}, 'agent': {}}, "Mock Formatted Context")
    
    # Invoke the CLI command
    result = runner.invoke(cli.main.cli, ['ask', 'Test query'])
    
    # Assertions
    assert result.exit_code == 0, f"CLI exited with code {result.exit_code}, output: {result.output}"
    assert "Mock LLM Response" in result.output
    
    # Check if ContextManager was instantiated with the mocked config loader instance
    MockContextManagerClass.assert_called_once_with(config=MockConfigLoaderInstance)
    # Check if LLMInterface was instantiated with the mocked config loader instance
    MockLLMInterfaceClass.assert_called_once_with(config=MockConfigLoaderInstance)
    
    # Check if context was fetched (agent_name=None expected here)
    # Assert on the instance returned by the mocked class
    mock_context_instance.get_context.assert_called_once_with(agent_name=None)
    
    # Check if LLM was called
    # Assert on the instance returned by the mocked class
    mock_llm_instance.generate_text.assert_called_once_with(
        prompt='Test query', 
        system_context="Mock Formatted Context"
    )

# Add more tests later: for --agent flag, error handling, etc. 