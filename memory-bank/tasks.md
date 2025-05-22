# CRITICAL INSTRUCTIONS
All agents MUST `style-guide.md` & `systemPatterns.md`, and adhere to established patterns unless EXPLICITLY told by the user to deviate.
All agents MUST 

# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## PENDING / ACTIVE TASKS

**NEW TASK: Refactor: Implement Robust Short-Term Memory (STM) with Persistent `session_id`**
*   **Status:** Planning Complete - Implementation Next
*   **Complexity:** 3 (Moderately Complex - involves DB, Backend, Frontend, State Management)
*   **Objective:** Implement a stable and persistent short-term memory solution for agents using `langchain-postgres` and a robust client-managed `session_id` strategy to ensure conversation continuity.
*   **Associated Design Discussion:** Based on chat history leading to this plan.
*   **Implementation Plan (Phased):**
    *   **Phase 1: Database Setup**
        *   [X] Define & Apply DDL for `user_agent_active_sessions` table (PK: `user_id`, `agent_name`; Columns: `active_session_id`, `last_active_at`, `created_at`). Include RLS.
        *   [X] Define & Apply DDL for `chat_message_history` table (compatible with `langchain-postgres`). Include RLS (application-level control focus initially).
        *   [X] Document DDL in `memory-bank/clarity/ddl.sql`.
    *   **Phase 2: Backend (`chatServer/main.py`) Adjustments**
        *   [X] Modify `ChatInput` model: `session_id: str` becomes required.
        *   [X] Update `chat_endpoint`: Remove server-side `session_id` generation; rely on client-provided `session_id`.
        *   [X] Ensure `PostgresChatMessageHistory` uses the correct table name (e.g., "chat_message_history").
        *   [X] Verify `PGEngine` initialization and `CHAT_MESSAGE_HISTORY_TABLE_NAME`.
    *   **Phase 3: Client-Side (`webApp`) Implementation**
        *   [X] Create React Query Hooks (`useChatSessionHooks.ts` or similar):
            *   [X] `useFetchActiveChatSession(userId, agentName)`: Fetches from `user_agent_active_sessions`.
            *   [X] `useUpsertActiveChatSession()`: Mutation to upsert into `user_agent_active_sessions`.
            *   [X] `generateNewSessionId()` utility.
        *   [X] Update `useInitializeChatStore(agentName: string)` in `webApp/src/stores/useChatStore.ts`:
            *   [X] Implement full initialization logic: localStorage -> DB fetch -> new session generation.
            *   [X] Use `agentName` consistently (renamed from `agentId` in store state).
            *   [X] Persist/retrieve `session_id` from `localStorage`.
            *   [X] Ensure store state (`sessionId`, `currentAgentName`) is correctly set.
        *   [X] Update `ChatPanel.tsx` (and `fetchAiResponse`):
            *   [X] Pass `agentName` to `useInitializeChatStore`.
            *   [X] Retrieve `sessionId` from `useChatStore`.
            *   [X] Send `sessionId` in JSON body to `/api/chat`.
        *   [X] Remove client-side archival logic (`doArchiveChatDirect`, associated hooks and store methods) and DDL for `recent_conversation_history` table.
    *   **Phase 4: Testing & Refinement**
        *   **Current Status:** Core functionality (STM/LTM) working. New issues identified.
        *   [X] **RESOLVED:** Major PostgreSQL connection issues (incorrect DB URL).
        *   [X] **VERIFIED:** Short-term memory (STM) working (messages save/retrieve within a session).
        *   [X] **VERIFIED:** Long-term memory (LTM) DB writes working (conceptual).
        *   [ ] **NEW - CRITICAL:** Investigate and fix `session_id` persistence. Session IDs do not seem to persist across browser/server restarts or correctly link to user/chat history in the DB.
            *   [ ] Review client-side `session_id` generation and storage (`localStorage`, `useChatSessionHooks.ts`, `useChatStore.ts`).
            *   [ ] Review server-side handling of `session_id` in `chatServer/main.py` and its interaction with `PostgresChatMessageHistory`.
            *   [ ] Verify `user_agent_active_sessions` table is correctly populated and utilized if part of the session persistence design.
            *   [ ] Test `session_id` persistence across browser refresh/reopen for the same user/agent.
            *   [ ] E2E: Conversation continuity across tab/browser close.
            *   [ ] E2E: Separate agent conversations have separate histories.
            *   [ ] E2E: Cross-device session resumption (latest session from DB should win, if applicable).
        *   [ ] **NEW - IMPORTANT:** Investigate and address chat response latency.
            *   [ ] Add detailed timestamps to `chatServer/main.py` logs (request received, agent invocation start/end, DB interaction start/end, response sent).
            *   [ ] Analyze logs to pinpoint bottlenecks.
        *   [ ] User to continue with detailed testing plan in the morning.
    *   **Phase 5: Code Cleanup & Documentation**
        *   [ ] Delete `src/core/history/supabase_chat_history.py`.
        *   [ ] Remove old `session_id` logic from `chatServer/main.py`.
        *   [ ] Refactor/remove client-side batch archival if deemed redundant.
        *   [ ] Update relevant documentation (`activeContext.md`, `tasks.md` (this entry), READMEs).

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

**0. Agent Memory System v2 Implementation (Efficient & Evolving)**
    *   **Status:** In Progress
    *   **Complexity:** 4 (Complex System)
    *   **Associated Creative Design:** `memory-bank/creative/agent_memory_system_v2_efficient_evolving.md`
    *   **Implementation Plan:** `memory-bank/implementation_plans/agent_memory_system_v2_impl_plan.md`
    *   **Objective:** Refactor the agent memory system to minimize database writes, implement an evolving natural language LTM, leverage client-side buffering, and ensure robust short-term context.
    *   **Sub-Tasks (Phased Implementation):**
        *   **Phase 1: Backend Foundation - LTM & Short-Term Cache Core** (Status: DONE)
            *   Define/migrate schemas for `agent_long_term_memory` and `agent_sessions` (optional). RLS.
            *   Implement `server_session_cache` in `chatServer`.
            *   Create `ManageLongTermMemoryTool` (`read`, `overwrite`/`append`).
            *   Modify `agent_loader.py` and `CustomizableAgent` for LTM.
            *   Unit/Integration tests for tool and LTM read/write.
        *   **Phase 2: Client-Side Buffering & Direct DB Archival** (Status: UI Integration for Chat Store Init DONE - Testing Archival Next)
            *   Define/migrate schema for `recent_conversation_history`. RLS. (Status: DONE)
            *   Create `/api/chat/session/archive_messages` endpoint in `chatServer`. (Status: DONE - but to be deprecated)
            *   Implement client-side archival triggers in `useChatStore.ts`. (Status: DONE)
            *   Refactor client-side archival logic (`useChatStore.ts` and `useArchiveChatMutation` hook) to use direct Supabase client writes to `recent_conversation_history` instead of API endpoint. (Status: DONE)
            *   Integrate `agentId` into `ChatPanel` and initialize `useChatStore` correctly. (Status: DONE)
            *   Align client-side data synchronization triggers (for tasks and chat archival) towards a common event-driven or centralized mechanism where feasible. (Status: DEFERRED - Current separate mechanisms deemed acceptable for now)
            *   Test client triggers and direct Supabase batch storage. (Status: To Do - Part of UI Integration Testing)
        *   **Phase 3: Integrating Short-Term Context Flow & Debugging Core Agent Execution** (Status: In Progress -> **SUPERSEDED by "Refactor: Implement Robust STM"**)
            *   Modify client `/api/chat` calls (send only new messages). (Status: To Do -> Covered by new plan)
            *   Refactor `chatServer` `/api/chat` endpoint for `server_session_cache` and new client messages. (Status: To Do -> Covered by new plan, `server_session_cache` removed)
            *   Ensure `CustomizableAgentExecutor` processes assembled short-term history. (Status: In Progress -> Core of new plan)
            *   **[RESOLVED]** Resolve `InvalidArgument: 400 * GenerateContentRequest.contents[X].parts: contents.parts must not be empty.` error occurring after tool calls with Gemini model. (Status: RESOLVED - Switched to `format_to_tool_messages` and `ToolsAgentOutputParser`)
            *   E2E testing of conversational flow. (Status: To Do - Unblocked)
        *   **Phase 4: Refinements, Advanced LTM Operations & Pruning** (Status: To Do)
            *   Enhance `ManageLongTermMemoryTool` (section-based editing).
            *   Implement pruning/archival for `recent_conversation_history`.
            *   Execute full test plan (`comprehensive_agent_memory_and_customization_test_plan_v1.md`).
            *   Documentation updates.

**1. Supabase Schema Design/Refinement (Original V1 approach - Review and Adapt for V2)**
    *   **Task 1.1: Define Schema for Agent Memory (V1: `agent_sessions`, `agent_chat_messages`)**
        *   **Goal:** Design tables & stores. (V1 `agent_chat_messages` is superseded by V2 `recent_conversation_history` and client/server caching. `agent_sessions` might still be used or adapted for V2).
        *   **Output:** DDL & store schema for agent memory tables.
        *   **Status:** V1 Backend MVP Implemented. **Action: Review and adapt for V2. `agent_chat_messages` likely removed/repurposed.**
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
    *   **Task 1.4: Define RLS Policies for Agent-Related Tables (Original V1 - Review and Adapt for V2)**
        *   **Goal:** Ensure appropriate Row Level Security.
        *   **Action:** Implement RLS for V2 tables: `recent_conversation_history`, `agent_long_term_memory`, (and `agent_sessions` if used).
        *   **Output:** SQL migration scripts for RLS policies.
        *   **Status:** V1 Backend MVP Implemented. **Action: Ensure V2 tables have RLS.**

**2. API Endpoints in `chatServer/` (Original V1 - Review and Adapt for V2)**
    *   **Task 2.1: Design and Implement Endpoints for Agent Memory (V1)**
        *   **Goal:** Allow agents (via `chatServer`) to save/load conversation history/summaries from Supabase.
        *   **Action:** Create FastAPI endpoints.
        *   **Output:** New API endpoints in `chatServer/main.py`.
        *   **Status:** Achieved via direct Supabase client in `SupabaseChatMessageHistory` class (V1). **Action: V2 uses new `/api/chat/session/archive_messages` and modified `/api/chat`. Direct Supabase client for per-message history (V1) is superseded.**
    *   **Task 2.2: Design and Implement Endpoints for Agent Prompts/Contexts**
        *   **Goal:** Allow agents to fetch/update their specific prompts/customizations from Supabase.
        *   **Action:** Create FastAPI endpoints for prompt customizations.
        *   **Output:** New API endpoints in `chatServer/main.py`.
        *   **Status:** Backend MVP Implemented (`/api/agent/prompt_customizations/...` endpoints created)

**3. Backend MVP Validation & Documentation (Original V1 - Superseded by V2 Implementation & Test Plan)**
    *   **Status:** Partially Done for V1. **Action: This entire task section is superseded by the implementation and testing of Agent Memory System V2 (Task 0 above) and its associated test plan (`comprehensive_agent_memory_and_customization_test_plan_v1.md`).**
    *   **Objective:** Ensure the implemented backend MVP (agent memory, prompt customization, customizable agent) is robust, well-tested, and documented before proceeding to UI development.
    *   **Task 3.1: Manual Testing of Backend MVP (V1)**
        *   **Goal:** Verify all new backend components (Supabase schemas, `SupabaseChatMessageHistory`, `PromptManagerService`, `CustomizableAgent`, `UpdateSelfInstructionsTool`, updated `agent_loader.py`, and `chatServer/main.py` endpoints) are functioning as expected.
        *   **Key Actions:**
            *   Define test scenarios for chat history persistence with `test_agent`. (Verified: Chat messages are persisted and retrieved across sessions via Supabase).
            *   Define test scenarios for prompt customization using `UpdateSelfInstructionsTool` and verifying changes through `PromptManagerService` and direct API calls. (Next focus for manual testing).
            *   Execute tests (e.g., using `curl` to interact with `chatServer/main.py` API endpoints, and observing Supabase data changes, and using the CLI for `test_agent` tool usage).
            *   Document results and any issues found.
        *   **Files/Areas:** `chatServer/main.py` endpoints (`/api/chat`, `/api/agent/prompt_customizations`), Supabase tables (`agent_sessions`, `agent_chat_messages`, `user_agent_prompt_customizations`), `config/agents/test_agent/agent_config.yaml`, `src/cli/main.py`.
        *   **Status:** In Progress - Core memory persistence (Supabase integration for chat history) is now working. The `RuntimeError: Event loop is closed` is resolved. Next is to verify prompt customization persistence.
        *   **Note:** Initial `RuntimeError: Event loop is closed` issue during tool use has been resolved. Focus is now on verifying the full scope of Task 3.1.
    *   **Task 3.2: Implement Unit Tests for Backend MVP Components (V1)**
        *   **Goal:** Create unit tests for new Python classes and functions to ensure their correctness and facilitate future refactoring.
        *   **Key Actions:**
            *   Write unit tests for `src/core/memory/supabase_chat_history.py` (`SupabaseChatMessageHistory`), mocking Supabase client interactions.
            *   Write unit tests for `src/core/prompting/prompt_manager.py` (`PromptManagerService`), mocking HTTP requests.
            *   Write unit tests for `src/core/agents/customizable_agent.py` (`CustomizableAgent`), focusing on prompt construction and tool integration.
            *   Write unit tests for `src/core/tools/prompt_tools.py` (`UpdateSelfInstructionsTool`).
            *   Write unit tests for relevant new/modified logic in `src/core/agent_loader.py`.
        *   **Files:** New test files in `tests/core/memory/`, `tests/core/prompting/`, `tests/core/agents/`, `tests/core/tools/`, and `tests/core/`.
        *   **Status:** To Do
    *   **Task 3.3: Update Technical Documentation for Backend MVP (V1)**
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
    *   **Goal:** Refactor `TaskDetailView` state management to align with the new state management approach and best practices.
    *   **Status:** To Do
    *   **Complexity:** Level 4 (involves refactoring a complex component and integrating new state management logic)
    *   **Depends On:** Successful completion of Task 7 (abstraction of state management logic into reusable hooks)
    *   **Key Actions:**
        1.  **Phase 1: Refactor `TaskDetailView` to use the new state management approach**
            *   Replace direct state management with the new state management pattern
            *   Integrate the new state management logic into `TaskDetailView`
        2.  **Phase 2: Refine and verify the new state management implementation**
            *   Test the refactored `TaskDetailView` against the manual test plan in `memory-bank/clarity/testing/task-detail-view-test-plan.md`
            *   Address any issues arising from the integration
            *   Refine the implementation if necessary based on practical application
    *   **Files Affected:** `webApp/src/components/features/TaskDetail/TaskDetailView.tsx`

*   **Task 9: Refactor `TaskDetailView` State Management (Align with Option 2 & Best Practices)**
    *   **Goal:** Refactor `TaskDetailView` state management to align with the new state management approach and best practices.
    *   **Status:** To Do
    *   **Complexity:** Level 4 (involves refactoring a complex component and integrating new state management logic)
    *   **Depends On:** Successful completion of Task 7 (abstraction of state management logic into reusable hooks)
    *   **Key Actions:**
        1.  **Phase 1: Refactor `TaskDetailView` to use the new state management approach**
            *   Replace direct state management with the new state management pattern
            *   Integrate the new state management logic into `TaskDetailView`
        2.  **Phase 2: Refine and verify the new state management implementation**
            *   Test the refactored `TaskDetailView` against the manual test plan in `memory-bank/clarity/testing/task-detail-view-test-plan.md`
            *   Address any issues arising from the integration
            *   Refine the implementation if necessary based on practical application
    *   **Files Affected:** `webApp/src/components/features/TaskDetail/TaskDetailView.tsx`