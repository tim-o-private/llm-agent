import datetime

# Active Context & Current Focus

This document outlines the current high-priority task, relevant files, and key considerations for the AI agent.

**Last Updated:** 2025-01-28

## Current High-Priority Task:

**1. TASK-AGENT-001: Implement Email Digest Agent with Gmail Tools Integration**
*   **Status:** Phase 1 Complete - Phase 2 In Progress (Database-driven Gmail tools)
*   **Complexity:** Level 3 (Intermediate Feature - Agent with secure OAuth integration and scheduled functionality)
*   **Objective:** Create Email Digest Agent using LangChain Gmail toolkit with Supabase Vault token storage and scheduled daily digest functionality
*   **Key Architecture Components:**
    - **✅ OAuth Security**: Supabase Vault for encrypted token storage (enterprise-grade security) - **COMPLETE**
    - **🔄 Gmail Integration**: LangChain Gmail toolkit for reliable API access - **IN PROGRESS**
    - **Agent Framework**: Database-driven tool configuration using existing CRUDTool patterns
    - **Scheduling**: Daily digest generation at 7:30 AM per user timezone
    - **Control Flow**: Scheduler → Email Digest Agent → Gmail Tools → LLM Analysis → Assistant Integration
*   **Implementation Timeline:** 4 weeks (32 hours total effort)
*   **Current Phase:** Phase 2 - Database-Driven Gmail Tools (Week 2: Feb 4 - Feb 10)
*   **Priority:** High - Core Clarity v2 functionality for daily email digest

**✅ Phase 1 Completed (Week 1: Jan 28 - Feb 3):**
- [X] Create database migration for vault integration (`20250128000001_vault_oauth_tokens.sql`)
- [X] Implement `VaultTokenService` for secure OAuth token management
- [X] Create `user_api_tokens` view with RLS policies
- [X] Update `external_api_connections` table to reference vault secrets
- [X] Comprehensive unit tests for vault token operations (25 test cases)
- [X] Migration script for existing tokens (if any)

**🔄 Phase 2 Current Focus (Week 2: Feb 4 - Feb 10):**
- [ ] Insert agent configuration in `agent_configurations` table
- [ ] Configure Gmail tools in `agent_tools` table with `runtime_args_schema`
- [ ] Implement `GmailTool` class using LangChain Gmail toolkit
- [ ] Add Gmail tools to `TOOL_REGISTRY` in `agent_loader_db.py`
- [ ] Support operations: search, get_message, generate_digest
- [ ] Integration with vault token service for credentials

**Technical Implementation Details:**
- **✅ Security**: Supabase Vault uses libsodium AEAD with key separation - **COMPLETE**
- **✅ Integration**: Uses existing `CustomizableAgentExecutor` and `load_agent_executor_db` - **COMPLETE**
- **🔄 Configuration**: Tools configured via `agent_tools` table with `runtime_args_schema` - **IN PROGRESS**
- **LLM**: Leverages existing LLM interface for email summarization
- **Authentication**: Integrates with existing Supabase auth system

**✅ Files Created in Phase 1:**
- `supabase/migrations/20250128000001_vault_oauth_tokens.sql` - Vault integration migration
- `chatServer/services/vault_token_service.py` - Secure token management service
- `tests/chatServer/services/test_vault_token_service.py` - Comprehensive vault service tests (25 test cases)

**Files to Create in Phase 2:**
- `chatServer/tools/gmail_tools.py` - LangChain Gmail toolkit integration
- Database records in `agent_configurations` and `agent_tools` tables
- Updates to `src/core/agents/agent_loader_db.py` - Add Gmail tools to registry

## Recently Completed:

**✅ TASK-UI-001: Add Notes Pane to Stacked Card System (2025-01-27) - FULLY COMPLETE**
- Successfully integrated NotesPane component into TodayViewMockup
- Added 'notes' as fifth pane type with auto-save and keyboard shortcuts
- Maintained consistency with existing UI patterns
- **COMPLETE DATA PERSISTENCE**: Created notes table DDL, useNotesStore, full CRUD operations
- **ENHANCED UI**: Notes list sidebar, title/content editing, delete functionality
- **SUPABASE INTEGRATION**: RLS policies, optimistic updates, following useChatStore patterns
- **COMPREHENSIVE UNIT TESTS**: 19/19 tests passing (8 store tests + 11 component tests)
- **TYPESCRIPT QUALITY**: Proper typing with `vi.mocked()`, no `any` types, full type safety
- **PRODUCTION READY**: All quality gates met, ready for production use

**✅ TASK-API-001: External API Integration Layer (2025-01-28) - FULLY COMPLETE**
- Created database migration for OAuth token storage (`external_api_connections` table)
- Implemented `BaseAPIService` with rate limiting, caching, and OAuth token management
- Created `GmailService` with Gmail API integration and email parsing
- Built `EmailDigestService` with AI-powered email summarization using existing LLM infrastructure
- Added FastAPI router with full CRUD operations for API connections
- Implemented comprehensive unit tests with mocked API responses
- **FUTURE-PROOFED**: Architecture ready for Google Calendar integration
- **IN-MEMORY SOLUTIONS**: Rate limiting and caching as requested
- **USER CREDENTIALS**: OAuth tokens stored in Supabase with RLS policies

**2. CLARITY-V2: Clarity v2 Executive Assistant Implementation**
*   **Status:** Planning Complete - Phase 1 Foundation In Progress
*   **Complexity:** Level 4 (Complex System - Full executive assistant with AI agents, memory system, and multi-platform integrations)
*   **Objective:** Implement Clarity v2 as a comprehensive executive-function assistant that filters inbound noise, multiplies outbound output, and eliminates manual data entry through proactive AI agents.
*   **Key Architecture Components:**
    *   **Memory System:** Multi-layered memory (working, short-term, long-term) with vector search
    *   **Agent Orchestrator:** Handles agent lifecycle, job queuing, status reporting
    *   **Prompt Engine:** Builds structured prompt chains and tool calls
    *   **UI Bridge:** Real-time state synchronization between backend and frontend
    *   **AI Agents:** Specialized agents for digest, reply drafting, scheduling
    *   **User Interface:** Chat window, planner view, digest feed, brain dump interface
*   **Technology Stack:**
    *   Frontend: React 18+, TailwindCSS, Radix UI Primitives, Zustand, React Query, Vite
    *   Backend: FastAPI (chatServer/), Supabase (Auth, DB, Storage)
    *   AI/LLM: LangChain, Google Gemini Pro, OpenAI API
    *   Integrations: Google Calendar API, Gmail API, Slack API
    *   Database: PostgreSQL (Supabase), Vector DB (Pinecone/Weaviate)
*   **Implementation Phases:**
    *   Phase 1: Foundation – Ingest + Tasking (Target: 2025-02-15) - **IN PROGRESS**
    *   Phase 2: Output Automation – Agents & Digest (Target: 2025-03-15)
    *   Phase 3: Assistant as Multiplier (Target: 2025-04-30)
*   **Current Milestone:** Technology Validation Complete - Implementing Gmail Tools Integration
*   **Relevant Files:**
    *   `memory-bank/Clarity v2: PRD.md` (Product Requirements)
    *   `memory-bank/tasks.md` (Detailed implementation plan)
*   **Task Tracking:** `memory-bank/tasks.md` (CLARITY-V2 - Phase 1 In Progress)

## Key Focus Areas for Implementation:

1.  **Supabase Vault Token Storage (CURRENT FOCUS - Phase 1):**
    *   Create database migration for vault integration with OAuth tokens
    *   Implement VaultTokenService for secure token management
    *   Create user_api_tokens view with proper RLS policies
    *   Update external_api_connections table to reference vault secrets
    *   Comprehensive unit testing for all vault operations

2.  **Upcoming Phase 2 (Week 2: Feb 4 - Feb 10):**
    *   Database-driven Gmail tools using LangChain toolkit
    *   Agent configuration in agent_configurations and agent_tools tables
    *   GmailTool implementation with search, get_message, generate_digest operations
    *   Integration with vault token service for secure credential access

3.  **Quality Assurance Focus:**
    *   Maintain TypeScript quality standards (no `any` types)
    *   100% test coverage for all new components
    *   Security audit for vault token storage implementation
    *   Follow established patterns from existing codebase
    *   Proper error handling and logging

**Mode Recommendation:** IMPLEMENT (For TASK-AGENT-001 Phase 1 - Supabase Vault Token Storage)

**General Project Goal:** Complete Clarity v2 executive assistant implementation with comprehensive AI agent orchestration, memory system, and multi-platform integrations.

**Current Implementation Focus:**
*   **Week 1 (Jan 28 - Feb 3)**: Supabase Vault token storage foundation
*   **Week 2 (Feb 4 - Feb 10)**: Database-driven Gmail tools with LangChain toolkit
*   **Week 3 (Feb 11 - Feb 17)**: Email Digest Agent implementation and scheduling
*   **Week 4 (Feb 18 - Feb 24)**: API integration, testing, and assistant integration

**Key Technical Decisions Made:**
*   ✅ **OAuth Security**: Supabase Vault for enterprise-grade token encryption
*   ✅ **Gmail Integration**: LangChain Gmail toolkit for reliability and maintenance
*   ✅ **Agent Framework**: Database-driven configuration using existing CRUDTool patterns
*   ✅ **Scheduling**: Daily digest at 7:30 AM per user timezone as per PRD
*   ✅ **Control Flow**: Scheduler → Agent → Tools → LLM → Assistant integration

**Pending Decisions/Questions:**
*   Gmail API OAuth setup and client credentials configuration
*   User onboarding flow for Gmail connection authorization
*   Digest presentation format in the assistant UI
*   Error handling strategy for failed Gmail API calls

**Previous Focus (Completed/Superseded in this context):**
*   **Task Editing UI/Logic Refactor (COMPLETED):** Fixed critical infinite form reset loop in `useEditableEntity.ts`
*   CLI/Core Backend MVP Testing (Task 3.1 from `memory-bank/tasks.md`):
    *   Core agent memory persistence via Supabase (original V1 approach) was working.
    *   RuntimeError during tool execution was resolved.
    *   Prompt customization persistence verified.
*   Agent Memory System v1 Design & Implementation (Superseded by V2)
*   Linter error fixes in `useTaskHooks.ts` and `types.ts`.
*   Refactor `useChatApiHooks.ts` for direct Supabase writes.
*   Update `useChatStore.ts` to use direct archival logic.
*   UI integration of `agentId` for `ChatPanel` and `useChatStore` initialization.

**Upcoming Focus (Post Email Digest Agent):**
*   TASK-AGENT-002: Reply Drafter Agent implementation
*   TASK-VOICE-001: Voice Input for Notes
*   TASK-SYNC-001: Real-time State Synchronization
*   TASK-MOBILE-001: Mobile Responsive Stacked Cards

**Key Files Recently Modified/Reviewed:**
*   `memory-bank/tasks.md` (Updated with complete Gmail tools integration plan)
*   `memory-bank/activeContext.md` (Updated with current focus)
*   `chatServer/services/gmail_service.py` (Existing service layer foundation)
*   `chatServer/models/external_api.py` (OAuth token models)
*   `supabase/migrations/20250128000000_create_external_api_connections.sql` (Foundation migration)

**Key Files to Create (Phase 1):**
*   `supabase/migrations/20250128000001_vault_oauth_tokens.sql` (Vault integration migration)
*   `chatServer/services/vault_token_service.py` (Secure token management)
*   `tests/chatServer/services/test_vault_token_service.py` (Comprehensive testing)

**Open Questions/Considerations:**
*   Should we implement Gmail OAuth flow in the frontend or backend?
*   What's the optimal caching strategy for Gmail API responses?
*   How should we handle Gmail API rate limits in the scheduled digest?
*   What level of email content should be stored vs. fetched on-demand?

Last updated: 2025-01-28

**Mode Recommendation:** IMPLEMENT (For TASK-AGENT-001 Phase 1 - Supabase Vault Token Storage)

**General Project Goal:** Complete Clarity v2 executive assistant implementation with comprehensive AI agent orchestration, memory system, and multi-platform integrations.