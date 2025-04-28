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

## Phase 3: Tools, Memory, and Refinement

- **[COMPLETED] Step 3.0: Restructure Config/Data Directories**
  - Separated static configuration (`/config`) from dynamic runtime data (`/data`).
  - Static agent definitions (base context, prompts) now reside in `/config/agents/<agent_name>/`.
  - Dynamic agent data (outputs, memory) will reside in `/data/agents/<agent_name>/`.
  - Updated `config/settings.yaml` with new paths (`config.base_dir`, `config.agents_dir`, etc.).
  - Refactored `ContextManager` to load static agent context from the new config path.
  - Updated `ContextManager` tests (`temp_dirs` fixture, assertions) to match the new structure.

- **[ ] Step 3.1: File Writing Tool**
  - Define a mechanism/format for the LLM to request writing to a file (e.g., function call signature, specific output format like JSON/XML).
  - Implement a `FileWriterTool` class/function (e.g., in `src/tools/file_writer.py`) that takes `filename` and `content` (potentially `mode` like 'append'/'overwrite').
  - Ensure the tool writes files *only* within a safe, agent-specific directory (e.g., `data/agents/<agent_name>/output/`). Handle path validation and errors.
  - Modify the main application flow (`cli/main.py` or `LLMInterface`) to:
    - Inform the LLM about the tool's availability and usage.
    - Detect tool use requests in the LLM response.
    - Parse arguments (filename, content) from the response.
    - Execute the `FileWriterTool`.
    - Optionally, report the execution outcome (success/failure) back to the LLM.
  - Add tests for the `FileWriterTool`.

- **[ ] Step 3.2: Memory Implementation (Placeholder)**
  - Design and implement conversation history storage.

- **[ ] Step 3.3: Tool Loading/Discovery (Placeholder)**
  - Implement a way to load tools dynamically based on configuration or agent needs.

- **[ ] Step 3.4: Refine Context Formatting/Prompting (Placeholder)**
  - Improve how context is presented to the LLM.
