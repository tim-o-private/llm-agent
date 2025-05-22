# Future Tests for Agent Memory System

This file contains test cases that are deferred for future execution, typically because they require additional setup (e.g., multiple user accounts) or are lower priority for the current testing phase.

## 5.1.3. `agent_long_term_memory` Table & RLS Manual Verification

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

## 5.4. End-to-End (E2E) Tests - STM & Session Persistence

*   **Test Case STM-E2E-004: Separate Agent Histories (Same User)**
    *   **Description:** If a user chats with Agent A, then Agent B, their histories should be separate.
    *   **Steps:**
        1.  Chat with `agentName="agent_A"`.
        2.  Switch UI or context to chat with `agentName="agent_B"`.
        3.  Chat with Agent B.
        4.  Switch back to Agent A.
    *   **Expected Result:** Agent A remembers its conversation, Agent B remembers its own. `user_agent_active_sessions` should have distinct entries for (`user_id`, `agent_A`) and (`user_id`, `agent_B`) with potentially different `active_session_id`s. `chat_message_history` reflects this.
*   **Test Case STM-E2E-005: `localStorage` Cleared**
    *   **Description:** Test behavior if user clears `localStorage` (simulates new browser/device without prior `localStorage` state).
    *   **Steps:**
        1.  Start a conversation (establishes `session_id` in DB via `user_agent_active_sessions`).
        2.  Manually clear `localStorage` for the site.
        3.  Refresh page / re-initialize chat.
    *   **Expected Result:** Client should fetch the active `session_id` from `user_agent_active_sessions` for that user/agent and resume the session. If no record in `user_agent_active_sessions` (e.g. first ever use, or if that table was also cleared), a brand new session is created. 