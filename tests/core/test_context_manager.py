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
def temp_data_dir():
    """Creates a temporary data directory structure for testing."""
    base_dir = tempfile.mkdtemp()
    global_dir = os.path.join(base_dir, 'global_context')
    agents_dir = os.path.join(base_dir, 'agents')
    agent_a_dir = os.path.join(agents_dir, 'agent_a')
    agent_b_dir = os.path.join(agents_dir, 'agent_b')
    
    os.makedirs(global_dir)
    os.makedirs(agent_a_dir)
    os.makedirs(agent_b_dir)
    
    # Create global files
    with open(os.path.join(global_dir, 'bio.md'), 'w') as f: f.write(GLOBAL_BIO_CONTENT)
    with open(os.path.join(global_dir, 'prefs.yaml'), 'w') as f: yaml.dump(GLOBAL_PREFS_CONTENT, f)
    
    # Create agent A files
    with open(os.path.join(agent_a_dir, 'notes.md'), 'w') as f: f.write(AGENT_A_NOTES_CONTENT)
    with open(os.path.join(agent_a_dir, 'tasks.yaml'), 'w') as f: yaml.dump(AGENT_A_TASKS_CONTENT, f)

    # Create agent B files
    with open(os.path.join(agent_b_dir, 'readme.md'), 'w') as f: f.write(AGENT_B_README_CONTENT)
    # Add an ignored file type
    with open(os.path.join(agent_b_dir, 'image.png'), 'w') as f: f.write("PNGDATA")
    
    yield base_dir # Return the path to the base temporary directory
    
    # Cleanup
    shutil.rmtree(base_dir)

@pytest.fixture
def mock_config(temp_data_dir): # Depends on temp_data_dir
    """Creates a mock ConfigLoader pointing to the temp data dir."""
    config = MagicMock(spec=ConfigLoader)
    config.get.side_effect = lambda key, default=None: {
        'data.base_dir': temp_data_dir,
        'data.global_context_dir': 'global_context/',
        'data.agents_dir': 'agents/'
    }.get(key, default)
    return config

# --- Tests ---

def test_context_manager_load_global_only(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name=None)
    
    # Check raw data
    assert 'global' in raw_context
    assert 'agent' in raw_context
    assert 'bio' in raw_context['global']
    assert 'prefs' in raw_context['global']
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert raw_context['global']['prefs'] == GLOBAL_PREFS_CONTENT
    assert not raw_context['agent'] # Agent context should be empty
    
    # Check formatted string (basic checks)
    assert "## Global Context" in formatted_context
    assert "### Bio" in formatted_context
    assert GLOBAL_BIO_CONTENT in formatted_context
    assert "### Prefs" in formatted_context
    assert "theme: dark" in formatted_context
    assert "notifications: false" in formatted_context
    assert "Agent Context" not in formatted_context

def test_context_manager_load_agent_a(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name='agent_a')

    # Check raw data (global + agent A)
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert 'notes' in raw_context['agent']
    assert 'tasks' in raw_context['agent']
    assert raw_context['agent']['notes'] == AGENT_A_NOTES_CONTENT
    assert raw_context['agent']['tasks'] == AGENT_A_TASKS_CONTENT
    
    # Check formatted string
    assert "## Global Context" in formatted_context
    assert "## Agent Context: agent_a" in formatted_context
    assert "### Notes" in formatted_context
    assert AGENT_A_NOTES_CONTENT in formatted_context
    assert "### Tasks" in formatted_context
    assert "id: 1" in formatted_context
    assert "desc: Task A1" in formatted_context

def test_context_manager_load_agent_b(mock_config):
    manager = ContextManager(config=mock_config)
    raw_context, formatted_context = manager.get_context(agent_name='agent_b')

    # Check raw data (global + agent B)
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert 'readme' in raw_context['agent']
    assert raw_context['agent']['readme'] == AGENT_B_README_CONTENT
    assert 'tasks' not in raw_context['agent'] # Agent B has no tasks.yaml
    assert 'image' not in raw_context['agent'] # Should ignore .png
    
    # Check formatted string
    assert "## Global Context" in formatted_context
    assert "## Agent Context: agent_b" in formatted_context
    assert "### Readme" in formatted_context
    assert AGENT_B_README_CONTENT in formatted_context
    assert "### Tasks" not in formatted_context

def test_context_manager_missing_agent(mock_config, caplog):
    """Test loading an agent that doesn't exist."""
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
        raw_context, formatted_context = manager.get_context(agent_name='non_existent_agent')
    
    # Check raw data
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert not raw_context['agent']
    
    # Check formatted string and logs
    assert "## Global Context" in formatted_context
    assert "## Agent Context: non_existent_agent" in formatted_context
    assert "No context files found for this agent." in formatted_context
    assert "Context directory not found" in caplog.text
    assert "non_existent_agent" in caplog.text

def test_context_manager_missing_global(mock_config, temp_data_dir, caplog):
    """Test loading when the global context directory is missing."""
    # Remove the global dir created by the fixture
    global_dir = os.path.join(temp_data_dir, 'global_context')
    shutil.rmtree(global_dir)
    
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
         raw_context, formatted_context = manager.get_context(agent_name='agent_a')

    # Check raw data
    assert not raw_context['global']
    assert raw_context['agent']['notes'] == AGENT_A_NOTES_CONTENT # Agent should still load
    
    # Check formatted string and logs
    assert "## Global Context" not in formatted_context # Section shouldn't appear if dir missing
    assert "## Agent Context: agent_a" in formatted_context 
    assert "Context directory not found" in caplog.text
    assert "global_context" in caplog.text 