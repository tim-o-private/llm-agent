# Implementation Plan: Local LLM Terminal Environment

This document provides a step-by-step implementation plan for building the Local LLM Terminal Environment, based on the requirements outlined in the PRD.md, the technologies defined in techstack.md, and the project structure. This plan reflects the current state of development and outlines upcoming tasks.

**AI Assistant Development Guidelines:**

- **Dependencies:** When adding new functionality that requires external libraries, update `requirements.txt` with the necessary packages and minimum versions (e.g., `some-library>=1.2.0`). Ensure `langchain-community` is included for toolkits.
    
- **Testing:**
    
    - For every new module/class/function in `src/`, create a corresponding test file in `tests/` mirroring the directory structure (e.g., `src/core/foo.py` -> `tests/core/test_foo.py`).
            - Write comprehensive tests using `pytest` and `unittest.mock` (for mocking dependencies/API calls).
            - Ensure necessary `__init__.py` files exist in both `src` and `tests` subdirectories to make them packages.
            - Use absolute imports from the package root within tests (e.g., `from core.context_manager import ContextManager`).
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
*   **Step 2: Implement Custom Callback Handler for Tracking and Logging
*   **Step 3: Integrate Handler and CLI Flags
*   **Note on Documentation: ...**

## Implementation Plan: Refactor Project Structure for Proper Packaging and Module Imports

**Backlog Item:** Refactor Project Structure for Proper Packaging and Module Imports

**Overall Goal:** Transition the project from using `sys.path` manipulations for imports to a standard Python packaging setup (e.g., using `pyproject.toml` and `setuptools`), making the project more robust, maintainable, and easier to test and distribute.

**Phase 1: Setup Packaging and Basic Conversion**

*   **Step 1.1: Choose Packaging Tools and Create Configuration**
    *   **Goal:** Decide on the packaging tools (e.g., `setuptools` with `pyproject.toml`) and create the initial packaging configuration file.
    *   **File(s):** `pyproject.toml` (New)
    *   **Key Functionality:**
        *   Research and decide between `setuptools` (with `pyproject.toml`), `poetry`, or other modern Python packaging tools. (Recommendation: `setuptools` with `pyproject.toml` for broad compatibility).
        *   Create `pyproject.toml` with basic project metadata (name, version, author), dependencies (from `requirements.txt`), and configuration for `setuptools` to find packages (e.g., in `src`).
    *   **Tech Stack:** `pyproject.toml`, `setuptools`
    *   **AI Assistance Guidance:** "Draft a `pyproject.toml` file using `setuptools` as the build backend. Include project name 'LocalLLMTerminalEnv', version '0.2.0' (or current). List dependencies by referencing `requirements.txt` or by manually transcribing them. Configure `setuptools` to find packages in the `src` directory."
    *   **Testing:**
        *   Validate `pyproject.toml` syntax.
        *   Attempt to build a source distribution (e.g., `python -m build --sdist`) to verify basic setup.

*   **Step 1.2: Make Project Installable in Editable Mode**
    *   **Goal:** Ensure the project can be installed in editable mode (`pip install -e .`) so that changes in `src` are immediately reflected.
    *   **File(s):** `pyproject.toml` (Updates if necessary), `src/**/__init__.py` (New/Verify)
    *   **Key Functionality:**
        *   Ensure `pyproject.toml` is correctly configured for editable installs.
        *   Add `__init__.py` files to all necessary directories within `src` to make them discoverable as packages/modules (e.g., `src/core/__init__.py`, `src/utils/__init__.py`, `src/cli/__init__.py`, and any subdirectories containing Python modules).
    *   **Tech Stack:** Python, `pip`, `setuptools`
    *   **AI Assistance Guidance:** "Identify all directories under `src/` that should be Python packages and ensure an empty `__init__.py` file exists in each. Guide on how to verify editable install."
    *   **Testing:**
        *   Run `pip install -e .` from the project root.
        *   In a Python interpreter, try importing a module from `src` (e.g., `from core import agent_loader`) to confirm successful installation.

**Phase 2: Update Imports and Remove Hacks**

*   **Step 2.1: Remove `sys.path` Hacks**
    *   **Goal:** Remove all manipulations of `sys.path` from the codebase, particularly in test files and any entry points.
    *   **File(s):** All `tests/**/*.py` files, `src/cli/main.py` (if applicable), any other script using `sys.path.insert` or `sys.path.append`.
    *   **Key Functionality:** Delete lines of code that modify `sys.path`.
    *   **Tech Stack:** Python
    *   **AI Assistance Guidance:** "Search for all occurrences of `sys.path.insert` and `sys.path.append` in the project, especially in `tests/` and `scripts/`, and prepare an edit to remove them."
    *   **Testing:** After removal, tests will likely fail until imports are fixed in the next step. This is expected.

*   **Step 2.2: Update Import Statements**
    *   **Goal:** Modify all import statements throughout the project (`src` and `tests`) to use absolute imports based on the new package structure (e.g., `from core.agent_loader import ...` or `from utils.chat_helpers import ...`).
    *   **File(s):** All `*.py` files in `src/` and `tests/`.
    *   **Key Functionality:**
        *   Change relative imports (like `from ..utils import something`) or old top-level imports that relied on `sys.path` hacks to absolute imports from the `src` package (e.g., `from src.core.some_module import MyClass` becomes `from core.some_module import MyClass` assuming `src` is the root package source).
        *   For tests, imports will also be absolute, e.g., `from core.agent_loader import AgentExecutor`.
    *   **Tech Stack:** Python
    *   **AI Assistance Guidance:** "Analyze import statements in all Python files. For files in `src/`, ensure imports of other `src/` modules are absolute from the package root (e.g., `from core.config_loader import ...`). For files in `tests/`, ensure they import `src/` modules absolutely (e.g., `from core.agent_loader import ...`). Provide edits."
    *   **Testing:**
        *   Run `pytest`. Most tests should now pass if imports are correct and the editable install works.
        *   Run the main application (`python -m src.cli.main chat`) to ensure it starts and basic functionality is intact.

**Phase 3: Finalize and Document**

*   **Step 3.1: Update Documentation and CI/CD**
    *   **Goal:** Update any project documentation (README, contributing guides) and CI/CD scripts to reflect the new packaging structure and build/test process.
    *   **File(s):** `README.md`, `.github/workflows/*.yml` (if exists), any developer documentation, `memory-bank/implementation-plan.md`.
    *   **Key Functionality:**
        *   Update setup instructions to use `pip install -e .`.
        *   Ensure CI/CD pipelines correctly install dependencies and run tests with the new structure.
        *   Remove the "Import Hack" note from `memory-bank/implementation-plan.md` (under "AI Assistant Development Guidelines").
    *   **Tech Stack:** Markdown, YAML (for GitHub Actions)
    *   **AI Assistance Guidance:** "Review `README.md` for setup instructions and update them. If a GitHub Actions workflow exists for testing, review it to ensure it will work with the new packaging (it likely will if it uses `pip install -r requirements.txt` followed by `pip install -e .`). Prepare an edit for `memory-bank/implementation-plan.md` to remove the import hack boilerplate."
    *   **Testing:**
        *   Manually follow setup instructions in `README.md`.
        *   If CI/CD exists, trigger a build to verify it passes.

## Implementation Plan: Investigate and Fix Failing Pytest Suite

**Backlog Item:** Investigate and Fix Failing Pytest Suite

**Overall Goal:** Diagnose and resolve all failures in the Pytest suite to ensure a reliable testing foundation for the project, enabling confident code changes and feature development.

**Phase 1: Initial Diagnosis and Triage**

*   **Step 1.1: Execute Test Suite and Categorize Failures**
    *   **Goal:** Run the entire Pytest suite and systematically categorize the types of failures and errors observed.
    *   **File(s):** Test output logs.
    *   **Key Functionality:**
        *   Execute `pytest` from the project root.
        *   Collect all error messages and tracebacks.
        *   Group failures by common patterns (e.g., import errors, assertion errors, specific exceptions like `FileNotFoundError`, mock errors).
    *   **Tech Stack:** `pytest`
    *   **AI Assistance Guidance:** "Suggest `pytest` command options to maximize verbosity and capture output (e.g., `pytest -vv > test_failures.log`). Help analyze the output to identify common error types."
    *   **Testing:** N/A (This step is diagnostic)

*   **Step 1.2: Prioritize Fixes (Focus on Systemic Issues First)**
    *   **Goal:** Identify if systemic issues (like widespread import errors due to recent packaging changes, or problems with test environment setup) are causing a large number of failures.
    *   **File(s):** Test failure analysis from Step 1.1.
    *   **Key Functionality:**
        *   Analyze categorized failures to see if a few root causes are responsible for many errors.
        *   Hypothesize primary blockers (e.g., "If all import errors are fixed, X% of tests might pass").
    *   **Tech Stack:** Analytical skills.
    *   **AI Assistance Guidance:** "Based on the categorized failures, help determine if there are overarching issues (e.g., if many tests fail with `ModuleNotFoundError`, this points to a systemic import problem that should be addressed before individual test logic)."
    *   **Testing:** N/A (This step is analytical)

**Phase 2: Addressing Systemic Failures (If Applicable)**

*   **Step 2.1: Address Widespread Import/Environment Issues**
    *   **Goal:** Fix any identified systemic problems related to imports (likely linked to the packaging refactor) or test environment configuration.
    *   **File(s):** `pyproject.toml`, `tests/**/*.py`, `conftest.py` (if it exists), CI configuration files.
    *   **Key Functionality:**
        *   If import errors are prevalent, ensure the packaging refactor (previous backlog item) is complete and correctly implemented (editable install works, `__init__.py` files are in place, imports are absolute).
        *   Check `conftest.py` for any fixtures or configurations that might be causing widespread issues.
        *   Verify that `requirements.txt` (or `pyproject.toml` dependencies) includes all necessary testing libraries.
    *   **Tech Stack:** Python, `pytest`, `setuptools`
    *   **AI Assistance Guidance:** "If import errors are common, cross-reference with the packaging implementation plan to ensure all steps were completed. Suggest checks for `__init__.py` files in `src/` and `tests/` directories, and verify absolute imports in test files."
    *   **Testing:** Re-run `pytest` after changes. Observe if a significant number of previously failing tests now pass.

**Phase 3: Fixing Individual Test Failures**

*   **Step 3.1: Iteratively Fix Test Groups**
    *   **Goal:** Work through the categorized test failures group by group, or file by file, to fix the underlying issues in test logic or source code.
    *   **File(s):** Specific `tests/**/*.py` files and corresponding `src/**/*.py` files.
    *   **Key Functionality:**
        *   For each failing test:
            *   Understand the test's purpose.
            *   Analyze the assertion failure or exception.
            *   Debug the test and the code it's testing.
            *   Update mocks if external calls or dependencies have changed.
            *   Modify test logic or source code as needed.
    *   **Tech Stack:** Python, `pytest`, `unittest.mock`
    *   **AI Assistance Guidance:** "For a given failing test (provide error and test code), help diagnose the issue. If it's a mock error, suggest how to update the mock. If it's an assertion error, help compare actual vs. expected. If the source code logic seems to have changed, help identify the relevant change."
    *   **Testing:** Run `pytest <path_to_specific_test_file>` or `pytest -k <test_function_name>` frequently to confirm fixes for individual tests.

*   **Step 3.2: Ensure All Tests Pass**
    *   **Goal:** Continue fixing tests until the entire suite (`pytest`) runs successfully with no failures or errors.
    *   **File(s):** All `tests/**/*.py` and `src/**/*.py` files.
    *   **Key Functionality:** Diligent debugging and fixing.
    *   **Tech Stack:** Python, `pytest`
    *   **AI Assistance Guidance:** "Provide ongoing support for diagnosing and fixing individual test failures as they are tackled."
    *   **Testing:** The final `pytest` run shows all tests passing.

**Phase 4: Refinement and Documentation (If Needed)**

*   **Step 4.1: Refactor Tests for Clarity/Efficiency (Optional)**
    *   **Goal:** If, during the fixing process, tests are found to be poorly written, duplicative, or inefficient, refactor them.
    *   **File(s):** `tests/**/*.py`
    *   **Key Functionality:** Improve test readability, reduce redundancy using fixtures, improve mock strategies.
    *   **Tech Stack:** `pytest`
    *   **AI Assistance Guidance:** "If a test looks overly complex or has a lot of boilerplate, suggest ways to simplify it using `pytest` fixtures or by improving its structure."
    *   **Testing:** Ensure refactored tests still pass and correctly cover the intended functionality.

*   **Step 4.2: Document Any Common Pitfalls or Solutions**
    *   **Goal:** If common issues were found (e.g., a particular way mocks needed to be updated), document this for future reference.
    *   **File(s):** Developer notes, potentially `README.md` or a `CONTRIBUTING.md`.
    *   **Key Functionality:** Briefly note any patterns or solutions that were key to fixing the test suite.
    *   **Tech Stack:** Markdown
    *   **AI Assistance Guidance:** "Help summarize any recurring themes or tricky fixes encountered during the process that might be useful for future test development."
    *   **Testing:** N/A

## Implementation Plan: Prepare Project for Public Release: Scrub Sensitive Data

**Backlog Item:** Prepare Project for Public Release: Scrub Sensitive Data

**Overall Goal:** Ensure that no sensitive personal data, chat logs, or private configurations are included when the project is prepared for public release on GitHub.

**Phase 1: Identification and Strategy**

*   **Step 1.1: Identify All Sensitive Files and Data Types**
    *   **Goal:** Create a comprehensive list of all files, directories, and types of data within the project that should be considered sensitive and not for public release.
    *   **File(s):** Project file structure, potentially a temporary checklist document.
    *   **Key Functionality:**
        *   Review project directories: `memory-bank/` (especially chat histories, detailed plans that might contain private thoughts), `data/agents/*/memory/`, `data/agents/*/session_log.md`.
        *   Check configuration files for any accidentally committed secrets (though `.env` should prevent this for API keys).
        *   Consider if any example files or test data might contain sensitive placeholders.
    *   **Tech Stack:** File system navigation, text search.
    *   **AI Assistance Guidance:** "Based on the project structure (provide if necessary, or I can list common sensitive locations), help enumerate typical files and directories that should be scrubbed. For example: `memory-bank/*`, `data/agents/**/chat_history.json`, `data/agents/**/session_log.md`, `.env` file (though this should already be in `.gitignore`)."
    *   **Testing:** Review the generated list for completeness.

*   **Step 1.2: Define Scrubbing Strategy**
    *   **Goal:** Decide on the method for excluding or cleaning sensitive data for the public release.
    *   **File(s):** `.gitignore`, potentially a new script for cleaning.
    *   **Key Functionality:**
        *   **Option A (Recommended for `memory-bank` and dynamic agent data):** Add sensitive directories/files (like `memory-bank/`, `data/agents/*/memory/`, `data/agents/*/session_log.md`) to `.gitignore` so they are never committed. Provide example/template structures for these directories instead.
        *   **Option B (For specific files that need versions):** Create a script to clean or anonymize specific files if they need to exist in the public repo but in a sanitized form.
        *   **Option C (For one-time cleanup):** Manually delete or clean files before the initial public commit.
        *   Ensure `.env` is in `.gitignore`.
    *   **Tech Stack:** `.gitignore` syntax, shell scripting (if Option B).
    *   **AI Assistance Guidance:** "Discuss the pros and cons of using `.gitignore` vs. a cleaning script for `memory-bank/` and agent-specific data. Recommend using `.gitignore` and providing template structures for users."
    *   **Testing:** N/A (Strategy definition).

**Phase 2: Implementation of Scrubbing**

*   **Step 2.1: Update `.gitignore`**
    *   **Goal:** Add all identified sensitive files and directories that should be entirely excluded from the public repository to the `.gitignore` file.
    *   **File(s):** `.gitignore`
    *   **Key Functionality:**
        *   Add patterns like:
            ```
            # Sensitive data and logs
            memory-bank/
            data/agents/*/memory/
            data/agents/*/session_log.md
            *.env
            logs/
            ```
        *   Ensure these files are not already tracked by Git (use `git rm --cached <file>` if they are).
    *   **Tech Stack:** `.gitignore` syntax, Git CLI.
    *   **AI Assistance Guidance:** "Draft the additions for the `.gitignore` file. Provide `git` commands to unstage already tracked files if necessary (e.g., `git rm -r --cached memory-bank/`)."
    *   **Testing:**
        *   Run `git status` to ensure the ignored files/directories no longer appear as modified or untracked (unless they are new and untracked).
        *   Verify that `git clean -fdx` (with caution, or `-fdxn` for a dry run) would remove these items if they existed locally but were untracked.

*   **Step 2.2: Create Template/Example Structures (If Needed)**
    *   **Goal:** If directories like `memory-bank/` are ignored, provide template files or a README within those locations to guide users on how to structure their own data.
    *   **File(s):** e.g., `memory-bank/README.md`, `memory-bank/backlog.template.md`, `data/agents/README.md`.
    *   **Key Functionality:**
        *   Create placeholder READMEs or template files (e.g., `backlog.example.md`, `prd.example.md`) in the now-ignored directories to show users the expected structure.
        *   These template files *would* be committed to the repository.
    *   **Tech Stack:** Markdown.
    *   **AI Assistance Guidance:** "Suggest content for a `memory-bank/README.md` that explains its purpose and how users can create their own `backlog.md`, `prd.md`, etc. Suggest creating empty template files like `backlog.example.md`."
    *   **Testing:** Check that these template files are tracked by Git and provide useful guidance.

*   **Step 2.3: Implement Cleaning Script (If Opted for Option B in 1.2)**
    *   **Goal:** If any files need to be version-controlled but sanitized, create a script to perform this cleaning.
    *   **File(s):** e.g., `scripts/scrub_data.sh` or `scripts/scrub_data.py`.
    *   **Key Functionality:** Script to remove specific sections, anonymize names, or clear content from specified files.
    *   **Tech Stack:** Shell scripting or Python.
    *   **AI Assistance Guidance:** "If a cleaning script is needed for specific files, help draft the script logic (e.g., regex for removing certain patterns, JSON parsing for anonymizing fields)."
    *   **Testing:** Run the script on sample files and verify the output is correctly sanitized.

**Phase 3: Verification and Documentation**

*   **Step 3.1: Final Review Before Public Push**
    *   **Goal:** Perform a final check of the repository to ensure no sensitive data remains before making it public or pushing changes related to scrubbing.
    *   **File(s):** Entire project repository.
    *   **Key Functionality:**
        *   Manually browse files that were borderline or where scrubbing was applied.
        *   Use search tools to look for common sensitive keywords or patterns.
        *   Double-check `git status` and the `.gitignore` rules.
    *   **Tech Stack:** Git CLI, text search tools.
    *   **AI Assistance Guidance:** "Suggest common keywords or regex patterns to search for to catch accidentally committed sensitive data (e.g., email addresses, API key patterns, common personal identifiers if they were ever in notes)."
    *   **Testing:** Thorough manual review.

*   **Step 3.2: Document Data Handling for Users/Contributors**
    *   **Goal:** Update project documentation (e.g., `README.md` or `CONTRIBUTING.md`) to explain how sensitive data is handled, what users need to create locally (e.g., their own `memory-bank`), and how to manage their `.env` file.
    *   **File(s):** `README.md`, `CONTRIBUTING.md`.
    *   **Key Functionality:** Explain which directories are in `.gitignore` and why, and how users should set up their local environment for personal data.
    *   **Tech Stack:** Markdown.
    *   **AI Assistance Guidance:** "Draft a section for `README.md` explaining that `memory-bank/` and agent chat histories are not committed, and users should create their own. Also, reiterate `.env` usage for API keys."
    *   **Testing:** Read the documentation from a new user's perspective to ensure clarity.

## Implementation Plan: Implement CI/CD Pipeline for Automated Pytest on PRs

**Backlog Item:** Implement CI/CD Pipeline for Automated Pytest on PRs

**Overall Goal:** Set up a Continuous Integration (CI) pipeline using GitHub Actions to automatically run the Pytest suite on every Pull Request (PR) against the main development branch, blocking merges if tests fail.

**Phase 1: Basic Workflow Setup**

*   **Step 1.1: Create GitHub Actions Workflow File**
    *   **Goal:** Create the basic YAML file for the GitHub Actions workflow.
    *   **File(s):** `.github/workflows/python-pytest.yml` (New)
    *   **Key Functionality:**
        *   Define the workflow name (e.g., "Python Pytest CI").
        *   Specify triggers: `on: [pull_request]` (targeting `main` or `develop` branch).
    *   **Tech Stack:** YAML (GitHub Actions syntax)
    *   **AI Assistance Guidance:** "Draft the initial structure for `.github/workflows/python-pytest.yml`, including the `name` and `on: pull_request` trigger for the main branch."
    *   **Testing:** Commit the workflow file and open a test PR to see if the action is triggered (it will likely fail at this stage as no jobs are defined).

*   **Step 1.2: Define a Job to Checkout Code and Set Up Python**
    *   **Goal:** Add a job to the workflow that checks out the repository code and sets up the correct Python version.
    *   **File(s):** `.github/workflows/python-pytest.yml`
    *   **Key Functionality:**
        *   Define a job (e.g., `build` or `test`) that `runs-on: ubuntu-latest`.
        *   Add steps:
            *   `actions/checkout@vX` (use a recent version, e.g., v3 or v4)
            *   `actions/setup-python@vX` (use a recent version) specifying the Python version used by the project (e.g., 3.10, 3.11).
    *   **Tech Stack:** YAML (GitHub Actions syntax)
    *   **AI Assistance Guidance:** "Add a job named `test` that runs on `ubuntu-latest`. Include steps for `actions/checkout@v4` and `actions/setup-python@v5` with Python version 3.11 (or user-specified version)."
    *   **Testing:** Push changes to the test PR. Verify the workflow runs, checks out code, and sets up Python successfully.

**Phase 2: Dependency Installation and Test Execution**

*   **Step 2.1: Install Project Dependencies**
    *   **Goal:** Add steps to install the project's dependencies as defined in `requirements.txt` (and `pip install -e .` if using packaging).
    *   **File(s):** `.github/workflows/python-pytest.yml`
    *   **Key Functionality:**
        *   Add a step to install dependencies:
            ```yaml
            - name: Install dependencies
              run: |
                python -m pip install --upgrade pip
                pip install -r requirements.txt
                # If project uses packaging (pyproject.toml):
                pip install -e .
            ```
    *   **Tech Stack:** YAML (GitHub Actions syntax), `pip`
    *   **AI Assistance Guidance:** "Add a step named 'Install dependencies' that upgrades pip, installs from `requirements.txt`, and then runs `pip install -e .` (assuming the packaging refactor is complete)."
    *   **Testing:** Push changes to the test PR. Verify the workflow installs dependencies without error.

*   **Step 2.2: Run Pytest**
    *   **Goal:** Add a step to execute the Pytest suite.
    *   **File(s):** `.github/workflows/python-pytest.yml`
    *   **Key Functionality:**
        *   Add a step to run tests:
            ```yaml
            - name: Test with pytest
              run: pytest
            ```
    *   **Tech Stack:** YAML (GitHub Actions syntax), `pytest`
    *   **AI Assistance Guidance:** "Add a step named 'Test with pytest' that simply runs the `pytest` command."
    *   **Testing:** Push changes to the test PR.
        *   If tests are currently failing, this step *should* fail, and the PR check should reflect this.
        *   If tests are passing, this step should pass.

**Phase 3: Branch Protection and Refinements**

*   **Step 3.1: Configure Branch Protection Rules**
    *   **Goal:** Configure GitHub branch protection rules for the main development branch to require the "Python Pytest CI" (or whatever name was chosen) check to pass before merging.
    *   **File(s):** N/A (Configuration in GitHub repository settings)
    *   **Key Functionality:**
        *   Go to Repository Settings -> Branches -> Add branch protection rule.
        *   Select the main branch (e.g., `main`).
        *   Check "Require status checks to pass before merging."
        *   Search for and select the name of your CI job/workflow.
    *   **Tech Stack:** GitHub UI
    *   **AI Assistance Guidance:** "Provide instructions on how to navigate GitHub settings to set up branch protection rules, requiring the specific CI job to pass."
    *   **Testing:** Attempt to merge a PR with failing tests (if any exist); GitHub should block it. Merge a PR with passing tests; GitHub should allow it.

*   **Step 3.2: Optimize Workflow (Optional)**
    *   **Goal:** Add caching for dependencies to speed up workflow runs.
    *   **File(s):** `.github/workflows/python-pytest.yml`
    *   **Key Functionality:**
        *   Use `actions/cache@vX` to cache `pip` dependencies.
            ```yaml
            - name: Cache pip dependencies
              uses: actions/cache@v3 # Or newer
              with:
                path: ~/.cache/pip
                key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
                restore-keys: |
                  ${{ runner.os }}-pip-
            ```
        *   Place this step before dependency installation.
    *   **Tech Stack:** YAML (GitHub Actions syntax)
    *   **AI Assistance Guidance:** "Add a caching step for pip dependencies using `actions/cache@v3` (or newer), configured to use `requirements.txt` for the cache key."
    *   **Testing:** Observe workflow run times; subsequent runs after the first one with caching should be faster in the dependency installation step.