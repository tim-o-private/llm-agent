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

**Overall Task II.2 Status (Keyboard Navigability):** COMPLETED (Initial Audit & Fixes - Advanced shortcuts are future scope)

## IMPLEMENT Mode: UI/UX Enhancements - Drag-and-Drop Task Reordering

**Current Phase:** Task II.3: Drag-and-Drop Task Reordering (within Today View list, using `dnd-kit`)

**Last Major Action:** Successfully debugged and implemented persistence for drag-and-drop reordering. This involved:
*   Correcting React Query key invalidation in `useUpdateTaskOrder`.
*   Ensuring the `Task` type in `webApp/src/api/types.ts` includes the `position` field.
*   Modifying `useFetchTasks` to order by the `position` field.
*   Verifying keyboard accessibility for drag-and-drop.

**Current Focus:** Core drag-and-drop functionality (including persistence and keyboard accessibility) is now complete.

**Next Steps:** Styling and interaction refinements for drag-and-drop handle and keyboard accessibility are now complete.

**Overall Task II.3 Status (Drag-and-Drop Reordering - Core Functionality):** COMPLETED
**Overall Task II.3.5 Status (Drag-and-Drop Styling/Interaction Refinements):** COMPLETED

## V. UI Implementation: Fast Task Entry, TaskDetailView, Subtasks (P-P-E-R Phase 1)

**Overall Goal:** Implement core UI features for enhanced task management as defined in `memory-bank/creative/creative-PER-cycle.md` (Fast Task Entry, TaskDetailView, Subtask Display).

**Status:** In Progress

**1. Implement Fast Task Entry Mechanism**
    *   **Status:** COMPLETED
    *   **Key Files Created/Modified:**
        *   `webApp/src/utils/taskParser.ts` (Created)
        *   `webApp/src/components/features/TodayView/FastTaskInput.tsx` (Created)
        *   `webApp/src/pages/TodayView.tsx` (Integrated `FastTaskInput`, added hotkey 'T' focusing, and callback for query invalidation).
        *   `webApp/src/api/hooks/useTaskHooks.ts` (Verified `useCreateTask` suitability).
        *   `webApp/src/api/types.ts` (Verified `NewTaskData` suitability).
    *   **Summary:** A `FastTaskInput` component is now at the top of `TodayView`. Pressing 'T' focuses it. It parses input for title, priority (p0-p3), and description (d:/desc:), then calls `useCreateTask`. Task list refreshes on creation. New tasks receive focus.

**2. Implement TaskDetailView**
    *   **Status:** In Progress (Core modal, form for basic fields, save, and trigger from TaskCard implemented. Keyboard navigation for focus within TodayView and triggering TaskDetailView also implemented.)
    *   **Depends on:** DDL/Types for `Task` (all fields) and Subtasks are complete.
    *   **Components & Files:**
        *   `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` (Created: Modal with form for Title, Description, Notes, Status, Priority; Save functionality).
        *   `webApp/src/api/hooks/useTaskHooks.ts` (Created `useFetchTaskById`; `useUpdateTask` utilized).
        *   `webApp/src/pages/TodayView.tsx` (Integrated opening `TaskDetailView`, state management, callbacks for update/delete, hotkeys for task focus (N/P) and opening detail view (E)).
        *   `webApp/src/components/ui/TaskCard.tsx` (Modified to trigger `TaskDetailView` on click of title area or dedicated edit icon; visual focus indicator added).
        *   `webApp/src/components/ui/Textarea.tsx` (Created for multi-line input in `TaskDetailView`).
        *   `webApp/src/lib/utils.ts` (Created for `cn` utility, used by `Textarea`).
    *   **Detailed Steps Progress:**
        *   **V.2.1. Design `TaskDetailView.tsx` Structure (Modal/Panel):** DONE (Radix Dialog modal structure created).
        *   **V.2.2. Implement Form Fields:** In Progress (Title, Description, Notes, Status, Priority implemented. Others like due_date, category are pending).
        *   **V.2.3. Implement Actions:** In Progress (Save implemented. Cancel closes. Delete is pending).
        *   **V.2.4. Create `useFetchTaskById` hook:** DONE.
        *   **V.2.5. Integrate Trigger:** DONE (TaskCard title area click or edit icon opens detail view; 'E' key on focused task also opens it).
        *   **V.2.6. Subtask Management Section:** To Do.
    *   **Summary:** `TaskDetailView` modal can be opened by clicking a task card's title/edit icon, or by pressing 'E' on a focused task. It fetches task data and displays a form with Title, Description, Notes, Status, and Priority. Changes can be saved. Delete functionality and other fields are pending. `TodayView` supports keyboard navigation for focusing tasks and opening the detail view.

**3. Implement Subtask Display in TaskCard**
    *   **Status:** To Do
    *   **Depends on:** DDL/Types for Subtasks are complete. `useFetchTasks` can fetch tasks with their subtasks, or subtasks are fetched separately.
    *   **Components & Files:**
        *   `webApp/src/components/tasks/TaskCard.tsx` (Modify to display subtask accordion)
        *   `webApp/src/components/tasks/SubtaskList.tsx` (New component to render list of subtasks)
        *   `webApp/src/components/tasks/SubtaskCard.tsx` (New, potentially simplified version of `TaskCard` for subtasks)
        *   `webApp/src/api/hooks/useTaskHooks.ts` (`useFetchTasks` to potentially fetch subtasks).
    *   **Detailed Steps:**
        *   **3.1. Modify `useFetchTasks` (Strategy for fetching subtasks):**
            *   Option A: Fetch parent tasks, then if a task has `parent_task_id IS NULL`, make a separate query for its children where `parent_task_id = parent.id`.
            *   Option B: Attempt a JOIN in Supabase if possible (e.g., using RPC function) to fetch tasks and their subtasks in a nested structure. This is more complex with RLS.
            *   Option C (Simpler Start): Fetch all tasks; client-side logic in `TodayView.tsx` groups subtasks under parents based on `parent_task_id`.
            *   *Initial Recommendation: Option C for simplicity, then optimize if performance suffers.*
        *   **3.2. Create `SubtaskCard.tsx`:**
            *   A simpler version of `TaskCard.tsx` for displaying subtasks. Might omit some details or have different actions.
            *   Subtasks should also be focusable for the P-P-E-R cycle.
        *   **3.3. Create `SubtaskList.tsx`:**
            *   Takes an array of subtasks (`Task[]`) as props.
            *   Renders a list of `SubtaskCard.tsx` components.
        *   **3.4. Modify `TaskCard.tsx` for Parent Tasks:**
            *   If `task.subtasks` array is present and not empty (or if client-side grouping indicates subtasks exist):
                *   Display an accordion toggle icon (e.g., Lucide `ChevronDown`/`ChevronRight`).
                *   On toggle, render `SubtaskList.tsx` with the subtasks.
            *   Ensure the parent task itself is not directly "startable" for P-P-E-R if it has subtasks (as per creative doc).
        *   **3.5. Styling:**
            *   Ensure clear visual distinction between parent tasks and their subtasks (e.g., indentation, slightly different styling for `SubtaskCard`).
        *   **3.6. Testing:**
            *   Parent tasks with subtasks display accordion correctly.
            *   Subtasks are listed under their parent.
            *   Accordion expands/collapses.
            *   Interaction rules (parent not startable if subtasks exist) are followed.

**4. Update API Hooks for Subtasks and `description`**
    *   **Status:** To Do
    *   **Files:** `webApp/src/api/hooks/useTaskHooks.ts`
    *   **Detailed Steps:**
        *   **4.1. `useCreateTask`:** Modify to accept and save `description` and `parent_task_id` (if creating a subtask).
        *   **4.2. `useUpdateTask`:** Modify to accept and save `description`, `parent_task_id` (if re-parenting), `subtask_position`.
        *   **4.3. (If not covered by `useFetchTasks` modifications for subtasks) Create `useFetchSubtasks(parentId: string)` if needed.**

**General Considerations:**
*   **State Management:** Use Zustand store (`useTaskStore` or a new one) for managing `TodayView` tasks, selected task for detail view, etc. React Query will handle server state.
*   **Error Handling:** Implement robust error handling and user feedback (e.g., `react-hot-toast`) for all mutations.
*   **Accessibility:** Ensure all new interactive elements are keyboard accessible and have appropriate ARIA attributes.

This plan will be tracked and updated in `memory-bank/progress.md` as implementation proceeds.