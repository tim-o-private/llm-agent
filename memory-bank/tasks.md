# CRITICAL INSTRUCTIONS
All agents MUST `style-guide.md` & `systemPatterns.md`, and adhere to established patterns unless EXPLICITLY told by the user to deviate.
All agents MUST 

# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## PENDING / ACTIVE TASKS

**NEW TASK: CRUD Tool Migration to DB Configuration**
*   **Status:** In Progress
*   **Complexity:** 2-3 (Simple to Moderate - DB, Backend Loader, Minimal Code)
*   **Objective:** Move all CRUD tool logic (table, method, field_map, etc.) to the `agent_tools` table as config. Only the generic `CRUDTool` class remains in code. Loader instantiates tools from DB config and runtime values. No code changes are needed to add new CRUD tools.
*   **Plan:**
    *   All CRUD tool definitions (table, method, field_map) are now stored in the `config` column of `agent_tools`.
    *   The loader reads these configs and instantiates the generic `CRUDTool` with runtime values (`user_id`, `agent_id`, `supabase_url`, `supabase_key`).
    *   The registry only needs to include `CRUDTool` (and any custom tools).
    *   To add a new CRUD tool, insert a row in `agent_tools` with the correct config—no code changes required.
*   **Checklist:**
    *   [X] Migrate all LTM CRUD tools to DB config (see pattern file for example inserts).
    *   [X] Remove explicit CRUD tool subclasses from code (except generic `CRUDTool`).
    *   [X] Update loader to instantiate tools from DB config and runtime values.
    *   [ ] Test: Add a new CRUD tool by DB insert only—no code change.
    *   [ ] Document the new pattern in `tool-creation-pattern.md` and update onboarding docs.

**NEW TASK: Refactor: Implement Robust Session Management & Agent Executor Caching**
*   **Status:** Implementation, Documentation, and Reflection Complete. See `memory-bank/clarity/references/guides/memory_system_v2.md` and `memory-bank/reflection/reflection-session-mgmt-v2.md`.
*   **Complexity:** 3 (Moderately Complex - involves DB, Backend, Frontend, State Management)
*   **Objective:** Implement a stable and persistent chat session management system using the `chat_sessions` table, and optimize server performance by caching AgentExecutors based on active client sessions.
*   **Associated Design Discussion:** `session_management_and_executor_caching_plan.md`
*   **Implementation Plan (Phased - See `session_management_and_executor_caching_plan.md` for full details):**
    *   **Phase 0: Database Setup (User Completed DDL for `chat_sessions`)**
        *   [X] `public.chat_sessions` table created by user.
        *   [X] **Action:** Remove the old `user_agent_active_sessions` table from the database.
    *   **Phase 1: Client-Side - Managing `chat_id` (Persistent Chat ID) and `chat_sessions.id` (Session Instance ID)**
        *   **P1.1: Adapt/Refactor Supabase Client Hooks in `webApp/src/api/hooks/useChatSessionHooks.ts`:**
            *   [X] Rename `UserAgentActiveSession` interface to `ChatSessionInstance`.
            *   [X] Adapt `useFetchActiveChatSession` to `useFetchLatestChatId(userId, agentName)`.
            *   [X] Adapt `useUpsertActiveChatSession` to `useManageChatSessionInstance` (handling create & update for `chat_sessions.id` rows).
        *   **P1.2: Refactor `webApp/src/stores/useChatStore.ts`:**
            *   [X] Update store state: `activeChatId: string | null`, `currentSessionInstanceId: string | null`.
            *   [X] Refactor `initializeSessionAsync(agentName)` logic.
            *   [X] Refactor `addMessage` for heartbeat.
            *   [X] Refactor `clearCurrentSessionAsync()` for deactivation.
            *   [X] **FIXED:** Add `isInitializingSession` flag to prevent multiple concurrent `initializeSessionAsync` calls.
        *   **P1.3: Update `webApp/src/components/ChatPanel.tsx`:**
            *   [X] Trigger `initializeSessionAsync` on mount/`agentName` change.
            *   [X] Ensure `fetchAiResponse` sends `activeChatId` as `session_id` to `/api/chat`.
            *   [X] Implement periodic "heartbeat".
            *   [X] Implement "best-effort" `beforeunload` listener.
            *   [X] **REFACTOR:** Moved `fetchAiResponse` logic into `useSendMessageMutation` hook in `useChatApiHooks.ts`.
        *   **P1.4: All client-side session management logic refactored and tested.**
    *   **Phase 2: Server-Side Executor Cache Logic (`chatServer/main.py`)**
        *   **P2.1: `AGENT_EXECUTOR_CACHE` Key & Type:**
            *   [X] Key: `(user_id, agent_name)`.
            *   [X] Type: `cachetools.Cache` (no self-TTL).
        *   **P2.2: `/api/chat` Endpoint Adaptation:**
            *   [X] Use new cache key for `AGENT_EXECUTOR_CACHE`.
            *   [X] Ensure `PostgresChatMessageHistory` uses `chat_sessions.chat_id` (from request's `session_id` field).
            *   [X] Confirm no writes to `chat_sessions` table from this endpoint.
        *   **P2.3: Implement Server-Side Scheduled Tasks (Background Tasks):**
            *   [X] Function `deactivate_stale_chat_session_instances()`.
            *   [X] Function `evict_inactive_executors()`.
            *   [X] Schedule these tasks to run periodically (e.g., via FastAPI `lifespan` and `asyncio.create_task`).
            *   [X] **FIXED:** Moved scheduled task definitions before `lifespan` function to resolve `NameError`.
        *   **P2.4: All server-side cache and liveness logic refactored and tested.**
    *   **Phase 3: Testing & Refinement**
        *   [ ] Integration testing in progress. Bugs to be fixed separately.
    *   **Phase 4: Code Cleanup & Documentation Update (Post-Implementation)**
        *   [X] Documentation and reflection complete. See new guide and reflection doc.
        *   [X] Delete `src/core/history/supabase_chat_history.py` (if confirmed fully unused after `PostgresChatMessageHistory` is sole mechanism).
        *   [ ] Remove any other old session logic from `chatServer/main.py`.
        *   [ ] Update relevant documentation (`activeContext.md`, `tasks.md` (this entry), READMEs, `session_management_and_executor_caching_plan.md` with completion status). Create "memoryAccess" pattern file in memory-bank/clarity/references/guides.

---
*PREVIOUS STM REFACTOR TASK - TO BE ARCHIVED/CLEANED UP AFTER NEW PLAN IS FULLY IMPLEMENTED AND VERIFIED*
**OLD TASK: Refactor: Implement Robust Short-Term Memory (STM) with Persistent `session_id`**
*   **Status:** Implementation Largely Complete - Testing & Refinement In Progress - *Superseded by "Refactor: Implement Robust Session Management & Agent Executor Caching"*
*   **Complexity:** 3 (Moderately Complex - involves DB, Backend, Frontend, State Management)
*   **Objective:** Implement a stable and persistent short-term memory solution for agents using `langchain-postgres` and a robust client-managed `session_id` strategy to ensure conversation continuity.
*   **Associated Design Discussion:** Based on chat history leading to this plan.
*   **Implementation Plan (Phased):**
    *   **Phase 1: Database Setup (COMPLETED)**
        *   [X] Define & Apply DDL for `user_agent_active_sessions` table (PK: `user_id`, `agent_name`; Columns: `active_session_id`, `last_active_at`, `created_at`). Include RLS.
        *   [X] Define & Apply DDL for `chat_message_history` table (compatible with `langchain-postgres`). Include RLS (application-level control focus initially).
        *   [X] Document DDL in `memory-bank/clarity/ddl.sql`.
    *   **Phase 2: Backend (`chatServer/main.py`) Adjustments (COMPLETED - but will be revised by new plan)**
        *   [X] Modify `ChatInput` model: `session_id: str` becomes required.
        *   [X] Update `chat_endpoint`: Remove server-side `session_id` generation; rely on client-provided `session_id`.
        *   [X] Ensure `PostgresChatMessageHistory` uses the correct table name (e.g., "chat_message_history").
        *   [X] Verify `PGEngine` (now `AsyncConnectionPool`) initialization and `CHAT_MESSAGE_HISTORY_TABLE_NAME`.
        *   [X] Implement `psycopg_pool.AsyncConnectionPool` managed by FastAPI lifespan events.
        *   [X] Implemented `TTLCache` for agent executors (key: `user_id, agent_name, session_id`) - *This cache will be re-designed.*
    *   **Phase 3: Client-Side (`webApp`) Implementation (COMPLETED - but will be revised by new plan)**
        *   [X] Create React Query Hooks (`useChatSessionHooks.ts`):
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
    *   **Phase 4: Testing & Refinement (ACTIVE - but work paused for new plan)**
        *   **Current Status:** Core STM functionality working. `session_id` generation and initial persistence verified. Focus on robust cross-session persistence and latency.
        *   [X] **RESOLVED:** Major PostgreSQL connection issues (incorrect DB URL).
        *   [X] **VERIFIED:** Short-term memory (STM) working (messages save/retrieve within a session using `PostgresChatMessageHistory`).
        *   [X] **VERIFIED (User Confirmed):** `session_id` is being created, passed, and persisted at least for the initial session.
        *   [ ] **NEW** Review logic for instantiating and retrievings & agent_executors - *Addressed by new plan.*
            *   [ ] **NEW** Review `session_id` client-side logic, identify when new session_id will be created. Review with user for correctness. - *Addressed by new plan.*
            *   [ ] **NEW** Improve chat latency by implementing an in-memory per-session agent executor cache. - *Addressed by new plan.*
        *   [ ] User to perform integration testing.
    *   **Phase 5: Code Cleanup & Documentation (PENDING - will be part of new plan's Phase 4)**
        *   [ ] Delete `src/core/history/supabase_chat_history.py` (if confirmed fully unused).
        *   [ ] Remove any other old `session_id` logic from `chatServer/main.py` that might have been missed.
        *   [ ] Final review for and removal of any client-side batch archival code if confirmed redundant.
        *   [ ] Create holistic process diagrams documenting agentExecutor instantiation and destruction, as well as memory creation and retrieval.
        *   [ ] Update relevant documentation (`activeContext.md`, `tasks.md` (this entry), READMEs).
--- 
## GENERAL BACKLOG / FUTURE TASKS
### PROJECT: Create tools for agent task management.

### CLI & Core System Development
*   **Task: Implement Additional Agent Tools**
    *   **Goal:** Add tools for capabilities like web search, reading specific external documents, calendar interaction, etc.
    *   **Status:** Needs Refinement / To Do
*   **Task: Refine Context Formatting/Prompting**
    *   **Goal:** Improve how static context, dynamic context (memory), and tool outputs are presented to the LLM for better performance and reasoning.
    *   **Status:** Needs Refinement
*   **Task: CORE - Rationalize and Refactor Agent Tool Loading & Calling Logic**
    *   **Goal:** Refactor `src/core/agent_loader.py` and related components to establish a clear, robust, and extensible system for defining, loading, and invoking agent tools, separating duties cleanly, and defining a coherent interaction model.
    *   **Status:** To Do
    *   **Complexity:** Level 3-4

### Clarity Web Application UI/UX Tasks (ON HOLD / PENDING)
*   **Task 1.3: Refine `tasks` Table Schema (and other UI-related tables)** (From old "III. Agent Memory & Tooling Enhancement")
    *   **Goal:** Ensure `tasks` table and any other UI-centric tables are well-defined.
    *   **Status:** To Do (Not part of this backend MVP iteration)
*   **Sub-Task 4.1.UI.4: Implement Subtask Display & Interaction Logic** (From "II. Clarity Web Application UI/UX Tasks")
    *   **Status:** To Do - *Next priority after Prioritize View*
*   **Sub-Task 4.1.UI.5: Implement Prioritize View (Modal)** (From "II. Clarity Web Application UI/UX Tasks")
    *   **Status:** In Progress - **Primary Focus**
*   **Sub-Task 4.1.UI.9: Refine Chat Panel Collapse/Expand Animation** (From "II. Clarity Web Application UI/UX Tasks")
    *   **Status:** To Do
*   **Task 5.3: Extend Architecture to Other EntityTypes** (From "II. Clarity Web Application UI/UX Tasks")
    *   **Goal:** Apply the new state management pattern to other entity types.
    *   **Status:** To Do

---
## COMPLETED TASKS

### STM Refactor (Phases 1-3)
*   **Phase 1: Database Setup (COMPLETED)** (Details listed under active task)
*   **Phase 2: Backend (`chatServer/main.py`) Adjustments (COMPLETED)** (Details listed under active task)
*   **Phase 3: Client-Side (`webApp`) Implementation (COMPLETED)** (Details listed under active task)

### General Project / CLI / Core / UI
*   **PLAN-STEP-1:** Finalize project plan document (From BRAINPLN-001)
*   **Task: Refactor Project Structure for Proper Packaging and Module Imports (CLI Core)** (From old "I. CLI & Core Agent Development Tasks")
*   **Task: Investigate and Fix Failing Pytest Suite (CLI Core)** (From old "I. CLI & Core Agent Development Tasks")
*   **Task: Prepare Project for Public Release: Scrub Sensitive Data (CLI Core & General)** (From old "I. CLI & Core Agent Development Tasks")
*   **Task: Implement CI/CD Pipeline for Automated Pytest on PRs (CLI Core)** (From old "I. CLI & Core Agent Development Tasks")
*   **Task 1.2: Define Schema for Storing Agent Configurations/Prompts** (From old "III. Agent Memory & Tooling Enhancement")
    *   **Status:** Backend MVP Implemented (DDL `20240801000100_prompt_customization_schema.sql` created; `PromptManagerService` and API endpoints implemented)
*   **Task 2.2: Design and Implement Endpoints for Agent Prompts/Contexts** (From old "III. Agent Memory & Tooling Enhancement")
    *   **Status:** Backend MVP Implemented (`/api/agent/prompt_customizations/...` endpoints created)
*   **Theming Strategy (Radix Themes + Tailwind)** (Task 1 from "II. Clarity Web Application UI/UX Tasks") - ALL SUBTASKS DONE
*   **Keyboard Navigability Audit & Implementation** (Task 2 from "II. Clarity Web Application UI/UX Tasks") - ALL SUBTASKS DONE
*   **Drag-and-Drop Task Reordering** (Task 3 from "II. Clarity Web Application UI/UX Tasks") - ALL SUBTASKS DONE
*   **Sub-Task 4.1.UI.2: Implement TaskDetailView UI & Logic** (From "II. Clarity Web Application UI/UX Tasks") - COMPLETED
*   **Sub-Task 4.1.UI.5.A: Refactor `TaskCard.tsx` for Prioritization** (From "II. Clarity Web Application UI/UX Tasks") - COMPLETED
*   **Sub-Task 4.1.UI.8: Restore and Enhance Collapsible Chat Panel in `TodayView`** (From "II. Clarity Web Application UI/UX Tasks") - COMPLETED
*   **Sub-Task 4.1.UI.10: Refine and Verify Toast Notification System** (From "II. Clarity Web Application UI/UX Tasks") - COMPLETE
*   **State Management Refactoring (Task 5.1, 5.2)** (From "II. Clarity Web Application UI/UX Tasks") - COMPLETE

---
## CANCELED / SUPERSEDED TASKS

**Agent Memory System v2 Implementation (Efficient & Evolving) (Task 0 under old "III. Agent Memory & Tooling Enhancement")**
    *   **Status:** SUPERSEDED by "Refactor: Implement Robust STM"
    *   (Include its sub-tasks here, marked as superseded)

**Task 1.1: Define Schema for Agent Memory (V1: `agent_sessions`, `agent_chat_messages`)**
    *   **Status:** SUPERSEDED

**Task 1.4: Define RLS Policies for Agent-Related Tables (Original V1)**
    *   **Status:** SUPERSEDED

**Task 2.1: Design and Implement Endpoints for Agent Memory (V1)**
    *   **Status:** SUPERSEDED

**Task 3. Backend MVP Validation & Documentation (Original V1)**
    *   **Status:** SUPERSEDED

# Task Board (Original - Retained for historical context if needed, but primary tasks are above)

## BRAINPLN-001: Brainstorm and Plan Next Major Features for Task View and Agent Capabilities (Status: Backend MVP Implemented; UI/Integration Next)
*   **PLAN-STEP-2:** Initiate CREATIVE phase for "Memory Solution Selection and Design." (Status: Backend MVP Implemented - *This MVP is now superseded by STM refactor*)
*   **PLAN-STEP-3:** Initiate CREATIVE phase for "Agent Execution Logic & Prompt Customization Architecture." (Status: Backend MVP Implemented)
*   **PLAN-STEP-4:** Initiate CREATIVE phase for "UI/UX Design for Conversational Task Management." (Status: Creative Output `conversational_ui_ux_design_v1.md` produced; Implementation Planning Next)
*   **PLAN-STEP-5:** Define detailed implementation tasks for Phase 1 (Conversational UI/UX) based on creative outputs. (Status: In Progress)

**User Stories Addressed:** (Retained for context)
...

**Core Context Considered:** (Retained for context)
...