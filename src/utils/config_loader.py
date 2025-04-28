import os
import yaml
from dotenv import load_dotenv
from typing import Any, Optional

class ConfigLoader:
    """
    Loads configuration from a YAML file and environment variables.
    Environment variables take precedence for sensitive data.
    """
    def __init__(self, settings_path: str = 'config/settings.yaml', dotenv_path: str = '.env'):
        self.settings_path = settings_path
        self.dotenv_path = dotenv_path
        self.settings = {}
        self._load()

    def _load(self):
        # Load .env first
        load_dotenv(self.dotenv_path)
        # Load YAML config
        try:
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
