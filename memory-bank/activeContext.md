import datetime

# Active Context & Current Focus

This document outlines the current high-priority task, relevant files, and key considerations for the AI agent.

**Last Updated:** 2025-01-25

## Current High-Priority Task:

**1. Assistant-UI Migration Implementation**

*   **Status:** Active - Planning Complete, Ready for Implementation
*   **Objective:** Migrate existing custom ChatPanel implementation to assistant-ui library for enhanced functionality, better accessibility, and improved maintainability.
*   **Key Points:**
    *   Implement custom runtime adapter to preserve existing backend API
    *   Replace custom chat components with assistant-ui's production-ready interface
    *   Maintain session management and state synchronization
    *   Add streaming support and enhanced tool visualization
    *   Preserve all existing functionality while gaining rich message types, accessibility, and performance improvements
*   **Current Step:** Ready to begin Phase 1 - Environment Setup and Dependencies
*   **Implementation Plan:** `memory-bank/implementation_plans/assistant-ui-migration-plan.md`

**2. ChatServer Main.py Decomposition - Phase 3: Extract Services and Background Tasks**

*   **Status:** Completed
*   **Objective:** Extract business logic into service classes and background task management into dedicated modules, further reducing main.py complexity and improving maintainability.
*   **Results:** Successfully completed all services extraction - ChatService, PromptCustomizationService, and BackgroundTaskService implemented with comprehensive testing (40 tests total)

**2. CRUD Tool Migration to DB Configuration**

*   **Status:** Completed
*   **Objective:** Move all CRUD tool logic (table, method, field_map, etc.) to the `agent_tools` table as config. Only the generic `CRUDTool` class remains in code. Loader instantiates tools from DB config and runtime values. No code changes are needed to add new CRUD tools.
*   **Key Points:**
    *   All CRUD tool definitions (table, method, field_map) are now stored in the `config` column of `agent_tools`.
    *   The loader reads these configs and instantiates the generic `CRUDTool` with runtime values (`user_id`, `agent_id`, `supabase_url`, `supabase_key`).
    *   The registry only needs to include `CRUDTool` (and any custom tools).
    *   To add a new CRUD tool, insert a row in `agent_tools` with the correct config—no code changes required.
    *   Refactored `src/core/tools/crud_tool.py`: Removed redundant `None` checks in the `_run` method for `data_for_processing` and `final_data_payload`, relying on earlier Pydantic/loader validations and the robustness of internal helper methods like `_prepare_data_payload`.
    *   See `tool-creation-pattern.md` for the new pattern and example inserts.

**3. Refactor: Implement Robust Session Management & Agent Executor Caching**

*   **Status:** Implementation, Documentation, and Reflection Complete. See `memory-bank/clarity/references/guides/memory_system_v2.md` and `memory-bank/reflection/reflection-session-mgmt-v2.md`.
*   **Objective:** Implement a stable and persistent chat session management system using the `chat_sessions` table, and optimize server performance by caching AgentExecutors based on active client sessions.
*   **Core Logic:** See new guide for details.
*   **Next Steps:** Integration testing and future enhancements.
*   **Recent Fixes:**
    *   Resolved `NameError` on server startup by reordering scheduled task definitions.
    *   Refactored client-side API call for sending messages into a `useSendMessageMutation` hook.
    *   Prevented multiple session instance creation on chat open with an `isInitializingSession` flag in `useChatStore`.
*   **Design Document:** `session_management_and_executor_caching_plan.md`
*   **Task Breakdown:** See `memory-bank/tasks.md` for detailed phases and sub-tasks.

## Key Focus Areas for Implementation:

1.  **Assistant-UI Migration (Primary Focus):**
    *   Phase 1: Install dependencies and setup environment
    *   Phase 2: Implement custom runtime adapter for backend integration
    *   Phase 3: Replace ChatPanel with assistant-ui components
    *   Phase 4: Integrate with existing Zustand state management
    *   Phase 5: Add advanced features (streaming, tool visualization)
    *   Phase 6: Comprehensive testing and optimization
    *   Phase 7: Documentation and deployment
2.  **CRUD Tool System:**
    *   All CRUD tool logic is now DB-driven. No code changes are needed to add new CRUD tools—just DB inserts.
    *   Loader and registry are minimal and generic.
    *   See `tool-creation-pattern.md` for details.
3.  **Client-Side (`webApp`):**
    *   `webApp/src/api/hooks/useChatApiHooks.ts`: Implemented `useSendMessageMutation`.
    *   `webApp/src/stores/useChatStore.ts`: Refactored store state and logic for session initialization (including `isInitializingSession` fix), message handling (heartbeat), and session deactivation.
    *   `webApp/src/components/ChatPanel.tsx`: Integrated new mutation hook, manages session lifecycle (init, heartbeat, unload).
4.  **Server-Side (`chatServer/main.py`):**
    *   Adapted `AGENT_EXECUTOR_CACHE` to use `(user_id, agent_name)` as key and remove self-TTL.
    *   Ensured `/api/chat` uses `chat_sessions.chat_id` (from request's `session_id` field) for `PostgresChatMessageHistory`.
    *   Implemented background tasks (and fixed startup error) to deactivate stale `chat_session_instances` and evict corresponding inactive `AgentExecutors` from the cache.

## Relevant Files (Under Active Development/Review):

*   **Assistant-UI Migration Focus:**
    *   `webApp/src/components/ChatPanel.tsx` (Current implementation to be migrated)
    *   `webApp/src/stores/useChatStore.ts` (State management integration)
    *   `webApp/src/api/hooks/useChatApiHooks.ts` (Backend integration)
    *   `webApp/src/lib/assistantui/` (New runtime adapter module)
    *   `webApp/src/components/ChatPanelV2.tsx` (New assistant-ui implementation)
    *   `memory-bank/implementation_plans/assistant-ui-migration-plan.md` (Implementation plan)
*   **Completed ChatServer Decomposition:**
    *   `chatServer/services/` (All services implemented)
    *   `chatServer/models/` (Phase 1 - Models and Protocols)
    *   `chatServer/protocols/` (Phase 1 - Models and Protocols)
    *   `chatServer/config/` (Phase 2 - Configuration)
    *   `chatServer/database/` (Phase 2 - Database)
    *   `chatServer/dependencies/` (Phase 2 - Dependencies)
*   **Other Active Files:**
    *   `tool-creation-pattern.md` (CRUD tool pattern)
    *   `session_management_and_executor_caching_plan.md` (Primary Plan)
    *   `memory-bank/tasks.md` (Detailed Task List)

## Key Constraints & Considerations:

*   **Service Layer Architecture:** Extract business logic while maintaining clean separation of concerns
*   **Background Task Management:** Centralize scheduled task logic for better maintainability
*   **Minimal Server Endpoints:** Client-side logic handles direct DB interactions with `chat_sessions` via RLS.
*   **CRUD Tool Extensibility:** All CRUD tools are now DB-configured. No code changes required for new tools.
*   **Idempotency & Race Conditions:** Addressed a key race condition in `initializeSessionAsync`.
*   **TTL Management:** Client-side heartbeats and server-side scheduled tasks will manage session and executor liveness.
*   **Clarity of IDs:**
    *   `chat_sessions.id`: PK, unique identifier for a specific client engagement/session instance.
    *   `chat_sessions.chat_id`: Foreign key (conceptually) to a persistent chat conversation/memory.
    *   `/api/chat` request body's `session_id` field will carry the `chat_sessions.chat_id` value.

## Previous Context (Completed):

*   **Phase 2 (COMPLETED):** Configuration, database, and dependencies extraction
    *   Successfully removed 200+ lines from main.py
    *   Created 18 new files (9 implementation + 9 test files)
    *   Achieved 94 tests passing with 100% pass rate
    *   Fixed import compatibility for both module and direct execution
*   **Phase 1 (COMPLETED):** Models and protocols extraction
    *   Clean separation of data models and interfaces
    *   Comprehensive test coverage (31 tests)
    *   Fixed Pydantic deprecation warnings

**Last Task Archived:** Task 9: Architect and Implement `useEditableEntity` Hook & Refactor `TaskDetailView`
**Archive Document:** `memory-bank/archive/archive-task9.md`

**Immediate Focus / Next Steps:**
1.  **[ACTIVE] Assistant-UI Migration Implementation**
    *   **Objective:** Migrate ChatPanel to assistant-ui for enhanced functionality and maintainability
    *   **Current Step:** Phase 1 - Environment Setup and Dependencies
    *   **Implementation Plan:** `memory-bank/implementation_plans/assistant-ui-migration-plan.md`
2.  **[COMPLETED] ChatServer Main.py Decomposition - Phase 3**
    *   **Objective:** Extract services and background tasks to complete the decomposition
    *   **Status:** All services implemented with comprehensive testing
3.  **[ACTIVE] CRUD Tool Migration to DB Configuration**
    *   **Objective:** Complete testing and documentation of the new DB-driven pattern
4.  **[ACTIVE] Refactor: Implement Robust Session Management & Agent Executor Caching**
    *   **Objective:** Complete integration testing of the new session management system

**Mode Recommendation:** IMPLEMENT (Assistant-UI Migration - Phase 1)

**General Project Goal:** Migrate to assistant-ui for enhanced chat functionality while maintaining existing backend architecture and session management.

**Pending Decisions/Questions:**
*   Service interface design for chat processing and session management
*   Background task scheduling and lifecycle management approach
*   Integration testing strategy for the new service layer

**Previous Focus (Completed/Superseded in this context):**
*   CLI/Core Backend MVP Testing (Task 3.1 from `memory-bank/tasks.md`):
    *   Core agent memory persistence via Supabase (original V1 approach) was working.
    *   RuntimeError during tool execution was resolved.
    *   Prompt customization persistence verified.
*   Agent Memory System v1 Design & Implementation (Superseded by V2)
*   Linter error fixes in `useTaskHooks.ts` and `types.ts`.
*   Refactor `useChatApiHooks.ts` for direct Supabase writes.
*   Update `useChatStore.ts` to use direct archival logic.
*   UI integration of `agentId` for `ChatPanel` and `useChatStore` initialization.

**Upcoming Focus (Post ChatServer Decomposition):**
*   Agent Memory System v2 - Phase 4: Refinements, Advanced LTM & Pruning
*   Additional agent tool development and testing

**Key Files Recently Modified/Reviewed (related to Phase 2 completion):**
*   `chatServer/config/settings.py` (Configuration management)
*   `chatServer/database/connection.py` (Database connection pooling)
*   `chatServer/database/supabase_client.py` (Supabase client management)
*   `chatServer/dependencies/auth.py` (Authentication dependencies)
*   `chatServer/main.py` (Updated to use extracted modules)
*   `pytest.ini` (Async test configuration)

**Open Questions/Considerations:**
*   How should the service layer interfaces be designed for maximum testability?
*   What's the best approach for dependency injection in the service layer?
*   How should background tasks be managed and monitored?

Last updated: 2025-01-25

**Mode Recommendation:** IMPLEMENT (ChatServer Services Extraction - Phase 3)

**General Project Goal:** Complete chatServer main.py decomposition with service layer architecture. Enable clean separation of business logic and improved maintainability.