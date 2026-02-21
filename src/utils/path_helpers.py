import os
import sys
from typing import TYPE_CHECKING, Optional

# Type checking imports to avoid circular dependency
if TYPE_CHECKING:
    from utils.config_loader import ConfigLoader

# New function to determine base path
def get_base_path():
    """ Get the base path for the application, handling bundled exe. """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (e.g., --onedir or --onefile temporary)
        # For --onedir, _MEIPASS is the bundled directory
        # For --onefile, _MEIPASS is a temporary directory
        # In both cases, we want the directory containing the executable for relative data/config
        return os.path.dirname(sys.executable) # Return dir of executable itself
        # return sys._MEIPASS # Keep original note, but use dirname(sys.executable)
    else:
        # Running as a normal script
        # Assume this script (path_helpers.py) is in src/utils/
        # Go up two levels to get the project root where config/ and data/ are
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_agent_data_dir(agent_name: str, config_loader: 'ConfigLoader', user_id: Optional[str] = None) -> str:
    """Get the data directory path for a specific agent, optionally scoped by user_id."""
    base_data_dir_rel = config_loader.get('data.base_dir', 'data/')
    project_base_path = get_base_path()

    if user_id:
        # Path for user-specific agent data: data/users/<user_id>/agents/<agent_name>
        users_data_subdir = config_loader.get('data.users_dir', 'users/') # New config option
        agents_subdir_within_user = config_loader.get('data.agents_dir_user_scope', 'agents/') # New config option
        return os.path.join(project_base_path, base_data_dir_rel, users_data_subdir, user_id, agents_subdir_within_user, agent_name)  # noqa: E501
    else:
        # Path for general agent data (CLI or system agents): data/agents/<agent_name>
        agents_data_subdir = config_loader.get('data.agents_dir', 'agents/')
        return os.path.join(project_base_path, base_data_dir_rel, agents_data_subdir, agent_name)

def get_task_list_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the task list directory path.
    If 'data.task_list_dir' in the global config is an absolute path, it is used directly.
    Otherwise, it's treated as relative to the application's base path and the agent_name is appended.
    Note: Agent name is NOT appended if the path is absolute.
    """
    base_task_list_dir = config_loader.get('data.task_list_dir', '')
    if os.path.isabs(base_task_list_dir):
        # If the configured path is absolute, use it directly
        return base_task_list_dir
    else:
        # Otherwise, join it with the application's base path and append agent name
        return os.path.join(get_base_path(), base_task_list_dir, agent_name)

def get_agent_config_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the configuration directory path for a specific agent."""
    base_config_dir_rel = config_loader.get('config.base_dir', 'config/')
    agents_config_subdir = config_loader.get('config.agents_dir', 'agents/')
    # Use get_base_path()
    # Note: Agent config is bundled WITH the app via --add-data 'config:config'
    # So the base for *agent* config is relative to the app base path.
    return os.path.join(get_base_path(), base_config_dir_rel, agents_config_subdir, agent_name)

def get_agent_config_file_path(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the path to an agent's configuration file."""
    agent_config_dir = get_agent_config_dir(agent_name, config_loader)
    return os.path.join(agent_config_dir, 'agent_config.yaml')

def get_agent_memory_dir(agent_name: str, config_loader: 'ConfigLoader', user_id: Optional[str] = None) -> str:
    """Get the memory directory path for a specific agent, optionally user-scoped."""
    agent_data_dir = get_agent_data_dir(agent_name, config_loader, user_id)
    return os.path.join(agent_data_dir, 'memory') # Standardized to 'memory' subdir

def get_agent_output_dir(agent_name: str, config_loader: 'ConfigLoader', user_id: Optional[str] = None) -> str:
    """Get the output directory path for a specific agent, optionally user-scoped."""
    agent_data_dir = get_agent_data_dir(agent_name, config_loader, user_id)
    return os.path.join(agent_data_dir, 'output') # Standardized to 'output' subdir

# Added function to get the base config directory (for settings.yaml)
def get_config_base_dir(config_loader: 'ConfigLoader') -> str:
    """Get the base config directory path."""
    base_config_dir_rel = config_loader.get('config.base_dir', 'config/')
    return os.path.join(get_base_path(), base_config_dir_rel)

# Added function to get the base data directory (for global context, etc.)
def get_data_base_dir(config_loader: 'ConfigLoader') -> str:
    """Get the base data directory path."""
    base_data_dir_rel = config_loader.get('data.base_dir', 'data/')
    return os.path.join(get_base_path(), base_data_dir_rel)

# Added function to get the memory-bank directory path
def get_memory_bank_dir(config_loader: 'ConfigLoader') -> str:
    """Get the absolute path to the memory-bank directory, assumed to be at the project root."""
    # Assuming memory-bank is always at the root, alongside src/, config/, data/
    # If its location can be configured, this would need adjustment.
    return os.path.join(get_base_path(), 'memory-bank')

# Note: Might need to update other parts of the code (e.g., ContextManager)
# that construct paths using config values directly without path_helpers.
# Also need to update ConfigLoader to use get_base_path() for loading settings.yaml.
