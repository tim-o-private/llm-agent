# CRITICAL INSTRUCTIONS
All agents MUST `style-guide.md` & `systemPatterns.md`, and adhere to established patterns unless EXPLICITLY told by the user to deviate.
All agents MUST 

# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## PENDING / ACTIVE TASKS


# Task Board

## BRAINPLN-001: Brainstorm and Plan Next Major Features for Task View and Agent Capabilities (Status: Backend MVP Implemented; UI/Integration Next)

**Complexity:** 4 (Complex System)

**Objective:** Define the scope, architecture, and implementation strategy for new features including agent memory, agent-driven task management, enhanced agent tooling, and real-time UI updates.

**Sub-Tasks (derived from Planning Phase):**

*   **PLAN-STEP-1:** Finalize project plan document (Status: Done)
*   **PLAN-STEP-2:** Initiate CREATIVE phase for "Memory Solution Selection and Design." (Status: Backend MVP Implemented)
    *   **Key Decision:** Memory solution (mem0.ai, Langchain, homespun).
    *   **Output:** Decision document for memory solution, high-level API design.
*   **PLAN-STEP-3:** Initiate CREATIVE phase for "Agent Execution Logic & Prompt Customization Architecture." (Status: Backend MVP Implemented)
    *   **Key Decision:** Refactoring agent execution logic (which parts, where they live).
    *   **Output:** Architecture document for refactored agent core.
*   **PLAN-STEP-4:** Initiate CREATIVE phase for "UI/UX Design for Conversational Task Management." (Status: Creative Output `conversational_ui_ux_design_v1.md` produced; Implementation Planning Next)
    *   **Output:** Mockups, user flows for chat interface, agent-task interaction, confirmation process.
*   **PLAN-STEP-5:** Define detailed implementation tasks for Phase 1 (Conversational UI/UX) based on creative outputs. (Status: In Progress)

**User Stories Addressed:**
*   As a user, I can chat with an agent that remembers my conversations and can customize itself based on feedback.
*   As a user, my agent can create and edit tasks and subtasks for me.
*   As a user, I can review and confirm agent-created tasks before they are finalized.
*   As an agent, I have access to tools that are complete and easy to use and understand.
*   As an agent, I can alter a portion of my prompt to better serve users.
*   As an agent, I can edit, reorder, and suggest new tasks based on my conversations with the user.
*   As a developer, I have a way to easily create new tools for agents.

**Core Context Considered:**
*   Supabase live updates for task stores.
*   `agent_tool_architecture_v1.md` for tool architecture.
*   `agent-core-instructions.md` for general agent development.

**Next Mode Recommendation:** CREATIVE

## III. Agent Memory & Tooling Enhancement (Supabase Integration)
    *   **Status:** Backend MVP Implemented - **Critical for Chat Panel and future agent capabilities.**

**1. Supabase Schema Design/Refinement (Agent Memory, Prompts, Tasks)**
    *   **Task 1.1: Define Schema for Agent Memory**
        *   **Goal:** Design tables & stores for `agent_sessions` and `agent_chat_messages`. Update `ddl.sql`.
        *   **Output:** DDL & store schema for agent memory tables.
        *   **Status:** Backend MVP Implemented (DDL `20240801000000_agent_memory_schema.sql` created; `SupabaseChatMessageHistory` class implemented)
    *   **Task 1.2: Define Schema for Storing Agent Configurations/Prompts**
        *   **Goal:** Design tables for user-specific agent configurations/overrides.
        *   **Action:** Draft DDL for `user_agent_prompt_customizations`. Update `ddl.sql`.
        *   **Output:** DDL for prompt/config tables.
        *   **Status:** Backend MVP Implemented (DDL `20240801000100_prompt_customization_schema.sql` created; `PromptManagerService` and API endpoints implemented)
    *   **Task 1.3: Refine `tasks` Table Schema (and other UI-related tables)**
        *   **Goal:** Ensure `tasks` table and any other UI-centric tables are well-defined.
        *   **Action:** Review existing DDL. Incorporate fields from `techContext.md`.
        *   **Output:** Updated `data/db/ddl.sql`.
        *   **Status:** To Do (Not part of this backend MVP iteration)
    *   **Task 1.4: Define RLS Policies for Agent-Related Tables (and review UI tables)**
        *   **Goal:** Ensure appropriate Row Level Security.
        *   **Action:** Implement RLS for `agent_sessions`, `agent_chat_messages`, `user_agent_prompt_customizations`.
        *   **Output:** SQL migration scripts for RLS policies.
        *   **Status:** Backend MVP Implemented (Included in DDL migration scripts)

**2. API Endpoints in `chatServer/` (for Supabase interactions by agents)**
    *   **Task 2.1: Design and Implement Endpoints for Agent Memory**
        *   **Goal:** Allow agents (via `chatServer`) to save/load conversation history/summaries from Supabase.
        *   **Action:** Create FastAPI endpoints.
        *   **Output:** New API endpoints in `chatServer/main.py`.
        *   **Status:** Achieved via direct Supabase client in `SupabaseChatMessageHistory` class (no separate API endpoints needed for agents to call for memory).
    *   **Task 2.2: Design and Implement Endpoints for Agent Prompts/Contexts**
        *   **Goal:** Allow agents to fetch/update their specific prompts/customizations from Supabase.
        *   **Action:** Create FastAPI endpoints for prompt customizations.
        *   **Output:** New API endpoints in `chatServer/main.py`.
        *   **Status:** Backend MVP Implemented (`/api/agent/prompt_customizations/...` endpoints created)

**3. Backend MVP Validation & Documentation**
    *   **Status:** To Do
    *   **Objective:** Ensure the implemented backend MVP (agent memory, prompt customization, customizable agent) is robust, well-tested, and documented before proceeding to UI development.

    *   **Task 3.1: Manual Testing of Backend MVP**
        *   **Goal:** Verify all new backend components (Supabase schemas, `SupabaseChatMessageHistory`, `PromptManagerService`, `CustomizableAgent`, `UpdateSelfInstructionsTool`, updated `agent_loader.py`, and `chatServer/main.py` endpoints) are functioning as expected.
        *   **Key Actions:**
            *   Define test scenarios for chat history persistence with `test_agent`. (Verified: Chat messages are persisted and retrieved across sessions via Supabase).
            *   Define test scenarios for prompt customization using `UpdateSelfInstructionsTool` and verifying changes through `PromptManagerService` and direct API calls. (Next focus for manual testing).
            *   Execute tests (e.g., using `curl` to interact with `chatServer/main.py` API endpoints, and observing Supabase data changes, and using the CLI for `test_agent` tool usage).
            *   Document results and any issues found.
        *   **Files/Areas:** `chatServer/main.py` endpoints (`/api/chat`, `/api/agent/prompt_customizations`), Supabase tables (`agent_sessions`, `agent_chat_messages`, `user_agent_prompt_customizations`), `config/agents/test_agent/agent_config.yaml`, `src/cli/main.py`.
        *   **Status:** In Progress - Core memory persistence (Supabase integration for chat history) is now working. The `RuntimeError: Event loop is closed` is resolved. Next is to verify prompt customization persistence.
        *   **Note:** Initial `RuntimeError: Event loop is closed` issue during tool use has been resolved. Focus is now on verifying the full scope of Task 3.1.

    *   **Task 3.2: Implement Unit Tests for Backend MVP Components**
        *   **Goal:** Create unit tests for new Python classes and functions to ensure their correctness and facilitate future refactoring.
        *   **Key Actions:**
            *   Write unit tests for `src/core/memory/supabase_chat_history.py` (`SupabaseChatMessageHistory`), mocking Supabase client interactions.
            *   Write unit tests for `src/core/prompting/prompt_manager.py` (`PromptManagerService`), mocking HTTP requests.
            *   Write unit tests for `src/core/agents/customizable_agent.py` (`CustomizableAgent`), focusing on prompt construction and tool integration.
            *   Write unit tests for `src/core/tools/prompt_tools.py` (`UpdateSelfInstructionsTool`).
            *   Write unit tests for relevant new/modified logic in `src/core/agent_loader.py`.
        *   **Files:** New test files in `tests/core/memory/`, `tests/core/prompting/`, `tests/core/agents/`, `tests/core/tools/`, and `tests/core/`.
        *   **Status:** To Do

    *   **Task 3.3: Update Technical Documentation for Backend MVP**
        *   **Goal:** Document the new backend architecture, components, APIs, and Supabase schema changes for clarity and maintainability.
        *   **Key Actions:**
            *   Update `memory-bank/techContext.md` with details of the new agent memory system (`SupabaseChatMessageHistory`), `CustomizableAgent`, `PromptManagerService`, and associated Supabase tables (`agent_sessions`, `agent_chat_messages`, `user_agent_prompt_customizations`) including their schemas and RLS policies.
            *   Create/update API documentation (e.g., in `docs/api_reference.md` or a relevant section in `README.md`) for the `/api/chat` and `/api/agent/prompt_customizations/...` endpoints in `chatServer/main.py`.
            *   Ensure `config/agents/test_agent/agent_config.yaml` serves as a clear example of how to configure the `CustomizableAgent` and `supabase_buffer` memory.
        *   **Files:** `memory-bank/techContext.md`, `docs/api_reference.md` (new or existing), `README.md`, `config/agents/test_agent/agent_config.yaml`.
        *   **Status:** To Do

---
## ON HOLD
## II. Clarity Web Application UI/UX Tasks

### Area: UI/UX Overhaul & Cyclical Flow Implementation

**4. Cyclical Flow Implementation (Prioritize -> Execute -> Reflect)**
    *   **Status:** Planning Complete - Data/Types Updated - **Current Focus: Full Implementation of "Prioritize" Flow. "Execute" and "Reflect" phases are deferred until "Prioritize" is complete.**
    *   **Task 4.1: Define/Refine Core Data Structures and State for Cyclical Flow**
        *   **Status:** DDL Updated for P-E-R core, TypeScript types updated, Zustand store planned. (DONE)
    *   **Task 4.1.UI: Implement P-P-E-R UI Features (Phase 1: Prioritize Flow Focus)**
        *   **Sub-Task 4.1.UI.4: Implement Subtask Display & Interaction Logic** (To Do - *Next priority after Prioritize View*)
        *   **Sub-Task 4.1.UI.5: Implement Prioritize View (Modal)** (In Progress - **Primary Focus**)
            *   **Key Actions:** Design and implement the main UI for the "Prioritize" phase. This will likely involve selecting tasks for the day/session.
            *   **Progress:** 
                *   Created `PrioritizeViewModal.tsx` with initial structure, form fields for motivation, completion note, session breakdown, and timer duration. Handles fetching task data and updating task details.
                *   Integrated `PrioritizeViewModal` into `TodayView.tsx`.
                *   Added a "Focus" button to `TaskCard.tsx` to trigger the modal.
                *   `TodayView.tsx` now manages state for the modal and includes a `handleStartFocusSession` callback (currently logs data, to be expanded for actual focus session initiation).
            *   **Next Steps:** Test the flow. Implement actual transition to an "Execute" phase/view from `handleStartFocusSession`.
        *   **Sub-Task 4.1.UI.9: Refine Chat Panel Collapse/Expand Animation**
            *   **Goal:** Ensure a smoother and more visually appealing animation when the chat panel is minimized (collapsed) and maximized (expanded).
            *   **Status:** To Do
            *   **Complexity:** Level 1-2 (UI Polish)
            *   **Details:**
                *   Review current CSS transitions in `webApp/src/pages/TodayView.tsx` for the chat panel container.
                *   Explore techniques for smoother width transitions and potentially opacity/transform animations for the `ChatPanel` content itself to prevent content from appearing/disappearing abruptly before the container finishes resizing.
                *   Consider if child elements within `ChatPanel` contribute to animation issues.
                *   Ensure animation is performant.
            *   **Files Affected:** `webApp/src/pages/TodayView.tsx`, global CSS/Tailwind config (if needed).

---
## COMPLETED / ARCHIVED TASKS

## I. CLI & Core Agent Development Tasks

### Phase: REPL Enhancements, Tool Expansion, and Refinement (Ongoing)
### Status: COMPLETE

*   **Task: Implement Additional Agent Tools**
    *   **Goal:** Add tools for capabilities like web search, reading specific external documents, calendar interaction, etc.
    *   **Status:** Needs Refinement / To Do
    *   **Key Functionality:**
        *   Identify needed tools (e.g., `langchain_community.tools.tavily_search.TavilySearchResults`).
        *   Implement custom tools if necessary (e.g., `ObsidianNoteReader`, Calendar Tool) following LangChain conventions. Define clear descriptions and argument schemas.
        *   Update `load_tools` in `src/core/agent_loader.py` to handle instantiation based on `agent_config.yaml`.
        *   Define how calendar interaction should work (read-only? create events?). Requires OAuth setup.
        *   Handle API keys/auth for new tools (e.g., Tavily, Google Calendar) in `.env`.
    *   **Testing:** Unit tests for custom tools. Test tool integration manually via REPL.
    *   **Files:** `src/tools/`, `src/cli/main.py`, agent configs.

*   **Task: Get Visibility and Token Use [ON HOLD]**
    *   **Goal:** Add output to show token usage after each agent turn in the REPL.
    *   **Status:** CANCELED
    *   **Key Functionality:** (Details from `implementation-plan.md` involving `TokenUsageCallbackHandler`)

### Phase: Future Phases & Backlog (CLI Core)

*   **Task: Refine Context Formatting/Prompting**
    *   **Goal:** Improve how static context, dynamic context (memory), and tool outputs are presented to the LLM for better performance and reasoning.
    *   **Status:** Needs Refinement
    *   **Files:** `src/cli/main.py` (prompt creation), agent prompt files.

*   **Task: Agent Self-Correction/Improvement (Using Data Dir)**
    *   **Goal:** Allow agents to suggest modifications or store learned preferences in their data directory.
    *   **Status:** CANCELED
    *   **Key Functionality:** Use file I/O tools to allow agents to read/write to their `agent_prompt.md` or other notes. Core prompt changes remain manual.

*   **Task: Comprehensive Testing (CLI Core)**
    *   **Goal:** Add unit tests for agent loading, REPL state management, and integration tests for agent execution with tool calls.
    *   **Status:** CANCELLED
    *   **Files:** `tests/` directory.

*   **Task: Update Documentation (README for CLI)**
    *   **Goal:** Update README with `chat` command usage, agent configuration details, tool setup, and other relevant information for the CLI.
    *   **Status:** CANCELLED
    *   **Files:** `README.md`.

*   **Task: Optimize Memory Usage (Long-Term Chat)**
    *   **Goal:** Investigate strategies for managing long-term conversation memory (e.g., Summarization, Token Buffers).
    *   **Status:** CANCELLED
    *   **Files:** `src/utils/chat_helpers.py`, potentially `src/core/llm_interface.py`.

*   **Task: Address LangChainDeprecationWarnings (CLI Core)**
    *   **Goal:** Update LangChain imports and usage to eliminate remaining deprecation warnings.
    *   **Status:** CANCELLED

*   **Task: Improve Logging Implementation (CLI Core)**
    *   **Goal:** Refactor logging to use a dedicated application logger. Use `logger.error` for exceptions.
    *   **Status:** CANCELLED

*   **Task: Enhance Error Handling (CLI Core)**
    *   **Goal:** Improve granularity and user-facing messages during agent loading and other operations.
    *   **Status:** CANCELLED

*   **Task: Refactor for Code Clarity and Readability (CLI Core)**
    *   **Goal:** Apply various refactoring suggestions to improve code structure.
    *   **Status:** CANCELLED

*   **Task: Standardize Memory Management (CLI Core)**
    *   **Goal:** Investigate using standard LangChain `AgentExecutor` memory integration instead of manual load/save.
    *   **Status:** CANCELLED

*   **Task: Implement Proper Packaging (CLI Executable - PyInstaller)**
    *   **Goal:** Create a standalone executable using PyInstaller.
    *   **Status:** CANCELLED

*   **Task: Refactor Project Structure for Proper Packaging and Module Imports (CLI Core)**
    *   **Goal:** Transition from `sys.path` manipulations to standard Python packaging (`pyproject.toml`, `setuptools`).
    *   **Status:** DONE
    *   **Phases:**
        1.  Setup Packaging and Basic Conversion (`pyproject.toml`, editable install).
        2.  Update Imports and Remove Hacks (remove `sys.path` mods, use absolute imports).
        3.  Finalize and Document (README, CI/CD).

*   **Task: Investigate and Fix Failing Pytest Suite (CLI Core)**
    *   **Goal:** Diagnose and resolve all failures in the Pytest suite.
    *   **Status:** DONE
    *   **Phases:**
        1.  Initial Diagnosis and Triage.
        2.  Addressing Systemic Failures (if any).
        3.  Fixing Individual Test Failures.
        4.  Refinement and Documentation (optional).

*   **Task: Prepare Project for Public Release: Scrub Sensitive Data (CLI Core & General)**
    *   **Goal:** Ensure no sensitive data (chat logs, private configs) is in the public GitHub repo.
    *   **Status:** DONE
    *   **Phases:**
        1.  Identification and Strategy (list sensitive files, define scrubbing method - `.gitignore` recommended for `memory-bank/` and agent data).
        2.  Implementation of Scrubbing (update `.gitignore`, create template/example structures).
        3.  Verification and Documentation (final review, update README on data handling).

*   **Task: Implement CI/CD Pipeline for Automated Pytest on PRs (CLI Core)**
    *   **Goal:** Set up GitHub Actions to run Pytest on PRs, block merge on failure.
    *   **Status:** DONE
    *   **Phases:**
        1.  Basic Workflow Setup (`.github/workflows/python-pytest.yml`, checkout, setup Python).
        2.  Dependency Installation and Test Execution (install `requirements.txt`, `pip install -e .`, run `pytest`).
        3.  Branch Protection and Refinements (GitHub settings, optional caching).

*   **Task: Avoid redundant summarization**
    *   **Goal:** Prevent multiple summary updates in short sessions.
    *   **Status:** CANCELLED

*   **Task: Develop a Flexible Agent Evaluation Framework**
    *   **Goal:** Re-architect agent evaluation process (from `langsmith/eval-permissions.py`) into a flexible framework.
    *   **Status:** CANCELLED
    *   **Key Requirements:** Modular evaluators, support for various evaluation types against different agents.

*   **Task: CORE - Rationalize and Refactor Agent Tool Loading & Calling Logic**
    *   **Goal:** Refactor `src/core/agent_loader.py` and related components to establish a clear, robust, and extensible system for defining, loading, and invoking agent tools, separating duties cleanly, and defining a coherent interaction model.
    *   **Status:** To Do
    *   **Complexity:** Level 3-4
    *   **Blocks:** Task II.4.1.10 (Implement AI Task Interactivity), Future new agent tool development.
    *   **Key Phases & Steps:**
        1.  **Phase 1: Design & Creative (Define Target Architecture)**
            *   Document current tool loading flow and pain points.
            *   Define target architecture for tool management (registration, scope/context provision, API-backed tool patterns).
            *   Review `agent_loader.py` and identify specific refactoring targets.
            *   Output: Design document/notes.
        2.  **Phase 2: Incremental Refactoring of `src/core/agent_loader.py`**
            *   Refactor scope management.
            *   Refactor tool instantiation (LangChain toolkits, custom tools).
            *   Implement standard pattern for API client tools (e.g., for `chatServer`).
            *   Update agent configuration handling (`tools_config` in YAMLs) if needed.
            *   Add/update unit tests.
        3.  **Phase 3: Integration & Testing**
            *   Adapt callers of `load_agent_executor` / `load_tools`.
            *   Test existing agents for regressions with their current tools.
            *   Update documentation.
    *   **Files Affected:** `src/core/agent_loader.py`, agent config YAMLs, `src/utils/path_helpers.py`, `src/cli/main.py`.


## II. Clarity Web Application UI/UX Tasks

### Area: UI/UX Overhaul & Cyclical Flow Implementation

**1. Theming Strategy (Radix Themes + Tailwind)**
    *   **Status:** COMPLETED
    *   **Task 1.1: Integrate Radix Themes Provider** (DONE)
    *   **Task 1.2: Configure Base Light/Dark Mode using Radix Themes** (DONE)
    *   **Task 1.3: Define Semantic Color Mappings (Tailwind to Radix Variables)** (DONE)
    *   **Task 1.4: Refactor Existing Components for Radix Theme Compatibility** (DONE)
    *   **Task 1.5: Document Multi-Palette & Advanced Theming Approach** (DONE)

**2. Keyboard Navigability Audit & Implementation**
    *   **Status:** COMPLETED (Initial Audit & Fixes - Advanced shortcuts are future scope; Specific enhancements for TodayView task navigation implemented separately under Task 4)
    *   **Task 2.1: Comprehensive Keyboard Navigation Audit & Fixes** (DONE)
    *   **Task 2.2: Implement Fixes for Basic Keyboard Accessibility Issues (Component Level)** (DONE)
    *   **Task 2.3: Ensure Accessibility of Radix UI Components** (DONE)
    *   **Task 2.4: Address Complex Keyboard Interactions (Modals, Custom Controls)** (DONE)
    *   **Task 2.5: Document Keyboard Navigation Patterns** (DONE)

**3. Drag-and-Drop Task Reordering (within Today View list, using `dnd-kit`)**
    *   **Status:** COMPLETED
    *   **Sub-Task 3.1: Install dnd-kit packages** (DONE)
    *   **Sub-Task 3.2: Update `techContext.md`** (DONE)
    *   **Sub-Task 3.3: Make `TaskCard.tsx` sortable** (DONE)
    *   **Sub-Task 3.4: Implement Drag and Drop in `TodayView.tsx`** (DONE)
    *   **Sub-Task 3.5: Style Drag-and-Drop Interactions** (DONE)
    *   **Sub-Task 3.6: Persist Reordered Task Positions** (DONE)

**4. Cyclical Flow Implementation (Prioritize -> Execute -> Reflect)**
    *   **Task 4.1.UI: Implement P-P-E-R UI Features (Phase 1: Prioritize Flow Focus)**
        *   **Sub-Task 4.1.UI.1: Implement Fast Task Entry Mechanism** (ARCHIVED - See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
            *   **Key Actions:** Refactored as part of TodayView State Refactor.
        *   **Sub-Task 4.1.UI.2: Implement TaskDetailView UI & Logic** (COMPLETED)
            *   **Status:** Core modal with fields (Title, Description, Notes, Status, Priority) and Save functionality implemented. Trigger from `TaskCard` (click title/icon or 'E' key on focused task) operational. `Textarea` and `utils.ts` created. Debugged schema cache issue for `subtask_position`. Delete button in modal footer connected.
            *   **Bug fixes implemented:** Fixed icon consistency by replacing Lucide icons with Radix icons. Ensured `TodayView.tsx` correctly passes the `onDeleteTaskFromDetail` prop.
        *   **Sub-Task 4.1.UI.3: Implement Enhanced Keyboard Navigation in TodayView** (ARCHIVED - See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
            *   **Key Actions:** Refactored as part of TodayView State Refactor.
        *   **Sub-Task 4.1.UI.5.A: Refactor `TaskCard.tsx` for Prioritization** (COMPLETED - **Part of Prioritize View Focus**)
            *   **Goal:** Adapt `TaskCard` for use in the prioritization flow.
            *   **Key Actions:** 
                *   Change checkbox functionality: Instead of marking complete, it should act as a selection mechanism for prioritization (e.g., add to "Today's Focus").
                *   Add explicit buttons for "Edit", "Complete", and "Delete" actions, accessible via click and keyboard commands. Update keyboard navigation accordingly.
        *   **Sub-Task 4.1.UI.8: Restore and Enhance Collapsible Chat Panel in `TodayView`**
            *   **Goal:** Restore broken chat send/receive functionality and enhance the ChatPanel UI, particularly making it collapsible via an icon on the panel itself.
            *   **Status:** COMPLETED
            *   **Context:** Core chat send/receive functionality was previously broken. It has been restored by modifying `ChatPanel.tsx` to use the `/api/chat` endpoint in `chatServer/main.py`. The `chatServer/routers/chat_router.py` and its `/api/chat/send_message` endpoint are now deprecated for this UI feature and the `routers` directory has been removed. The UI has been enhanced to use a persistent toggle button on the panel itself.
            *   **Implementation Steps:**
                1.  **Phase 1: Restore Core Chat Functionality (Diagnosis & Fixes)** - COMPLETED
                    *   Diagnose current failure: Review recent changes affecting chat; test `chatServer` endpoints; trace data flow; check console/network for errors.
                    *   Implement fixes: Modified `ChatPanel.tsx` to target `chatServer/main.py`'s `/api/chat` endpoint and adapt request/response formats.
                    *   Verify: Thoroughly test send/receive. (Verified by user as working).
                2.  **Phase 2: UI/UX Enhancements (Post-Restoration)** - COMPLETED
                    *   Expand/Collapse Trigger: Implemented persistent icon button on the panel itself (in `TodayView.tsx`) to toggle `isOpen` state. Icon changes appropriately. Header chat toggle removed.
                    *   Visual Polish: Basic transitions in place. (Further refinement logged as Sub-Task 4.1.UI.9).
                    *   Test all UI interactions. (Verified by user as working).
            *   **Files Affected (Primary for this task going forward):** `webApp/src/components/ChatPanel.tsx`, `webApp/src/pages/TodayView.tsx`, `webApp/src/stores/useChatStore.ts`, `chatServer/main.py` (for the `/api/chat` endpoint).
            *   **Deprecated/To Be Removed:** `chatServer/routers/chat_router.py` (and the `routers` directory if empty). - DONE (directory removed)
        *   **Sub-Task 4.1.UI.10: Refine and Verify Toast Notification System**
            *   **Goal:** Ensure a reliable, accessible, and correctly displayed toast notification system for user feedback.
            *   **Status:** COMPLETE
            *   **Details:**
                *   Switched from `react-hot-toast` to `@radix-ui/react-toast` to address stacking context issues with modals.
                *   Refactored `webApp/src/components/ui/toast.tsx` to a simplified implementation using Radix UI primitives directly, removing prior complex state management. The import mechanism for Radix primitives was corrected, and an imperative API (`toast.success()`, `toast.error()`, `toast.default()`) was established and integrated across relevant files (`useTaskHooks.ts`, `TaskDetailView.tsx`, `TodayView.tsx`, `FastTaskInput.tsx`, `useTaskStore.ts`).
                *   Default toast duration was made configurable and issues with auto-closing were resolved. Styling for default toast background was updated.
                *   **Next Step:** The core functionality of the toast system is now considered stable. Minor style refinements or variant additions can be handled as needed.
                *   **Blocks:** Smooth user experience for actions requiring feedback (e.g., save, delete, errors).
**5. State Management Refactoring**
   * **Status:** COMPLETE
   * **Task 5.2: Implement Task Store with New Architecture**
      * **Goal:** Refactor task management to use the new state management approach
      * **Status:** COMPLETE
      * **Detailed Plan:** See `memory-bank/clarity/implementation-plan-state-management.md`
      * **Implementation Plan:**
         * **Phase 1: ✅ Core Store Implementation** 
            * Created `useTaskStore.ts` with local-first state
            * Added background sync with Supabase
            * Implemented optimistic UI updates
            * Created utility hooks for store initialization
         * **Phase 2: ✅ TodayView Component Migration**
            * Updated FastTaskInput to use the store
            * Refactored TodayView.tsx to use store actions and selectors
            * Fixed UI issues and added proper type handling
         * **Phase 3: ✅ TaskDetail Integration**
            * Updated SubtaskItem to use store actions
            * Implemented consistent store access across components
         * **Phase 4: 🔄 Testing and Verification** - *In Progress*
         * **Phase 5: 🔄 Documentation and Cleanup** - *Pending*
      * **Files Affected:** 
         * `webApp/src/stores/useTaskStore.ts` (new)
         * `webApp/src/pages/TodayView.tsx`
         * `webApp/src/components/TaskCard.tsx` 
         * `webApp/src/components/features/TaskDetail/TaskDetailView.tsx`
         * `webApp/src/components/features/TaskDetail/SubtaskItem.tsx`
      * **Dependencies:**
         * Proper authentication for user_id availability
         * Toast notification system for sync feedback
      * **Estimated Timeline:** 6-9 days
*   **Task 5.3: Extend Architecture to Other EntityTypes**
      * **Goal:** Apply the new state management pattern to other entity types (focus sessions, user preferences, etc.)
      * **Status:** To Do
      * **Dependency:** Successful implementation of Task 5.2
      * **Key Actions:**
         * Identify next priority entity types for conversion
         * Create stores following the reference architecture
         * Refactor relevant components
      * **Files Affected:** Various store and component files

**5. State Management Refactoring**
   * **Task 5.1: Design New State Management Architecture**
      * **Goal:** Create a consistent, robust state management pattern for the entire application
      * **Status:** COMPLETED
      * **Key Actions:** 
         * Documented core principles (entity-centric stores, local-first with eventual sync)
         * Created a comprehensive design document (`memory-bank/clarity/state-management-design.md`)
         * Developed a reference implementation (`memory-bank/clarity/state-management-example.ts`)
         * Created component integration example (`memory-bank/clarity/state-management-component-example.tsx`)

*   **Task 7: Abstract TaskDetailView State Management into Reusable Hooks**
    *   **Goal:** Abstract state management logic (RHF hooks for parent object, data fetching, save/close handlers, child list management including DND reordering and item CRUD) out of `TaskDetailView.tsx` into new custom hooks: `useObjectEditManager`, `useReorderableList`, and the orchestrating `useTaskDetailStateManager` (which internally uses `useEntityEditManager`). `TaskDetailView.tsx` should then become primarily a presentational component, consuming these hooks and interacting with `useTaskStore` for data persistence.
    *   **Status:** SUPERSEDED by Task 9 (The hooks `useObjectEditManager`, `useReorderableList`, `useEntityEditManager`, `useTaskDetailStateManager` were deprecated and removed as part of Task 9.8, replaced by `useEditableEntity`)
    *   **Complexity:** Level 4 (involves creating generic, reusable hooks and refactoring a complex component)
    *   **Depends On:** Successful completion and verification of Task 6 (robust internal state management in `TaskDetailView` which served as the basis for abstraction).
    *   **Documentation:** 
        *   Conceptual design and API for these hooks: `memory-bank/clarity/references/patterns/reusable-ui-logic-hooks.md` (Updated to match implementation).
        *   Data flow diagram: `memory-bank/clarity/diagrams/hook-data-flow-tdv.md` (NEW).
    *   **Phases:**
        1.  **Phase 1: Develop `useObjectEditManager` Hook (COMPLETED)**
            *   Implemented the hook based on the API defined in `reusable-ui-logic-hooks.md`.
            *   Generic typing, RHF integration. Refactored to remove direct data persistence.
            *   Unit tests: To Be Done.
        2.  **Phase 2: Develop `useReorderableList` Hook (COMPLETED)**
            *   Implemented the hook based on the API defined in `reusable-ui-logic-hooks.md`.
            *   Generic typing, `dnd-kit` integration, local list management. Refactored to remove direct data persistence.
            *   Unit tests: To Be Done.
        3.  **Phase 2.5: Develop `useEntityEditManager` Hook (COMPLETED - Implicitly as part of `useTaskDetailStateManager`'s needs)**
            *   Generic hook for snapshot-based dirty checking and delegated save logic.
            *   Unit tests: To Be Done.
        4.  **Phase 2.75: Develop `useTaskDetailStateManager` Hook (COMPLETED)**
            *   Orchestrates `useEntityEditManager` for `TaskDetailData` (parent task + subtasks).
            *   Defines `getLatestData` by combining parent form values (from `useObjectEditManager` instance) and local subtasks (from `useReorderableList` instance).
            *   Defines `taskSaveHandler` to compute deltas and dispatch actions to `useTaskStore`.
            *   Unit tests: To Be Done.
        5.  **Phase 3 & 4: Refactor `TaskDetailView.tsx` to use these hooks (COMPLETED)**
            *   Replaced parent task editing logic with `useObjectEditManager`.
            *   Replaced subtask list management with `useReorderableList`.
            *   Integrated `useTaskDetailStateManager` for overall control, dirty state, and save operations.
            *   Ensured all existing functionalities are intended to be preserved (pending testing).
        6.  **Phase 5: Integration Testing & Refinement (NEXT STEP / IN PROGRESS)**
            *   Thoroughly test the refactored `TaskDetailView.tsx` against the manual test plan in `memory-bank/clarity/testing/task-detail-view-test-plan.md`.
            *   Address any issues arising from the integration.
            *   Refine hook APIs if necessary based on practical application.
        7.  **Phase 6: Unit Testing for Hooks**
            *   Implement unit tests for `useObjectEditManager.ts`.
            *   Implement unit tests for `useReorderableList.ts`.
            *   Implement unit tests for `useEntityEditManager.ts`.
            *   Implement unit tests for `useTaskDetailStateManager.ts`.
        8.  **Phase 7: Documentation Update & Cleanup (Partially Done, ongoing)**
            *   Update `reusable-ui-logic-hooks.md` with any API changes or implementation notes (Already done for current state).
            *   Ensure `hook-data-flow-tdv.md` is accurate.
            *   Clean up `TaskDetailView.tsx`, removing any redundant code (Largely done, verify post-testing).
            *   Consider creating examples of how to use these hooks for other object types.
    *   **Files Affected (Primary):** 
        *   `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` (major refactor)
        *   `webApp/src/hooks/useObjectEditManager.ts` (updated/refactored)
        *   `webApp/src/hooks/useReorderableList.ts` (updated/refactored)
        *   `webApp/src/hooks/useEntityEditManager.ts` (new or significantly refactored)
        *   `webApp/src/hooks/useTaskDetailStateManager.ts` (new file)
    *   **Future Scope:** Apply these hooks to other parts of the application where similar patterns exist.

*   **Task 8: Refactor `TaskDetailView` State Management (Align with Option 1 & Best Practices)**
    *   **Goal:** Refactor `TaskDetailView.tsx` and its associated hooks (`useObjectEditManager`, `useReorderableList`, `useTaskDetailStateManager`) to align with "Option 1: Full Adherence to Zustand-First with Eventual Sync" as detailed in `memory-bank/clarity/creative-task8-state-management-refactor.md`. This will simplify `TaskDetailView`, make hooks more reusable and focused, and ensure all data persistence goes through `useTaskStore.ts`.
    *   **Status:** SUPERSEDED by Task 9
    *   **Complexity:** Level 3-4
    *   **Depends On:** Successful completion of Task 7 (existing hooks provide a baseline).
    *   **Creative Design:** `memory-bank/clarity/creative-task8-state-management-refactor.md` (Section 7).
    *   **Phases:**
        *   **Phase 0: Achieve Passing Test Suite for `TaskDetailView`**
            *   **Objective:** Ensure the current `TaskDetailView.tsx` implementation is stable and bug-free by having all tests in `memory-bank/clarity/testing/task-detail-view-test-plan.md` pass.
            *   **P0.1:** Resolve All Failing Tests in `task-detail-view-test-plan.md` (starting with PT-2).
        *   **Phase 1: Refactor Core UI Logic Hooks**
            *   **P1.1:** Refactor `useObjectEditManager.ts` (pure RHF management, no direct persistence).
            *   **P1.2:** Refactor `useReorderableList.ts` (pure local list & DND, no direct persistence).
        *   **Phase 2: Refactor `TaskDetailView.tsx` and Orchestration Logic**
            *   **P2.1:** Update `TaskDetailView.tsx` for data sourcing from `useTaskStore` and snapshot creation.
            *   **P2.2:** Integrate refactored `useObjectEditManager` and `useReorderableList`.
            *   **P2.3:** Implement/Refine `useTaskDetailStateManager.ts` integration for dirty checking and save handling (delta calculation and dispatch to `useTaskStore`).
            *   **P2.4:** Implement modal save/cancel/close logic according to `modal-editor-state-flow-v2.md`.
        *   **Phase 3: Post-Refactor Integration Testing**
            *   **P3.1:** Execute full test plan from `task-detail-view-test-plan.md`.
            *   **P3.2:** Address any regressions.
        *   **Phase 4: Unit Testing for Hooks**
            *   **P4.1:** Unit Test `useObjectEditManager.ts`.
            *   **P4.2:** Unit Test `useReorderableList.ts`.
            *   **P4.3:** Unit Test `useTaskDetailStateManager.ts`.
            *   **P4.4:** Unit Test `useEntityEditManager.ts`.
        *   **Phase 5: Documentation & Cleanup**
            *   **P5.1:** Update hook documentation (`reusable-ui-logic-hooks.md`).
            *   **P5.2:** Update architectural diagrams.
            *   **P5.3:** Code cleanup.
            *   **P5.4:** Update `tasks.md` and `progress.md` upon completion.
    *   **Files Affected (Primary):** Same as Task 7, but with significant refactoring based on the new plan.

*   **Task 9 (Clarity UI): Architect and Implement `useEditableEntity` Hook & Refactor `TaskDetailView`**
    *   **Goal:** Design and build a new comprehensive hook, `useEditableEntity`, to manage editable entity state (forms, lists, dirty checking, saving) in a configurable and reusable way. Refactor `TaskDetailView.tsx` to use this hook, simplifying its logic and establishing a robust pattern for future editable components.
    *   **Status:**
        *   [x] `9.1` Design `useEditableEntity` Hook - COMPLETED
        *   [x] `9.2` Implement Core Logic & Form Integration - COMPLETED
        *   [x] `9.3` Implement List Management - COMPLETED
        *   [x] `9.4` Unit Testing for `useEditableEntity` - COMPLETED
        *   [x] `9.5` Refactor `TaskDetailView.tsx` - COMPLETED
        *   [x] `9.6` Comprehensive Testing of `TaskDetailView.tsx` - COMPLETED (Note: ST-1 failing, see reflection)
        *   [x] `9.7` Documentation for `useEditableEntity` - COMPLETED
        *   [x] `9.8` Cleanup - Deprecate/remove old hooks - COMPLETED
        *   [x] Reflection complete (see `memory-bank/reflection/reflection-task9.md`)
        *   [x] Archiving complete (see `memory-bank/archive/archive-task9.md`)
    *   **Archive:**
        *   **Date**: 2024-07-26 (Please update if specific)
        *   **Archive Document**: `memory-bank/archive/archive-task9.md`
        *   **Status**: COMPLETED (pending ST-1 resolution as noted in Reflection & Archive)
    *   **Reflection Highlights:**
        *   **What Went Well**: Core hook functionality for parent entities successful; `EntityTypeConfig` pattern effective; simplification of `TaskDetailView` state; cleanup of old hooks.
        *   **Challenges**: Subtask display failure due to `transformSubCollectionToList` not being called by `useEditableEntity`; type system complexities (missing `completed_at`, `transformSubCollectionToList` signature, `saveHandler` type finessing); AI model struggles with precise diff application.
        *   **Lessons Learned**: Crucial to verify interface contracts (especially callbacks) early; ensure data model completeness before integration; need for focused testing on sub-entity features during hook development; generics demand rigor; AI refactoring needs oversight.
        *   **Next Steps from Reflection**: Critical: Debug and fix `transformSubCollectionToList` non-invocation in `useEditableEntity.ts`. Complete all subtask tests. Finalize documentation.
    *   **Description:** Complete the full lifecycle of designing, implementing, testing, documenting the `useEditableEntity` hook, refactoring `TaskDetailView.tsx` to use it, and then cleaning up superseded hooks.
    *   **Phases:**
        *   `9.1` Design `useEditableEntity` Hook - COMPLETED
        *   `9.2` Implement Core Logic & Form Integration - COMPLETED
        *   `9.3` Implement List Management - COMPLETED
        *   `9.4` Unit Testing for `useEditableEntity` - COMPLETED
        *   `9.5` Refactor `TaskDetailView.tsx` - COMPLETED
        *   `9.6` Comprehensive Testing of `TaskDetailView.tsx` - COMPLETED
        *   `9.7` Documentation for `useEditableEntity` - COMPLETED
        *   `9.8` Cleanup - Deprecate/remove old hooks - COMPLETED
                    *   `9.8.1` Evaluate Completeness - COMPLETED
                    *   `9.8.2` Plan Migration for Other Components - COMPLETED
                    *   `9.8.3` Mark old hooks as deprecated - COMPLETED
                    *   `9.8.4` Remove old hook files - COMPLETED

## IV. Conversational UI/UX Implementation (Phase 1 - Based on `conversational_ui_ux_design_v1.md`)
    *   **Status:** To Do (Blocked by Backend MVP Validation & Documentation)
    *   **Objective:** Implement the UI/UX for conversational task management, including an integrated chat panel, in-line task previews, confirmation modals for agent actions, and a feedback mechanism.

**1. Chat Panel Core Implementation (`webApp/src/components/features/ChatPanel/`)**
    *   **Task 1.1: Basic ChatPanel Component Structure**
        *   **Goal:** Create the main `ChatPanel.tsx` component with areas for message display, message input, and agent status.
        *   **Key Actions:**
            *   Develop `MessageList.tsx` to render a list of messages (user and agent).
            *   Develop `MessageInput.tsx` for user text input and send button.
            *   Style basic layout using Tailwind CSS.
        *   **Files:** `ChatPanel.tsx`, `MessageList.tsx`, `MessageItem.tsx`, `MessageInput.tsx`
        *   **Status:** To Do
    *   **Task 1.2: Connect ChatPanel to `chatServer` API**
        *   **Goal:** Enable sending user messages to `/api/chat` and displaying agent responses.
        *   **Key Actions:**
            *   Implement API call logic (e.g., using `fetch` or a library like `axios`/`tanstack-query`) in `ChatPanel.tsx` or a dedicated hook.
            *   Manage chat history state (e.g., using `useState` or Zustand).
            *   Handle streaming responses if applicable (initially, non-streaming is acceptable for MVP).
            *   Display loading/pending states for agent responses.
        *   **Files:** `ChatPanel.tsx`, `webApp/src/api/hooks/useChatApi.ts` (new or existing)
        *   **Status:** To Do
    *   **Task 1.3: Implement Thumbs Up/Down Feedback Mechanism**
        *   **Goal:** Allow users to provide feedback on agent messages.
        *   **Key Actions:**
            *   Add UI elements (thumbs up/down icons) to each agent message in `MessageItem.tsx`.
            *   Implement a handler to send feedback to a new `chatServer` endpoint (e.g., `/api/chat/feedback`). This endpoint will initially log feedback; Supabase integration can be a follow-up.
        *   **Files:** `MessageItem.tsx`, `ChatPanel.tsx`, `chatServer/main.py` (new endpoint)
        *   **Status:** To Do

**2. In-line Task Previews and Confirmation**
    *   **Task 2.1: Design "Draft" Task Card UI**
        *   **Goal:** Create a distinct visual representation for tasks proposed by the agent but not yet confirmed by the user (Ghost/Draft cards).
        *   **Key Actions:**
            *   Adapt `TaskCard.tsx` or create a new `DraftTaskCard.tsx`.
            *   Include "Confirm" and "Discard" buttons.
        *   **Files:** `TaskCard.tsx` or `DraftTaskCard.tsx` (new)
        *   **Status:** To Do
    *   **Task 2.2: Agent Message Parsing for Task Proposals**
        *   **Goal:** Identify when an agent's message contains a task proposal that should be rendered as a draft task card.
        *   **Key Actions:**
            *   Define a simple convention for agents to indicate a task proposal in their message (e.g., a special prefix or a structured JSON block).
            *   Implement logic in `ChatPanel.tsx` or `MessageItem.tsx` to parse these messages and render `DraftTaskCard.tsx` instead of/alongside plain text.
        *   **Files:** `ChatPanel.tsx`, `MessageItem.tsx`
        *   **Status:** To Do
    *   **Task 2.3: Implement Confirmation Modal for Complex Agent Actions**
        *   **Goal:** For significant agent actions (e.g., creating multiple tasks, modifying existing critical tasks), show a confirmation modal.
        *   **Key Actions:**
            *   Design a generic `ConfirmationModal.tsx`.
            *   Trigger this modal from agent messages that signify such actions (requires a convention similar to Task 2.2).
            *   On confirmation, send a follow-up message to the agent/API to proceed.
        *   **Files:** `ConfirmationModal.tsx` (new), `ChatPanel.tsx`
        *   **Status:** To Do

**3. Integration with Task Management and Agent State**
    *   **Task 3.1: Connect Chat to Agent Session Management**
        *   **Goal:** Ensure chat interactions are associated with the correct agent session using `agent_id` and `session_id` from `SupabaseChatMessageHistory`.
        *   **Key Actions:**
            *   Pass `agent_id` (e.g., "test_agent") to the `/api/chat` endpoint.
            *   The backend (`chatServer/main.py` and `agent_loader.py`) should already handle session creation/loading.
            *   Ensure `user_id` is correctly passed and used for RLS in Supabase.
        *   **Files:** `ChatPanel.tsx`, `chatServer/main.py`
        *   **Status:** To Do (Verify frontend correctly sends identifiers)
    *   **Task 3.2: Real-time Task List Updates (Post-Confirmation)**
        *   **Goal:** When a draft task is confirmed, it should be added to the main task list and persist.
        *   **Key Actions:**
            *   On "Confirm" in `DraftTaskCard.tsx`, call an API endpoint to create/update the task in Supabase.
            *   Ensure the main task list (e.g., in `TodayView.tsx`) refreshes or an event is triggered to show the new task (Supabase real-time subscriptions can be leveraged here).
        *   **Files:** `DraftTaskCard.tsx`, `TodayView.tsx`, relevant API endpoint in `chatServer/main.py` or direct Supabase call from frontend.
        *   **Status:** To Do

**4. UI Polish and Refinements**
    *   **Task 4.1: Chat Panel Styling and Usability**
        *   **Goal:** Ensure the chat panel is visually appealing and easy to use.
        *   **Key Actions:**
            *   Refine styles, message spacing, color scheme.
            *   Implement auto-scrolling to the latest message.
            *   Consider clear visual distinction for user vs. agent messages.
        *   **Files:** `ChatPanel.tsx`, `MessageList.tsx`, `MessageItem.tsx`, `MessageInput.tsx`, Tailwind CSS config.
        *   **Status:** To Do
    *   **Task 4.2: Responsive Design for Chat Panel**
        *   **Goal:** Ensure the chat panel works well on different screen sizes.
        *   **Key Actions:** Apply responsive Tailwind CSS classes.
        *   **Files:** `ChatPanel.tsx` and child components.
        *   **Status:** To Do