import os
from typing import TYPE_CHECKING

# Type checking imports to avoid circular dependency
if TYPE_CHECKING:
    from utils.config_loader import ConfigLoader

def get_agent_data_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the data directory path for a specific agent."""
    base_data_dir = config_loader.get('data.base_dir', 'data/')
    agents_data_subdir = config_loader.get('data.agents_dir', 'agents/')
    return os.path.join(base_data_dir, agents_data_subdir, agent_name)

def get_agent_config_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the configuration directory path for a specific agent."""
    base_config_dir = config_loader.get('config.base_dir', 'config/')
    agents_config_subdir = config_loader.get('config.agents_dir', 'agents/')
    return os.path.join(base_config_dir, agents_config_subdir, agent_name)

def get_agent_config_file_path(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the path to an agent's configuration file."""
    agent_config_dir = get_agent_config_dir(agent_name, config_loader)
    return os.path.join(agent_config_dir, 'agent_config.yaml')

def get_agent_memory_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the memory directory path for a specific agent."""
    agent_data_dir = get_agent_data_dir(agent_name, config_loader)
    return os.path.join(agent_data_dir, 'memory')

def get_agent_output_dir(agent_name: str, config_loader: 'ConfigLoader') -> str:
    """Get the output directory path for a specific agent."""
    agent_data_dir = get_agent_data_dir(agent_name, config_loader)
    return os.path.join(agent_data_dir, 'output')
