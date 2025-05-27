import datetime

# Active Context & Current Focus

This document outlines the current high-priority task, relevant files, and key considerations for the AI agent.

**Last Updated:** {datetime.date.today().isoformat()}

## Current High-Priority Task:

**1. Refactor Task Editing UI and Logic**
*   **Status:** Implementation of Core Components Complete - Ready for Testing
*   **Objective:** Improve maintainability, type safety, and user experience of the task editing interface.
*   **Key Achievements:**
    *   Refactored `useEditableEntity.ts` hook, resolving typing and Zod schema issues.
    *   Implemented `TaskForm.tsx` with robust Zod validation and Zustand integration (`getEntityDataFn`, `saveEntityFn`).
    *   Resolved all identified linter errors related to these components.
*   **Relevant Files:**
    *   `webApp/src/hooks/useEditableEntity.ts`
    *   `webApp/src/components/features/TaskDetail/TaskForm.tsx`
    *   `webApp/src/types/editableEntityTypes.ts`
    *   `webApp/src/stores/useTaskStore.ts`
*   **Next Steps:** Comprehensive unit and integration testing for `TaskForm`, `useEditableEntity`, `TaskDetailView`, and `SubtaskList`.
*   **Task Tracking:** `memory-bank/tasks.md` (Refactor Task Editing UI and Logic)

**2. Assistant-UI Migration Implementation**

*   **Status:** COMPLETED - Full Implementation with Professional Styling ✅
*   **Objective:** Migrate existing custom ChatPanel implementation to assistant-ui library for enhanced functionality, better accessibility, and improved maintainability.
*   **Key Achievements:**
    *   Successfully replaced ChatPanel internals globally across all pages (/today, /coach, etc.)
    *   Implemented resizable panels with react-resizable-panels (50% default width, smooth animations)
    *   Enabled assistant-ui by default via feature flags
    *   **NEW**: Added professional styling matching existing design system
    *   **NEW**: Fixed animation issues with smooth transitions (duration-500 ease-in-out)
    *   **NEW**: Integrated MessageHeader component for consistent branding
    *   **NEW**: Applied custom CSS variables to match existing color scheme
    *   Maintained all existing functionality (session management, authentication, backend integration)
    *   Zero backend changes required
*   **Implementation Results:** All phases 1-5 complete - fully production ready
*   **Next Steps:** Optional enhancements (streaming, tool visualization, message actions)
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

1.  **Task Editing UI/Logic Refactor (Testing Next):**
    *   Core components (`useEditableEntity`, `TaskForm`) implementation complete.
    *   Zod schemas and TypeScript typings resolved.
    *   Ready for unit and integration testing.

2.  **Assistant-UI Migration (COMPLETED ✅):**
    *   ✅ Phase 1: Install dependencies and setup environment
    *   ✅ Phase 2: Implement custom runtime adapter for backend integration
    *   ✅ Phase 3: Replace ChatPanel with assistant-ui components (styling deferred)
    *   ✅ Phase 4: Integrate with existing Zustand state management
    *   ✅ Global Implementation: Resizable panels with enhanced UX
    *   [ ] Phase 5: Add advanced features (styling customization, streaming, tool visualization)
    *   [ ] Phase 6: Comprehensive testing and optimization
    *   [ ] Phase 7: Documentation and deployment
*   **Task Editing Refactor (Active - Testing Next):**
    *   `webApp/src/hooks/useEditableEntity.ts`
    *   `webApp/src/components/features/TaskDetail/TaskForm.tsx`
    *   `webApp/src/types/editableEntityTypes.ts`
    *   `webApp/src/components/features/TaskDetail/TaskDetailView.tsx`
    *   `webApp/src/components/features/TaskDetail/SubtaskList.tsx`
*   **Completed ChatServer Decomposition:**
    *   `chatServer/services/` (All services implemented)
    *   `chatServer/models/` (Phase 1 - Models and Protocols)
    *   `chatServer/protocols/` (Phase 1 - Models and Protocols)
    *   `chatServer/config/` (Phase 2 - Configuration)
    *   `chatServer/database/` (Phase 2 - Database)
    *   `chatServer/dependencies/` (Phase 2 - Dependencies)
4.  **[ACTIVE] Refactor: Implement Robust Session Management & Agent Executor Caching**
    *   **Objective:** Complete integration testing of the new session management system

**Mode Recommendation:** PLAN (For testing strategy of Task Editing UI Refactor)

**General Project Goal:** Complete chatServer main.py decomposition with service layer architecture. Enable clean separation of business logic and improved maintainability.

**Pending Decisions/Questions:**
*   Strategy for unit and integration testing of the new task editing components.

**Previous Focus (Completed/Superseded in this context):**
*   CLI/Core Backend MVP Testing (Task 3.1 from `memory-bank/tasks.md`):
    *   Core agent memory persistence via Supabase (original V1 approach) was working.
    *   RuntimeError during tool execution was resolved.
    *   Prompt customization persistence verified.
*   Agent Memory System v1 Design & Implementation (Superseded by V2)
*   Linter error fixes in `useTaskHooks.ts` and `types.ts`.
*   **Linter error fixes and Zod/Typing refinements in `TaskForm.tsx` and `useEditableEntity.ts`.**
*   Refactor `useChatApiHooks.ts` for direct Supabase writes.
*   Update `useChatStore.ts` to use direct archival logic.
*   UI integration of `agentId` for `ChatPanel` and `useChatStore` initialization.

**Upcoming Focus (Post ChatServer Decomposition):**
*   **Testing of Task Editing UI/Logic Refactor.**
*   Agent Memory System v2 - Phase 4: Refinements, Advanced LTM & Pruning
*   Additional agent tool development and testing

**Key Files Recently Modified/Reviewed (related to Task Editing Refactor):**
*   `webApp/src/components/features/TaskDetail/TaskForm.tsx`
*   `webApp/src/hooks/useEditableEntity.ts`
*   `webApp/src/types/editableEntityTypes.ts`
*   `webApp/src/api/types.ts` (for TaskPriority, TaskStatus type usage)

**Open Questions/Considerations:**
*   How should the service layer interfaces be designed for maximum testability?
*   What's the best approach for dependency injection in the service layer?
*   How should background tasks be managed and monitored?

Last updated: {datetime.date.today().isoformat()}

**Mode Recommendation:** PLAN (For testing strategy of Task Editing UI Refactor)

**General Project Goal:** Complete chatServer main.py decomposition with service layer architecture. Enable clean separation of business logic and improved maintainability.