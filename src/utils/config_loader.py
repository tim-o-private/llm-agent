import os
import yaml
from dotenv import load_dotenv
from typing import Any, Optional

# Import the helper function
from src.utils.path_helpers import get_base_path

class ConfigLoader:
    """
    Loads configuration from a YAML file and environment variables.
    Environment variables take precedence for sensitive data.
    """
    # Removed default paths from __init__ signature, they are now determined dynamically
    def __init__(self, settings_rel_path: str = 'config/settings.yaml', dotenv_rel_path: Optional[str] = '.env'):
        # Store relative paths for potential reference, but use absolute paths for loading
        self.settings_rel_path = settings_rel_path
        self.dotenv_rel_path = dotenv_rel_path

        # Determine the base path
        base_dir = get_base_path()

        # Construct absolute paths
        self.settings_path = os.path.join(base_dir, settings_rel_path)
        self.dotenv_path = os.path.join(base_dir, dotenv_rel_path) if dotenv_rel_path else None

        self.settings = {}
        self._load()

    def _load(self):
        # Load .env first, if path exists
        if self.dotenv_path and os.path.exists(self.dotenv_path):
            load_dotenv(self.dotenv_path)
        elif self.dotenv_rel_path:
             # Check default location relative to CWD if not found relative to base_path
             # Useful for development when .env is in project root
             if os.path.exists(self.dotenv_rel_path):
                 load_dotenv(self.dotenv_rel_path)

        # Load YAML config using the absolute path
        try:
            # Ensure the config directory (relative to base_path) exists if needed
            config_dir = os.path.dirname(self.settings_path)
            # PyInstaller bundles config, so we don't need to create it.
            # if not os.path.exists(config_dir):
            #    os.makedirs(config_dir, exist_ok=True)

            with open(self.settings_path, 'r') as f:
                self.settings = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {self.settings_path} not found. Using defaults and environment variables.")
            self.settings = {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            self.settings = {}

    def get(self, key_path: str, default: Optional[Any] = None) -> Any:
        """
        Retrieve a config value by dot-separated key path (e.g., 'llm.model').
        Environment variables take precedence if present.
        """
        env_key = key_path.upper().replace('.', '_')
        env_val = os.getenv(env_key)
        if env_val is not None:
            return env_val
        # Traverse nested dicts
        keys = key_path.split('.')
        val = self.settings
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val
