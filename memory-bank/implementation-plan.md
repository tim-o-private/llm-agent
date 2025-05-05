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

## Implementation Plan: Create 'Architect' Agent

**Backlog Item:** Create 'Architect' Agent

**Phase 1: Agent Configuration and Basic Loading**

*   **Step 1.1: Create Agent Configuration**
    *   **Goal:** Define the basic configuration file for the Architect agent.
    *   **File(s):** `config/agents/architect/agent_config.yaml` (New)
    *   **Key Functionality:** Create the YAML file specifying the agent's name, description, system prompt (initial draft incorporating brainstorming/structuring goals and knowledge of core docs), LLM configuration (referencing global settings), and required tools (initially file read/write tool identifiers).
    *   **Tech Stack:** YAML
    *   **AI Assistance Guidance:** Draft the initial `agent_config.yaml` including a comprehensive system prompt based on the refined requirements and the `architect-prompt` rule definition. Ensure the prompt emphasizes referencing core documents and guiding the user through the backlog refinement process.
    *   **Testing:** Manual verification of the YAML structure. Review the drafted system prompt for clarity and coverage of requirements.

*   **Step 1.2: Update Agent Loading Logic**
    *   **Goal:** Ensure the new Architect agent can be discovered and loaded by the application.
    *   **File(s):** `src/core/agent_loader.py`
    *   **Key Functionality:** Modify `load_agent_config` and potentially `load_tools` (or related functions) to handle the Architect agent. Ensure the specific tool loading logic for 'architect' (as detailed in Step 2.1) is implemented here.
    *   **Tech Stack:** Python, LangChain
    *   **AI Assistance Guidance:** Identify the necessary code changes in `agent_loader.py` to load the new agent type and trigger the specific tool instantiation logic required for 'architect'.
    *   **Testing:** Unit test agent loading for 'architect'. Manually test loading the agent in the REPL (`/agent architect`). Verify tool permissions once Step 2.1 is complete.

*   **Step 1.3: Integrate into REPL**
    *   **Goal:** Make the Architect agent selectable in the REPL interface.
    *   **File(s):** `src/cli/main.py`, potentially `src/utils/chat_helpers.py`
    *   **Key Functionality:** Ensure the `/agent architect` command works correctly, loading the agent configuration and switching the context. Update any agent listing logic if necessary.
    *   **Tech Stack:** Python, `prompt_toolkit`
    *   **AI Assistance Guidance:** Review `main.py` and `chat_helpers.py` to confirm the agent switching mechanism handles the new agent. Add 'architect' to any relevant lists or discovery mechanisms.
    *   **Testing:** Manually test switching to and from the 'architect' agent using the `/agent` command in the REPL.

**Phase 2: Core Functionality - Backlog Interaction**

*   **Step 2.1: Implement Split-Scope File System Tools**
    *   **Goal:** Provide the agent with tools to read from the entire project and write specifically to the `memory-bank` directory.
    *   **File(s):** `src/core/agent_loader.py`
    *   **Key Functionality:** In `load_tools`, when loading tools for the 'architect' agent:
        1.  Instantiate a read-only `FileManagementToolkit` scoped to the project root (e.g., `ConfigLoader.get_workspace_root()`). Select only read-related tools (`read_file`, `list_directory`). Rename these tools clearly (e.g., `read_project_file`, `list_project_directory`).
        2.  Instantiate a separate `FileManagementToolkit` scoped strictly to the `memory-bank` directory (e.g., `get_memory_bank_dir(config_loader)` - helper needed). Select read/write tools (`read_file`, `write_file`, `list_directory`). Rename these tools clearly (e.g., `read_memory_bank_file`, `write_memory_bank_file`, `list_memory_bank_directory`).
        3.  Ensure the agent's system prompt (Step 2.2) clearly explains which tool variant to use for which operation and scope.
        *   **Note:** This step requires updating the "Tool Sandboxing" section in `memory-bank/systemPatterns.md` to document the Architect agent's specific project-wide read and `memory-bank` write permissions, which differ from the standard agent sandbox.
    *   **Tech Stack:** Python, LangChain (`FileManagementToolkit`)
    *   **AI Assistance Guidance:** Modify `load_tools` to instantiate two `FileManagementToolkit` instances for the 'architect' agent as described. Implement any necessary helper functions (like `get_memory_bank_dir`). Define clear names and descriptions for the distinct read/write/list tools. Add checks to ensure this logic only applies to the 'architect' agent unless configured otherwise.
    *   **Testing:** Unit tests for the modified `load_tools` logic for the architect. Integration test: within the REPL, ask the Architect agent to read a file from the project root (`src/cli/main.py`) using `read_project_file`. Ask it to read `memory-bank/backlog.md` using `read_memory_bank_file`. Ask it to write a change to `memory-bank/backlog.md` using `write_memory_bank_file`. Verify that attempts to write outside `memory-bank` using any tool fail or are disallowed by the agent's instructions/tool availability.

*   **Step 2.2: Refine Prompt for Backlog Management**
    *   **Goal:** Optimize the agent's system prompt to effectively guide conversations towards creating and refining well-structured backlog items.
    *   **File(s):** `config/agents/architect/agent_config.yaml`
    *   **Key Functionality:** Iterate on the system prompt based on initial testing. Explicitly instruct the agent on:
        *   The target format (`backlog.md` structure).
        *   The key elements to elicit (Problem/Goal, User Value, Functional Req, Non-Functional, Approach, Dependencies, Effort, Ready for PRD criteria).
        *   How to use file tools (distinguishing between project read and memory-bank write tools).
        *   How to handle brainstorming vs. structuring phases.
        *   How to attempt effort estimation (S/M/L).
    *   **Tech Stack:** YAML (Prompt Engineering)
    *   **AI Assistance Guidance:** Refine the system prompt in `agent_config.yaml` to be more directive regarding the backlog definition process. Add specific instructions on asking clarifying questions based on the "Definition & Refinement Guidance", attempting effort estimation, and using the correct file tools (`read_project_file` vs. `write_memory_bank_file`).
    *   **Testing:** Manual testing through conversation in the REPL. Try defining a new simple backlog item. Try refining an existing (hypothetical) vague item. Evaluate the agent's ability to follow the format, ask relevant questions, and use file tools appropriately.

**Phase 3: Memory and Grooming Assistance**

*   **Step 3.1: Implement Agent Memory**
    *   **Goal:** Enable persistent memory for the Architect agent across sessions.
    *   **File(s):** `src/utils/chat_helpers.py`, `src/cli/main.py`
    *   **Key Functionality:** Adapt the existing memory loading/saving mechanism (currently used by `assistant`) to work for the Architect agent, storing its history/summary in `data/agents/architect/`. Ensure memory is loaded at the start of a session with the agent and saved on exit or agent switch.
    *   **Tech Stack:** Python, JSON/File I/O
    *   **AI Assistance Guidance:** Review the memory handling in `chat_helpers.py` and `main.py`. Ensure the logic correctly identifies the current agent ('architect') and uses the corresponding data directory (`data/agents/architect/`) for loading and saving memory files (e.g., `memory.json`, `summary.txt`).
    *   **Testing:** Start a chat, interact with the architect agent, exit. Restart the application, switch back to the architect agent, and verify if the previous conversation context is recalled (e.g., ask "what were we just talking about?").

*   **Step 3.2: Enhance Prompt for Grooming Tasks**
    *   **Goal:** Enable the agent to assist with backlog grooming tasks beyond just creation/refinement.
    *   **File(s):** `config/agents/architect/agent_config.yaml`
    *   **Key Functionality:** Update the system prompt to include instructions for grooming activities: identifying related items, suggesting splits for large items, marking items (deferred/duplicate), prompting for refinement on items marked "Needs Refinement," and assisting with re-prioritization (by rewriting sections of `backlog.md` based on user direction using the `write_memory_bank_file` tool).
    *   **Tech Stack:** YAML (Prompt Engineering)
    *   **AI Assistance Guidance:** Add specific instructions to the system prompt regarding grooming tasks. For example: "If the user asks to groom the backlog, read `memory-bank/backlog.md` using the appropriate tool, identify items marked 'Needs Refinement', and ask the user if they want to refine any. You can also help reorder items or mark them as deferred/duplicate if requested, using the `write_memory_bank_file` tool."
    *   **Testing:** Manual testing in the REPL. Ask the agent to "help groom the backlog," "find items related to X," "mark item Y as deferred," "move item Z higher in the priority." Verify its ability to understand and execute these requests by checking the changes in `memory-bank/backlog.md`.