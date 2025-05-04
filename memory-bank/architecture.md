# System Architecture

This document describes the high-level architecture and components of the Local LLM Terminal Environment.

## Core Components (`src/`)

### Utilities (`src/utils/`)

- **`config_loader.py`:**
  - **Purpose:** Handles loading application configuration.
  - **Functionality:** Reads settings from a base YAML file (`config/settings.yaml`) and overrides them with environment variables (loaded from `.env` or the shell environment). Environment variables take precedence, especially for secrets like API keys. Provides a `get()` method for easy access to nested configuration values using dot notation (e.g., `llm.model`). Includes basic error handling for missing or malformed YAML files.

- **`path_helpers.py`:**
  - **Purpose:** Provides centralized functions for constructing file paths within the project.
  - **Functionality:** Offers functions like `get_agent_config_dir`, `get_agent_data_dir`, `get_global_context_dir`, etc., based on the base paths defined in `settings.yaml` via `ConfigLoader`. Ensures consistent path generation across the application.

- **`chat_helpers.py`:**
  - **Purpose:** Contains helper functions specifically for the `chat` REPL command.
  - **Functionality:** Manages loading/saving of agent conversation memory (`ConversationBufferMemory`) to/from JSON files (`/data/agents/<agent_name>/memory/chat_history.json`). Handles REPL-specific commands like `/agent`, `/exit`, `/summarize`. Coordinates the generation and saving of session summaries to `/data/agents/<agent_name>/session_summary.md`.

### Core Logic (`src/core/`)

- **`llm_interface.py`:**
  - **Purpose:** Provides a consistent interface for interacting with the configured Large Language Model (LLM).
  - **Functionality:** Uses LangChain (`langchain-google-genai`) to connect to the specified LLM (e.g., Gemini Pro). Initializes the model with parameters (API key, temperature) loaded via `ConfigLoader`. Offers a `generate_text` method to send prompts (with optional system context) to the LLM and retrieve the response. Includes basic error handling for missing API keys and API communication failures.

- **`file_parser.py`:**
  - **Purpose:** Provides utility functions for reading specific file types used for context.
  - **Functionality:** Includes `read_markdown(filepath)` to read `.md` files into strings and `read_yaml(filepath)` to parse `.yaml` files into Python dictionaries. Both functions handle `FileNotFoundError` and `IOError`. `read_yaml` also handles `yaml.YAMLError` for invalid files and returns an empty dictionary for empty files.

- **`context_manager.py`:**
  - **Purpose:** Gathers and formats context from the global context directory.
  - **Functionality:** Uses `ConfigLoader` to find the global context directory (`data/global_context/`). Uses `file_parser` to read Markdown and YAML files within that directory. Formats the collected content into a structured Markdown string with clear headings (e.g., `## Global Context`). Returns the formatted string. Includes logging for missing directories or files. Note: Agent-specific context (config, prompt) is now handled by `agent_loader.py`.

- **`agent_loader.py`:**
  - **Purpose:** Loads agent configuration, tools, and constructs the LangChain `AgentExecutor`.
  - **Functionality:** Reads agent settings from `/config/agents/<agent_name>/agent_config.yaml` (e.g., model params, tool list). Loads the agent's system prompt from `/config/agents/<agent_name>/system_prompt.md`. Uses `ContextManager` to retrieve formatted global context. Instantiates required tools (e.g., `FileManagementToolkit`) based on configuration, sandboxing file access tools to agent-specific directories (`/data/agents/<agent_name>/...`). Initializes the LLM via `LLMInterface`. Combines global context, formatted agent config details, and the system prompt. Creates the `ChatPromptTemplate` and the tool-calling agent logic. Builds and returns the configured `AgentExecutor`.
