# Project Progress Log: Local LLM Terminal Environment

This document tracks the development progress of the Local LLM Terminal Environment project.

## Current Focus

- Working on Phase 4: REPL Enhancements, Tool Expansion, and Refinement - specifically focusing on implementing additional tools and getting visibility/token use.

## Completed Steps

### Phase 1: Core Foundation

- **[COMPLETED] Step 1.1: Configuration Loading**
    - Implemented `ConfigLoader` class in `src/utils/config_loader.py`.
    - Loads settings from `config/settings.yaml` and `.env`.
    - Prioritizes environment variables.
    - Added tests in `tests/utils/test_config_loader.py`.

- **[COMPLETED] Step 1.2: Context Management (Data Structure)**
    - Defined `ContextManager` class in `src/core/context_manager.py`.
    - Initial implementation focuses on loading context from files.
    - Handles global context and agent-specific contexts (`<agent_name>`).
    - Base directory configurable via `settings.yaml` (`data.base_dir`, `data.agents_dir`).
    - Added basic tests in `tests/core/test_context_manager.py`.

- **[COMPLETED] Step 1.3: LLM Interface**
    - Created `LLMInterface` class in `src/core/llm_interface.py`.
    - Uses LangChain and `langchain-google-genai`.
    - Configures model name, temperature, and API key via `ConfigLoader`.
    - Provides `generate_text` method.
    - Added basic tests in `tests/core/test_llm_interface.py`.


### Phase 2: CLI and Agent Framework Setup

- **[COMPLETED] Step 2.1: Basic CLI Structure (towards `chat`)**
    - Implemented initial CLI structure using `click` in `src/cli/main.py` (originally as `ask`, later refactored into `chat`).
    - Laid groundwork for instantiating `ConfigLoader`, `ContextManager`, and `LLMInterface`.
    - Tested basic command invocation and dependency mocking.

- **[COMPLETED] Step 2.2: Context Switching Logic (Agent Selection)**
    - Added logic to accept an optional `--agent <name>` (`-a <name>`) flag.
    - Ensured the agent name (or `None` for global-only) was passed to `ContextManager` for context loading.
    - Removed early ideas about automatic context detection based on CWD/Git, favoring explicit agent selection.

- **[COMPLETED] Step 2.3: Integrating Context into LLM Prompts**
    - Ensured `ContextManager.get_context` provided formatted context.
    - Integrated passing the `formatted_context` string to `LLMInterface` (initially for simple calls, later adapted for Agent system prompts).
    - Verified context inclusion using LangChain's `SystemMessage` mechanism.

- **[COMPLETED] Step 2.4: Introduce Agent Executor Pattern**
    - Adopted the LangChain Agent Executor pattern for more complex interactions involving tools and memory, used by the `chat` command.
    - Added `load_agent_executor` function, handling agent config, system prompt, context, LLM, tools, and creating the `AgentExecutor`.


### Phase 3: REPL, Tools, and Memory

- **[COMPLETED] Step 3.0: Restructure Config/Data Directories**
    - Separated static configuration (`/config`) from dynamic runtime data (`/data`).
    - Static agent definitions now reside in `/config/agents/<agent_name>/`.
    - Dynamic agent data will reside in `/data/agents/<agent_name>/`.
    - Updated `settings.yaml` and `ContextManager`.

- **[COMPLETED] Step 3.1: File I/O Tools (Initial - Write Only)**
    - Used LangChain's built-in `FileManagementToolkit`.
    - Scoped write access to `/data/agents/<agent_name>/output/`.

- **[COMPLETED] Step 3.2: Interactive REPL Implementation**
    - Created `chat` command using `prompt_toolkit`.
    - Implemented main loop, `/exit`, `/agent` commands.
    - Implemented per-agent in-memory conversation history (`ConversationBufferMemory`).
    - Added configurable logging.

- **[COMPLETED] Step 3.3: Agent Context Refactor & Tools**
    - Renamed agent config file to `agent_config.yaml`.
    - Simplified context loading (global + system prompt auto-loaded).
    - Added `read_config_tool` and updated `file_management` tool for accessing other files via agent.
    - Agents rely on prompt instructions + tools for accessing non-auto-loaded context.

- **[COMPLETED] Step 3.4: Memory Persistence**
    - Implemented saving/loading of conversation history to JSON (`data/agents/<agent_name>/memory/chat_history.json`).
    - Used `message_to_dict` and `messages_from_dict`.
    - Refactored saving logic into `save_agent_memory` helper.
    - History is saved on clean exit and before agent switching.


### Phase 4: REPL Enhancements, Tool Expansion, and Refinement

- **[COMPLETED] Refactor Chat Helpers**
    - Moved `get_memory_file_path` and `save_agent_memory` to `src/utils/chat_helpers.py`.

- **[COMPLETED] Session Summarization**
    - Created `generate_and_save_summary` helper.
    - Added `/summarize` command.
    - Added automatic summary generation on session exit.
    - Saved summary to `data/agents/<agent_name>/session_summary.md`.

- **[COMPLETED] Code Refactoring and Organization**
    - Created `src/utils/path_helpers.py`.
    - Created `src/core/agent_loader.py`.
    - Enhanced `src/utils/chat_helpers.py`.
    - Passed `config_loader` via Click context.
    - Removed `ask` command, made `chat` default.
    - Updated LangChain imports.


## Notes & Decisions

- Decided to prioritize YAML for structured data due to readability, but will keep JSON in mind for API ingest later (as per PRD).
- Confirmed `--no-sandbox` is needed for Cursor AppImage on Ubuntu 24.04 (development environment note).
- Decided to use LangChain's built-in `FileManagementToolkit` instead of a custom tool for initial file I/O.
- Removed early ideas about automatic context detection based on CWD/Git, favoring explicit agent selection via `--agent` flag.
- Formalized separation of static config (`/config`) and dynamic data (`/data`).
- Simplified automatic context loading to global + system prompt only.
- Implemented tool sandboxing to restrict agent file access.
- Implemented per-agent memory persistence using JSON.
- Implemented session summarization for context continuity.
- Refactored code into helper modules (`path_helpers`, `agent_loader`, `chat_helpers`).
- Addressed some LangChain deprecation warnings, but some remain.