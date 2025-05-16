# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## I. CLI & Core Agent Development Tasks

### Phase: REPL Enhancements, Tool Expansion, and Refinement (Ongoing)

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
    *   **Status:** On Hold
    *   **Key Functionality:** (Details from `implementation-plan.md` involving `TokenUsageCallbackHandler`)

### Phase: Future Phases & Backlog (CLI Core)

*   **Task: Refine Context Formatting/Prompting**
    *   **Goal:** Improve how static context, dynamic context (memory), and tool outputs are presented to the LLM for better performance and reasoning.
    *   **Status:** Needs Refinement
    *   **Files:** `src/cli/main.py` (prompt creation), agent prompt files.

*   **Task: Agent Self-Correction/Improvement (Using Data Dir)**
    *   **Goal:** Allow agents to suggest modifications or store learned preferences in their data directory.
    *   **Status:** Idea
    *   **Key Functionality:** Use file I/O tools to allow agents to read/write to their `agent_prompt.md` or other notes. Core prompt changes remain manual.

*   **Task: Comprehensive Testing (CLI Core)**
    *   **Goal:** Add unit tests for agent loading, REPL state management, and integration tests for agent execution with tool calls.
    *   **Status:** Needs Refinement
    *   **Files:** `tests/` directory.

*   **Task: Update Documentation (README for CLI)**
    *   **Goal:** Update README with `chat` command usage, agent configuration details, tool setup, and other relevant information for the CLI.
    *   **Status:** Needs Refinement
    *   **Files:** `README.md`.

*   **Task: Optimize Memory Usage (Long-Term Chat)**
    *   **Goal:** Investigate strategies for managing long-term conversation memory (e.g., Summarization, Token Buffers).
    *   **Status:** Idea
    *   **Files:** `src/utils/chat_helpers.py`, potentially `src/core/llm_interface.py`.

*   **Task: Address LangChainDeprecationWarnings (CLI Core)**
    *   **Goal:** Update LangChain imports and usage to eliminate remaining deprecation warnings.
    *   **Status:** Needs Refinement

*   **Task: Improve Logging Implementation (CLI Core)**
    *   **Goal:** Refactor logging to use a dedicated application logger. Use `logger.error` for exceptions.
    *   **Status:** Needs Refinement (Code Review Follow-up)

*   **Task: Enhance Error Handling (CLI Core)**
    *   **Goal:** Improve granularity and user-facing messages during agent loading and other operations.
    *   **Status:** Needs Refinement (Code Review Follow-up)

*   **Task: Refactor for Code Clarity and Readability (CLI Core)**
    *   **Goal:** Apply various refactoring suggestions to improve code structure.
    *   **Status:** Needs Refinement (Code Review Follow-up)

*   **Task: Standardize Memory Management (CLI Core)**
    *   **Goal:** Investigate using standard LangChain `AgentExecutor` memory integration instead of manual load/save.
    *   **Status:** Needs Refinement (Code Review Follow-up)

*   **Task: Implement Proper Packaging (CLI Executable - PyInstaller)**
    *   **Goal:** Create a standalone executable using PyInstaller.
    *   **Status:** Deferred (PyInstaller `--add-data` issues).

*   **Task: Refactor Project Structure for Proper Packaging and Module Imports (CLI Core)**
    *   **Goal:** Transition from `sys.path` manipulations to standard Python packaging (`pyproject.toml`, `setuptools`).
    *   **Status:** To Do
    *   **Phases:**
        1.  Setup Packaging and Basic Conversion (`pyproject.toml`, editable install).
        2.  Update Imports and Remove Hacks (remove `sys.path` mods, use absolute imports).
        3.  Finalize and Document (README, CI/CD).

*   **Task: Investigate and Fix Failing Pytest Suite (CLI Core)**
    *   **Goal:** Diagnose and resolve all failures in the Pytest suite.
    *   **Status:** To Do
    *   **Phases:**
        1.  Initial Diagnosis and Triage.
        2.  Addressing Systemic Failures (if any).
        3.  Fixing Individual Test Failures.
        4.  Refinement and Documentation (optional).

*   **Task: Prepare Project for Public Release: Scrub Sensitive Data (CLI Core & General)**
    *   **Goal:** Ensure no sensitive data (chat logs, private configs) is in the public GitHub repo.
    *   **Status:** To Do
    *   **Phases:**
        1.  Identification and Strategy (list sensitive files, define scrubbing method - `.gitignore` recommended for `memory-bank/` and agent data).
        2.  Implementation of Scrubbing (update `.gitignore`, create template/example structures).
        3.  Verification and Documentation (final review, update README on data handling).

*   **Task: Implement CI/CD Pipeline for Automated Pytest on PRs (CLI Core)**
    *   **Goal:** Set up GitHub Actions to run Pytest on PRs, block merge on failure.
    *   **Status:** To Do
    *   **Phases:**
        1.  Basic Workflow Setup (`.github/workflows/python-pytest.yml`, checkout, setup Python).
        2.  Dependency Installation and Test Execution (install `requirements.txt`, `pip install -e .`, run `pytest`).
        3.  Branch Protection and Refinements (GitHub settings, optional caching).

*   **Task: Avoid redundant summarization**
    *   **Goal:** Prevent multiple summary updates in short sessions.
    *   **Status:** Needs refinement

*   **Task: Develop a Flexible Agent Evaluation Framework**
    *   **Goal:** Re-architect agent evaluation process (from `langsmith/eval-permissions.py`) into a flexible framework.
    *   **Status:** Needs Refinement
    *   **Key Requirements:** Modular evaluators, support for various evaluation types against different agents.

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
    *   **Status:** Planning Complete - Data/Types Updated - **Current Focus: Full Implementation of "Prioritize" Flow. "Execute" and "Reflect" phases are deferred until "Prioritize" is complete.**
    *   **Task 4.1: Define/Refine Core Data Structures and State for Cyclical Flow**
        *   **Status:** DDL Updated for P-E-R core, TypeScript types updated, Zustand store planned. (DONE)
    *   **Task 4.1.UI: Implement P-P-E-R UI Features (Phase 1: Prioritize Flow Focus)**
        *   **Sub-Task 4.1.UI.1: Implement Fast Task Entry Mechanism** (ARCHIVED - See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
            *   **Key Actions:** Refactored as part of TodayView State Refactor.
        *   **Sub-Task 4.1.UI.2: Implement TaskDetailView UI & Logic** (COMPLETED)
            *   **Status:** Core modal with fields (Title, Description, Notes, Status, Priority) and Save functionality implemented. Trigger from `TaskCard` (click title/icon or 'E' key on focused task) operational. `Textarea` and `utils.ts` created. Debugged schema cache issue for `subtask_position`. Delete button in modal footer connected.
            *   **Bug fixes implemented:** Fixed icon consistency by replacing Lucide icons with Radix icons. Ensured `TodayView.tsx` correctly passes the `onDeleteTaskFromDetail` prop.
        *   **Sub-Task 4.1.UI.3: Implement Enhanced Keyboard Navigation in TodayView** (ARCHIVED - See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
            *   **Key Actions:** Refactored as part of TodayView State Refactor.
        *   **Sub-Task 4.1.UI.4: Implement Subtask Display & Interaction Logic** (To Do - *Next priority after Prioritize View*)
        *   **Sub-Task 4.1.UI.5: Implement Prioritize View (Modal)** (In Progress - **Primary Focus**)
            *   **Key Actions:** Design and implement the main UI for the "Prioritize" phase. This will likely involve selecting tasks for the day/session.
            *   **Progress:** 
                *   Created `PrioritizeViewModal.tsx` with initial structure, form fields for motivation, completion note, session breakdown, and timer duration. Handles fetching task data and updating task details.
                *   Integrated `PrioritizeViewModal` into `TodayView.tsx`.
                *   Added a "Focus" button to `TaskCard.tsx` to trigger the modal.
                *   `TodayView.tsx` now manages state for the modal and includes a `handleStartFocusSession` callback (currently logs data, to be expanded for actual focus session initiation).
            *   **Next Steps:** Test the flow. Implement actual transition to an "Execute" phase/view from `handleStartFocusSession`.
        *   **Sub-Task 4.1.UI.5.A: Refactor `TaskCard.tsx` for Prioritization** (COMPLETED - **Part of Prioritize View Focus**)
            *   **Goal:** Adapt `TaskCard` for use in the prioritization flow.
            *   **Key Actions:** 
                *   Change checkbox functionality: Instead of marking complete, it should act as a selection mechanism for prioritization (e.g., add to "Today's Focus").
                *   Add explicit buttons for "Edit", "Complete", and "Delete" actions, accessible via click and keyboard commands. Update keyboard navigation accordingly.
        *   **Sub-Task 4.1.UI.6: Implement Execute View (Focus Window)** (To Do - *Defer until after Prioritize flow completion*)
        *   **Sub-Task 4.1.UI.7: Implement Reflect View (Modal)** (To Do - *Defer until after Prioritize flow completion*)
        *   **Sub-Task 4.1.UI.8: Implement Collapsible Chat Panel in `TodayView`** (COMPLETED)
            *   **Goal:** Provide an integrated chat interface on the right side of the `TodayView`.
            *   **Progress:** 
                *   Created `ChatPanel.tsx` with basic UI (title, close button, placeholder message area, input field).
                *   Integrated `ChatPanel` into `TodayView.tsx` with state for `isOpen` and a toggle function.
                *   `TodayView` main content area now adjusts with padding when the chat panel is open.
            *   **Bug fixes implemented:** Fixed Chat Panel close functionality with proper Radix Cross1Icon and styling.
            *   **Next Steps:** Implement actual chat functionality (message state, sending/receiving, connecting to agent/backend).
    *   **Task 4.2: Enhance \"Today View\" for Prioritization (`Prioritize` Phase)** (Renamed to 4.1.UI.5)
    *   **Task 4.3: Implement \"Focus Mode\" (`Execute` Phase)** (Renamed to 4.1.UI.6)
    *   **Task 4.4: Implement \"Reflection Modal/View\" (`Reflect` Phase)** (Renamed to 4.1.UI.7)
    *   **Task 4.5: Implement Transitions and AI Nudges Between Phases** (To Do - *Defer until after Prioritize flow completion*)
    *   **Task 4.6: Document the Cyclical Flow and UI States** (To Do - Update as "Prioritize" flow is built)

## III. Agent Memory & Tooling Enhancement (Supabase Integration)
    *   **Status:** Planning Complete - **Implementation ongoing, critical for Chat Panel and future agent capabilities.**

**1. Supabase Schema Design/Refinement (Agent Memory, Prompts, Tasks)**
    *   **Task 1.1: Define Schema for Agent Memory**
        *   **Goal:** Design tables for agent conversation history & summaries.
        *   **Action:** Draft DDL for `agent_sessions` (session_id, agent_id, user_id, created_at, summary) and `agent_chat_messages` (message_id, session_id, timestamp, sender_type, content_type, content, tokens). Consider LangChain `ChatMessageHistory` compatibility. Update `ddl.sql`.
        *   **Output:** DDL for agent memory tables.
    *   **Task 1.2: Define Schema for Storing Agent Configurations/Prompts**
        *   **Goal:** Design tables for core system prompts and user-specific agent configurations/overrides. Move agent context and prompts to PostgreSQL (Supabase) with local caching.
        *   **Action:** Draft DDL for `agent_core_prompts` (prompt_id, agent_name, prompt_type, content, version) and `user_agent_configs` (config_id, user_id, agent_name, custom_instructions, tool_preferences). Update `ddl.sql`.
        *   **Output:** DDL for prompt/config tables.
    *   **Task 1.3: Refine `tasks` Table Schema (and other UI-related tables)**
        *   **Goal:** Ensure `tasks` table and any other UI-centric tables (e.g., `user_preferences`, `reflections`, `streaks`) are well-defined.
        *   **Action:** Review existing DDL for `tasks` in `data/db/ddl.sql`. Incorporate fields from `techContext.md` (Section 5. Core Data Models) if missing. Design schemas for `user_preferences`, `reflections`, `streaks`, `scratch_pad_entries`, `focus_sessions` based on `techContext.md`.
        *   **Output:** Updated `data/db/ddl.sql` with all necessary schemas.
    *   **Task 1.4: Define RLS Policies for Agent-Related Tables (and review UI tables)**
        *   **Goal:** Ensure appropriate Row Level Security for all new and existing tables.
        *   **Action:** Implement RLS for `agent_sessions`, `agent_chat_messages`, `user_agent_configs` ensuring users can only access their own data. Review RLS for `tasks` and other UI tables.
        *   **Reference:** `memory-bank/clarity/supabaseRLSGuide.md` for RLS helper function and patterns.
        *   **Output:** SQL migration scripts for RLS policies.

**2. API Endpoints in `chatServer/` (for Supabase interactions by agents)**
    *   **Task 2.1: Design and Implement Endpoints for Agent Memory**
        *   **Goal:** Allow agents (via `chatServer`) to save/load conversation history/summaries from Supabase.
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/memory/load`, `/api/agent/memory/save`) that interact with Supabase memory tables. Implement with async operations.
        *   **Output:** New API endpoints in `chatServer/main.py`.
    *   **Task 2.2: Design and Implement Endpoints for Agent Prompts/Contexts**
        *   **Goal:** Allow agents to fetch their specific prompts/contexts from Supabase (which were moved from local files).
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/context/load`) to retrieve from `user_agent_configs` (and potentially `agent_core_prompts`).
        *   **Output:** New API endpoints.
    *   **Task 2.3: Design and Implement Endpoints for Task Interactions by Agents**
        *   **Goal:** Enable agents (called by `chatServer`) to read and write task data from/to Supabase.
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/tasks/create`, `/api/agent/tasks/update/{task_id}`, `/api/agent/tasks/get/{task_id_or_query_params}`).
        *   **Output:** New API endpoints.

**3. Agent Tool Modifications/Creations**
    *   **Task 3.1: Develop/Refactor Task Management Tools for Agents**
        *   **Goal:** Create LangChain tools for agents to interact with tasks via the new `chatServer` Supabase endpoints (enabling them to read/write tasks).
        *   **Action:** Create `CreateTaskTool`, `UpdateTaskTool`, `ReadTaskTool`. These tools will make HTTP requests to the `chatServer` endpoints. Define clear Pydantic schemas for tool inputs.
        *   **Output:** New/updated Python tool files in `src/tools/`.
    *   **Task 3.2: Develop/Refactor Memory Management Tools/Mechanisms for Agents**
        *   **Goal:** Enable agents to persist and load their conversational memory using `chatServer` endpoints.
        *   **Action:** Integrate memory saving/loading into the agent lifecycle (e.g., `AgentExecutor` callbacks or manual calls within `chat_helpers.py`). This might involve a custom `BaseChatMessageHistory` implementation that uses the `chatServer` API.
        *   **Output:** Updated agent memory handling logic in `src/utils/chat_helpers.py` or custom history class.
    *   **Task 3.3: Develop/Refactor Prompt/Context Loading for Agents**
        *   **Goal:** Ensure agents load their base and user-specific prompts/contexts via `chatServer` (which fetches from Supabase, replacing direct file reads).
        *   **Action:** Modify `src/core/agent_loader.py` to call `chatServer` endpoints to get prompt data, integrating with the caching layer.
        *   **Output:** Updated `agent_loader.py`.

**4. Caching and Asynchronous Data Strategy (Integrated into relevant tasks)**
    *   **Task 4.1: Implement Caching for Agent Data in `chatServer` / Python Core**
        *   **Goal:** Minimize direct DB hits for frequently accessed agent data.
        *   **Action:** Apply caching (e.g., `cachetools.LRUCache`, `functools.lru_cache`) in `chatServer` for Supabase query results related to prompts, contexts, and potentially recent memory/tasks. Define cache invalidation/TTL strategy.
        *   **Output:** Caching implemented in `chatServer` service layer.
    *   **Task 4.2: Ensure Asynchronous Operations for DB Writes via `chatServer`**
        *   **Goal:** Non-blocking DB writes for agent memory, tasks, etc.
        *   **Action:** Ensure all FastAPI endpoint handlers in `chatServer` that perform Supabase writes do so asynchronously (`await`). Use `supabase-py` async client or `httpx` for direct async REST calls if needed.
        *   **Output:** Async DB operations in `chatServer`.
    *   **Task 4.3: Error Handling for Async Operations & Cache**
        *   **Goal:** Graceful error handling for DB/cache operations.
        *   **Action:** Implement try-except blocks, logging, and potential retry mechanisms for DB calls in `chatServer`. Handle cache misses by fetching from DB and populating cache.
        *   **Output:** Robust error handling.

**5. Refactor Configuration Management for Agents**
    *   **Task 5.1: Analyze Current Configuration Usage**
        *   **Goal:** Understand current `agent_config.yaml` structure and usage.
        *   **Action:** Review `agent_config.yaml` to map static vs. user-specific elements.
        *   **Output:** Analysis document/notes.
    *   **Task 5.2: Define New Configuration Loading Strategy (Supabase + Optional Local Base)**
        *   **Goal:** Load user-specific configurations/prompts from Supabase, potentially augmenting with static base configs (from files or a separate DB table).
        *   **Action:** User-specific: Store in `user_agent_configs` Supabase table. Static base: Could remain in `config/` YAMLs or be seeded into `agent_core_prompts`. Define merging logic in `agent_loader.py`.
        *   **Output:** Documented configuration strategy.
    *   **Task 5.3: Implement Refactored Configuration Loading**
        *   **Goal:** Modify `agent_loader.py` for new strategy (Supabase-first for user prompts/configs).
        *   **Action:** Update `agent_loader.py` to fetch user-specific configs from Supabase (via `chatServer` API, using cache) and merge with base configs if applicable. Ensure `chatServer` can pass `user_id` / `agent_type_identifier`.
        *   **Output:** Updated `agent_loader.py`.
    *   **Task 5.4: Plan for User Modification of Specific Configs (Future)**
        *   **Goal:** Design for future UI/agent tool to modify user-specific agent configs in Supabase.
        *   **Action:** Plan what settings are modifiable. Design UI considerations. Design secure agent tool concept.
        *   **Output:** Design notes for future configurability.

**5. Review and Update UI/API Development Guidance**
    *   **Status:** To Do
    *   **Task 5.1: Align `clarity-ui-api-development-guidance.md` with Current Decisions**
        *   **Goal:** Ensure the guidance document in `memory-bank/clarity/clarity-ui-api-development-guidance.md` reflects the current architectural decisions, especially the adoption of Radix UI Themes and Colors.
        *   **Action:** Review the document, particularly "Pattern 2: UI Component Strategy". Update it to recommend Radix UI Themes and Colors, and ensure it aligns with `techContext.md` and `style-guide.md`. Remove or update any conflicting advice.
        *   **Output:** Updated `memory-bank/clarity/clarity-ui-api-development-guidance.md`.
        *   **Verification:** Guidance document is consistent with current project plans and decisions.

*   **Task: Refactor `TodayView.tsx` State Management with `useTaskViewStore`**
    *   **Goal:** Implement a robust and simple Zustand-based state management for `TodayView.tsx` as per PLAN mode discussion to resolve errors, simplify logic, and improve maintainability.
    *   **Status:** In Progress (Build Phase)
    *   **Complexity:** Level 3-4 (Significant architectural change to a core component)
    *   **Key Implementation Phases & Steps:**
        1.  **Phase 1: Create `useTaskViewStore.ts`**
            *   **Action:** Define `TaskViewState` and `TaskViewActions` interfaces. Implement the Zustand store with initial state and actions for: raw task data (`setRawTasks`, `clearRawTasks`), focus management (`setFocusedTaskId`, `setFastInputFocused`), selection management (`toggleSelectedTask`, `addSelectedTask`, `removeSelectedTask`, `clearSelectedTasks`), modal management (`openDetailModal`, `closeDetailModal`, `openPrioritizeModal`, `closePrioritizeModal`), and optimistic DND reordering (`reorderRawTasks`). Utilize `devtools` and `immer` middleware.
            *   **File:** `src/stores/useTaskViewStore.ts`
            *   **Testing:** Verify store instantiation and that actions update state correctly (initially via devtools, potentially unit tests later).
        2.  **Phase 2: Refactor `webApp/src/pages/TodayView.tsx`**
            *   **Action:** 
                *   Integrate `useTaskViewStore`: Remove local `useState`s for store-managed state; use store selectors for state access; update event handlers to dispatch store actions.
                *   Sync API Tasks: Add `useEffect` to call `store.setRawTasks(tasksFromApi)` when data from `useFetchTasks` changes.
                *   Compute `displayTasks`: Re-implement `displayTasks: TaskCardProps[]` computation using `useMemo`. Dependencies will include relevant state from `useTaskViewStore` (e.g., `rawTasks`, `focusedTaskId`, `selectedTaskIds`) and memoized component-level API/modal handlers (e.g., `handleMarkComplete`, `store.openDetailModal`). `mapRawTaskToViewModel` (defined in/near `TodayView.tsx`) will be called within this `useMemo`.
                *   Refactor `useEffect` hooks (keyboard navigation, DND `handleDragEnd`, initial focus logic) to use store state and dispatch store actions.
            *   **Testing:** Verify `TodayView.tsx` renders correctly with data from the store, all interactive functionalities (task display, DND, modal triggers, keyboard navigation, fast task input) operate as expected with the new store, and ensure the "Maximum update depth exceeded" error is resolved.
        3.  **Phase 3: Refactor `webApp/src/components/ui/TaskCard.tsx`**
            *   **Action:** 
                *   Update checkbox to reflect selection: `checked` state from `props.isSelected` (derived via `displayTasks` mapping from `store.selectedTaskIds`). Checkbox `onChange` should call `props.onSelectTask(props.id, newSelectedState)`.
                *   Add an explicit "Mark Complete" button/icon that calls `props.onMarkComplete()`.
                *   Ensure other actions (`onEdit`, `onDeleteTask`, `onStartFocus`) correctly use their respective props from `displayTasks`.
            *   **Testing:** `TaskCard` selection mechanism, new completion action, and other existing actions function correctly.
        4.  **Phase 4: Documentation & Final Testing**
            *   **Action:** Document `useTaskViewStore.ts` (state structure, purpose of each action). Conduct comprehensive testing of all refactored components and their interactions. Verify absence of console errors, especially render loops.
    *   **Files Affected:** `src/stores/useTaskViewStore.ts`, `webApp/src/pages/TodayView.tsx`, `webApp/src/components/ui/TaskCard.tsx`.
    *   **Relevant Rules:** `ui-dev` (for component patterns, though the core state logic moves to Zustand).

## IV. Completed / Migrated Tasks (Reference Only)

*   **CLI: Architect Agent Implementation** (Status: DONE in `implementation-plan.md`)
    *   Phase 1: Agent Configuration and Basic Loading (Complete)
    *   Phase 2: Core Functionality - Backlog Interaction (Complete - Split-Scope File Tools, Prompt Refinement)
    *   Phase 3: Memory and Grooming Assistance (Complete - Agent Memory, Grooming Prompt)
*   **UI: Phase 0 - Infrastructure & Foundations** (Status: Complete in `ui-implementation-plan.md`)
    *   Project Setup (Complete)
    *   Authentication Foundation (Complete)
    *   Core UI Components (Complete & Migrated)
    *   Layout & Navigation (AppShell, SideNav, TopBar) (Complete)
    *   Specialized Shared UI Components (TaskCard, TaskStatusBadge, ToggleField, FAB) (Complete & Mig మన)

### Area: Foundational Backend & Data Model for P-E-R

**1. Database Schema Updates for P-E-R** (DONE - User to apply any further pending changes to live DB)
    *   **Task 1.1: Update `tasks` table** (DONE - DDL Updated)
        *   Fields: `status`, `priority`, `motivation`, `completion_note`.
    *   **Task 1.1b: Add `description` to `tasks` table** (DONE - DDL Updated)
        *   Action: Added `description TEXT` to `public.tasks` in `data/db/ddl.sql`.
        *   Verification: DDL updated.
    *   **Task 1.1c: Add Subtask Support to `tasks` table** (DONE - DDL Updated)
        *   Action: Added `parent_task_id UUID NULL REFERENCES public.tasks(id)` and `subtask_position INTEGER NULL` to `public.tasks` table in `data/db/ddl.sql`.
        *   Verification: DDL updated to support task hierarchies.
    *   **Task 1.2: Create `focus_sessions` table** (DONE - DDL Updated)
    *   **Task 1.3: Create `scratch_pad_entries` table** (DONE - DDL Updated)
    *   **(Deferred: `user_preferences`, `streak_tracker`, `projects` tables)**

**2. TypeScript Type Definitions** (Some DONE, some To Do)
    *   **Task 2.1: Update `Task` Interface (Initial P-E-R)** (DONE)
    *   **Task 2.1b: Add `description` to `Task` Interface** (DONE)
        *   Action: Added `description?: string | null` to `Task` interface in `webApp/src/api/types.ts`.
        *   Verification: Type definition updated.
    *   **Task 2.1c: Add Subtask Support to `Task` Interface** (DONE - Types Updated)
        *   Action: Added `parent_task_id?: string | null`, `subtask_position?: number | null`, and `subtasks?: Task[]` to `Task` interface. Adjusted `NewTaskData` and `UpdateTaskData`.
        *   Verification: Type definition updated for hierarchies.
    *   **Task 2.2: Create `FocusSession` Related Enums & Interface** (DONE)
    *   **Task 2.3: Create `ScratchPadEntry` Interface** (DONE)

**3. API Hooks for P-E-R & Enhanced Task Management** (Initial P-E-R DONE, needs expansion)
    *   **Task 3.1: Update `useFetchTasks`** (DONE - for priority/position)
        *   Needs update to fetch subtasks with parent tasks if implementing client-side nesting.
    *   **Task 3.2: Update `useUpdateTask`** (DONE - for initial P-E-R fields)
        *   Needs update to handle `description`, `parent_task_id`, `subtask_position`.
    *   **Task 3.2b: Update `useCreateTask` (or NewTaskData type)** (DONE - Verified suitable for parser output)
        *   To handle `description` and potentially `parent_task_id` on creation.
    *   **Task 3.3: Create `useCreateFocusSession`** (DONE)
    *   **Task 3.4: Create `useEndFocusSession`** (DONE)
    *   **Task 3.5: Create `useCreateScratchPadEntry`** (DONE)

**4. Integrating P-P-E-R & Enhanced Task Management with Frontend Components**
    *   **Task 4.1: Implement Fast Task Entry UI & Logic** (COMPLETED)
        *   **Action:** Created `taskParser.ts` utility. Created `FastTaskInput.tsx` component. Integrated into `TodayView.tsx` with 'T' hotkey for focus and callback for query invalidation on task creation.
        *   **Output:** Functional fast task entry from `TodayView`.
        *   **Verification:** Users can quickly add tasks with optional priority and description from the `TodayView` input.
    *   **Task 4.2: Implement TaskDetailView UI & Logic** (In Progress - core fields, save, trigger from card/key)
        *   **Action:** Created `TaskDetailView.tsx` as a Radix Dialog modal. Implemented `useFetchTaskById` hook. Added form state and fields for Title, Description, Notes, Status, Priority. Implemented Save functionality using `useUpdateTask`. Integrated opening of the modal from `TaskCard.tsx` click via `TodayView.tsx` state management.
        *   **Output:** `TaskDetailView.tsx`, updated `useTaskHooks.ts`, `TodayView.tsx`, `TaskCard.tsx`.
        *   **Verification (Partial):** Modal opens with task data. Basic fields can be edited and saved. Cancel closes. Loading/error states handled for fetch. Save button has loading state.
        *   **Pending:** Delete functionality, remaining form fields (category, due date, etc.), subtask management.
    *   **Task 4.3: Implement Subtask Display & Interaction Logic** (To Do)
    *   **Task 4.4: Implement Prioritize View (Modal)** (To Do - based on `creative-PER-cycle.md`)
    *   **Task 4.5: Implement Execute View (Focus Window)** (To Do - based on `creative-PER-cycle.md`)
    *   **Task 4.6: Implement Reflect View (Modal)** (To Do - based on `creative-PER-cycle.md`)
    *   **Task 4.7: Implement Collapsible Chat Panel** (To Do)
    *   **Task 4.8: Update `TaskCard.tsx` (for subtask toggle, P-P-E-R triggers)** (To Do)
    *   **Task 4.9: Update `TodayView.tsx` (for fast task entry, P-P-E-R flow initiation)** (To Do)

### Area: Project Review & Refinement (Post Drag-and-Drop & Initial P-E-R Backend)

**1. Code Review & Best Practices Alignment**
    *   **Status:** Pending
    *   **Task 1.1: Review API Call Structures**
        *   Focus on `webApp/src/api/hooks/useTaskHooks.ts` and other API interaction points.
        *   Ensure consistent use of Supabase client, error handling, and adherence to RESTful principles where applicable (though Supabase client is RPC-like).
        *   Minimize per-function Supabase client imports if a shared/singleton instance can be used more effectively within the hooks module.
    *   **Task 1.2: Check for Blocking API Calls in UI Logic**
        *   Ensure mutations and queries are handled asynchronously, with appropriate loading/error states in the UI.
        *   Verify that UI remains responsive during API interactions.
    *   **Task 1.3: Review State Management for P-E-R Cycle**
        *   Evaluate if existing Zustand stores (`useAuthStore`, `useTaskStore`, `useThemeStore`) are sufficient or if a new store (e.g., `useCycleStore` or `useFocusSessionStore`) is needed for managing active P-E-R state (current phase, active task for focus, timer state, etc.).
        *   Decision: `useCycleStore` with Zustand is planned for P-E-R state.

**2. Documentation and Context File Review for Next Phase (Cyclical P-E-R Flow UI Implementation)**
    *   **Status:** Pending
    *   **Task 2.1: Review `data/db/ddl.sql` for Completeness**
        *   Ensure all necessary fields and tables for the full P-E-R cycle (including planning inputs, reflection inputs, scratchpad) are defined.
        *   Identify any DDL lagging behind planned UI/feature implementation.
    *   **Task 2.2: Review `productContext.md` and `techContext.md`**
        *   Ensure these documents accurately reflect the current understanding of the P-E-R flow, its data requirements, and the technologies involved.
        *   Update if new decisions or insights have emerged.
    *   **Task 2.3: Update `progress.md` and `tasks.md`**
        *   Reflect the completion of the drag-and-drop feature and the setup for P-E-R backend.
        *   Clearly define the next set of tasks for implementing the P-E-R UI based on the creative design.