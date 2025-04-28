# System Architecture

This document describes the high-level architecture and components of the Local LLM Terminal Environment.

## Core Components (`src/`)

### Utilities (`src/utils/`)

- **`config_loader.py`:**
  - **Purpose:** Handles loading application configuration.
  - **Functionality:** Reads settings from a base YAML file (`config/settings.yaml`) and overrides them with environment variables (loaded from `.env` or the shell environment). Environment variables take precedence, especially for secrets like API keys. Provides a `get()` method for easy access to nested configuration values using dot notation (e.g., `llm.model`). Includes basic error handling for missing or malformed YAML files.

### Core Logic (`src/core/`)

- **`llm_interface.py`:**
  - **Purpose:** Provides a consistent interface for interacting with the configured Large Language Model (LLM).
  - **Functionality:** Uses LangChain (`langchain-google-genai`) to connect to the specified LLM (e.g., Gemini Pro). Initializes the model with parameters (API key, temperature) loaded via `ConfigLoader`. Offers a `generate_text` method to send prompts (with optional system context) to the LLM and retrieve the response. Includes basic error handling for missing API keys and API communication failures.

- **`file_parser.py`:**
  - **Purpose:** Provides utility functions for reading specific file types used for context.
  - **Functionality:** Includes `read_markdown(filepath)` to read `.md` files into strings and `read_yaml(filepath)` to parse `.yaml` files into Python dictionaries. Both functions handle `FileNotFoundError` and `IOError`. `read_yaml` also handles `yaml.YAMLError` for invalid files and returns an empty dictionary for empty files.

- **`context_manager.py`:**
  - **Purpose:** Gathers and formats context from various sources (global, project-specific) before passing it to the LLM.
  - **Functionality:** Uses `ConfigLoader` to find the relevant data directories (global, projects base). Uses `file_parser` to read Markdown and YAML files within the global directory and the specified project directory. Formats the collected content into a structured Markdown string with clear headings (e.g., `## Global Context`, `## Project Context: ...`). Returns both the raw data (as a dictionary) and the formatted string. Includes logging for missing directories or files.
