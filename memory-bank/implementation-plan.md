Implementation Plan: Local LLM Terminal Environment

**AI Assistant Development Guidelines:**
- **Dependencies:** When adding new functionality that requires external libraries, update `requirements.txt` with the necessary packages and minimum versions (e.g., `some-library>=1.2.0`). Ensure `langchain-community` is included for toolkits.
- **Testing:**
    - For every new module/class/function in `src/`, create a corresponding test file in `tests/` mirroring the directory structure (e.g., `src/core/foo.py` -> `tests/core/test_foo.py`).
    - Write comprehensive tests using `pytest` and `unittest.mock` (for mocking dependencies/API calls).
    - Ensure necessary `__init__.py` files exist in both `src` and `tests` subdirectories to make them packages.
    - **Import Hack:** Until a better solution (like `pyproject.toml`) is implemented, start test files with the `sys.path.insert(...)` boilerplate to ensure `src` is importable:
      ```python
      import sys
      import os
      sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
      # ... rest of imports ...
      ```
    - Use relative imports within tests (e.g., `from core.context_manager import ContextManager`).
- **Installation Reminder:** After updating `requirements.txt`, remind the user to run `pip install -r requirements.txt`.
- **Tool Usage:** Prioritize using pre-built LangChain tools and integrations. Only create custom tools (following LangChain conventions: `BaseTool`/`@tool`, Pydantic args) if a suitable pre-built option isn't available or doesn't meet specific security/functional requirements (like writing to designated paths).

---

This document provides a step-by-step implementation plan for building the Local LLM Terminal Environment, based on the requirements outlined in the PRD.md, the technologies defined in techstack.md, and the project structure (aligned with project-structure.md principles). This plan reflects the current state of development.

The plan is broken down into phases, starting with core components and building towards the full feature set.

## Phase 1: Core Foundation [COMPLETED]

**Goal:** Establish the fundamental capabilities for loading settings, interacting with the LLM, reading local files, and managing context sources.

**Step 1.1: Configuration Loading [COMPLETED]**

-   **Goal:** Create a utility to load application settings from `/config/settings.yaml` and environment variables (`.env`).
-   **File(s):** `src/utils/config_loader.py`, `config/settings.yaml`, `.env`
-   **Key Functionality:** Loads settings, prioritizes environment variables.
-   **Testing:** Tests written and passing in `tests/utils/test_config_loader.py`.

**Step 1.2: File Parsing (Markdown & YAML) [COMPLETED]**

-   **Goal:** Create utilities to read content from Markdown and YAML files.
-   **File(s):** `src/core/file_parser.py`
-   **Key Functionality:** `read_markdown(filepath)` and `read_yaml(filepath)` functions.
-   **Testing:** Tests written and passing in `tests/core/test_file_parser.py`.

**Step 1.3: Context Management (Initial) [COMPLETED]**

-   **Goal:** Create a module to gather and format context from static agent configuration files.
-   **File(s):** `src/core/context_manager.py`
-   **Key Functionality:**
    -   Aware of separate config (`/config`) and data (`/data`) directories (as defined in `config/settings.yaml`).
    -   `get_context(agent_name)` loads files (YAML/MD) from the agent's static config directory (`/config/agents/<agent_name>/`).
    -   Also loads global context from `/data/global_context/` (location may be revisited).
    -   Formats loaded content into structured strings.
-   **Testing:** Tests written and passing in `tests/core/test_context_manager.py`, verifying loading from correct directories.

**Step 1.4: LLM Interface (Core Class) [COMPLETED]**

-   **Goal:** Define a basic class to encapsulate LLM settings and basic interaction (used by the `ask` command).
-   **File(s):** `src/core/llm_interface.py`
-   **Key Functionality:**
    -   Initializes `ChatGoogleGenerativeAI` with settings from `ConfigLoader`.
    -   Provides `generate_text` method for simple, non-agentic LLM calls.
-   **Testing:** Tests written and passing in `tests/core/test_llm_interface.py`.

## Phase 2: CLI and Agent Framework Setup [COMPLETED]

**Goal:** Build the command-line entry points and integrate the LangChain Agent framework for structured interaction.

**Step 2.1: Basic CLI Structure (`ask` command) [COMPLETED]**

-   **Goal:** Set up the main CLI group and a simple, single-shot `ask` command.
-   **File(s):** `src/cli/main.py`
-   **Key Functionality:**
    -   Defines `cli` group using Click.
    -   Implements `ask` command taking query and optional `--agent`.
    -   Uses `LLMInterface` for direct LLM call, passing context loaded via `ContextManager`.
-   **Testing:** Basic integration test in `tests/cli/test_main.py`.

**Step 2.2: Agent Name Switching Logic (`ask` command) [COMPLETED]**

-   **Goal:** Allow specifying different agent configurations for the `ask` command.
-   **File(s):** `src/cli/main.py`
-   **Key Functionality:** `--agent` flag (`-a`) accepts an agent name, passed to `ContextManager` to load the appropriate static context from `/config/agents/`. Defaults to global context if flag is omitted. No CWD detection.
-   **Testing:** Covered by `ContextManager` tests and `ask` command integration test.

**Step 2.3: Initial Context Integration (`ask` command) [COMPLETED]**

-   **Goal:** Pass loaded static context to the LLM in the `ask` command.
-   **File(s):** `src/cli/main.py`
-   **Key Functionality:** `ask` command retrieves formatted context from `ContextManager` and passes it as `system_context` to `LLMInterface.generate_text`.
-   **Testing:** Verified manually; core logic tested via `ContextManager` tests.

**Step 2.4: Introduce Agent Executor Pattern [COMPLETED]**

-   **Goal:** Adopt the LangChain Agent Executor pattern for more complex interactions involving tools and memory, used by the `chat` command.
-   **File(s):** `src/cli/main.py`
-   **Key Functionality:**
    -   Added `load_agent_executor` function.
    -   This function loads agent configuration (`agent_meta.yaml`) and system prompt (`system_prompt.md`) from `/config/agents/<agent_name>/`.
    -   Integrates `ContextManager` to load additional static context files from the same directory and prepend them to the system prompt.
    -   Instantiates `ChatGoogleGenerativeAI` model based on global and agent-specific settings.
    -   Loads tools specified in `agent_meta.yaml` via `load_tools` helper.
    -   Creates a `ChatPromptTemplate` suitable for tool calling agents.
    -   Uses `create_tool_calling_agent` to define the agent logic.
    -   Instantiates the `AgentExecutor`.
-   **Testing:** Logic is exercised by the `chat` command tests/manual runs. Specific unit tests for `load_agent_executor` are deferred.

## Phase 3: REPL, Tools, and Memory [COMPLETED]

**Goal:** Implement an interactive chat loop, enable tool use, and manage conversation memory.

**Step 3.1: Restructure Config/Data Directories [COMPLETED]**

-   **Goal:** Separate static configuration from dynamic runtime data.
-   **File(s):** `config/settings.yaml`, directory structure, `src/core/context_manager.py`
-   **Key Functionality:** Defined `/config` for static definitions (app settings, agent configs) and `/data` for runtime data (agent outputs, memory, tool data). Updated `settings.yaml` and `ContextManager` accordingly.
-   **Testing:** Verified via `ContextManager` tests.

**Step 3.2: File I/O Tools (Initial - Write Only) [COMPLETED]**

-   **Goal:** Allow agents to write to their output directories safely.
-   **File(s):** `src/cli/main.py` (in `load_tools`), agent configs (`agent_meta.yaml`).
-   **Key Functionality:**
    -   Utilized `FileManagementToolkit` from `langchain-community`.
    -   Configured via `tools` list in `agent_meta.yaml`.
    -   **Write Access:** `file_management` key loaded the toolkit scoped to `/data/agents/<agent_name>/output/`.
-   **Testing:** File writing verified manually via REPL.

**Step 3.3: Interactive REPL Implementation [COMPLETED]**

-   **Goal:** Create an interactive chat interface.
-   **File(s):** `src/cli/main.py`
-   **Key Functionality:**
    -   Added `chat` command using Click.
    -   Uses `prompt_toolkit` for user input with history.
    -   Main loop handles user input, `/exit` command, and `/agent <name>` command for switching agents.
    -   Calls `load_agent_executor` on startup and agent switch.
    -   Invokes the current `AgentExecutor` with user input and chat history.
    -   Implemented per-agent, in-memory conversation history (`ConversationBufferMemory`) stored in a dictionary, preserving state during agent switches within a session.
    -   Added configurable logging (`--log-level`, `--verbose`) controlling both standard logs and `AgentExecutor` verbosity.
-   **Testing:** Verified manually. Specific unit/integration tests for REPL state deferred.

**Step 3.4: Agent Configuration Read/Write Tools [COMPLETED]**
- **Goal:** Allow agents to read their own static configuration files and write to their designated data directory.
- **Files:** `src/cli/main.py` (in `load_tools`), agent configs (`agent_meta.yaml`), `config/settings.yaml`.
- **Key Functionality:**
    - Modified `load_tools` in `src/cli/main.py`:
        - **Write Access:** Updated the `file_management` tool key scope to the agent's specific data directory: `data/agents/<agent_name>/`.
        - **Read-Only Config Access:** Added handling for `read_config_tool: true` in `agent_meta.yaml` to instantiate `FileManagementToolkit` scoped read-only to `config/agents/<agent_name>/`, renaming the tool to `read_agent_configuration_file`.
    - Updated `ContextManager` to load `agent_data_context.md` from `data/agents/<agent_name>/`.
    - Updated `load_agent_executor` to use the full formatted context from `ContextManager` directly.
    - **Permission Prompting:** Relied on instructions within the agent's system prompt.
    - **Agent-Specific Permissions:** Deferred.
- **Testing:** Manually tested via REPL.

**Step 3.5: Memory Persistence [COMPLETED]**

-   **Goal:** Save conversation history to disk so it persists between sessions and agent switches.
-   **File(s):** `src/cli/main.py`.
-   **Key Functionality:**
    -   Used JSON storage format (`data/agents/<agent_name>/memory/chat_history.json`).
    -   Modified `get_or_create_memory` to load history from JSON using `messages_from_dict`.
    -   Extracted saving logic into `save_agent_memory` helper function using `message_to_dict` list comprehension.
    -   Called `save_agent_memory` from `finally` block on exit.
    -   Called `save_agent_memory` before switching agents in the `/agent` command handler.
-   **Testing:** Tested saving and loading history across separate runs and agent switches.

## Backlog [NEXT]

**Goal:** Add more tools and refine agent behavior. Prioritize based on need.

**Implement Additional Tools [NEXT]**

-   **Goal:** Add tools for capabilities like web search, reading specific external documents (notes), calendar interaction, etc.
-   **File(s):** `src/tools/`, `src/cli/main.py` (in `load_tools`), agent configs.
-   **Key Functionality:**
    -   Identify needed tools (e.g., `langchain_community.tools.tavily_search.TavilySearchResults`).
    -   Implement custom tools if necessary (e.g., `ObsidianNoteReader`) following LangChain conventions (`@tool` or `BaseTool`). Define clear descriptions and argument schemas.
    -   Update `load_tools` to handle instantiation of new tools based on keys in `agent_meta.yaml`.
-   **Testing:** Write unit tests for custom tools. Test tool integration manually via REPL.

**Refine Context Formatting/Prompting**

-   **Goal:** Improve how static context, dynamic context (memory), and tool outputs are presented to the LLM for better performance and reasoning.
-   **File(s):** `src/cli/main.py` (prompt creation), agent prompt files.

**Agent Self-Correction/Improvement (Using Data Dir)**

-   **Goal:** Allow agents to suggest modifications or store learned preferences in their data directory.
-   **File(s):** Requires careful implementation of file I/O tools (Step 3.2, Step 4.1), prompt engineering.
-   **Key Functionality:** Use the `read_configuration_file` tool (read-only access to `/config`) and the standard `write_file` tool (scoped write access to `/data/agents/<agent_name>/output/` or a dedicated `/data/agents/<agent_name>/editable_state.yaml`) to allow the agent to read its base prompt, read/write its current editable state, and save *suggestions* or *new state* to the designated editable file in the data directory. Core prompt changes remain manual.

### Refinement, Testing, and Documentation

**Comprehensive Testing**
-   Add unit tests for agent loading, REPL state management.
-   Write integration tests for agent execution with tool calls.

**Documentation**
-   Update README with `chat` command usage, agent configuration details, tool setup.

**Code Review and Refinement**
-   Linting, formatting, docstrings, type hints.
-   Address warnings (Step 3.7 from `progress.md`).
-   Optimize memory usage (Step 3.6 from `progress.md`). Consider LangGraph migration if complexity warrants it.
