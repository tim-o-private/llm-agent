# Agent Memory System - Consolidated Test Plan

**Version:** 2.0 (Reflects STM Refactor)
**Date:** ''' + datetime.now().strftime('%Y-%m-%d') + '''
**Associated Design:** Current STM Refactor (driven by chat history), original LTM concepts from `memory-bank/creative/agent_memory_system_v2_efficient_evolving.md`.

## 1. Introduction

This document outlines the test plan for the agent memory system, focusing on the implemented Short-Term Memory (STM) solution using `langchain-postgres` with `PostgresChatMessageHistory`, client-side `session_id` management, and the existing Long-Term Memory (LTM) capabilities. The goal is to ensure the system is robust, reliable, and meets current requirements for conversation persistence and agent knowledge.

## 2. Scope of Testing

### In Scope:

*   **Short-Term Memory (STM) & Session Persistence:**
    *   `chat_message_history` Supabase table: Schema, RLS policies, data integrity.
    *   `user_agent_active_sessions` Supabase table: Schema, RLS policies, data integrity.
    *   Backend (`chatServer/main.py`):
        *   Usage of `PostgresChatMessageHistory` with client-provided `session_id`.
        *   Correct loading and saving of messages to `chat_message_history`.
        *   Interaction with `ConversationBufferWindowMemory`.
    *   Client-Side (`webApp` - `useChatStore.ts`, `useChatSessionHooks.ts`):
        *   `session_id` generation for new user/agent interactions.
        *   `session_id` retrieval from `localStorage`.
        *   Fetching/Upserting `session_id` in `user_agent_active_sessions` table.
        *   Passing `session_id` and `agentName` to the backend.
*   **Long-Term Memory (LTM):**
    *   `agent_long_term_memory` Supabase table: Schema, RLS policies.
    *   `ManageLongTermMemoryTool`: `read`, `overwrite`, `append` operations.
    *   Agent Core Integration: Loading LTM notes into agent prompts, availability and correct functioning of `ManageLongTermMemoryTool`.
*   **Chat Flow & Agent Interaction:**
    *   Basic message send/receive functionality.
    *   Agent response generation using both STM and LTM where applicable.
*   **Overall System & Configuration:**
    *   Agent configuration for LTM tool.
    *   Client initialization of chat store with `agentName` and `session_id`.

### Out of Scope (for this specific test plan iteration):

*   Superseded STM mechanisms: `server_session_cache`, client-side batch archival to `recent_conversation_history` (JSONB table).
*   Advanced LTM operations (e.g., section-based editing, summarization within LTM tool beyond basic CRUD).
*   Pruning/archival mechanisms for `chat_message_history` (beyond basic RLS and application logic).
*   Automated UI tests (focus is on unit, integration, and manual E2E for core logic).
*   Comprehensive performance, load, and stress testing (basic latency observation is in scope).
*   Agent prompt customization features (unless implicitly tested with LTM).

## 3. Testing Strategy

A combination of testing types will be employed:

*   **Unit Tests:** To verify individual functions, methods, and components in isolation (mocking dependencies).
*   **Integration Tests:** To verify interactions between components (e.g., agent using LTM tool, client hooks interacting with Supabase tables).
*   **Manual E2E Tests:** To verify user flows and overall system behavior from the UI and API perspectives, including database interactions.
*   **Database Verification:** Manual checks of Supabase table schemas, RLS policies, and data integrity.

## 4. Test Environment & Tools

*   **Local Development Environment:** With Supabase local development setup.
*   **Backend:** Python, FastAPI, `psycopg_pool`, `langchain-postgres`, `supabase-py`.
*   **Frontend:** TypeScript, React, Zustand, `@tanstack/react-query`.
*   **Testing Frameworks:**
    *   Python: `pytest`, `pytest-mock`.
    *   JavaScript/TypeScript: `jest` or `vitest`, `testing-library/react`.
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

#### 5.1.2. LTM Integration Tests (Agent using the tool)

*   PASS **Test Case LTM-IT-001: Agent Reads LTM**
    *   **Description:** An agent successfully reads its LTM notes.
    *   **Steps:**
        1.  Manually add LTM notes for a test_user_id, test_agent_id in Supabase.
        2.  Configure an agent (`test_agent`) to have the `ManageLongTermMemoryTool`.
        3.  Interact with the agent (e.g., via CLI) and instruct it to "Read your long term memory."
    *   **Expected Result:** The agent's response includes the LTM notes. The agent's prompt template correctly incorporates LTM content fetched during `load_agent_executor`.
*   PASS **Test Case LTM-IT-002: Agent Overwrites LTM**
    *   **Description:** An agent successfully overwrites its LTM.
    *   **Steps:**
        1.  Configure `test_agent` with `ManageLongTermMemoryTool`.
        2.  Instruct the agent: "Overwrite your long term memory with: Today is a sunny day."
        3.  Verify in Supabase `agent_long_term_memory` table that the content is updated.
    *   **Expected Result:** LTM notes in DB are updated. Agent confirms action.
*   PASS **Test Case LTM-IT-003: Agent Appends to LTM**
    *   **Description:** An agent successfully appends to its LTM.
    *   **Steps:**
        1.  Ensure some LTM notes exist (e.g., "Initial notes. ").
        2.  Configure `test_agent` with `ManageLongTermMemoryTool`.
        3.  Instruct the agent: "Append to your long term memory: Remember to buy milk."
        4.  Verify in Supabase that content is "Initial notes. Remember to buy milk.".
    *   **Expected Result:** LTM notes in DB are appended. Agent confirms action.

#### 5.1.3. `agent_long_term_memory` Table & RLS Manual Verification

*   SKIPPED **Test Case LTM-DB-001: Table Schema Verification** (Columns: `id`, `user_id`, `agent_name`, `notes`, `created_at`, `updated_at`)
*   FUTURE **Test Case LTM-DB-002: RLS Policy - User Can Access Own LTM**
    *   **Description:** Verify RLS allows users to select/insert/update/delete their own LTM entries.
    *   **Steps:**
        1.  As test_user_1, attempt to CRUD LTM for an agent associated with test_user_1.
    *   **Expected Result:** Operations succeed.
*   FUTURE **Test Case LTM-DB-003: RLS Policy - User Cannot Access Others' LTM**
    *   **Description:** Verify RLS prevents users from accessing LTM of other users.
    *   **Steps:**
        1.  As test_user_1, attempt to CRUD LTM for an agent associated with test_user_2.
    *   **Expected Result:** Operations fail due to RLS.

---

### 5.2. Backend - Short-Term Memory (STM) & `chatServer` Logic

#### 5.2.1. `PostgresChatMessageHistory` & `/api/chat` Endpoint Integration

*   PASS **Test Case STM-BE-IT-001: Message Saving**
    *   **Description:** Verify new messages sent to `/api/chat` are saved to `chat_message_history`.
    *   **Steps:**
        1.  Send a message via API call to `/api/chat` with a `session_id`, `user_id`, `agentName`.
        2.  Check `chat_message_history` table in Supabase for the new message associated with the `session_id`.
    *   **Expected Result:** Message (user and AI response) is present with correct `session_id`, type, and content.
*   PASS **Test Case STM-BE-IT-002: Message Loading & Context Building**
    *   **Description:** Verify existing messages are loaded for an ongoing session.
    *   **Steps:**
        1.  Ensure messages exist in `chat_message_history` for a `session_id`.
        2.  Send a new message to `/api/chat` with that `session_id`.
        3.  (Requires backend logging/debugger) Verify `PostgresChatMessageHistory` loads previous messages and `ConversationBufferWindowMemory` receives them.
    *   **Expected Result:** Agent receives appropriate conversational history.
*   FAIL **Test Case STM-BE-IT-003: Empty History for New Session ID**
    *   **Description:** Verify that a new, unknown `session_id` results in an empty history for the agent.
    *   **Steps:** Send a message to `/api/chat` with a completely new `session_id`.
    *   **Expected Result:** `PostgresChatMessageHistory` initializes as empty; agent gets no prior STM. Messages are then saved under this new `session_id`.
    *   **Note:** Unable to provoke a new session_id; it's always pulled from cache. Verified path works for initial ID creation.

#### 5.2.2. `chat_message_history` Table & RLS Manual Verification

*   PASS **Test Case STM-DB-001: Table Schema Verification**
    *   **Description:** Verify schema of `chat_message_history` table.
    *   **Steps:** Inspect table in Supabase Studio.
    *   **Expected Result:** Columns (e.g., `id`, `session_id`, `message_type`, `message_content`, `created_at` - or as per `langchain-postgres` spec), types, indexes are correct.
*   **Test Case STM-DB-002: RLS Policy Verification**
    *   **Description:** Verify RLS policies (e.g., user can only interact with their own session data if policies are user-centric, or application-level control).
    *   **Steps:** Attempt direct DB operations under different user contexts if applicable, or verify application logic correctly isolates session data.
    *   **Expected Result:** Policies prevent unauthorized access/modification.

---

### 5.3. Client-Side - `session_id` Management & STM Interaction

#### 5.3.1. `useChatStore.ts` & `useChatSessionHooks.ts` Unit/Integration Tests

*   **Test Case STM-CS-UT-001: `initializeSessionAsync` - New Session (No localStorage, No DB record)**
    *   **Description:** Verify new `session_id` is generated, persisted to `localStorage`, and upserted to `user_agent_active_sessions`.
    *   **Steps:**
        1.  Mock `localStorage` to be empty.
        2.  Mock `useFetchActiveChatSession` to return no session.
        3.  Mock `useUpsertActiveChatSession` to succeed.
        4.  Call `initializeSessionAsync` in `useChatStore`.
    *   **Expected Result:** New `session_id` in store state. `localStorage.setItem` called. `useUpsertActiveChatSession` called with new `session_id`.
*   **Test Case STM-CS-UT-002: `initializeSessionAsync` - Existing Session in `localStorage`**
    *   **Description:** Verify `session_id` from `localStorage` is used and potentially validated/updated in `user_agent_active_sessions`.
    *   **Steps:**
        1.  Mock `localStorage` to return an existing `session_id`.
        2.  Mock `useFetchActiveChatSession` (can return same/different or no session to test merging logic).
        3.  Mock `useUpsertActiveChatSession` to succeed.
        4.  Call `initializeSessionAsync`.
    *   **Expected Result:** `session_id` from `localStorage` is prioritized. Store state updated. `useUpsertActiveChatSession` potentially called to update `last_active_at`.
*   **Test Case STM-CS-UT-003: `initializeSessionAsync` - Existing Session in DB (No `localStorage`)**
    *   **Description:** Verify `session_id` from `user_agent_active_sessions` is used and set in `localStorage`.
    *   **Steps:**
        1.  Mock `localStorage` to be empty.
        2.  Mock `useFetchActiveChatSession` to return an existing `session_id` and `last_active_at`.
        3.  Mock `useUpsertActiveChatSession` to succeed.
        4.  Call `initializeSessionAsync`.
    *   **Expected Result:** `session_id` from DB is used. Store state updated. `localStorage.setItem` called. `useUpsertActiveChatSession` potentially called.
*   **Test Case STM-CS-UT-004: `addMessage` and `fetchAiResponse` Integration**
    *   **Description:** Verify `addMessage` updates UI and `fetchAiResponse` (or equivalent) sends correct `session_id` and `agentName` to backend.
    *   **Steps:**
        1.  Initialize store with a `session_id` and `agentName`.
        2.  Call `addMessage` (user message).
        3.  Trigger AI response, mocking the actual API call but spying on its parameters.
    *   **Expected Result:** Backend API call parameters include the correct `session_id` and `agentName`.
*   **Test Case STM-CS-UT-005: `generateNewSessionId` Utility**
    *   **Description:** Verify utility generates valid UUIDs.
    *   **Expected Result:** Returns a string matching UUID format.

#### 5.3.2. `user_agent_active_sessions` Table & RLS Manual Verification

*   PASS **Test Case SESS-DB-001: Table Schema Verification**
    *   **Description:** Verify schema of `user_agent_active_sessions`.
    *   **Steps:** Inspect table in Supabase Studio.
    *   **Expected Result:** Columns (`user_id`, `agent_name`, `active_session_id`, `last_active_at`, `created_at`), PK (`user_id`, `agent_name`), types are correct.
*   **Test Case SESS-DB-002: RLS Policy Verification**
    *   **Description:** Verify RLS allows users to manage their own active session records.
    *   **Steps:** Use client UI (which triggers hooks) or direct API calls (if any) as different authenticated users.
    *   **Expected Result:** Users can only fetch/upsert their own `user_agent_active_sessions` entries.

---

### 5.4. End-to-End (E2E) Tests - STM & Session Persistence

*   PASS **Test Case STM-E2E-001: Conversation Continuity - Single Session**
    *   **Description:** Basic multi-turn conversation within one browser session.
    *   **Steps:** Open chat, send several messages, verify agent responds contextually. Check `chat_message_history` table for all messages under the same `session_id`.
    *   **Expected Result:** Coherent conversation. All messages in DB.
*   PASS **Test Case STM-E2E-002: Conversation Continuity - Browser Refresh**
    *   **Description:** Test if conversation resumes after a browser refresh.
    *   **Steps:**
        1.  Start a conversation, send a few messages.
        2.  Refresh the browser page.
        3.  Chat UI re-initializes.
        4.  Send a new message.
    *   **Expected Result:** Agent responds remembering prior context from the refreshed session. `session_id` in `localStorage` and `user_agent_active_sessions` should be consistent. `chat_message_history` should show continuous log.
*   PASS **Test Case STM-E2E-003: Conversation Continuity - Browser Close & Reopen**
    *   **Description:** Test if conversation resumes after closing and reopening the browser.
    *   **Steps:**
        1.  Start a conversation.
        2.  Close browser tab/window.
        3.  Reopen browser, navigate back to the app.
        4.  Chat UI re-initializes.
        5.  Send a new message.
    *   **Expected Result:** Agent responds remembering prior context.
*   CANNOT TEST **Test Case STM-E2E-004: Separate Agent Histories (Same User)**
    *   **Description:** If a user chats with Agent A, then Agent B, their histories should be separate.
    *   **Steps:**
        1.  Chat with `agentName="agent_A"`.
        2.  Switch UI or context to chat with `agentName="agent_B"`.
        3.  Chat with Agent B.
        4.  Switch back to Agent A.
    *   **Expected Result:** Agent A remembers its conversation, Agent B remembers its own. `user_agent_active_sessions` should have distinct entries for (`user_id`, `agent_A`) and (`user_id`, `agent_B`) with potentially different `active_session_id`s. `chat_message_history` reflects this.
*   CANNOT TEST **Test Case STM-E2E-005: `localStorage` Cleared**
    *   **Description:** Test behavior if user clears `localStorage` (simulates new browser/device without prior `localStorage` state).
    *   **Steps:**
        1.  Start a conversation (establishes `session_id` in DB via `user_agent_active_sessions`).
        2.  Manually clear `localStorage` for the site.
        3.  Refresh page / re-initialize chat.
    *   **Expected Result:** Client should fetch the active `session_id` from `user_agent_active_sessions` for that user/agent and resume the session. If no record in `user_agent_active_sessions` (e.g. first ever use, or if that table was also cleared), a brand new session is created.
*   **Test Case STM-E2E-006: Latency Observation**
    *   **Description:** Observe chat response latency during E2E tests.
    *   **Steps:** Perform various chat interactions.
    *   **Expected Result:** Responses should be reasonably quick. Note any significant delays for investigation (detailed analysis via server logs with timestamps).

---

### 5.5. Combined System E2E Tests (STM + LTM)

*   PASS **Test Case COMB-E2E-001: LTM Influence on STM Conversation**
    *   **Description:** Agent uses LTM to inform responses in an STM conversation.
    *   **Steps:**
        1.  Ensure LTM has a note: "User's favorite color is blue."
        2.  Start a new chat session (STM).
        3.  User: "What color should I paint my bike?"
    *   **Expected Result:** Agent suggests blue, referencing LTM. Conversation (STM) continues.
*   PASS **Test Case COMB-E2E-002: Agent Updates LTM During STM Conversation**
    *   **Description:** Agent learns something new in STM and updates LTM.
    *   **Steps:**
        1.  Start STM chat. User: "My project deadline is next Friday."
        2.  Agent uses `ManageLongTermMemoryTool` to save this to LTM.
        3.  Verify LTM content in DB.
        4.  Later in STM conversation (or new session), User: "Remind me about my deadlines."
    *   **Expected Result:** Agent recalls "project deadline is next Friday" from LTM.

---

### 5.6. Overall System & Configuration

*   PASS **Test Case CONF-IT-001: Agent Configuration for LTM Tool**
    *   **Description:** Agent loads and uses LTM based on its config.
    *   **Steps:**
        1.  In `config/agents/test_agent/agent_config.yaml`, ensure `ManageLongTermMemoryTool` is listed.
        2.  Pre-populate LTM for this agent.
        3.  Run the `test_agent` (e.g. via CLI). Its initial prompt should reflect the LTM.
    *   **Expected Result:** Agent's system prompt includes LTM notes. The tool is available to the agent.
*   **Test Case CONF-E2E-001: `ChatPanel` Initialization with `agentName` & `session_id` flow**
    *   **Description:** `ChatPanel` uses `useChatStore` which correctly initializes `agentName` and derives/retrieves `session_id`.
    *   **Steps:**
        1.  In `TodayView.tsx`, ensure a specific `agentName` is passed to `ChatPanel`/`useChatStore` initialization.
        2.  Using browser dev tools or Zustand devtools, inspect `useChatStore` state for `currentAgentName` and `sessionId`.
    *   **Expected Result:** `currentAgentName` matches. `sessionId` is initialized according to the logic (new, from `localStorage`, or from DB).

## 6. Test Deliverables

*   This Test Plan document.
*   Unit test scripts (`*.test.py`, `*.test.ts`).
*   Test execution results (summary, especially for manual tests).
*   Bug reports for any issues found.

## 7. Assumptions & Dependencies

*   Supabase local development environment is set up and functional.
*   Node.js, Python, and relevant package managers are installed.
*   Required environment variables are configured.
*   Core agent execution logic (LLM calls, basic tool use) is stable.

--- 