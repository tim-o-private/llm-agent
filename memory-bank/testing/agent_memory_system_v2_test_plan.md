# Agent Memory System v2 - Test Plan

**Version:** 1.0
**Date:** 2024-08-04
**Associated Creative Design:** `memory-bank/creative/agent_memory_system_v2_efficient_evolving.md`
**Associated Implementation Plan:** `memory-bank/implementation_plans/agent_memory_system_v2_impl_plan.md`

## 1. Introduction

This document outlines the test plan for the Agent Memory System v2, covering functionalities implemented in Phase 1 (Backend Foundation - LTM & Short-Term Cache Core) and Phase 2 (Client-Side Buffering & Direct DB Archival). The goal is to ensure the system is robust, reliable, and meets the specified requirements.

## 2. Scope of Testing

### In Scope:

*   **Phase 1: Backend Foundation - LTM & Short-Term Cache Core**
    *   `agent_long_term_memory` Supabase table: Schema, RLS policies.
    *   `ManageLongTermMemoryTool`: `read`, `overwrite`, `append` operations.
    *   Agent Core Integration: Loading LTM notes into agent prompts, availability and correct functioning of `ManageLongTermMemoryTool`.
    *   `server_session_cache` in `chatServer/main.py`: Basic initialization and interaction via the `/api/chat` endpoint (as it pertains to message flow, not full Phase 3 short-term context retrieval yet).
*   **Phase 2: Client-Side Buffering & Direct DB Archival**
    *   `recent_conversation_history` Supabase table: Schema, RLS policies.
    *   `webApp/src/stores/useChatStore.ts`:
        *   Session initialization with `agentId`.
        *   Message addition to local store.
        *   Archival triggers: periodic timer, `visibilitychange` event, `beforeunload` event.
        *   Direct archival mechanism calling `doArchiveChatDirect`.
        *   Correct updating of `lastArchivedMessageCount`.
    *   `webApp/src/api/hooks/useChatApiHooks.ts`:
        *   `doArchiveChatDirect` function for batch inserting messages into `recent_conversation_history` via Supabase client.
    *   `webApp/src/components/ChatPanel.tsx`:
        *   Correct initialization of `useChatStore` with `agentId`.
        *   Message sending to `/api/chat` and displaying responses.
    *   `webApp/src/pages/TodayView.tsx`:
        *   Passing `agentId` to `ChatPanel`.

### Out of Scope (for this specific test plan iteration):

*   Full E2E testing of Phase 3 Short-Term Context Flow (client sending only new messages, server assembling history from cache and new messages).
*   Advanced LTM operations (e.g., section-based editing, summarization within LTM tool) from Phase 4.
*   Pruning/archival mechanisms for `recent_conversation_history` (Phase 4).
*   `agent_sessions` table functionality (unless implicitly tested via LTM or other features).
*   Automated UI tests (focus is on unit, integration, and manual E2E for core logic).
*   Performance and stress testing.

## 3. Testing Strategy

A combination of testing types will be employed:

*   **Unit Tests:** To verify individual functions, methods, and components in isolation.
    *   Mocking dependencies like Supabase client, external APIs.
*   **Integration Tests:** To verify interactions between components or modules.
    *   e.g., Agent using LTM tool, `useChatStore` interacting with `doArchiveChatDirect`.
*   **Manual E2E Tests:** To verify user flows and overall system behavior from the UI perspective, including interactions with the database.
*   **Database Verification:** Manual checks of Supabase table schemas, RLS policies, and data integrity.

## 4. Test Environment & Tools

*   **Local Development Environment:** With Supabase local development setup.
*   **Backend:** Python, FastAPI, `supabase-py`.
*   **Frontend:** TypeScript, React, Zustand, `@tanstack/react-query`.
*   **Testing Frameworks:**
    *   Python: `pytest`, `pytest-mock`.
    *   JavaScript/TypeScript: `jest` or `vitest` (assuming one is standard for the project), `testing-library/react`.
*   **Browsers:** Chrome, Firefox for manual testing.
*   **Tools:** Supabase Studio, browser developer tools, `curl` or Postman for API endpoint testing.

## 5. Test Cases

---

### 5.1. Backend - Long-Term Memory (LTM)

#### 5.1.1. `ManageLongTermMemoryTool` Unit Tests (`tests/core/tools/test_memory_tools.py`)

*   **Test Case LTM-UT-001: Read LTM - Notes Exist**
    *   **Description:** Verify the tool correctly reads LTM notes for a given user_id and agent_id when notes exist.
    *   **Steps:**
        1.  Mock Supabase client `select` to return mock LTM data.
        2.  Instantiate `ManageLongTermMemoryTool` with a user_id.
        3.  Call `_run` with `action="read"`, `agent_id`.
    *   **Expected Result:** Tool returns the mock LTM content. Supabase client called with correct table, filters.
*   **Test Case LTM-UT-002: Read LTM - No Notes Exist**
    *   **Description:** Verify the tool returns an appropriate message or empty string when no LTM notes exist.
    *   **Steps:**
        1.  Mock Supabase client `select` to return empty data or raise a "no rows" equivalent.
        2.  Instantiate `ManageLongTermMemoryTool`.
        3.  Call `_run` with `action="read"`.
    *   **Expected Result:** Tool returns a message like "No LTM notes found for this agent." or an empty string.
*   **Test Case LTM-UT-003: Overwrite LTM - New Notes**
    *   **Description:** Verify the tool correctly overwrites LTM notes.
    *   **Steps:**
        1.  Mock Supabase client `upsert` to succeed.
        2.  Instantiate `ManageLongTermMemoryTool`.
        3.  Call `_run` with `action="overwrite"`, `agent_id`, `content="New notes"`.
    *   **Expected Result:** Tool returns a success message. Supabase `upsert` called with correct data, `user_id`, `agent_id`, and `on_conflict` strategy.
*   **Test Case LTM-UT-004: Append LTM - Existing Notes**
    *   **Description:** Verify the tool correctly appends content to existing LTM notes.
    *   **Steps:**
        1.  Mock Supabase client `select` to return existing notes "Old notes. ".
        2.  Mock Supabase client `upsert` to succeed.
        3.  Instantiate `ManageLongTermMemoryTool`.
        4.  Call `_run` with `action="append"`, `agent_id`, `content="Appended content."`.
    *   **Expected Result:** Tool returns a success message. Supabase `upsert` called with content "Old notes. Appended content.".
*   **Test Case LTM-UT-005: Append LTM - No Existing Notes**
    *   **Description:** Verify appending behaves like overwrite if no notes exist.
    *   **Steps:**
        1.  Mock Supabase client `select` to return no data.
        2.  Mock Supabase client `upsert` to succeed.
        3.  Instantiate `ManageLongTermMemoryTool`.
        4.  Call `_run` with `action="append"`, `agent_id`, `content="New notes via append."`.
    *   **Expected Result:** Tool returns a success message. Supabase `upsert` called with content "New notes via append.".
*   **Test Case LTM-UT-006: Invalid Action**
    *   **Description:** Verify the tool handles invalid actions gracefully.
    *   **Steps:**
        1.  Instantiate `ManageLongTermMemoryTool`.
        2.  Call `_run` with `action="delete_all"`.
    *   **Expected Result:** Tool returns an error message indicating the invalid action.

#### 5.1.2. LTM Integration Tests (Agent using the tool - Manual/CLI or Scripted)

*   **Test Case LTM-IT-001: Agent Reads LTM**
    *   **Description:** An agent successfully reads its LTM notes.
    *   **Steps:**
        1.  Manually add LTM notes for a test_user_id, test_agent_id in Supabase.
        2.  Configure an agent (`test_agent`) to have the `ManageLongTermMemoryTool`.
        3.  Interact with the agent (e.g., via CLI) and instruct it to "Read your long term memory."
    *   **Expected Result:** The agent's response includes the LTM notes. The agent's prompt template correctly incorporates LTM content fetched during `load_agent_executor`.
*   **Test Case LTM-IT-002: Agent Overwrites LTM**
    *   **Description:** An agent successfully overwrites its LTM.
    *   **Steps:**
        1.  Configure `test_agent` with `ManageLongTermMemoryTool`.
        2.  Instruct the agent: "Overwrite your long term memory with: Today is a sunny day."
        3.  Verify in Supabase `agent_long_term_memory` table that the content is updated.
    *   **Expected Result:** LTM notes in DB are updated. Agent confirms action.
*   **Test Case LTM-IT-003: Agent Appends to LTM**
    *   **Description:** An agent successfully appends to its LTM.
    *   **Steps:**
        1.  Ensure some LTM notes exist (e.g., "Initial notes. ").
        2.  Configure `test_agent` with `ManageLongTermMemoryTool`.
        3.  Instruct the agent: "Append to your long term memory: Remember to buy milk."
        4.  Verify in Supabase that content is "Initial notes. Remember to buy milk.".
    *   **Expected Result:** LTM notes in DB are appended. Agent confirms action.

#### 5.1.3. `agent_long_term_memory` Table & RLS Manual Verification

*   **Test Case LTM-DB-001: Table Schema Verification**
    *   **Description:** Verify schema of `agent_long_term_memory` table matches DDL.
    *   **Steps:** Inspect table in Supabase Studio.
    *   **Expected Result:** Columns (`user_id`, `agent_id`, `notes_content`, `created_at`, `updated_at`), types, constraints (unique on `user_id, agent_id`), and trigger for `updated_at` are correct.
*   **Test Case LTM-DB-002: RLS Policy - User Can Access Own LTM**
    *   **Description:** Verify RLS allows users to select/insert/update/delete their own LTM entries.
    *   **Steps:**
        1.  As test_user_1, attempt to CRUD LTM for an agent associated with test_user_1.
    *   **Expected Result:** Operations succeed.
*   **Test Case LTM-DB-003: RLS Policy - User Cannot Access Others' LTM**
    *   **Description:** Verify RLS prevents users from accessing LTM of other users.
    *   **Steps:**
        1.  As test_user_1, attempt to CRUD LTM for an agent associated with test_user_2.
    *   **Expected Result:** Operations fail due to RLS.

---

### 5.2. Client-Side - Chat History Archival (`recent_conversation_history`)

#### 5.2.1. `useChatStore.ts` - Archival Logic Unit/Integration Tests (e.g., `tests/stores/useChatStore.test.ts`)

*   **Test Case CS-UT-001: Initialize Session**
    *   **Description:** Verify `initializeSession` correctly sets `sessionId`, `currentAgentId`, messages.
    *   **Steps:** Call `initializeSession` with mock data.
    *   **Expected Result:** Store state is updated as expected. Archival listeners/timers are set up (mock setup calls).
*   **Test Case CS-UT-002: Add Message**
    *   **Description:** Verify `addMessage` adds a new message with correct ID, timestamp, sender.
    *   **Steps:** Call `addMessage`.
    *   **Expected Result:** Message is added to `messages` array.
*   **Test Case CS-UT-003: Archive Chat Session - Sufficient Messages**
    *   **Description:** Verify `archiveChatSession` calls `doArchiveChatDirect` when new messages exist.
    *   **Steps:**
        1.  Mock `doArchiveChatDirect` to return success.
        2.  Initialize session, add messages.
        3.  Call `archiveChatSession`.
    *   **Expected Result:** `doArchiveChatDirect` is called with correct payload. `lastArchivedMessageCount` is updated. `isArchiving` flag is managed.
*   **Test Case CS-UT-004: Archive Chat Session - Insufficient Messages**
    *   **Description:** Verify `archiveChatSession` does not call `doArchiveChatDirect` if no new messages.
    *   **Steps:**
        1.  Mock `doArchiveChatDirect`.
        2.  Initialize session. Call `archiveChatSession` (no new messages).
    *   **Expected Result:** `doArchiveChatDirect` is not called.
*   **Test Case CS-UT-005: Archive Chat Session - `doArchiveChatDirect` Fails**
    *   **Description:** Verify store handles failure from `doArchiveChatDirect`.
    *   **Steps:**
        1.  Mock `doArchiveChatDirect` to return failure/throw error.
        2.  Initialize, add messages, call `archiveChatSession`.
    *   **Expected Result:** `lastArchivedMessageCount` is not updated. Error handled gracefully (e.g., logged). `isArchiving` flag reset.
*   **Test Case CS-UT-006: Archival Triggers (Conceptual - testing listener/timer setup)**
    *   **Description:** Verify `_setupArchivalListeners` and `_startPeriodicArchive` are called.
    *   **Steps:** Spy on these internal methods during `initializeSession`.
    *   **Expected Result:** Methods are called. (Actual event triggering is for E2E).

#### 5.2.2. `doArchiveChatDirect` (`webApp/src/api/hooks/useChatApiHooks.ts`) Unit Tests

*   **Test Case HOOK-UT-001: Successful Archival**
    *   **Description:** Verify `doArchiveChatDirect` correctly inserts a batch record into Supabase.
    *   **Steps:**
        1.  Mock `supabase.auth.getUser` to return a mock user.
        2.  Mock `supabase.from('recent_conversation_history').insert().select()` to return success and mock IDs.
        3.  Call `doArchiveChatDirect` with test data.
    *   **Expected Result:** Returns `{ success: true, archived_count, db_record_ids }`. Supabase client called with correct data.
*   **Test Case HOOK-UT-002: Archival Fails - Supabase Error**
    *   **Description:** Verify `doArchiveChatDirect` handles Supabase insert errors.
    *   **Steps:**
        1.  Mock `supabase.auth.getUser`.
        2.  Mock `supabase.from().insert()` to return an error.
        3.  Call `doArchiveChatDirect`.
    *   **Expected Result:** Returns `{ success: false, error: "Supabase error message" }`.
*   **Test Case HOOK-UT-003: Archival - No User Authenticated**
    *   **Description:** Verify `doArchiveChatDirect` handles unauthenticated user.
    *   **Steps:**
        1.  Mock `supabase.auth.getUser` to return no user.
        3.  Call `doArchiveChatDirect`.
    *   **Expected Result:** Returns `{ success: false, error: "User not authenticated" }`.
*   **Test Case HOOK-UT-004: Archival - No Messages**
    *   **Description:** Verify `doArchiveChatDirect` handles empty messages array.
    *   **Steps:** Call `doArchiveChatDirect` with empty `messages`.
    *   **Expected Result:** Returns `{ success: true, archived_count: 0 }`. Supabase client not called for insert.

#### 5.2.3. `recent_conversation_history` Table & RLS Manual Verification

*   **Test Case RCH-DB-001: Table Schema Verification**
    *   **Description:** Verify schema of `recent_conversation_history` table.
    *   **Steps:** Inspect table in Supabase Studio.
    *   **Expected Result:** Columns (`id`, `session_id`, `user_id`, `agent_id`, `message_batch_jsonb`, `batch_start_timestamp`, `batch_end_timestamp`, `created_at`, `archived_at`), types, indexes are correct.
*   **Test Case RCH-DB-002: RLS Policy - User Can Insert Own History**
    *   **Description:** Verify RLS allows users to insert their own chat history.
    *   **Steps:** Trigger archival from UI as test_user_1.
    *   **Expected Result:** Insert succeeds. Record in DB has `user_id` of test_user_1.
*   **Test Case RCH-DB-003: RLS Policy - User Cannot Select Others' History (if select is enabled)**
    *   **Description:** Verify RLS prevents users from selecting history of other users.
    *   **Steps:** (If select policy allows self-select) As test_user_1, try to select records for test_user_2.
    *   **Expected Result:** Operation fails or returns empty if RLS correctly filters.

#### 5.2.4. E2E/Manual UI Tests for Archival Triggers (`webApp`)

*   **Test Case ARCH-E2E-001: Periodic Archival**
    *   **Description:** Verify messages are archived periodically.
    *   **Steps:**
        1.  Open `TodayView`. Interact with `ChatPanel` to generate messages.
        2.  Wait for `ARCHIVE_INTERVAL` (e.g., 1 minute).
        3.  Check `recent_conversation_history` table in Supabase.
        4.  Send more messages. Wait again.
    *   **Expected Result:** New message batches are archived after each interval if new messages were sent. `lastArchivedMessageCount` updates.
*   **Test Case ARCH-E2E-002: Visibility Change Archival**
    *   **Description:** Verify messages are archived when browser tab visibility changes.
    *   **Steps:**
        1.  Open `TodayView`, send messages in `ChatPanel`.
        2.  Switch to another browser tab, then switch back.
        3.  Check Supabase.
    *   **Expected Result:** Messages are archived when tab becomes hidden.
*   **Test Case ARCH-E2E-003: Before Unload Archival**
    *   **Description:** Verify messages are attempted to be archived when tab/browser is closed.
    *   **Steps:**
        1.  Open `TodayView`, send messages.
        2.  Close the browser tab.
        3.  Check Supabase.
    *   **Expected Result:** Messages are archived. (Note: this can be less reliable due to browser restrictions on `beforeunload`).
*   **Test Case ARCH-E2E-004: Agent ID Correctly Stored**
    *   **Description:** Verify the correct `agent_id` is stored with the archived messages.
    *   **Steps:**
        1.  Ensure `ChatPanel` is initialized with a specific `agentId` (e.g., "test_agent_alpha").
        2.  Send messages, trigger archival.
        3.  Check `agent_id` column in `recent_conversation_history` table for the new records.
    *   **Expected Result:** The `agent_id` column matches "test_agent_alpha".
*   **Test Case ARCH-E2E-005: `lastArchivedMessageCount` Prevents Duplicates**
    *   **Description:** Verify `lastArchivedMessageCount` ensures messages are not re-archived.
    *   **Steps:**
        1.  Send messages, trigger archival (e.g., periodic).
        2.  Verify messages in DB.
        3.  Trigger archival again without sending new messages.
        4.  Inspect `recent_conversation_history` for duplicate entries of the same messages.
    *   **Expected Result:** No duplicate message batches are created. `doArchiveChatDirect` is not called or called with an empty list.

---

### 5.3. Chat Flow & Short-Term Context (Interaction with `/api/chat` & `server_session_cache`)

*   **Test Case CHAT-E2E-001: Basic Message Send/Receive**
    *   **Description:** User sends a message, `ChatPanel` calls `/api/chat`, receives a response.
    *   **Steps:**
        1.  Open `TodayView`, use `ChatPanel`.
        2.  Send a message like "Hello".
    *   **Expected Result:** AI response is displayed. `fetchAiResponse` in `ChatPanel.tsx` successfully calls the backend. The `agent_id` from `ChatPanel` (or default) is used in the `/api/chat` request.
*   **Test Case CHAT-IT-001: `/api/chat` and `server_session_cache` (Manual Check)**
    *   **Description:** Verify `/api/chat` endpoint in `chatServer/main.py` uses `server_session_cache`.
    *   **Steps:**
        1.  Send multiple messages in a sequence from the UI.
        2.  (Requires backend logging or debugger) Observe if `server_session_cache` in `chatServer/main.py` is being populated with messages for the session.
    *   **Expected Result:** The `server_session_cache` should contain the history of messages sent to `/api/chat` for the current `session_id` derived by the server. (This tests Phase 1 cache setup, not full Phase 3 retrieval).

---

### 5.4. Overall System & Configuration

*   **Test Case CONF-IT-001: Agent Configuration for LTM**
    *   **Description:** Agent loads and uses LTM based on its config.
    *   **Steps:**
        1.  In `config/agents/test_agent/agent_config.yaml`, ensure `ManageLongTermMemoryTool` is listed.
        2.  Pre-populate LTM for this agent.
        3.  Run the `test_agent` (e.g. via CLI). Its initial prompt should reflect the LTM.
    *   **Expected Result:** Agent's system prompt includes LTM notes. The tool is available to the agent.
*   **Test Case CONF-E2E-001: `ChatPanel` Initialization with `agentId`**
    *   **Description:** `ChatPanel` initializes `useChatStore` with the correct `agentId`.
    *   **Steps:**
        1.  In `TodayView.tsx`, ensure a specific `agentId` (e.g., `VITE_DEFAULT_CHAT_AGENT_ID` or a test one) is passed to `ChatPanel`.
        2.  Using browser dev tools or Zustand devtools, inspect `useChatStore` state.
    *   **Expected Result:** `currentAgentId` in `useChatStore` matches the `agentId` passed from `TodayView`. `sessionId` is initialized.

## 6. Test Deliverables

*   This Test Plan document.
*   Unit test scripts (`*.test.py`, `*.test.ts`).
*   Test execution results (summary, especially for manual tests).
*   Bug reports for any issues found.

## 7. Assumptions & Dependencies

*   Supabase local development environment is set up and functional.
*   Node.js, Python, and relevant package managers are installed.
*   Required environment variables (e.g., `VITE_DEFAULT_CHAT_AGENT_ID`, Supabase keys) are configured.
*   The core agent execution logic (without LTM/STM specific changes yet) is stable.

--- 