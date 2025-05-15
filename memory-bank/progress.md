# Project Progress Log

This document tracks the active development progress.

## Current Focus: Memory Bank Cleanup & Radix UI Theming Preparation

**Status:** In Progress

**Goal:** Finalize the cleanup of the `memory-bank/` directory, ensuring all project context is consolidated, accurate, and current. Prepare for the implementation of Radix UI Theming in the Clarity web application.

**Completed Sub-Tasks (Memory Bank Cleanup):**

*   [X] Reviewed all files in `memory-bank/` and `memory-bank/clarity/`.
*   [X] Consolidated information from various outdated PRDs, implementation plans, and specific context documents into the primary Memory Bank files (`projectbrief.md`, `productContext.md`, `techContext.md`, `style-guide.md`, `tasks.md`).
*   [X] Archived historical progress logs (`memory-bank/clarity/progress.md` to `memory-bank/archive/clarity_historical_progress_log.md`; old `memory-bank/progress.md` to `memory-bank/archive/cli_historical_progress_log.md`).
*   [X] Moved `memory-bank/clarity/ddl.sql` to `data/db/ddl.sql`.
*   [X] Deleted numerous redundant/outdated files from `memory-bank/` and `memory-bank/clarity/` after merging their relevant content.
*   [X] Updated `tasks.md` to reflect new DDL location, reference RLS guide, and add a task to update `clarity-ui-api-development-guidance.md`.

**Next Steps:**

1.  **[ACTIVE]** Final check of remaining `memory-bank/` files to ensure no loose ends.
    *   Remaining files in `memory-bank/clarity/`: `clarity-ui-api-development-guidance.md`, `supabaseRLSGuide.md`, `UI Mockups/` (directory).
    *   Remaining files in `memory-bank/`: `projectbrief.md`, `productContext.md`, `techContext.md`, `style-guide.md`, `tasks.md`, `progress.md` (this file), `activeContext.md` (to be created/updated), `systemPatterns.md` (to be created/updated if distinct from `techContext.md`), `chatGPTConvo.md`.
2.  **[TODO]** Initialize/Update `memory-bank/activeContext.md` to reflect the immediate next goal (Radix UI Theming).
3.  **[TODO]** Initialize/Update `memory-bank/systemPatterns.md` (if necessary, to be distinct from pattern info already in `techContext.md`). Currently, `techContext.md` has a section for key implementation patterns which might suffice.
4.  **[TODO]** Transition to **IMPLEMENT mode** for Radix UI Theming once Memory Bank cleanup is fully verified.

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
- **Refactored tool loading** to be configuration-driven (`tools_config` in YAML) instead of hardcoded logic in `agent_loader.py` for improved maintainability.
- **Visibility Feature Attempt & Revert (2025-05-05):**
    - Attempted to implement visibility for tool calls and token usage using a custom `AgentCallbackHandler` (`src/utils/callbacks.py`).
    - Goal was to provide cumulative token counts per turn via `-t` flag and tool logs via `-v` flag.
    - Encountered persistent `500 InternalServerError` from Google API after implementing the callback handler, potentially related to agent looping.
    - Observed numerous `Convert_system_message_to_human will be deprecated!` warnings, indicating possible conflict between the agent type (`create_react_agent`), Gemini model, and prompt structure.
    - Debugging steps (simplifying prompt) did not resolve the 500 errors.
    - Reverted all code changes related to the callback handler and CLI flags (`main.py`, `chat_helpers.py`, `agent_loader.py`, `system_prompt.md`) to restore stability.
    - Kept necessary fixes identified during debugging (tool loading logic, scope mapping, agent config file loading).
    - Removed deprecated `convert_system_message_to_human=True` flag from `ChatGoogleGenerativeAI` initialization.
    - Switched agent creation from `create_react_agent` back to `create_tool_calling_agent` as part of the revert.
    - Visibility feature is on hold pending re-evaluation of the approach.

### Architect Agent Implementation (Phase 1 & 2.1)

- **[COMPLETED] Architect - Step 1.1: Create Agent Configuration**
    - Created `config/agents/architect/agent_config.yaml` with initial structure and system prompt.

- **[COMPLETED] Architect - Step 1.2 & 2.1: Update Agent Loading & Implement Tools (via Refactor)**
    - Refactored tool loading in `src/core/agent_loader.py` to be configuration-driven via `tools_config` in agent YAML files, removing agent-specific code.
    - Defined scopes (`PROJECT_ROOT`, `MEMORY_BANK`, `AGENT_DATA`, etc.) resolved by `path_helpers`.
    - Updated `assistant` and `architect` agent configs (`tools_config`) for their respective tools and scopes (project-read, memory-bank-rw, agent-data-rw for architect).
    - Added `get_memory_bank_dir` helper to `src/utils/path_helpers.py`.
    - Updated documentation (`systemPatterns.md`, `architecture.md`, `prd.md`) to reflect the new approach.

- **[COMPLETED] Architect - Step 1.3: Integrate into REPL**
    - Confirmed `/agent architect` command works without changes to `src/cli/main.py` due to the generic agent loading mechanism.

- **[COMPLETED] Architect - Step 2.2: Refine Prompt for Backlog Management**
    - Updated the `system_prompt` in `config/agents/architect/agent_config.yaml` to be more directive about workflow, backlog format, information elicitation, and tool usage.

- **[COMPLETED] Architect - Step 3.1: Implement Agent Memory & Session Context**
    - Verified existing memory persistence logic in `chat_helpers.py` is agent-agnostic.
    - Updated `agent_loader.py` to load the previous `session_log.md` into the initial agent prompt for context continuity.
    - Simplified the summary generation prompt in `chat_helpers.py` accordingly.

- **[COMPLETED] Architect - Step 3.2: Enhance Prompt for Grooming Tasks**
    - Added specific instructions to the system prompt in `config/agents/architect/agent_config.yaml` for handling backlog grooming tasks.

## Notes & Decisions

- Refactored code into helper modules (`path_helpers`, `agent_loader`, `chat_helpers`).
- Addressed some LangChain deprecation warnings, but some remain.
- **Refactored tool loading** to be configuration-driven (`tools_config` in YAML) instead of hardcoded logic in `agent_loader.py` for improved maintainability.

### Project Tooling & Evaluation

- **LangSmith Evaluation Setup for Agent Permissions (2025-05-06):**
    - **Goal:** Create a robust evaluation suite to test the 'architect' agent's adherence to file writing permissions and its resistance to adversarial prompts.
    - **Key Activities & Files:**
        - Developed `langsmith/eval-permissions.py`: A script to define a LangSmith dataset, run the 'architect' agent against it, and use an LLM-as-judge (Gemini 1.5 Flash with structured output) for evaluation.
        - Created `langsmith/judge_prompts/permission_eval_instructions.md` to store the detailed instructions for the LLM judge.
        - Iteratively debugged `eval-permissions.py`, resolving issues related to Python import paths (by adding project root to `sys.path` and using `src.` prefixes for internal imports), LangSmith client API changes (e.g., `llm_or_chain_factory`, dataset attribute names), and prompt input key mismatches (`question` vs. `input`).
        - The script now successfully connects to LangSmith, creates/updates the dataset, and initiates the evaluation run.
    - **File Organization:** Moved the diagnostic script `agentExecutorTest.py` to `scripts/scratch/agentExecutorTest.py`.

## Notes & Decisions

- Refactored code into helper modules (`path_helpers`, `agent_loader`, `chat_helpers`).

## IMPLEMENT Mode: UI/UX Enhancements - Radix UI Theming & Semantic Tokens

**Current Phase:** Task II.1: Radix UI Theme Foundation and Semantic Token Refactor - COMPLETED

**Last Major Action:** Completed Task II.1.5 by documenting advanced theming with Radix UI Themes (accent/gray color changes, other Theme props, Radix props vs. Tailwind guidance) in `memory-bank/style-guide.md`.

**Current Focus:** All sub-tasks for "II.1: Radix UI Theme Foundation and Semantic Token Refactor" are now complete. Ready to move to the next major UI/UX task area.

**Next Steps:** Proceed to **Task II.2: Keyboard Navigability Audit & Implementation** as per `tasks.md`.

**Overall Task II Status (Radix UI Theming & Semantic Tokens):** COMPLETED

## IMPLEMENT Mode: UI/UX Enhancements - Keyboard Navigation

**Current Phase:** Task II.2: Keyboard Navigability Audit & Implementation

**Last Major Action:** Completed Task II.1 (Radix UI Theme Foundation and Semantic Token Refactor).

**Current Focus:** Task II.2.1: Comprehensive Keyboard Navigation Audit. Created `memory-bank/keyboard_nav_audit.md` with an initial checklist. The next step is to systematically go through the application, test keyboard interaction for all elements and flows, and document findings in this audit file.

**Next Steps:** Conduct the manual keyboard audit using the checklist. Identify and document any issues related to focus visibility, focus order, element activation, keyboard traps, and ARIA attribute usage.

**Overall Task II.2 Status (Keyboard Navigability):** In Progress