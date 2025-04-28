import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

import pytest
import tempfile
import shutil
import yaml
import logging
from unittest.mock import MagicMock, patch
from utils.config_loader import ConfigLoader
from core.context_manager import ContextManager

# --- Test Data ---

GLOBAL_BIO_CONTENT = "This is the global bio."
GLOBAL_PREFS_CONTENT = {'theme': 'dark', 'notifications': False}
AGENT_A_NOTES_CONTENT = "Notes for agent A."
AGENT_A_TASKS_CONTENT = {'tasks': [{'id': 1, 'desc': 'Task A1'}]}
AGENT_B_README_CONTENT = "Readme for agent B."

# --- Fixtures ---

@pytest.fixture
def temp_dirs(): # Renamed fixture to reflect multiple base dirs
    """Creates temporary config and data directory structures for testing."""
    # Use unique temp dirs for config and data roots
    base_config_dir = tempfile.mkdtemp(prefix='test_config_')
    base_data_dir = tempfile.mkdtemp(prefix='test_data_')
    
    # Config structure
    config_agents_dir = os.path.join(base_config_dir, 'agents')
    config_agent_a_dir = os.path.join(config_agents_dir, 'agent_a')
    config_agent_b_dir = os.path.join(config_agents_dir, 'agent_b')
    os.makedirs(config_agent_a_dir)
    os.makedirs(config_agent_b_dir)

    # Data structure
    data_global_dir = os.path.join(base_data_dir, 'global_context')
    data_agents_dir = os.path.join(base_data_dir, 'agents')
    data_agent_a_dir = os.path.join(data_agents_dir, 'agent_a') # For future dynamic data
    data_agent_b_dir = os.path.join(data_agents_dir, 'agent_b') # For future dynamic data
    os.makedirs(data_global_dir)
    os.makedirs(data_agent_a_dir)
    os.makedirs(data_agent_b_dir)
    
    # Create global context files (in data dir)
    with open(os.path.join(data_global_dir, 'bio.md'), 'w') as f: f.write(GLOBAL_BIO_CONTENT)
    with open(os.path.join(data_global_dir, 'prefs.yaml'), 'w') as f: yaml.dump(GLOBAL_PREFS_CONTENT, f)
    
    # Create agent A static context files (in config dir)
    with open(os.path.join(config_agent_a_dir, 'notes.md'), 'w') as f: f.write(AGENT_A_NOTES_CONTENT)
    with open(os.path.join(config_agent_a_dir, 'tasks.yaml'), 'w') as f: yaml.dump(AGENT_A_TASKS_CONTENT, f)

    # Create agent B static context files (in config dir)
    with open(os.path.join(config_agent_b_dir, 'readme.md'), 'w') as f: f.write(AGENT_B_README_CONTENT)
    # Add an ignored file type (in config dir)
    with open(os.path.join(config_agent_b_dir, 'image.png'), 'w') as f: f.write("PNGDATA")
    
    yield base_config_dir, base_data_dir # Return paths to both temp roots
    
    # Cleanup
    shutil.rmtree(base_config_dir)
    shutil.rmtree(base_data_dir)

@pytest.fixture
def mock_config(temp_dirs): # Depends on temp_dirs
    """Creates a mock ConfigLoader pointing to the temp dirs."""
    base_config_dir, base_data_dir = temp_dirs # Unpack the yielded tuple
    config = MagicMock(spec=ConfigLoader)
    config.get.side_effect = lambda key, default=None: {
        'config.base_dir': base_config_dir,
        'config.agents_dir': 'agents/', # Relative path within config root
        'data.base_dir': base_data_dir,
        'data.global_context_dir': 'global_context/', # Relative path within data root
        'data.agents_dir': 'agents/' # Relative path within data root
    }.get(key, default)
    return config

# --- Tests ---

def test_context_manager_load_global_only(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name=None) 
    
    # Check raw data
    assert 'global' in raw_context
    assert 'agent_static' in raw_context # Use new key
    assert 'bio' in raw_context['global']
    assert 'prefs' in raw_context['global']
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert raw_context['global']['prefs'] == GLOBAL_PREFS_CONTENT
    assert not raw_context['agent_static'] # Static agent context should be empty
    
    # Check formatted string (basic checks)
    assert "## Global Context" in formatted_context
    assert "### Bio" in formatted_context
    assert GLOBAL_BIO_CONTENT in formatted_context
    assert "### Prefs" in formatted_context
    assert "theme: dark" in formatted_context
    assert "notifications: false" in formatted_context
    assert "Agent Definition" not in formatted_context # Check new title isn't present

def test_context_manager_load_agent_a(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name='agent_a')

    # Check raw data (global + agent A static)
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert 'notes' in raw_context['agent_static'] # Use new key
    assert 'tasks' in raw_context['agent_static'] # Use new key
    assert raw_context['agent_static']['notes'] == AGENT_A_NOTES_CONTENT
    assert raw_context['agent_static']['tasks'] == AGENT_A_TASKS_CONTENT
    
    # Check formatted string
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: agent_a" in formatted_context # Check new title
    assert "### Notes" in formatted_context
    assert AGENT_A_NOTES_CONTENT in formatted_context
    assert "### Tasks" in formatted_context
    assert "id: 1" in formatted_context
    assert "desc: Task A1" in formatted_context

def test_context_manager_load_agent_b(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name='agent_b')

    # Check raw data (global + agent B static)
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert 'readme' in raw_context['agent_static'] # Use new key
    assert raw_context['agent_static']['readme'] == AGENT_B_README_CONTENT
    assert 'tasks' not in raw_context['agent_static'] # Agent B has no tasks.yaml
    assert 'image' not in raw_context['agent_static'] # Should ignore .png
    
    # Check formatted string
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: agent_b" in formatted_context # Check new title
    assert "### Readme" in formatted_context
    assert AGENT_B_README_CONTENT in formatted_context
    assert "### Tasks" not in formatted_context

def test_context_manager_missing_agent(mock_config, caplog):
    """Test loading an agent whose config directory doesn't exist."""
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
        raw_context, formatted_context = manager.get_context(agent_name='non_existent_agent')
    
    # Check raw data
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert not raw_context['agent_static'] # Use new key
    
    # Check formatted string and logs
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: non_existent_agent" in formatted_context # Check new title
    assert "No static context files found for this agent definition." in formatted_context # Check new text
    # Check that the warning mentions the CONFIG directory
    assert "Context directory not found" in caplog.text
    # Check for key parts of the path, avoiding the full temp path
    assert "agents" in caplog.text 
    assert "non_existent_agent" in caplog.text
    assert "test_config_" in caplog.text # Check for the temp dir prefix for config

def test_context_manager_missing_global(mock_config, temp_dirs, caplog):
    """Test loading when the global context data directory is missing."""
    base_config_dir, base_data_dir = temp_dirs
    # Remove the global dir from the DATA directory
    data_global_dir = os.path.join(base_data_dir, 'global_context')
    shutil.rmtree(data_global_dir)
    
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
         raw_context, formatted_context = manager.get_context(agent_name='agent_a')

    # Check raw data
    assert not raw_context['global']
    assert raw_context['agent_static']['notes'] == AGENT_A_NOTES_CONTENT # Agent static should still load
    
    # Check formatted string and logs
    assert "## Global Context" not in formatted_context # Section shouldn't appear if dir missing
    assert "## Agent Definition: agent_a" in formatted_context # Check new title
    assert "Context directory not found" in caplog.text
    assert "global_context" in caplog.text 
    assert base_data_dir in caplog.text # Ensure it's the data dir warning 