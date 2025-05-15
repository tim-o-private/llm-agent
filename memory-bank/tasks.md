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
    *   **Task 1.4: Refactor Existing Components for Radix Theme Compatibility**
        *   **Action:** Audit UI components. Remove conflicting Tailwind colors on Radix Primitives. Update custom components to use new semantic Tailwind classes.
        *   **Output:** Updated component files.
        *   **Verification:** All components render correctly in light/dark modes, colors derived from Radix Themes or semantic mappings.
    *   **Task 1.5: Document Multi-Palette & Advanced Theming Approach**
        *   **Action:** Document in `style-guide.md`/`techContext.md` how to switch `accentColor`, use other `<Theme>` props (`panelBackground`, `radius`, `scaling`), and when to use Radix props vs. Tailwind.
        *   **Output:** Updated documentation.
        *   **Verification:** Documentation is clear.

**2. Keyboard Navigability Audit & Implementation**
    *   **Status:** Planning Complete - Ready for Implementation
    *   **Task 2.1: Comprehensive Keyboard Navigation Audit**
        *   **Action:** Create audit checklist for all interactive elements/flows. Perform manual keyboard-only testing (Tab, Shift+Tab, Enter, Space, Arrows). Check focus order & visibility. Test modal escape. Use browser tools/Axe.
        *   **Output:** Detailed report of accessibility issues.
        *   **Verification:** Audit covers all interactive parts.
    *   **Task 2.2: Implement Fixes for Basic Keyboard Accessibility Issues**
        *   **Action:** Ensure semantic HTML. Add `tabindex="0"` and ARIA for custom interactive elements. Fix focus order (avoid `tabindex > 0`). Ensure visible focus indicators (Tailwind focus rings or Radix defaults).
        *   **Output:** Code changes addressing basic issues.
        *   **Verification:** Re-test fixed components/flows.
    *   **Task 2.3: Ensure Accessibility of Radix UI Components**
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
    *   **Status:** Planning Complete - Ready for Implementation
    *   **Task 3.1: Adopt `dnd-kit` and Initial Setup**
        *   **Action:** Install `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/modifiers`. Update `techContext.md` with choice.
        *   **Output:** `dnd-kit` installed. Docs updated.
        *   **Verification:** Project builds.
    *   **Task 3.2: Implement Basic Drag-and-Drop for `TaskCard`s within Today View list**
        *   **Action:** Wrap `TodayView.tsx` (or task list part) with `dnd-kit` provider. Make `TaskCard.tsx` draggable. Make task list a drop zone. Handle `onDragEnd` to update client-side state (Zustand/React Query cache).
        *   **Output:** Functional drag-and-drop reordering in the single "Today" list.
        *   **Verification:** Tasks reorder, state updates. Basic visual feedback.
    *   **Task 3.3: Implement Keyboard-Accessible Drag-and-Drop (with `dnd-kit` Keyboard sensor)**
        *   **Action:** Configure `dnd-kit` Keyboard sensor. Implement keyboard controls (Tab to list/card, Space/Enter to pick up/drop, Arrows to move, Esc to cancel). Provide instructions/cues (screen reader announcements).
        *   **Output:** Keyboard-operable drag-and-drop.
        *   **Verification:** Test with keyboard only. Screen reader announcements are clear.
    *   **Task 3.4: Persist Reordered Tasks (Supabase)**
        *   **Action:** Create/update React Query mutation hook (`useUpdateTaskOrder`) to save new task order (e.g., a `position` field) to Supabase. Call mutation in `onDragEnd`. Implement optimistic updates & error handling.
        *   **Output:** Task order persists after refresh.
        *   **Verification:** Reordering updates Supabase. Changes reflected correctly.
    *   **Task 3.5: Refine Visual Styling and Animations for Drag-and-Drop**
        *   **Action:** Style drag handle, dragged item appearance, placeholder/drop zone per `style-guide.md`. Implement subtle animations (via `dnd-kit` or CSS).
        *   **Output:** Visually polished drag-and-drop.
        *   **Verification:** Animations smooth. Visual feedback clear.
    *   **Task 3.6: (Future - Optional) Drag-and-Drop Between Different Conceptual Lists/Views**
        *   **Status:** Future consideration.

**4. Cyclical Flow Implementation (Prioritize -> Execute -> Reflect)**
    *   **Status:** Planning Complete - Ready for Implementation (High-level design)
    *   **Task 4.1: Define/Refine Core Data Structures and State for Cyclical Flow**
        *   **Action:** Review `tasks` model for `status`, `priority`, `position` (for "Today" list order). Define `reflections` model (mood, outcome, notes) and link to tasks/sessions. Update `ddl.sql`. Consider `useCycleStore` (Zustand) for current phase tracking.
        *   **Output:** Updated DDL. Frontend type definitions.
        *   **Verification:** Data models support the flow.
    *   **Task 4.2: Enhance "Today View" for Prioritization (`Prioritize` Phase - "What's Next" Focus)**
        *   **Goal:** Hub for identifying and focusing on next most important tasks.
        *   **Action:** UI: Single, stack-ranked list for "Today". `TaskCard` shows title, status, simple priority. Drag-and-drop for reordering. Prominent "Start Task". Empty state prompt.
        *   **Action:** AI Coach (`CoachCard`): Initial static prompts (welcome, add task, pick top 1-3). Future: AI helps break down tasks, suggests next task (advanced), assists with *optional* time-blocking.
        *   **Output:** Updated `TodayView.tsx`, `TaskCard.tsx`.
        *   **Verification:** Today View supports "what's next" prioritization.
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

### Existing UI Tasks (from previous plan - to be reviewed/integrated/updated)

*   **Phase 0.5: Core Task Management UI (Status: Review against new plan)**
    *   ~~Task: Today View Page Implementation~~ (Covered and revised in 4.2)
    *   Task: Add Task Tray (Quick + Detailed View)
        *   **Status:** Mostly Complete (Review for alignment with new "Today View" focus, ensure no forced time blocks like M/A/E in quick add).
    *   Task: Chat Interface Implementation
        *   **Status:** Mostly Complete (Ensure `CoachCard` from 4.2 integrates well with `ChatPanel` on `TodayView` and `CoachPage`).
    *   ~~Task: Focus Mode Screen & Components~~ (Covered in 4.3)
    *   Task: Scratch Pad / Brain Dump
        *   **Status:** To Do (Integrate with Focus Mode as per 4.3).

*   **Phase 0.4: Implement scalable design and implementation patterns.**
    *   **Status:** In Progress (Step 9 Pending)
    *   **Step 9: Accessibility Audit and Refinement (Pattern 10)**
        *   **Status:** Pending / To Do (Align with tasks in section "2. Keyboard Navigability Audit & Implementation").

*   **Phase 1: AI Coaching & Integrations (v0.2 Beta - Mostly To Do)**
    *   Task: Nudge System (Align with Task 4.5, focus on "what's next" nudges for v0).
    *   Task: Google Calendar Integration (Future, post-v0 focus on "what's next").
    *   Task: Google Docs Integration (Future).

*   **Phase 2: Smart Productivity Layer (v0.3 Beta - Mostly To Do)**
    *   ~~Task: Reflection Modal & Components~~ (Covered in 4.4)
    *   Task: Gamification Enhancements (e.g., `StreakCounter`) - (Can be a minor addition to Today View / Reflection).

*   **Phase 3: Application Polish & Configuration (NEW PHASE - To Do)**
    *   Task: Settings Screen & Components.
    *   Task: Done List (Task History View).

*   **Phase 0.6: Project Restructure, Deployment Strategy, and Enhanced Chat Server**
    *   Task: Define and Document Deployment Strategy - **Status: Complete**
    *   Task: Implement Project Structure Refactor (Web & API paths) - **Status: Complete**
    *   Task: Enhance `chatServer` Capabilities - **Status: On Hold**
    *   Task: Update All Project Documentation (Post Restructure) - **Status: Complete**
    *   Task: Implement and Test Deployment - **Status: To Do**

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