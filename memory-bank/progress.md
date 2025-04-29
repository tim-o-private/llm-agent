# Project Progress

## Phase 1: Core Foundation

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

## Phase 2: CLI and Core Logic

- **[COMPLETED] Step 2.1: Basic CLI Structure (`ask` command)**
  - Implemented initial CLI using `click` in `src/cli/main.py`.
  - Created a basic `ask` command that takes a query.
  - Instantiates `ConfigLoader`, `ContextManager`, and `LLMInterface`.
  - Calls `LLMInterface.generate_text` with the query (handling context via `ContextManager`).
  - Prints the LLM response.
  - Added tests in `tests/cli/test_main.py` mocking dependencies.
- **[COMPLETED] Step 2.2: Context Switching Logic**
  - Modified `ask` command in `src/cli/main.py` to accept an optional `--agent <name>` (`-a <name>`) flag using `click.option` with `type=str`.
  - If `--agent` is given, the provided `<name>` is passed to `ContextManager.get_context`.
  - If `--agent` is *not* given, `None` is passed to `ContextManager.get_context`, indicating that only global context should be used.
  - Removed the requirement for automatic context detection based on CWD/Git.
- **[COMPLETED] Step 2.3: Integrating Context into LLM Prompts**
  - `ContextManager.get_context` returns both raw and formatted context.
  - The `ask` command in `src/cli/main.py` passes the `formatted_context` string to `LLMInterface.generate_text` via the `system_context` parameter.
  - `LLMInterface` uses LangChain's `SystemMessage` to include the `system_context` in the messages list sent to the Gemini model (using `convert_system_message_to_human=True`).
  - Verified with a live test using an agent context file (`data/agents/test_agent/context.yaml`) and querying information contained within it.
  - Corrected path configuration in `config/settings.yaml` to ensure context files are loaded from the correct directories (e.g., `data/agents/<name>/`).
- **[COMPLETED] Step 2.4: Integrate Agent Executor Pattern**
  - Added `load_agent_executor` function to load agent config, prompt, tools (via `load_tools`), and context.
  - Uses `create_tool_calling_agent` and `AgentExecutor`.
  - Integrated `ContextManager` loading into this process.

## Phase 3: REPL, Tools, and Memory

- **[COMPLETED] Step 3.0: Restructure Config/Data Directories**
  - Separated static configuration (`/config`) from dynamic runtime data (`/data`).
  - Static agent definitions (base context, prompts) now reside in `/config/agents/<agent_name>/`.
  - Dynamic agent data (outputs, memory) will reside in `/data/agents/<agent_name>/`.
  - Updated `config/settings.yaml` with new paths (`config.base_dir`, `config.agents_dir`, etc.).
  - Refactored `ContextManager` to load static agent context from the new config path.
  - Updated `ContextManager` tests (`temp_dirs` fixture, assertions) to match the new structure.

- **[COMPLETED] Step 3.1: File I/O Tools (Initial - Write Only)**
  - Decided to use LangChain's built-in `FileManagementToolkit` instead of a custom tool.
  - Added `load_tools` function in `cli/main.py`.
  - When `file_management` is listed in an agent's `agent_meta.yaml` (`tools` list), `load_tools` instantiates `FileManagementToolkit` with `root_dir` set to the agent-specific output directory (`data/agents/<agent_name>/output/`) for sandboxing.
  - Ensured the `AgentExecutor` in `load_agent_executor` is created with the loaded tools.
  - Verified via manual testing in the `chat` REPL that the agent can successfully use the `write_file` tool from the toolkit to write a file within its designated output directory.

- **[COMPLETED] Step 3.2: Interactive REPL Implementation**
  - Created new `chat` command in `src/cli/main.py`.
  - Implemented agent loading (`load_agent_executor`) which reads `agent_meta.yaml`, loads the specified system prompt, combines it with other static context files loaded via `ContextManager`, creates LLM instance, and builds `AgentExecutor` using `create_tool_calling_agent`.
  - Integrated `prompt_toolkit` for user input with history.
  - Implemented REPL loop handling user input, `/exit`, and `/agent <name>` commands.
  - Implemented per-agent in-memory conversation history (`ConversationBufferMemory`) using a dictionary, allowing state persistence when switching agents during a session.
  - Integrated configurable logging (`--log-level` option) and controlled `AgentExecutor` verbosity.
  - Integrated ContextManager loading into agent loading process.
  - *Note:* Specific unit/integration tests for REPL state and agent loading are deferred.

- **[COMPLETED] Step 3.3: Agent Context Refactor & Tools**
  - Renamed agent config file to `agent_config.yaml`.
  - Simplified context loading: Only global context (`data/global_context/`) and the agent's specified system prompt (`config/agents/<name>/system_prompt.md`) are loaded automatically.
  - Agent config details (`description`, etc. from `agent_config.yaml`) are formatted and added to the prompt.
  - Added `read_config_tool` (read-only access to `config/agents/<name>/`) and updated `file_management` tool (R/W access to `data/agents/<name>/`).
  - Agents rely on prompt instructions + tools to access other context files (e.g., `data/agents/<name>/agent_prompt.md`).

- **[COMPLETED] Step 3.4: Memory Persistence**
  - Implemented saving/loading of conversation history to JSON (`data/agents/<agent_name>/memory/chat_history.json`).
  - Used `message_to_dict` and `messages_from_dict` for serialization/deserialization.
  - Refactored saving logic into `save_agent_memory` helper.
  - History is saved on clean exit and before agent switching via `/agent` command.

## Phase 4: Backlog / Future Work

- **[NEXT] Implement Additional Tools**
  - Identify and integrate tools like web search (e.g., Tavily), external document readers, etc.
  - Define custom tools if needed.
  - Update `load_tools` to handle new tool configurations.

- **[ ] Refine Context Formatting/Prompting**
  - Improve how context is presented to the LLM.

- **[ ] Agent Self-Correction/Improvement**
  - Explore allowing agents to modify their state/preferences within their data directory.

- **[ ] Comprehensive Testing**
  - Add unit tests for REPL state, agent loading.
  - Add integration tests for tool use.

- **[ ] Documentation**
  - Update README (Done for current state, keep updated).

- **[ ] Optimize Memory Usage (Low Priority)**
  - Investigate strategies for managing long-term conversation memory (e.g., Summarization, Token Buffers).

- **[ ] Address LangChain Warnings (Low Priority)**
  - Investigate `LangChainDeprecationWarning` for `ConversationBufferMemory`.
  - Update to newer patterns if appropriate.
