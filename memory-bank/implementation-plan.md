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
        
- **Get Visibility and Token Use [ON HOLD]**
    
    - **Goal:** Add output to show token usage after each agent turn in the REPL.
    - **Proposed Approach (Minimal Callback Handler):**
        - **Rationale:** Direct inspection of the `AgentExecutor`'s final response or the message stored in memory showed that `usage_metadata` was `None`, even though direct LLM calls populate it. Testing confirmed a callback handler *can* access the populated metadata during the `on_llm_end` event before the AgentExecutor finishes processing.
        - **File(s):** `src/cli/main.py`, `src/utils/chat_helpers.py`, `src/core/agent_loader.py`, `src/utils/callbacks.py` (New)
        - **Key Functionality:**
            - Create a simple `BaseCallbackHandler` (e.g., `TokenUsageCallbackHandler` in `callbacks.py`) with an attribute to store captured metadata (e.g., `self.captured_metadata = None`).
            - Implement `on_llm_end` in the handler to extract token usage from the `response: LLMResult` object (likely via `response.generations[0][0].message.usage_metadata`) and store it in `self.captured_metadata`.
            - Modify `load_agent_executor` (`agent_loader.py`) to instantiate this handler.
            - Modify `process_user_command` (`chat_helpers.py`):
                - Receive the handler instance (needs mechanism to pass it, e.g., return it alongside executor from `load_agent_executor` and store/pass in `main.py`).
                - Add the `--show-tokens` / `-t` flag to the `chat` command in `main.py` and pass it to `process_user_command`.
                - After `agent_executor.invoke`, if the flag is set, retrieve `handler.captured_metadata`.
                - Print the formatted token usage if metadata was captured.
                - Reset `handler.captured_metadata = None` for the next turn.
    - **Testing:** Run `chat` with `-t`. Verify token usage is printed after agent response. Check callback logs if needed.

## Future Phases & Backlog

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

*   **[COMPLETED] Step 1.1: Create Agent Configuration**
    *   **Goal:** Define the basic configuration file for the Architect agent.
    *   **File(s):** `config/agents/architect/agent_config.yaml` (New)
    *   **Key Functionality:** Create the YAML file specifying the agent's name, description, system prompt (initial draft incorporating brainstorming/structuring goals and knowledge of core docs), LLM configuration (referencing global settings), and required tools (initially file read/write tool identifiers).
    *   **Tech Stack:** YAML
    *   **AI Assistance Guidance:** Draft the initial `agent_config.yaml` including a comprehensive system prompt based on the refined requirements and the `architect-prompt` rule definition. Ensure the prompt emphasizes referencing core documents and guiding the user through the backlog refinement process.
    *   **Testing:** Manual verification of the YAML structure. Review the drafted system prompt for clarity and coverage of requirements.

*   **[COMPLETED] Step 1.2: Update Agent Loading Logic**
    *   **Goal:** Ensure the new Architect agent can be discovered and loaded by the application.
    *   **File(s):** `src/core/agent_loader.py`
    *   **Key Functionality:** Modify `load_agent_config` and potentially `load_tools` (or related functions) to handle the Architect agent. Ensure the specific tool loading logic for 'architect' (as detailed in Step 2.1) is implemented here.
    *   **Tech Stack:** Python, LangChain
    *   **AI Assistance Guidance:** Identify the necessary code changes in `agent_loader.py` to load the new agent type and trigger the specific tool instantiation logic required for 'architect'.
    *   **Testing:** Unit test agent loading for 'architect'. Manually test loading the agent in the REPL (`/agent architect`). Verify tool permissions once Step 2.1 is complete.
    *   **Note:** This step was completed as part of the tool loading refactor described below Step 2.1. The core agent loading logic did not require changes, but the tool loading did.

*   **[COMPLETED] Step 1.3: Integrate into REPL**
    *   **Goal:** Make the Architect agent selectable in the REPL interface.
    *   **File(s):** `src/cli/main.py`, potentially `src/utils/chat_helpers.py`
    *   **Key Functionality:** Ensure the `/agent architect` command works correctly, loading the agent configuration and switching the context. Update any agent listing logic if necessary.
    *   **Tech Stack:** Python, `prompt_toolkit`
    *   **AI Assistance Guidance:** Review `main.py` and `chat_helpers.py` to confirm the agent switching mechanism handles the new agent. Add 'architect' to any relevant lists or discovery mechanisms.
    *   **Testing:** Manually test switching to and from the 'architect' agent using the `/agent` command in the REPL.

**Phase 2: Core Functionality - Backlog Interaction**

*   **[COMPLETED] Step 2.1: Implement Split-Scope File System Tools**
    *   **Goal:** Provide the agent with tools to read from the entire project and write specifically to the `memory-bank` directory.
    *   **File(s):** `src/core/agent_loader.py`, `config/agents/architect/agent_config.yaml`, `config/agents/assistant/agent_config.yaml`
    *   **Key Functionality:** 
        *   **Refactoring:** Instead of hardcoding agent-specific logic in `load_tools`, refactored tool loading to be entirely configuration-driven via a new `tools_config` section in `agent_config.yaml`. Each entry defines the final tool name, the underlying `toolkit`, the `scope` (e.g., `PROJECT_ROOT`, `MEMORY_BANK`, `AGENT_DATA`), the `original_name` of the tool in the toolkit, and an optional `description` override.
        *   The `load_tools` function in `agent_loader.py` now parses `tools_config`, groups requirements by toolkit instance (class + scope) for efficiency, instantiates the toolkit (e.g., `FileManagementToolkit`) with the correct `root_dir` and `selected_tools`, and applies the final name/description.
        *   Updated `architect` and `assistant` agent YAML files to use the new `tools_config` structure.
        *   Added tools scoped to `AGENT_DATA` for the architect agent to allow memory persistence.
        *   Updated relevant documentation (`systemPatterns.md`, `architecture.md`, `prd.md`).
        *   **Original Plan Details (Implemented via Refactor):**
            *   ~~Instantiate a read-only `FileManagementToolkit` scoped to the project root... Rename tools...~~
            *   ~~Instantiate a separate `FileManagementToolkit` scoped strictly to the `memory-bank` directory... Rename tools...~~
            *   ~~Ensure the agent's system prompt... explains which tool variant to use...~~
        *   **Note:** This step requires updating the "Tool Sandboxing" section in `memory-bank/systemPatterns.md` to document the Architect agent's specific project-wide read and `memory-bank` write permissions, which differ from the standard agent sandbox. [Documentation Update Complete]
    *   **Tech Stack:** Python, LangChain (`FileManagementToolkit`)
    *   **AI Assistance Guidance:** Modify `load_tools` to instantiate two `FileManagementToolkit` instances for the 'architect' agent as described. Implement any necessary helper functions (like `get_memory_bank_dir`). Define clear names and descriptions for the distinct read/write/list tools. Add checks to ensure this logic only applies to the 'architect' agent unless configured otherwise. [Refactored to configuration-driven approach]
    *   **Testing:** Unit tests for the modified `load_tools` logic for the architect. Integration test: within the REPL, ask the Architect agent to read a file from the project root (`src/cli/main.py`) using `read_project_file`. Ask it to read `memory-bank/backlog.md` using `read_memory_bank_file`. Ask it to write a change to `memory-bank/backlog.md` using `write_memory_bank_file`. Verify that attempts to write outside `memory-bank` using any tool fail or are disallowed by the agent's instructions/tool availability. [Manual Testing Passed]

*   **[COMPLETED] Step 2.2: Refine Prompt for Backlog Management**
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

*   **[COMPLETED] Step 3.1: Implement Agent Memory**
    *   **Goal:** Enable persistent memory for the Architect agent across sessions.
    *   **File(s):** `src/utils/chat_helpers.py`, `src/cli/main.py`, `src/core/agent_loader.py`
    *   **Key Functionality:** 
        *   Verified existing memory loading/saving mechanism in `chat_helpers.py` uses agent-specific paths correctly.
        *   Implemented loading of the previous session's summary (`session_log.md`) within `load_agent_executor` in `agent_loader.py` and prepended it to the agent's system prompt for context continuity.
        *   Simplified the summary generation prompt in `chat_helpers.py` to focus only on summarizing the current session's memory.
    *   **Tech Stack:** Python, JSON/File I/O
    *   **AI Assistance Guidance:** Review the memory handling in `chat_helpers.py` and `main.py`. Ensure the logic correctly identifies the current agent ('architect') and uses the corresponding data directory (`data/agents/architect/`) for loading and saving memory files (e.g., `memory.json`, `summary.txt`). [Verified - Updated `agent_loader.py` to load previous summary into prompt.]
    *   **Testing:** Start a chat, interact with the architect agent, exit. Restart the application, switch back to the architect agent, and verify if the previous conversation context is recalled (e.g., ask "what were we just talking about?"). Verify summary is generated correctly and loaded on next startup. [Passed]

*   **[COMPLETED] Step 3.2: Enhance Prompt for Grooming Tasks**
    *   **Goal:** Enable the agent to assist with backlog grooming tasks beyond just creation/refinement.
    *   **File(s):** `config/agents/architect/agent_config.yaml`
    *   **Key Functionality:** Updated the system prompt to include specific instructions and workflow for grooming activities: identifying related items, suggesting splits for large items, marking items (deferred/duplicate), prompting for refinement on items marked "Needs Refinement," and assisting with re-prioritization (by rewriting sections of `backlog.md` based on user direction using the `write_memory_bank_file` tool).
    *   **Tech Stack:** YAML (Prompt Engineering)
    *   **AI Assistance Guidance:** Add specific instructions to the system prompt regarding grooming tasks. For example: "If the user asks to groom the backlog, read `memory-bank/backlog.md` using the appropriate tool, identify items marked 'Needs Refinement', and ask the user if they want to refine any. You can also help reorder items or mark them as deferred/duplicate if requested, using the `write_memory_bank_file` tool."
    *   **Testing:** Manual testing in the REPL. Ask the agent to "help groom the backlog," "find items related to X," "mark item Y as deferred," "move item Z higher in the priority." Verify its ability to understand and execute these requests by checking the changes in `memory-bank/backlog.md`.

### Backlog Item: Add Visibility for Tool Calls and Token Usage - [REPLACED]

**[DELETED - Replaced by simpler approach above]**

**Original Plan (Using Custom Callback Handler):**
*   **Step 1: Research Token Usage Retrieval (Completed - Feasible)**
*   **Step 2: Implement Custom Callback Handler (Attempted)**
*   **Step 3: Integrate Handler and CLI Flags (Attempted)**

**Issues Encountered & Revert Reason (2025-05-05):**
*   Persistent `500 InternalServerError` from Google API.
*   `Convert_system_message_to_human` warnings (when using `create_react_agent`).
*   Potential agent looping/instability.
*   **Decision:** Reverted all code changes related to this feature.

**Next Steps (Obsolete):**
*   Re-evaluate the approach...
*   Investigate root cause...
*   Consider simpler methods...

**Original Plan Details (Pre-Revert):**
```
# --- Original Plan Steps (Preserved for reference) ---
# Step 1: Research Token Usage Retrieval
# ...
# Step 2: Implement Custom Callback Handler for Tracking and Logging
# ...
# Step 3: Integrate Handler and CLI Flags
# ...
# Note on Documentation: ...
```