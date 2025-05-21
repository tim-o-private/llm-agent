# Comprehensive Test Plan: Agent Memory System v2 & Prompt Customization

**Date:** {datetime.now().isoformat()}
**Associated Designs:** 
*   `memory-bank/creative/agent_memory_system_v2_efficient_evolving.md` (Memory V2)
*   `memory-bank/creative/agent_execution_prompt_customization_design_v1.md` (AELPC)
**Implementation Plan:** `memory-bank/implementation_plans/agent_memory_system_v2_impl_plan.md`

## 1. Overview

This document outlines test cases for the integrated Agent Memory System v2 and the Agent Execution Logic & Prompt Customization (AELPC) features. The goal is to ensure:
*   The new memory system (client-buffering, batch archival, server-side short-term cache, LTM `notes`) functions as designed.
*   Agents can maintain short-term context and utilize long-term natural language memory (`notes`).
*   The `ManageLongTermMemoryTool` allows agents to curate their LTM `notes`.
*   The `CustomizableAgent` correctly assembles prompts from base instructions, LTM `notes`, and explicit prompt customizations.
*   The `PromptManagerService` and `update_self_instructions_tool` (or equivalent) correctly manage explicit agent prompt customizations.
*   Both systems work together seamlessly.

## 2. Test Levels & Scope

*   **Unit Tests:** Focus on individual functions, classes, and modules (e.g., agent tools, API endpoint logic, cache logic, client-side store actions).
*   **Integration Tests:** Test interactions between components (e.g., client calling archival API, agent using LTM tool to update Supabase, `CustomizableAgent` prompt assembly).
*   **End-to-End (E2E) Tests:** Simulate full user scenarios, from UI interaction to agent response, covering both memory persistence and prompt customization effects.
*   **Manual Testing:** Exploratory testing and verification of complex scenarios and data integrity.

## 3. Test Scenarios & Cases

### 3.1. Agent Memory System v2

#### 3.1.1. Client-Side Buffering (`useChatStore.ts`)
*   **Unit Tests (Zustand Store):**
    *   `UT.MEM.CS.1`: Test `addMessage` action correctly adds user messages.
    *   `UT.MEM.CS.2`: Test `addMessage` action correctly adds AI messages.
    *   `UT.MEM.CS.3`: Test message structure (id, text, sender, timestamp) is correct.
    *   `UT.MEM.CS.4`: Test `session_id` state management within or alongside the store.
*   **Unit Tests (Archival Trigger Logic - e.g., hooks or services using `useChatStore`):**
    *   `UT.MEM.CT.1`: Mock `onbeforeunload` / `navigator.sendBeacon`, verify archival API call is attempted with store messages.
    *   `UT.MEM.CT.2`: Mock chat panel close event, verify archival API call.
    *   `UT.MEM.CT.3`: Test periodic archival trigger (if implemented).
    *   `UT.MEM.CT.4`: Test correct batch of messages is prepared for the API call.

#### 3.1.2. Batch Archival API (`POST /api/chat/session/archive_messages`)
*   **Integration Tests (`chatServer` Endpoint):**
    *   `IT.MEM.BA.1`: Successful archival of a batch of messages to `recent_conversation_history`.
    *   `IT.MEM.BA.2`: Verify `session_id`, `user_id`, `message_batch`, `archived_at`, `start_timestamp`, `end_timestamp` are stored correctly.
    *   `IT.MEM.BA.3`: Test with empty `message_batch` (should ideally be a no-op or handled gracefully).
    *   `IT.MEM.BA.4`: Test request with missing `session_id` or auth failure (expect 4xx error).
    *   `IT.MEM.BA.5`: Test concurrent archival requests for different sessions.

#### 3.1.3. Server-Side Short-Term Cache (`server_session_cache` in `chatServer`)
*   **Unit Tests (Cache Logic):**
    *   `UT.MEM.SC.1`: Cache initialization for a new `session_id` (should be empty or default state).
    *   `UT.MEM.SC.2`: Correctly assemble short-term history from cache + new client messages.
    *   `UT.MEM.SC.3`: Cache update after agent response (includes user message, AI response, tool messages if applicable).
    *   `UT.MEM.SC.4`: Sliding window logic (if applicable, e.g., cache evicts oldest messages beyond N).
    *   `UT.MEM.SC.5`: Cache behavior if client sends full recent history vs. only new messages.

#### 3.1.4. Long-Term Memory (LTM - `agent_long_term_memory` & `ManageLongTermMemoryTool`)
*   **Unit Tests (`ManageLongTermMemoryTool`):**
    *   `UT.MEM.LTMTOOL.1`: `read` operation - empty notes for new user/agent.
    *   `UT.MEM.LTMTOOL.2`: `read` operation - retrieve existing notes.
    *   `UT.MEM.LTMTOOL.3`: `overwrite` operation - verify notes are replaced.
    *   `UT.MEM.LTMTOOL.4`: `append` operation - verify content is appended.
    *   `UT.MEM.LTMTOOL.5`: `prepend` operation - verify content is prepended.
    *   `UT.MEM.LTMTOOL.6`: `delete_all_notes` operation.
    *   `UT.MEM.LTMTOOL.7`: Section-based operations (e.g., `delete_section_by_header`, `replace_section_by_header`) with various inputs (Phase 4).
    *   `UT.MEM.LTMTOOL.8`: Error handling for invalid operations or Supabase errors (mocked).
*   **Integration Tests (Agent using LTM Tool):**
    *   `IT.MEM.LTM.1`: Agent successfully uses tool to `overwrite` LTM `notes`. Verify in Supabase.
    *   `IT.MEM.LTM.2`: Agent successfully uses tool to `append` to LTM `notes`. Verify.
    *   `IT.MEM.LTM.3`: Agent successfully uses tool to `read` its LTM `notes`.
    *   `IT.MEM.LTM.4`: New agent session for same user/agent correctly loads LTM `notes` into its prompt.

#### 3.1.5. Short-Term Context Flow (End-to-End within Memory System)
*   **Integration Tests:**
    *   `IT.MEM.STC.1`: Simulate multi-turn conversation. Verify `server_session_cache` is updated correctly each turn.
    *   `IT.MEM.STC.2`: Verify agent receives correctly assembled short-term history on each turn (mock agent input).
    *   `IT.MEM.STC.3`: If client sends full recent history strategy is adopted for `/api/chat`, test this path.

### 3.2. Agent Execution Logic & Prompt Customization (AELPC)

#### 3.2.1. `PromptManagerService` (or equivalent for explicit customizations)
*   **Unit/Integration Tests (Service Logic interacting with `user_agent_prompt_customizations` table):**
    *   `UT.AELPC.PMS.1`: Create a new prompt customization (e.g., `instruction_set`). Verify storage.
    *   `UT.AELPC.PMS.2`: Fetch active prompt customizations for a user/agent. Verify correct priority and active status honored.
    *   `UT.AELPC.PMS.3`: Update an existing prompt customization. Verify.
    *   `UT.AELPC.PMS.4`: Deactivate/activate a prompt customization.
    *   `UT.AELPC.PMS.5`: Handle cases where no customizations exist for a user/agent.

#### 3.2.2. `update_self_instructions_tool` (for explicit prompt customizations)
*   **Unit Tests (Tool Logic):**
    *   `UT.AELPC.TOOL.1`: Tool correctly parses input (e.g., `customization_type`, `content`).
    *   `UT.AELPC.TOOL.2`: Tool correctly calls `PromptManagerService` (or its backend) to save/update customization.
    *   `UT.AELPC.TOOL.3`: Error handling for invalid inputs.
*   **Integration Tests (Agent using Tool):**
    *   `IT.AELPC.TOOL.1`: Agent uses tool to add a new `instruction_set`. Verify in `user_agent_prompt_customizations` table.
    *   `IT.AELPC.TOOL.2`: Agent uses tool to modify an existing `instruction_set`. Verify.

#### 3.2.3. `CustomizableAgent` Prompt Assembly (Focus on explicit customizations)
*   **Unit/Integration Tests (Agent Logic):**
    *   `IT.AELPC.AGENT.1`: Agent loads and correctly incorporates active, prioritized explicit prompt customizations from `PromptManagerService` into its final prompt.
    *   `IT.AELPC.AGENT.2`: Agent uses base prompt if no customizations are found.
    *   `IT.AELPC.AGENT.3`: Test different `customization_type` effects if logic varies (e.g., how `instruction_set` is merged vs. other potential types).

### 3.3. Combined System E2E Tests (Memory V2 + AELPC)

*   **E2E.COMB.1: LTM Influence on Behavior**
    1.  User starts session 1. Conveys preference: "I prefer very short, direct answers."
    2.  Agent uses `ManageLongTermMemoryTool` to save "User prefers concise responses." to LTM `notes`.
    3.  User ends session 1 (client archives chat to `recent_conversation_history`).
    4.  User starts session 2.
    5.  `CustomizableAgent` loads LTM `notes`. Its prompt now includes this preference.
    6.  User asks a question.
    7.  **Expected:** Agent provides a concise answer, reflecting the LTM.
*   **E2E.COMB.2: Explicit Customization Influence on Behavior**
    1.  User starts session 1. Is frustrated with agent's verbosity.
    2.  Agent (or user via a UI, then agent via tool) uses `update_self_instructions_tool` to add an explicit instruction: `{"instruction_set": {"verbosity_level": "low"}}` to `user_agent_prompt_customizations`.
    3.  User starts session 2 (or continues current one after customization applies).
    4.  `CustomizableAgent` loads this explicit customization.
    5.  User asks a question.
    6.  **Expected:** Agent provides a less verbose answer, reflecting the explicit customization.
*   **E2E.COMB.3: LTM + Explicit Customization Interaction**
    1.  Setup: LTM `notes` = "User is a Star Trek fan.". Explicit customization = `{"instruction_set": {"personality_trait": "formal"}}`.
    2.  User starts session.
    3.  `CustomizableAgent` loads both LTM and explicit customization.
    4.  User asks: "Tell me about your capabilities."
    5.  **Expected:** Agent responds formally AND potentially includes a subtle Star Trek reference if contextually appropriate and its base prompt allows for such blending (tests how LTM and explicit instructions are synthesized).
*   **E2E.COMB.4: Short-Term Context with LTM & Customizations**
    1.  Setup: LTM `notes` = "User is planning a trip to Paris.". Explicit customization = `{"instruction_set": {"response_language": "French"}}` (if supported).
    2.  User (Turn 1): "What are some good museums there?"
    3.  Agent: (Responds in French about museums in Paris, using LTM for "Paris" and customization for language).
    4.  User (Turn 2): "And for dinner?"
    5.  **Expected:** Agent (responds in French about dinner options in Paris, using short-term context for "Paris" and "dinner", LTM for underlying Paris context, and customization for language).
*   **E2E.COMB.5: Data Integrity Across Sessions**
    1.  Engage in a conversation, update LTM, update explicit customizations.
    2.  Close session (trigger client archival).
    3.  Inspect `recent_conversation_history` for correct batch.
    4.  Inspect `agent_long_term_memory` for correct `notes`.
    5.  Inspect `user_agent_prompt_customizations` for correct explicit settings.
    6.  Start new session, verify all contexts are loaded and influence behavior as expected.

### 3.4. Manual Testing Checklist (Combined)
*   **LTM Curation:**
    *   Can the agent successfully add notes to LTM via its tool?
    *   Can the agent append to existing LTM notes?
    *   Can the agent overwrite LTM notes?
    *   Does the LTM persist across sessions for the same user/agent pair?
    *   Is LTM correctly isolated between different users?
    *   Is LTM correctly isolated between different agents for the same user (if applicable)?
*   **Explicit Prompt Customization:**
    *   Can agent (via tool) set an instruction set?
    *   Does this instruction set persist and affect behavior in subsequent sessions?
    *   How do multiple active customizations (if supported by `PromptManagerService` based on priority) interact?
*   **Conversational Flow & Context:**
    *   Engage in conversations requiring multi-turn context; verify agent doesn't lose track.
    *   Verify short-term context is not confused between different concurrent user sessions (if server supports this).
*   **Client Archival:**
    *   Open chat, send messages, close panel. Verify API call to archive is made and data appears in `recent_conversation_history`.
    *   Open chat, send messages, navigate away. Verify (using browser dev tools or server logs) archival attempt.
*   **Data Inspection (Supabase):**
    *   Regularly inspect `recent_conversation_history`, `agent_long_term_memory`, and `user_agent_prompt_customizations` tables for data correctness, integrity, and RLS enforcement (by attempting to access cross-user data if possible with test accounts).
*   **Error States:**
    *   Simulate API failures for archival – how does client react?
    *   Simulate DB errors for LTM/customization updates – how does agent/tool react?

## 4. Test Environment & Tools

*   **Client:** Web browser with developer tools.
*   **Server:** Local `chatServer` instance.
*   **Database:** Local or dev Supabase instance.
*   **Testing Frameworks:** Pytest for Python backend/tools, Jest/Vitest for `useChatStore` and client-side logic if applicable.
*   **API Testing Tool:** Postman, Insomnia, or `curl` for direct API endpoint testing.
*   **Mocking:** Libraries for mocking API calls, DB interactions, and browser events in unit tests.

## 5. Pruning and Data Management Tests (Phase 4 of Impl Plan)

*   **TEST.PRUNE.1:** Verify pruning strategy for `recent_conversation_history` (e.g., records older than X days are deleted/archived).
*   **TEST.LTM.MANAGE.1:** Test agent's ability to summarize or condense its LTM `notes` if it becomes too verbose (requires sophisticated agent logic or a dedicated summarization tool for LTM).

This comprehensive test plan should provide good coverage for the new memory system and its interaction with the prompt customization mechanisms. It will need to be executed iteratively as each phase of the implementation plan is completed. 