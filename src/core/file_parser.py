from typing import Any, Dict

import yaml


def read_markdown(filepath: str) -> str:
    """
    Reads a Markdown file and returns its content as a string.

    Args:
        filepath: The path to the Markdown file.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Let the caller handle FileNotFoundError specifically if needed
        raise
    except IOError as e:
        print(f"Error reading Markdown file {filepath}: {e}")
        raise

def read_yaml(filepath: str) -> Dict[str, Any]:
    """
    Reads a YAML file, parses it, and returns a Python dictionary.

    Args:
        filepath: The path to the YAML file.

    Returns:
        A dictionary representing the parsed YAML content.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file content is invalid YAML.
        IOError: If there is an error reading the file.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            # Handle empty YAML file case
            return data if data is not None else {}
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {filepath}: {e}")
        raise
    except IOError as e:
        print(f"Error reading YAML file {filepath}: {e}")
        raise
