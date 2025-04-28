import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
from unittest.mock import patch, MagicMock
from utils.config_loader import ConfigLoader

# Mock ConfigLoader fixture
@pytest.fixture
def mock_config():
    config = MagicMock(spec=ConfigLoader)
    config.get.side_effect = lambda key, default=None: {
        'GOOGLE_API_KEY': 'test-api-key',
        'llm.model': 'gemini-pro',
        'llm.temperature': '0.8' # Test string conversion
    }.get(key, default)
    return config

# Patch the ChatGoogleGenerativeAI class
@patch('core.llm_interface.ChatGoogleGenerativeAI')
def test_llm_interface_initialization(MockChatGoogle, mock_config):
    """Test if LLMInterface initializes ChatGoogleGenerativeAI correctly."""
    from core.llm_interface import LLMInterface
    interface = LLMInterface(config=mock_config)
    
    # Assert ChatGoogleGenerativeAI was called with correct parameters
    MockChatGoogle.assert_called_once_with(
        model='gemini-pro',
        google_api_key='test-api-key',
        temperature=0.8, # Check if temperature was converted to float
        convert_system_message_to_human=True
    )
    assert interface.llm == MockChatGoogle.return_value

@patch('core.llm_interface.ChatGoogleGenerativeAI')
def test_llm_interface_generate_text(MockChatGoogle, mock_config):
    """Test the generate_text method with mocking."""
    from core.llm_interface import LLMInterface
    # Configure the mock LLM instance
    mock_llm_instance = MockChatGoogle.return_value
    # Use a generic mock instead of AIMessage
    mock_response = MagicMock()
    mock_response.content = "Mocked response text" 
    mock_llm_instance.invoke.return_value = mock_response
    
    interface = LLMInterface(config=mock_config)
    prompt = "Test prompt"
    system_context = "Test system context"
    
    response_content = interface.generate_text(prompt=prompt, system_context=system_context)
    
    # Assert that invoke was called with the correct messages
    mock_llm_instance.invoke.assert_called_once()
    call_args = mock_llm_instance.invoke.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].content == system_context
    assert call_args[1].content == prompt
    
    # Assert the response content is correct
    assert response_content == "Mocked response text"

@patch('core.llm_interface.ChatGoogleGenerativeAI')
def test_llm_interface_generate_text_no_context(MockChatGoogle, mock_config):
    """Test generate_text without system context."""
    from core.llm_interface import LLMInterface
    mock_llm_instance = MockChatGoogle.return_value
     # Use a generic mock instead of AIMessage
    mock_response = MagicMock()
    mock_response.content = "Response without context"
    mock_llm_instance.invoke.return_value = mock_response
    
    interface = LLMInterface(config=mock_config)
    prompt = "Another prompt"
    
    response_content = interface.generate_text(prompt=prompt)
    
    mock_llm_instance.invoke.assert_called_once()
    call_args = mock_llm_instance.invoke.call_args[0][0]
    assert len(call_args) == 1 # Only HumanMessage should be present
    assert call_args[0].content == prompt
    assert response_content == "Response without context"

def test_llm_interface_missing_api_key(mock_config):
    """Test that ValueError is raised if API key is missing."""
    from core.llm_interface import LLMInterface
    mock_config_no_key = MagicMock(spec=ConfigLoader)
    mock_config_no_key.get.side_effect = lambda key, default=None: {
        'llm.model': 'gemini-pro',
        'llm.temperature': '0.7'
    }.get(key, default) # Simulate missing GOOGLE_API_KEY

    with pytest.raises(ValueError, match="Google API Key not found"):
        LLMInterface(config=mock_config_no_key)

@patch('core.llm_interface.ChatGoogleGenerativeAI')
def test_llm_interface_api_error(MockChatGoogle, mock_config):
    """Test that exceptions from the LLM API call are re-raised."""
    from core.llm_interface import LLMInterface
    mock_llm_instance = MockChatGoogle.return_value
    mock_llm_instance.invoke.side_effect = Exception("API call failed")

    interface = LLMInterface(config=mock_config)
    prompt = "Prompt that causes error"

    with pytest.raises(Exception, match="API call failed"):
        interface.generate_text(prompt=prompt) 