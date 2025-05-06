import sys
import os

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
    assert 'agent_static' not in raw_context # It should NOT be present
    assert 'bio' in raw_context['global']
    assert 'prefs' in raw_context['global']
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert raw_context['global']['prefs'] == GLOBAL_PREFS_CONTENT
    
    # Check formatted string (basic checks)
    assert "## Global Context" in formatted_context
    assert "### Bio" in formatted_context
    assert GLOBAL_BIO_CONTENT in formatted_context
    assert "### Prefs" in formatted_context
    assert "theme: dark" in formatted_context
    assert "notifications: false" in formatted_context
    assert "Agent Definition" not in formatted_context # Should not be present if agent_name is None

def test_context_manager_load_agent_a(mock_config, caplog):
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
        raw_context, formatted_context = manager.get_context(agent_name='agent_a')

    # Check raw data (global ONLY)
    assert 'global' in raw_context
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT
    assert 'agent_static' not in raw_context # Agent static context is NOT loaded by ContextManager anymore
    
    # Check formatted string (global ONLY)
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: agent_a" not in formatted_context # This section is no longer added by ContextManager
    assert AGENT_A_NOTES_CONTENT not in formatted_context # Agent A specific content not loaded here

    # Check for the warning log
    assert "ContextManager.get_context called with agent_name, but it now only loads global context" in caplog.text

def test_context_manager_load_agent_b(mock_config, caplog):
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
        raw_context, formatted_context = manager.get_context(agent_name='agent_b')

    # Check raw data (global ONLY)
    assert 'global' in raw_context
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT # Global context should still load
    assert 'agent_static' not in raw_context # Agent static context is NOT loaded by ContextManager
    
    # Check formatted string (global ONLY)
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: agent_b" not in formatted_context # No longer added by ContextManager
    assert AGENT_B_README_CONTENT not in formatted_context # Agent B specific content NOT loaded here
    assert 'image' not in formatted_context # Check if it appears in formatted global (it shouldn't)

    # Check for the warning log
    assert "ContextManager.get_context called with agent_name, but it now only loads global context" in caplog.text

def test_context_manager_missing_agent(mock_config, caplog):
    """Test loading with an agent_name whose config directory doesn't exist - ContextManager should ignore it."""
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
        raw_context, formatted_context = manager.get_context(agent_name='non_existent_agent')
    
    # Check raw data (global ONLY)
    assert 'global' in raw_context
    assert raw_context['global']['bio'] == GLOBAL_BIO_CONTENT # Global context should still load
    assert 'agent_static' not in raw_context # Agent static context is NOT loaded by ContextManager
        
    # Check formatted string (global ONLY)
    assert "## Global Context" in formatted_context
    assert "## Agent Definition: non_existent_agent" not in formatted_context # This section is no longer added by ContextManager
    # The following assertion is no longer relevant as ContextManager doesn't attempt to load or format agent static context
    # assert "No static context files found for this agent definition." in formatted_context
    
    # Check for the specific warning log for providing agent_name
    assert "ContextManager.get_context called with agent_name, but it now only loads global context" in caplog.text
    
    # Ensure the other warning about missing agent config dir (from _read_context_files) is NOT present 
    # because ContextManager no longer attempts to read agent-specific config paths.
    specific_agent_config_path_part = os.path.join("agents", "non_existent_agent")
    found_missing_dir_log_for_agent = False
    for record in caplog.records:
        if "Context directory not found" in record.message and specific_agent_config_path_part in record.message:
            found_missing_dir_log_for_agent = True
            break
    assert not found_missing_dir_log_for_agent, "ContextManager should not log missing config dir for an agent it ignores"

def test_context_manager_missing_global(mock_config, temp_dirs, caplog):
    """Test loading when the global context data directory is missing."""
    base_config_dir, base_data_dir = temp_dirs
    # Remove the global dir from the DATA directory
    data_global_dir = os.path.join(base_data_dir, 'global_context')
    if os.path.exists(data_global_dir): # Ensure it exists before trying to remove
        shutil.rmtree(data_global_dir)
    
    manager = ContextManager(config=mock_config)
    with caplog.at_level(logging.WARNING):
         raw_context, formatted_context = manager.get_context(agent_name='agent_a') # agent_name will be ignored

    # Check raw data
    assert 'global' in raw_context
    assert not raw_context['global'] # Global should be empty as dir is missing
    assert 'agent_static' not in raw_context # Agent static context is NOT loaded by ContextManager
    
    # Check formatted string
    assert "## Global Context" not in formatted_context # Section shouldn't appear if dir missing
    assert "## Agent Definition: agent_a" not in formatted_context # This section is no longer added by ContextManager
    # assert raw_context['agent_static']['notes'] == AGENT_A_NOTES_CONTENT # This is invalid as agent_static not loaded
    
    # Check for warning about missing global context directory
    assert "Context directory not found" in caplog.text # This is from _read_context_files for global_context_dir
    assert "global_context" in caplog.text 
    # Make the base_data_dir check more robust against trailing slashes
    assert os.path.normpath(base_data_dir) in os.path.normpath(caplog.records[-1].pathname) or base_data_dir in caplog.text

    # Check for the warning log about agent_name being passed
    assert "ContextManager.get_context called with agent_name, but it now only loads global context" in caplog.text

    # Ensure the other warning about missing agent config dir (from _read_context_files) is NOT present 
    # because ContextManager no longer attempts to read agent-specific config paths.
    specific_agent_config_path_part = os.path.join("agents", "agent_a")
    found_missing_dir_log_for_agent = False
    for record in caplog.records:
        if "Context directory not found" in record.message and specific_agent_config_path_part in record.message:
            found_missing_dir_log_for_agent = True
            break
    assert not found_missing_dir_log_for_agent, "ContextManager should not log missing config dir for an agent it ignores" 