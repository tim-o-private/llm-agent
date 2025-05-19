# CRITICAL INSTRUCTIONS
All agents MUST `style-guide.md` & `systemPatterns.md`, and adhere to established patterns unless EXPLICITLY told by the user to deviate.
All agents MUST 

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
   * **Status:** Design Complete, Implementation In Progress
   * **Task 5.1: Design New State Management Architecture**
      * **Goal:** Create a consistent, robust state management pattern for the entire application
      * **Status:** COMPLETED
      * **Key Actions:** 
         * Documented core principles (entity-centric stores, local-first with eventual sync)
         * Created a comprehensive design document (`memory-bank/clarity/state-management-design.md`)
         * Developed a reference implementation (`memory-bank/clarity/state-management-example.ts`)
         * Created component integration example (`memory-bank/clarity/state-management-component-example.tsx`)
   
   * **Task 5.2: Implement Task Store with New Architecture**
      * **Goal:** Refactor task management to use the new state management approach
      * **Status:** PARTIAL - IN PROGRESS (Phases 1-3 Complete)
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

*   **Task 6: Re-architect TaskDetailView Save & State Management**
    *   **Goal:** Refactor `TaskDetailView.tsx` to use React Hook Form for parent task field management and simplify save/close logic, improving robustness and maintainability, establishing a reference pattern for modal-based editors.
    *   **Status:** Implementation of RHF for parent fields complete.
    *   **Complexity:** Level 3
    *   **Key Phases & Steps:**
        1.  **Phase 1: Requirements & Design (Completed as part of interactive session)**
            *   Identify generalized save functionality requirements.
            *   Research and confirm React Hook Form as the key out-of-the-box solution.
            *   Map out a simple, straightforward implementation strategy.
            *   Define documentation strategy for the reference architecture. (See below)
            *   Capture existing manual test plan for `TaskDetailView`. (See below)
            *   Create a state diagram for the generalized object editor flow. (See below)
        2.  **Phase 2: React Hook Form Integration for Parent Task (Completed)**
            *   Confirmed `react-hook-form` is installed and correctly configured.
            *   Defined RHF form data types/schema for the Task entity (editable fields).
            *   Initialized `useForm` hook in `TaskDetailView.tsx`, managing default values from the fetched task and resetting appropriately.
            *   Replaced existing `formData` state and `handleChange` logic with RHF `register` or `Controller` components for all parent task form fields.
            *   Replaced manual `parentTaskHasChanges` memo with `formState.isDirty` from RHF.
        3.  **Phase 3: Refactor Save Logic (Completed)**
            *   Simplified the "Save Changes" button's `disabled` logic to primarily rely on `formState.isDirty` and relevant mutation loading states.
            *   Refactored the `handleSave` function to utilize `handleSubmit(onValidParentSubmit)` pattern from RHF.
            *   Implemented the `onValidParentSubmit` callback.
        4.  **Phase 4: Subtask Interaction & `childOperationsOccurredInSessionRef` (Completed)**
            *   Introduced `childOperationsOccurredInSessionRef = useRef(false)`.
            *   Ensured subtask operations set `childOperationsOccurredInSessionRef.current = true`.
            *   Reset `childOperationsOccurredInSessionRef.current = false` when the modal opens.
        5.  **Phase 5: Cleanup & Testing (Largely Completed, ongoing verification)**
            *   Removed old `formData` state and `parentTaskHasChanges` memo.
            *   Removed overly complex logging or workarounds.
            *   Thoroughly execute the captured manual test plan against the refactored component.
            *   Document test results in `activeContext.md`.
        6.  **Phase 6: Documentation (Partially complete with state diagram and test plan)**
            *   Create a new markdown document detailing this RHF-based modal editing pattern as a reference architecture for future similar components.
            *   Link to this new document from relevant guides like `ui-guide.md` or `api-data-guide.md`.
        7.  **Phase 7: Implement Conditional Close/Cancel Logic (Deferred)**
            *   **Goal:** Implement prompting mechanism before closing the modal if there are unsaved parent changes (`isDirty`) or unacknowledged child operations (`childOperationsOccurredInSessionRef`).
            *   **Status:** To Do
            *   **Details:** Modify `wrappedOnOpenChange` or a new cancel handler to check `isDirty` and `childOperationsOccurredInSessionRef`. If true, use `window.confirm()` or a custom modal to ask for confirmation before closing. If false, close directly.
    *   **Files Affected (Primary):** `webApp/src/components/features/TaskDetail/TaskDetailView.tsx`.
    *   **Supporting Files (Review/Minor Adjustments):** `webApp/src/api/hooks/useTaskHooks.ts`.
    *   **New Files:** New reference architecture documentation file.
    *   **Blocking:** Further complex feature additions to `TaskDetailView` until this refactor is complete and stable.

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

## III. Agent Memory & Tooling Enhancement (Supabase Integration)
    *   **Status:** Planning Complete - **Implementation ongoing, critical for Chat Panel and future agent capabilities.**

**1. Supabase Schema Design/Refinement (Agent Memory, Prompts, Tasks)**
    *   **Task 1.1: Define Schema for Agent Memory**
        *   **Goal:** Design tables & stores for `agent_sessions` (session_id, agent_id, user_id, created_at, summary) and `agent_chat_messages` (message_id, session_id, timestamp, sender_type, content_type, content, tokens). Consider LangChain `ChatMessageHistory` compatibility. Update `ddl.sql`.
        *   **Output:** DDL & store schema for agent memory tables.
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
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/context/load`) to retrieve from `user_agent_configs` (and potentially `agent_core_prompts`