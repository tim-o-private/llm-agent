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
    *   **Status:** Planning Complete - Ready for Implementation
    *   **Task 1.1: Integrate Radix Themes Provider**
        *   **Action:** Install `@radix-ui/themes`. Wrap root of `webApp` with `<Theme>`. Include Radix Themes CSS.
        *   **Output:** Basic Radix Theming activated.
        *   **Verification:** Default Radix styles visible.
    *   **Task 1.2: Configure Base Light/Dark Mode using Radix Themes**
        *   **Action:** Determine initial `accentColor` & `grayColor`. Configure `<Theme>` provider. Implement theme switching mechanism (e.g., Zustand/Context store for `appearance` prop, localStorage persistence).
        *   **Output:** Functional light/dark mode. UI toggle for switching.
        *   **Verification:** App switches themes, preference persists.
    *   **Task 1.3: Define Semantic Color Mappings (Tailwind to Radix Variables)**
        *   **Action:** Identify semantic color names for Tailwind. Map them in `tailwind.config.js` to CSS custom properties from Radix Themes (e.g., `primary: 'var(--accent-9)'`).
        *   **Output:** Updated `tailwind.config.js`.
        *   **Verification:** Semantic Tailwind classes correctly apply Radix Theme derived colors.
    *   **Task 1.4: Refactor Existing Components for Radix Theme Compatibility** (In Progress)
        *   Audit components in `webApp/src/components/ui/` and `webApp/src/components/ui/chat/`.
        *   Replace hardcoded Tailwind color classes (e.g., `bg-blue-500`, `dark:bg-gray-800`) with the new semantic tokens.
        *   Ensure components correctly adapt to light/dark modes via Radix Theme variables.
        *   Address any styling conflicts or visual regressions.
        *   Specific components reviewed/updated:
            *   `Button.tsx` (via `webApp/src/styles/ui-components.css`): Styles for `.btn-primary`, `.btn-secondary`, `.btn-danger` updated. PostCSS error for `.btn-danger` resolved by refactoring Tailwind key from `'bg-danger-solid'` to `'danger-bg'.` (Done)
            *   `Card.tsx` (Done)
            *   `Input.tsx` (Done)
            *   `Label.tsx` (Done)
            *   `Modal.tsx` (Done)
            *   `Spinner.tsx` (Done)
            *   `TaskCard.tsx` (Done)
            *   `TaskStatusBadge.tsx` (Done)
            *   `Checkbox.tsx` (Done)
            *   `CoachCard.tsx` (Done)
            *   `ErrorMessage.tsx` (Done)
            *   `FAB.tsx` (Done)
            *   `ToggleField.tsx` (Done)
            *   `chat/MessageBubble.tsx` (Done)
            *   `chat/MessageHeader.tsx` (Done)
            *   `chat/MessageInput.tsx` (Done - removed override on Input component)
        *   Remaining components to verify or refactor: (List any components not yet explicitly checked or known to need work)
    *   **Task 1.5: Document Multi-Palette & Advanced Theming Approach** (Done)
        *   **Action:** Document in `style-guide.md`/`techContext.md` how to switch `accentColor`, use other `<Theme>` props (`panelBackground`, `radius`, `scaling`), and when to use Radix props vs. Tailwind.
        *   **Output:** Updated documentation in `memory-bank/style-guide.md`.
        *   **Verification:** Documentation is clear and covers the specified points.

**2. Keyboard Navigability Audit & Implementation**
    *   **Status:** COMPLETED (Initial Audit & Fixes - Advanced shortcuts are future scope)
    *   **Task 2.1: Comprehensive Keyboard Navigation Audit & Fixes** (DONE)
        *   **Action:** Create audit checklist. Perform manual keyboard-only testing. Document findings in `memory-bank/keyboard_nav_audit.md`.
        *   **Fixes Implemented (II.2.1.1 - II.2.1.3):
            *   **II.2.1.1:** Button styling in Modals (e.g., `AddTaskTray`) fixed for Radix variables & focus visibility.
            *   **II.2.1.2:** Left navigation (`SideNav`) now supports ArrowUp/ArrowDown key navigation.
            *   **II.2.1.3:** Global tab order corrected to `TopBar` -> `SideNav` -> Main Content. Logo moved from `SideNav` to `TopBar`.
        *   **Output:** Updated `memory-bank/keyboard_nav_audit.md`. Code changes in `AppShell.tsx`, `SideNav.tsx`, `TopBar.tsx`, `webApp/src/styles/ui-components.css`.
        *   **Verification:** Major keyboard navigation issues in shell and modals resolved.
    *   **Task 2.2: Implement Fixes for Basic Keyboard Accessibility Issues (Component Level)** (DONE - Major components covered during II.2.1 fixes. Remaining minor components to be caught in general testing or future specific audits if issues arise.)
        *   **Action:** Ensure semantic HTML. Add `tabindex="0"` and ARIA for custom interactive elements. Fix focus order (avoid `tabindex > 0`). Ensure visible focus indicators (Tailwind focus rings or Radix defaults) for remaining components like `Checkbox.tsx`, `ToggleField.tsx`, etc.
        *   **Output:** Relevant component files updated as part of II.2.1.
        *   **Verification:** Core interactive UI elements are keyboard accessible.
    *   **Task 2.3: Ensure Accessibility of Radix UI Components** (DONE - Radix defaults largely respected; custom button styling uses direct outline for focus.)
        *   **Action:** Review Radix UI docs for keyboard patterns. Test Radix components in-app. Ensure custom styling/composition doesn't break their accessibility.
        *   **Output:** Minor code adjustments if needed.
        *   **Verification:** Radix components are fully keyboard operable.
    *   **Task 2.4: Address Complex Keyboard Interactions (Modals, Custom Controls)**
        *   **Action:** Modals: trap focus, Esc to close, focus returns to trigger. Custom Widgets: implement ARIA and keyboard handlers.
        *   **Output:** Code changes for complex interactions.
        *   **Verification:** Re-test complex components with keyboard.
    *   **Task 2.5: Document Keyboard Navigation Patterns**
        *   **Action:** Update `style-guide.md` or accessibility doc with app-specific keyboard patterns or global shortcuts (e.g., Cmd/Ctrl+K).
        *   **Output:** Updated documentation.
        *   **Verification:** Documentation is clear.

**3. Drag-and-Drop Task Reordering (within Today View list, using `dnd-kit`)**
    *   **Status:** COMPLETED
    *   **Sub-Task 3.1: Install dnd-kit packages** (DONE)
        *   `pnpm add @dnd-kit/core @dnd-kit/sortable @dnd-kit/modifiers @dnd-kit/utilities`
    *   **Sub-Task 3.2: Update `techContext.md`** (DONE)
        *   Added `dnd-kit` to UI libraries.
    *   **Sub-Task 3.3: Make `TaskCard.tsx` sortable** (DONE)
        *   Import necessary hooks and components from `dnd-kit`.
        *   Wrap `TaskCard` with `useSortable`.
        *   Add `transform`, `transition`, `attributes`, `listeners` props.
    *   **Sub-Task 3.4: Implement Drag and Drop in `TodayView.tsx`** (DONE)
        *   Add `DndContext`, `SortableContext`.
        *   Implement `handleDragEnd` for optimistic updates.
        *   Add sensors (`PointerSensor`, `KeyboardSensor`).
    *   **Sub-Task 3.5: Style Drag-and-Drop Interactions** (DONE)
        *   Add visual cues for dragging (shadow, z-index).
        *   Add drag handle (`GripVertical` icon) to `TaskCard.tsx`.
        *   Ensure checkbox and other interactive elements within `TaskCard` remain usable during drag operations and with keyboard.
        *   Final approach: Listeners exclusively on the drag handle, which is focusable.
    *   **Sub-Task 3.6: Persist Reordered Task Positions** (DONE)
        *   **3.6.1 DDL Changes:** (DONE - Applied to Supabase by user)
            *   Add `position INTEGER` to `public.tasks` in `data/db/ddl.sql`.
            *   Add `CREATE INDEX IF NOT EXISTS idx_tasks_position ON public.tasks(position);`
        *   **3.6.2 API Hook (`useUpdateTaskOrder`):** (DONE)
            *   Create `useUpdateTaskOrder` in `webApp/src/api/hooks/useTaskHooks.ts` to batch update task positions.
        *   **3.6.3 Integrate API Hook:** (DONE)
            *   Call `useUpdateTaskOrder` in `handleDragEnd` in `TodayView.tsx`.
        *   **3.6.4 Update Task Type & Fetch Logic:** (DONE)
            *   Add `position` to `Task` type in `webApp/src/api/types.ts`.
            *   Update `useFetchTasks` to order by `position`.
        *   **3.6.5 Verification & Debugging:** (DONE)
            *   Fixed `invalidateQueries` key.
            *   Ensured `displayTasks` updates correctly from `fetchedTasks`.
            *   Confirmed persistence after refresh.

**4. Cyclical Flow Implementation (Prioritize -> Execute -> Reflect)**
    *   **Status:** Planning Complete - Ready for Implementation (High-level design)
    *   **Task 4.1: Define/Refine Core Data Structures and State for Cyclical Flow**
        *   **Status:** Definition Complete - DDL Updated, Ready for API/Type Layer Changes
        *   **Actions:**
            *   **DONE:** Reviewed `tasks` model in `techContext.md` and `productContext.md`.
            *   **DONE:** Updated `data/db/ddl.sql`:
                *   Added `status TEXT CHECK (status IN ('pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred')) DEFAULT 'pending' NOT NULL` to `tasks` table.
                *   Added `priority INTEGER DEFAULT 0 NOT NULL` to `tasks` table.
                *   Created new `focus_sessions` table (for reflections/execution logs) with fields: `id`, `user_id`, `task_id`, `started_at`, `ended_at`, `duration_seconds`, `notes` (reflection), `mood`, `outcome`, `created_at`, and RLS policies/indexes.
            *   **Decision:** Will use Zustand for a `useCycleStore` to manage the current P-E-R phase (Prioritize, Execute, Reflect) and related temporary state.
            *   **Next:** Update TypeScript types (`webApp/src/api/types.ts`) to reflect new/changed DDL fields for `Task` and create a new `FocusSession` type. Update API hooks (`useTaskHooks.ts`, etc.) as needed.
    *   **Task 4.2: Enhance "Today View" for Prioritization (`Prioritize` Phase)**
        *   **Status:** Planning - Awaiting UI Mockups/Creative Design
        *   **Dependencies:** Task 4.1 (DDL/Types for `priority`, `status`)
    *   **Task 4.3: Implement "Focus Mode" (`Execute` Phase)**
        *   **Action:** Build `FocusModeScreen.tsx` (display active task via `FocusHeader.tsx`, integrate `FocusTimer.tsx`, `ScratchPadToggle.tsx` for `ScratchOverlay.tsx`). Navigation for complete/pause/exit.
        *   **Action:** State Management: Update task status to 'in-progress'. Manage timer. Transition to Reflect or TodayView on exit/completion.
        *   **Output:** Functional `FocusModeScreen.tsx` and sub-components.
        *   **Verification:** Users can start task, enter focus mode, use timer, access scratch pad.
    *   **Task 4.4: Implement "Reflection Modal/View" (`Reflect` Phase)**
        *   **Action:** Build `ReflectionModal.tsx` (triggered post-task/EOD). Integrate `MoodPicker.tsx`, `TaskOutcomeSelector.tsx`. Allow notes.
        *   **Action:** Data Persistence: Save reflection data to Supabase.
        *   **Action:** AI Coach (Future): Use reflection data to adapt suggestions.
        *   **Output:** Functional `ReflectionModal.tsx`. Reflection data saved.
        *   **Verification:** Modal appears appropriately. Input captured and saved.
    *   **Task 4.5: Implement Transitions and AI Nudges Between Phases**
        *   **Action:** Define transition logic (Today -> Focus -> Reflect -> Today). Implement basic nudges (e.g., `react-hot-toast`) for "Ready to start top task?". Ensure `ChatPanel` is accessible for detailed AI interaction.
        *   **Output:** Cohesive P-E-R cycle flow. Basic AI nudges.
        *   **Verification:** Transitions are logical. Nudges appear.
    *   **Task 4.6: Document the Cyclical Flow and UI States**
        *   **Action:** Update `productContext.md` (Core User Journey). Create state flow diagrams if helpful. Update `style-guide.md` with any new UI patterns.
        *   **Output:** Updated documentation.
        *   **Verification:** Documentation clearly explains the flow.

## III. Agent Memory & Tooling Enhancement (Supabase Integration)
    *   **Status:** Planning Complete - Ready for Implementation (High-level design)

**1. Supabase Schema Design/Refinement (Agent Memory, Prompts, Tasks)**
    *   **Task 1.1: Define Schema for Agent Memory**
        *   **Goal:** Design tables for agent conversation history & summaries.
        *   **Action:** Draft DDL for `agent_sessions` (session_id, agent_id, user_id, created_at, summary) and `agent_chat_messages` (message_id, session_id, timestamp, sender_type, content_type, content, tokens). Consider LangChain `ChatMessageHistory` compatibility. Update `ddl.sql`.
        *   **Output:** DDL for agent memory tables.
    *   **Task 1.2: Define Schema for Storing Agent Configurations/Prompts**
        *   **Goal:** Design tables for core system prompts and user-specific agent configurations/overrides.
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
        *   **Goal:** Allow agents to fetch their specific prompts/contexts from Supabase.
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/context/load`) to retrieve from `user_agent_contexts` (and potentially `base_agent_prompts`).
        *   **Output:** New API endpoints.
    *   **Task 2.3: Design and Implement Endpoints for Task Interactions by Agents**
        *   **Goal:** Enable agents to read, create, and update tasks in Supabase.
        *   **Action:** Create FastAPI endpoints (e.g., `/api/agent/tasks/create`, `/api/agent/tasks/update/{task_id}`, `/api/agent/tasks/get/{task_id_or_query_params}`).
        *   **Output:** New API endpoints.

**3. Agent Tool Modifications/Creations**
    *   **Task 3.1: Develop/Refactor Task Management Tools for Agents**
        *   **Goal:** Create LangChain tools for agents to interact with tasks via the new `chatServer` Supabase endpoints.
        *   **Action:** Create `CreateTaskTool`, `UpdateTaskTool`, `ReadTaskTool`. These tools will make HTTP requests to the `chatServer` endpoints. Define clear Pydantic schemas for tool inputs.
        *   **Output:** New/updated Python tool files in `src/tools/`.
    *   **Task 3.2: Develop/Refactor Memory Management Tools/Mechanisms for Agents**
        *   **Goal:** Enable agents to persist and load their conversational memory using `chatServer` endpoints.
        *   **Action:** Integrate memory saving/loading into the agent lifecycle (e.g., `AgentExecutor` callbacks or manual calls within `chat_helpers.py`). This might involve a custom `BaseChatMessageHistory` implementation that uses the `chatServer` API.
        *   **Output:** Updated agent memory handling logic in `src/utils/chat_helpers.py` or custom history class.
    *   **Task 3.3: Develop/Refactor Prompt/Context Loading for Agents**
        *   **Goal:** Ensure agents load their base and user-specific prompts/contexts via `chatServer` (which fetches from Supabase).
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
    *   **Task 5.2: Define New Configuration Loading Strategy (Files + Supabase)**
        *   **Goal:** Load static base configs (from files or DB) and augment with user-specific configs from Supabase.
        *   **Action:** Static base: Keep in `config/` YAMLs (Option A recommended). User-specific: Store in `user_agent_settings` or `user_agent_contexts` Supabase table. Define merging logic in `agent_loader.py`.
        *   **Output:** Documented configuration strategy.
    *   **Task 5.3: Implement Refactored Configuration Loading**
        *   **Goal:** Modify `agent_loader.py` for new strategy.
        *   **Action:** Update `agent_loader.py` to fetch user-specific configs from Supabase (via `chatServer` API, using cache) and merge with base configs. Ensure `chatServer` can pass `user_id` / `agent_type_identifier`.
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
        *   Add `status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (...))`.
        *   Add `priority INTEGER NOT NULL DEFAULT 0`.
        *   Add `motivation TEXT`.
        *   Add `completion_note TEXT`.
        *   (Deferred: `value_tag`, `linked_doc_url`, `reward_trigger`, `streak_eligible`, `breakdown` (JSON) - for later AI/advanced features)
    *   **Task 1.2: Create `focus_sessions` table** (DONE - DDL Updated)
        *   Fields: `id`, `user_id`, `task_id`, `start_time`, `end_time`, `notes` (reflection), `mood`, `outcome`.
    *   **Task 1.3: Create `scratch_pad_entries` table** (DONE - DDL Updated)
        *   Fields: `id`, `user_id`, `task_id` (nullable, if general), `focus_session_id` (nullable), `content`, `created_at`.
    *   **(Deferred: `user_preferences`, `streak_tracker` tables)**
    *   **Verification:** `data/db/ddl.sql` updated. User confirms manual application to Supabase for relevant changes.

**2. TypeScript Type Definitions** (DONE)
    *   **Task 2.1: Update `Task` Interface** (DONE)
        *   Add `status: TaskStatus`, `priority: TaskPriority`, `motivation?: string`, `completion_note?: string`.
    *   **Task 2.2: Create `FocusSession` Related Enums & Interface** (DONE)
        *   `FocusSessionMood`, `FocusSessionOutcome` enums.
        *   `FocusSession` interface.
    *   **Task 2.3: Create `ScratchPadEntry` Interface** (DONE)
    *   **Verification:** `webApp/src/api/types.ts` updated.

**3. API Hooks for P-E-R Backend Operations** (DONE - Initial versions for core P-E-R flow)
    *   **Task 3.1: Update `useFetchTasks`** (DONE)
        *   Order by `priority` (then by `position` or `created_at`).
    *   **Task 3.2: Update `useUpdateTask`** (DONE)
        *   To handle new fields like `status`, `priority`, `motivation`, `completion_note`.
    *   **Task 3.3: Create `useCreateFocusSession`** (DONE)
        *   To insert a new focus session.
    *   **Task 3.4: Create `useEndFocusSession`** (DONE)
        *   To update `end_time`, `notes`, `mood`, `outcome` for a focus session.
    *   **Task 3.5: Create `useCreateScratchPadEntry`** (DONE)
    *   **Verification:** Hooks implemented in `webApp/src/api/hooks/useTaskHooks.ts` (and potentially new `useFocusSessionHooks.ts`, `useScratchPadHooks.ts` if complexity warrants). Initial versions for task start/end and reflection exist.

**4. Integrating P-E-R Backend with Frontend Components** (DONE - TaskCard Start Button & TodayView Logic)
    *   **Task 4.1: Update `TaskCard.tsx`** (DONE)
        *   Display `priority` and `status`.
        *   Add "Start" button (or similar) to initiate a focus session / P-E-R flow.
    *   **Task 4.2: Update `TodayView.tsx`** (DONE)
        *   Implement `onStartTask` handler:
            *   Calls `updateTask` to set status to `in_progress`.
            *   Calls `createFocusSession` to log session start.
        *   (Future: Integrate Plan and Reflect views/modals).
    *   **Verification:** "Start" button updates task status and creates a focus session. Basic data flow for starting a task is functional. Solved `onStartTask` prop drilling and callback issues.

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

**4. Plan-Execute-Reflect (P-E-R) Cycle UI/UX Design**
    *   **Status:** Creative Design - Revisions Incorporating Feedback
    *   **Task 4.1: Create Initial P-E-R UI Design Document** (DONE)
        *   **Action:** Drafted `memory-bank/creative/creative-PER-cycle.md`.
        *   **Output:** `memory-bank/creative/creative-PER-cycle.md` created.
        *   **Verification:** Document covers key aspects of P-E-R UI/UX.
    *   **Task 4.2: Review and Refine P-E-R Design Document** (DONE - Feedback Incorporated, Revisions Made)
        *   **Action:** Incorporated user feedback into `memory-bank/creative/creative-PER-cycle.md`. Updated terminology to P-P-E-R (Prioritize-Execute-Reflect). Added designs for Fast Task Entry, TaskDetailView, Subtask handling, Chat Panel location, and refined Execute/Focus window.
        *   **Output:** Updated `memory-bank/creative/creative-PER-cycle.md`.
        *   **Verification:** Revised design document reflects user feedback.
    *   **Task 4.3: (Optional) Create Wireframes or Low-Fidelity Mockups**
        *   **Action:** If detailed visual clarification is needed.
        *   **Output:** Wireframes in `memory-bank/clarity/UI Mockups/PER-Cycle/`.
    *   **Task 4.4: Design Fast Task Entry Mechanism**
        *   **Status:** To Do
        *   **Action:** Detail the UI/UX for the top-of-screen input field, hotkey access, and inline property parsing logic (e.g., `p1`, `due:tmrw`).
        *   **Output:** Specifications for Fast Task Entry in `creative-PER-cycle.md` or a dedicated design doc.
    *   **Task 4.5: Design TaskDetailView**
        *   **Status:** To Do
        *   **Action:** Detail the UI/UX for the modal/panel showing all editable task properties and subtask management.
        *   **Output:** Specifications for `TaskDetailView` in `creative-PER-cycle.md` or a dedicated design doc.
    *   **Task 4.6: Design Subtask Display and Interaction**
        *   **Status:** To Do
        *   **Action:** Detail accordion display for subtasks, how subtasks are focused, and how parent task status might be derived.
        *   **Output:** Specifications for Subtasks in `creative-PER-cycle.md` or a dedicated design doc.

### Area: Foundational Backend & Data Model for P-E-R and Enhanced Task Management

**1. Database Schema Updates** (Some DONE, some To Do)
    *   **Task 1.1: Update `tasks` table (Initial P-E-R)** (DONE - DDL Updated)
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
        *   **Action:** Created `taskParser.ts` utility. Created `FastTaskInput.tsx` component. Integrated into `TodayView.tsx` with 'T' hotkey for focus and callback for query invalidation on task creation. Verified `useCreateTask` and `NewTaskData` are compatible.
        *   **Output:** Functional fast task entry from `TodayView`.
        *   **Verification:** Users can quickly add tasks with optional priority and description from the `TodayView` input.
    *   **Task 4.2: Implement TaskDetailView UI & Logic** (In Progress)
        *   **Action:** Created `TaskDetailView.tsx` as a Radix Dialog modal. Implemented `useFetchTaskById` hook. Added form state and fields for Title, Description, Notes, Status, Priority. Implemented Save functionality using `useUpdateTask`. Integrated opening of the modal from `TaskCard.tsx` click via `TodayView.tsx` state management. Callbacks for update/delete are passed from `TodayView`.
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