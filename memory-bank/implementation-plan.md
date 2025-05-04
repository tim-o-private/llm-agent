# Implementation Plan: Local LLM Terminal Environment

This document provides a step-by-step implementation plan for building the Local LLM Terminal Environment, based on the requirements outlined in the PRD.md, the technologies defined in techstack.md, and the project structure. This plan reflects the current state of development and outlines upcoming tasks.

**AI Assistant Development Guidelines:**

- **Dependencies:** When adding new functionality that requires external libraries, update `requirements.txt` with the necessary packages and minimum versions (e.g., `some-library>=1.2.0`). Ensure `langchain-community` is included for toolkits.
    
- **Testing:**
    
    - For every new module/class/function in `src/`, create a corresponding test file in `tests/` mirroring the directory structure (e.g., `src/core/foo.py` -> `tests/core/test_foo.py`).
            - Write comprehensive tests using `pytest` and `unittest.mock` (for mocking dependencies/API calls).
            - Ensure necessary `__init__.py` files exist in both `src` and `tests` subdirectories to make them packages.
            - **Import Hack:** Until a better solution (like `pyproject.toml`) is implemented, start test files with the `sys.path.insert(...)` boilerplate to ensure `src` is importable:
                ```
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
        # ... rest of imports ...
        ```
            - Use relative imports within tests (e.g., `from core.context_manager import ContextManager`).
        - **Installation Reminder:** After updating `requirements.txt`, remind the user to run `pip install -r requirements.txt`.
    
- **Tool Usage:** Prioritize using pre-built LangChain tools and integrations. Only create custom tools (following LangChain conventions: `BaseTool`/`@tool`, Pydantic args) if a suitable pre-built option isn't available or doesn't meet specific security/functional requirements (like writing to designated paths).
    

<!-- Sections below this line have been moved to backlog.md -->

## Upcoming Phases and Steps
        
### Phase 4: REPL Enhancements, Tool Expansion, and Refinement

- **Implement Additional Tools**
    
    - **Goal:** Add tools for capabilities like web search, reading specific external documents (notes), calendar interaction, etc.
            - **File(s):** `src/tools/`, `src/cli/main.py` (in `load_tools`), agent configs.
            - **Key Functionality:**
                - Identify needed tools (e.g., `langchain_community.tools.tavily_search.TavilySearchResults`).
            
        - Implement custom tools if necessary (e.g., `ObsidianNoteReader`) following LangChain conventions (`@tool` or `BaseTool`). Define clear descriptions and argument schemas.
            
        - Update `load_tools` to handle instantiation of new tools based on keys in `agent_meta.yaml`.
            
    - **Testing:** Write unit tests for custom tools. Test tool integration manually via REPL.
        - **Get Visibility and Token Use**
    
    - **Goal:** Add logging or output to show tool calls and token usage during agent execution.
            - **File(s):** `src/cli/main.py`, `src/core/llm_interface.py`
            - **Key Functionality:**
                - Configure LangChain verbosity or add custom logging to track tool calls and their inputs/outputs.
            
        - Investigate how to access token usage information from the `langchain-google-genai` integration.
            
        - Display this information in the REPL output based on verbosity settings.
            
    - **Testing:** Verify output manually or with specific logging tests.
        
## Future Phases & Backlog

- **[ON HOLD] Step 4.5: Compile Application into Executable**
    
    - **Goal:** Create a standalone executable for easier distribution.
            - **File(s):** `src/utils/path_helpers.py`, `src/utils/config_loader.py`, build configuration (e.g., `.spec` file).
            - **Key Functionality:**
                - Modify path handling to work with bundled resources.
            
        - Use a tool like PyInstaller.
            
    - **Testing:** Test executable in a clean environment.
            - _Note: Task paused due to unresolved issues with PyInstaller's `--add-data` not correctly bundling the config directory. Needs further investigation or potentially manual .spec file editing._
        - **Refine Context Formatting/Prompting**
    
    - **Goal:** Improve how static context, dynamic context (memory), and tool outputs are presented to the LLM for better performance and reasoning.
            - **File(s):** `src/cli/main.py` (prompt creation), agent prompt files.
        - **Agent Self-Correction/Improvement (Using Data Dir)**
    
    - **Goal:** Allow agents to suggest modifications or store learned preferences in their data directory (e.g., `agent_prompt.md`).
            - **Files:** Requires file I/O tools, prompt engineering.
            - **Key Functionality:** Use `read_config_tool` (read-only config) and `file_system_write_file` / `file_system_read_file` (R/W data) to allow the agent to read its base prompt/config, read/write `agent_prompt.md`, and save suggestions or state. Core prompt changes remain manual.
        - **Comprehensive Testing**
    
    - **Goal:** Add unit tests for agent loading, REPL state management, and integration tests for agent execution with tool calls.
            - **File(s):** `tests/` directory.
        - **Documentation**
    
    - **Goal:** Update README with `chat` command usage, agent configuration details, tool setup, and other relevant information.
            - **File(s):** `README.md`.
        - **Optimize Memory Usage (Low Priority)**
    
    - **Goal:** Investigate strategies for managing long-term conversation memory (e.g., Summarization, Token Buffers) to handle very long chat sessions efficiently.
            - **File(s):** `src/utils/chat_helpers.py`, potentially `src/core/llm_interface.py`.
        - **[PARTIALLY ADDRESSED] Address LangChainDeprecationWarnings**
    
    - **Goal:** Update LangChain imports and usage to eliminate remaining deprecation warnings.
            - **File(s):** Various files in `src/`.
            - _Note: Some warnings were addressed during Code Refactoring, but a full audit is needed._
        
### Code Review Follow-ups

- **Logging:** Use a dedicated application logger instead of modifying the root logger (`main.py`). Use `logger.error` instead of `print` in `file_parser.py` exceptions.
    
- **Error Handling:** Improve granularity and user-facing messages during agent loading (`main.py`, `agent_loader.py`). Clarify error handling if `agent_config_dir` is missing when `read_config_tool` is needed (`agent_loader.py`).
    
- **Code Clarity/Readability:** Consider returning a dataclass/dict from `process_user_command` for state updates (`main.py`, `chat_helpers.py`). Abstract tool configuration/renaming logic in `load_tools` (`agent_loader.py`). Refine LLM parameter handling logic (`agent_loader.py`). Make prompt construction from `agent_config` more explicit (include list vs. exclude list) (`agent_loader.py`). Clean up `ContextManager`: update docstring, remove unused attributes/parameters. Remove unnecessary `pass` in `main.py`.
    
- **LangChain Usage:** Investigate using standard `AgentExecutor` memory integration instead of manual load/save in `chat_helpers.py`; document if manual approach is required. Ensure summary prompt aligns with available tools (`chat_helpers.py`).
    
- **Packaging:** Replace `sys.path` hack with proper packaging (`main.py`, `tests/`).
    
- **UX:** Add `prompt_toolkit` command completer (`main.py`).