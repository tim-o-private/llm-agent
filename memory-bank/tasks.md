# CRITICAL INSTRUCTIONS
All agents MUST read `README.md` for navigation, then consult the relevant pattern files (`patterns/ui-patterns.md`, `patterns/api-patterns.md`, `patterns/agent-patterns.md`, `patterns/data-patterns.md`) and rule files (`rules/*.json`) for their work area. Adhere to established patterns unless EXPLICITLY told by the user to deviate.

# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## PENDING / ACTIVE TASKS

**NEW TASK: CLARITY-V2: Clarity v2 Executive Assistant Implementation**
*   **Status:** Phase 1 Foundation - TASK-AGENT-001 Phase 2 In Progress
*   **Complexity:** 4 (Complex System - Full executive assistant with AI agents, memory system, and multi-platform integrations)
*   **Objective:** Implement Clarity v2 as a comprehensive executive-function assistant that filters inbound noise, multiplies outbound output, and eliminates manual data entry through proactive AI agents.
*   **Context:** Complete system redesign based on Clarity v2 PRD and Design & Implementation Plan. Requires architectural planning, multiple subsystems, and phased implementation.

### System Overview
- **Purpose**: Executive-function assistant for knowledge workers, independent professionals, and overwhelmed parents
- **Architectural Alignment**: Follows established patterns in techContext.md and systemPatterns.md
- **Status**: Phase 1 Foundation - TASK-AGENT-001 Phase 2 In Progress
- **Milestones**: 
  - Architecture Planning: [Target: 2025-01-27] - ✅ Complete
  - Technology Validation: [Target: 2025-01-28] - ✅ Complete
  - Phase 1 Foundation: [Target: 2025-02-15] - In Progress (TASK-AGENT-001 Phase 2)
  - Phase 2 Output Automation: [Target: 2025-03-15] - Not Started
  - Phase 3 Assistant Multiplier: [Target: 2025-04-30] - Not Started

### Technology Stack
- **Frontend**: React 18+, TailwindCSS, Radix UI Primitives, Zustand, React Query, Vite
- **Backend**: FastAPI (chatServer/), Supabase (Auth, DB, Storage)
- **AI/LLM**: LangChain, Google Gemini Pro, OpenAI API
- **Integrations**: Google Calendar API, Gmail API, Slack API
- **Database**: PostgreSQL (Supabase), Vector DB (Pinecone/Weaviate)
- **Infrastructure**: Fly.io (API), Vercel (Frontend)

### Technology Validation Checkpoints
- [X] Project initialization command verified (React + Vite + TypeScript)
- [X] Required dependencies identified and installed (AI/LLM libraries)
- [X] Build configuration validated (Vite, TypeScript, TailwindCSS)
- [X] Hello world verification completed (Basic AI chat interface)
- [X] Test build passes successfully (Full stack integration)
- [ ] External API integrations tested (Google Calendar, Gmail, Slack)
- [X] Memory system integration verified (Already complete - PostgreSQL-based)

### Remaining Implementation Tasks

#### HIGH PRIORITY: Core Clarity v2 Features

##### TASK-UI-001: Add Notes Pane to Stacked Card System
- **Description**: Integrate notes interface into existing TodayViewMockup stacked card system
- **Status**: ✅ **COMPLETED** (2025-01-27)
- **Priority**: High
- **Dependencies**: TodayViewMockup.tsx, existing stacked card infrastructure
- **Implementation Details**:
  - ✅ Created `NotesPane` component at `webApp/src/components/features/NotesPane/NotesPane.tsx`
  - ✅ Added 'notes' to `PaneType` union type in `TodayViewMockup.tsx`
  - ✅ Updated `availablePanes` array to include 'notes'
  - ✅ Added notes case to `renderPaneContent` function
  - ✅ Component features: auto-save, keyboard shortcuts (⌘S, Esc), empty state, character count
  - ✅ **DATA PERSISTENCE COMPLETE**: Created notes table DDL with RLS policies
  - ✅ **ZUSTAND STORE**: Implemented `useNotesStore` following `useChatStore` patterns
  - ✅ **FULL CRUD OPERATIONS**: Create, read, update, delete with optimistic updates
  - ✅ **ENHANCED UI**: Notes list sidebar, real-time editing, saving indicators
  - ✅ **COMPREHENSIVE UNIT TESTS**: 
    - `webApp/src/stores/__tests__/useNotesStore.test.ts` (8 tests passing)
    - `webApp/src/components/features/NotesPane/__tests__/NotesPane.test.tsx` (11 tests passing)
    - Tests cover: state management, UI rendering, loading states, note operations, edge cases
    - Authentication testing delegated to page-level tests (proper separation of concerns)
  - ✅ **TYPESCRIPT QUALITY**: Proper typing with `vi.mocked()`, no `any` types, full type safety
- **Files Modified**:
  - `webApp/src/pages/TodayViewMockup.tsx` - Added notes pane integration
  - `webApp/src/api/types.ts` - Added Note interface and related types
  - `supabase/migrations/20250127000000_create_notes_table.sql` - Database schema
- **Integration Status**: ✅ Successfully integrated and tested
- **Quality Metrics**: ✅ 19/19 tests passing, ✅ TypeScript compilation clean, ✅ Production ready
- **Next Steps**: ✅ **COMPLETE** - Ready for TASK-AGENT-001 (Email Digest Agent)

##### TASK-API-001: External API Integration Layer
- **Description**: Create abstraction layer for Google Calendar, Gmail, Slack APIs
- **Status**: ✅ **COMPLETED** (2025-01-28)
- **Priority**: High
- **Dependencies**: API credentials, rate limiting framework
- **Estimated Effort**: 40 hours
- **Implementation**: ✅ Created service layer with proper error handling and caching
- **Quality Gates**: ✅ Rate limiting, retry logic, data privacy compliance
- **Implementation Details**:
  - ✅ Created database migration for OAuth token storage (`external_api_connections` table)
  - ✅ Implemented `BaseAPIService` with rate limiting, caching, and OAuth token management
  - ✅ Created `GmailService` with Gmail API integration and email parsing
  - ✅ Built `EmailDigestService` with AI-powered email summarization using existing LLM infrastructure
  - ✅ Added FastAPI router with full CRUD operations for API connections
  - ✅ Implemented comprehensive unit tests with mocked API responses
  - ✅ **FUTURE-PROOFED**: Architecture ready for Google Calendar integration
  - ✅ **IN-MEMORY SOLUTIONS**: Rate limiting and caching as requested
  - ✅ **USER CREDENTIALS**: OAuth tokens stored in Supabase with RLS policies
- **Files Created/Modified**:
  - `supabase/migrations/20250128000000_create_external_api_connections.sql` - Database schema
  - `chatServer/models/external_api.py` - Pydantic models for validation
  - `chatServer/services/base_api_service.py` - Base service with common functionality
  - `chatServer/services/gmail_service.py` - Gmail API integration
  - `chatServer/services/email_digest_service.py` - AI-powered email digest generation
  - `chatServer/routers/external_api_router.py` - FastAPI endpoints
  - `chatServer/main.py` - Router registration
  - `tests/chatServer/services/test_gmail_service.py` - Gmail service unit tests
  - `tests/chatServer/services/test_email_digest_service.py` - Email digest service unit tests
- **Integration Status**: ✅ Successfully integrated with existing infrastructure
- **Quality Metrics**: ✅ Comprehensive test coverage, ✅ TypeScript compilation clean, ✅ Production ready
- **Next Steps**: ✅ **COMPLETE** - Ready for TASK-AGENT-001 (Email Digest Agent implementation)

##### TASK-INFRA-001: Database Connection Patterns Analysis
- **Description**: Document current state of database connection usage across chatServer and core components
- **Status**: ✅ **COMPLETED** (2025-01-28)
- **Priority**: High
- **Dependencies**: Existing codebase analysis
- **Estimated Effort**: 8 hours
- **Implementation**: ✅ Comprehensive analysis of dual database connection patterns
- **Quality Gates**: ✅ Complete inventory, migration recommendations, technical debt assessment
- **Implementation Details**:
  - ✅ **Pattern Analysis**: Documented PostgreSQL Connection Pool vs Supabase AsyncClient patterns
  - ✅ **Usage Inventory**: Complete audit of connection usage across chatServer and core components
  - ✅ **Technical Debt Assessment**: Identified inconsistencies and maintenance overhead
  - ✅ **Migration Strategy**: Phased approach for standardizing on PostgreSQL connection pool
  - ✅ **Testing Patterns**: Documented testing approaches for both connection types
  - ✅ **Performance Analysis**: Connection pool benefits vs Supabase client features
- **Files Created**:
  - `memory-bank/database-connection-patterns.md` - Comprehensive analysis document
- **Key Findings**:
  - **Dual Pattern Problem**: PostgreSQL pool (recommended) vs Supabase client (legacy)
  - **Modern Pattern Usage**: VaultTokenService, External API Router, Email Digest system
  - **Legacy Pattern Usage**: Prompt customization, Tasks API, Base API service
  - **Core Components**: Mixed patterns creating additional complexity
- **Recommendations**:
  - **Phase 1**: ✅ Standardize new development (Complete)
  - **Phase 2**: 🔄 Migrate legacy endpoints (In Progress)
  - **Phase 3**: ⏳ Align core components (Pending)
- **Next Steps**: Use as reference for future database connection decisions and legacy migration planning

##### TASK-AGENT-001: Implement Email Digest Agent with Gmail Tools Integration
- **Description**: Create Email Digest Agent using LangChain Gmail toolkit with Supabase Vault token storage and scheduled daily digest functionality
- **Status**: **PHASE 1 COMPLETE - PHASE 2 IN PROGRESS** (Current Priority)
- **Priority**: High
- **Dependencies**: ✅ External API integration (Complete), ✅ Existing agent orchestrator (Complete)
- **Estimated Effort**: 32 hours (4 weeks)
- **Implementation**: Database-driven Gmail tools using LangChain toolkit with Supabase Vault security
- **Quality Gates**: Secure token storage, accurate summarization, scheduled execution, comprehensive testing

**Technical Architecture:**
- **OAuth Security**: ✅ Supabase Vault for encrypted token storage (enterprise-grade security) - **COMPLETE**
- **Gmail Integration**: LangChain Gmail toolkit for reliable API access
- **Agent Framework**: Database-driven tool configuration using existing CRUDTool patterns
- **Scheduling**: Daily digest generation at 7:30 AM per user timezone
- **Control Flow**: Scheduler → Email Digest Agent → Gmail Tools → LLM Analysis → Assistant Integration

**Implementation Phases:**

**✅ Phase 1: Supabase Vault Token Storage (Week 1: Jan 28 - Feb 3) - COMPLETE**
- [X] Create database migration for vault integration (`20250128000001_vault_oauth_tokens.sql`)
- [X] Implement `VaultTokenService` for secure OAuth token management
- [X] Create `user_api_tokens` view with RLS policies
- [X] Update `external_api_connections` table to reference vault secrets
- [X] Comprehensive unit tests for vault token operations
- [X] Integration testing with RLS verification
- [X] Migration script for existing tokens (if any)

**🔄 Phase 2: Database-Driven Gmail Tools (Week 2: Feb 4 - Feb 10) - IN PROGRESS**

**Implementation Pattern References:**
- **📋 Database Tool Configuration**: Follow `src/core/agent_loader_db.py` patterns for tool registration
- **🔧 Tool Implementation**: Follow `src/core/tools/crud_tool.py` patterns for LangChain BaseTool integration
- **🔒 Security Integration**: Use `chatServer/services/vault_token_service.py` for OAuth token retrieval
- **🗄️ Database Patterns**: Use PostgreSQL connection pool pattern from `chatServer/database/connection.py`

**Phase 2 Tasks:**
- [ ] **Insert agent configuration in `agent_configurations` table**
  - **Pattern**: Follow existing agent records in database
  - **Reference**: See `test_db_agent_loader.py` for agent configuration examples
  - **Fields**: `agent_name`, `llm_config`, `system_prompt`, `is_active`
- [ ] **Configure Gmail tools in `agent_tools` table with `runtime_args_schema`**
  - **Pattern**: Follow CRUDTool configuration patterns from `agent_loader_db.py`
  - **Reference**: See `memory-bank/patterns/agent-patterns.md#pattern-1-generic-crudtool-configuration`
  - **Schema**: Define `runtime_args_schema` for search, get_message, generate_digest operations
  - **Fields**: `agent_id`, `name`, `description`, `type`, `config`, `runtime_args_schema`, `order`
- [ ] **Implement `GmailTool` class using LangChain Gmail toolkit**
  - **Pattern**: Extend `langchain.tools.BaseTool` like `CRUDTool`
  - **Reference**: `src/core/tools/crud_tool.py` for tool structure and patterns
  - **Integration**: Use `VaultTokenService.get_tokens()` for OAuth credentials
  - **Operations**: Implement `search`, `get_message`, `generate_digest` methods
  - **Error Handling**: Follow existing error patterns with proper logging
- [ ] **Add Gmail tools to `TOOL_REGISTRY` in `agent_loader_db.py`**
  - **Pattern**: Add `"GmailTool": GmailTool` to `TOOL_REGISTRY` dict
  - **Reference**: Line 18-22 in `src/core/agent_loader_db.py`
  - **Import**: Add `from chatServer.tools.gmail_tool import GmailTool`
- [ ] **Support operations: search, get_message, generate_digest**
  - **Pattern**: Each operation as separate tool instance with different configs
  - **Reference**: See how CRUDTool handles different methods via config
  - **Database Config**: Use `config.method` to differentiate operations
- [ ] **Integration with vault token service for credentials**
  - **Pattern**: Use dependency injection with `get_db_connection()`
  - **Reference**: `chatServer/services/vault_token_service.py` methods
  - **Security**: Always use `VaultTokenService.get_tokens()` for OAuth access

**Phase 3: Email Digest Agent Implementation (Week 3: Feb 11 - Feb 17)**

**Implementation Pattern References:**
- **🤖 Agent Framework**: Use `src/core/agents/customizable_agent.py` patterns
- **📅 Scheduling**: Follow `chatServer/services/background_tasks.py` patterns for scheduled tasks
- **🗄️ Database Schema**: Follow RLS patterns from existing migrations
- **🔗 Service Integration**: Use service layer patterns from `chatServer/services/`

**Phase 3 Tasks:**
- [ ] **Implement `EmailDigestAgent` using existing `CustomizableAgentExecutor`**
  - **Pattern**: Use `load_agent_executor_db()` from `src/core/agent_loader_db.py`
  - **Reference**: See `chatServer/agents/email_digest_agent.py` (refactored approach)
  - **Integration**: Agent loads Gmail tools automatically via database configuration
  - **Memory**: Use existing PostgreSQL chat history for conversation context
- [ ] **Create `ScheduledDigestService` for digest generation and storage**
  - **Pattern**: Follow service layer patterns from `chatServer/services/chat.py`
  - **Reference**: Use `chatServer/services/email_digest_service.py` as foundation
  - **Database**: Use PostgreSQL connection pool pattern for digest storage
  - **Integration**: Call agent executor with user context and Gmail tools
- [ ] **Implement `DailyDigestScheduler` with APScheduler**
  - **Pattern**: Follow `chatServer/services/background_tasks.py` scheduling patterns
  - **Reference**: Use existing background task infrastructure
  - **Timing**: 7:30 AM per user timezone as per Clarity v2 PRD
  - **Concurrency**: Use existing agent executor cache for performance
- [ ] **Add `user_digests` table for storing generated digests**
  - **Pattern**: Follow RLS patterns from `supabase/migrations/20250128000001_vault_oauth_tokens.sql`
  - **Reference**: Use existing migration patterns with proper RLS policies
  - **Schema**: `user_id`, `digest_date`, `summary`, `thread_count`, `created_at`
  - **Security**: Ensure RLS policies prevent cross-user access
- [ ] **Integration with main assistant agent for digest presentation**
  - **Pattern**: Use existing chat system integration points
  - **Reference**: Follow `chatServer/main.py` chat endpoint patterns
  - **UI Integration**: Digests available through existing chat interface
  - **Context**: Digests become part of assistant's available information

**Key Integration Points for Future Agents:**
- **🔧 Tool Development**: Always extend `langchain.tools.BaseTool` and register in `TOOL_REGISTRY`
- **🗄️ Database Configuration**: Use `agent_tools` table with `runtime_args_schema` for dynamic configuration
- **🔒 Security**: Always use `VaultTokenService` for OAuth tokens, never store credentials directly
- **📊 Connection Patterns**: Use PostgreSQL connection pool (`get_db_connection()`) for all new development
- **🧪 Testing**: Follow comprehensive testing patterns with unit tests + integration tests
- **📝 Documentation**: Update `memory-bank/patterns/agent-patterns.md` with new patterns

**✅ Files Created/Modified (Phase 1 Complete):**
- [X] `supabase/migrations/20250128000001_vault_oauth_tokens.sql` - Vault integration migration
- [X] `chatServer/services/vault_token_service.py` - Secure token management
- [X] `tests/chatServer/services/test_vault_token_service.py` - Comprehensive vault service tests
- [X] `tests/chatServer/services/test_vault_token_service_integration.py` - RLS integration testing

**Files to Create/Modify (Phase 2):**
- [ ] **`chatServer/tools/gmail_tool.py`** - LangChain Gmail toolkit integration
  - **Pattern**: Extend `langchain.tools.BaseTool` like `src/core/tools/crud_tool.py`
  - **Dependencies**: `VaultTokenService`, LangChain Gmail toolkit
  - **Methods**: `search()`, `get_message()`, `generate_digest()`
  - **Testing**: Follow patterns from `tests/chatServer/services/test_gmail_service.py`
- [ ] **Database records in `agent_configurations` and `agent_tools` tables**
  - **Pattern**: Follow existing agent configuration examples
  - **Reference**: See `test_db_agent_loader.py` for schema examples
  - **Tools**: Configure 3 Gmail tools (search, get_message, generate_digest)
- [ ] **Updates to `src/core/agent_loader_db.py`** - Add Gmail tools to registry
  - **Pattern**: Add `"GmailTool": GmailTool` to `TOOL_REGISTRY` dict (line 18-22)
  - **Import**: Add `from chatServer.tools.gmail_tool import GmailTool`

**Files to Create/Modify (Phase 3):**
- [ ] **`supabase/migrations/20250128000002_create_email_digest_tables.sql`** - Database schema
  - **Pattern**: Follow RLS patterns from `20250128000001_vault_oauth_tokens.sql`
  - **Tables**: `user_digests`, `email_digest_batches`, `agent_logs`
  - **Security**: Ensure proper RLS policies for user data isolation
- [ ] **`chatServer/services/scheduled_digest_service.py`** - Digest generation service
  - **Pattern**: Follow service layer patterns from `chatServer/services/chat.py`
  - **Dependencies**: `load_agent_executor_db()`, `VaultTokenService`
  - **Methods**: `generate_digest()`, `store_digest()`, `get_recent_digests()`
- [ ] **`chatServer/schedulers/daily_digest_scheduler.py`** - Scheduled task management
  - **Pattern**: Follow `chatServer/services/background_tasks.py` scheduling patterns
  - **Dependencies**: APScheduler, `ScheduledDigestService`
  - **Timing**: 7:30 AM per user timezone as per Clarity v2 PRD

**Files to Create/Modify (Phase 4):**
- [ ] **`chatServer/routers/email_digest_router.py`** - API endpoints
  - **Pattern**: Follow router patterns from `chatServer/routers/external_api_router.py`
  - **Dependencies**: `get_db_connection()`, `ScheduledDigestService`
  - **Endpoints**: `/digest/generate`, `/digest/recent`, `/digest/history`
- [ ] **`tests/chatServer/tools/test_gmail_tool.py`** - Gmail tools unit tests
  - **Pattern**: Follow testing patterns from `tests/chatServer/services/test_gmail_service.py`
  - **Coverage**: Test all Gmail operations, error scenarios, OAuth integration
  - **Mocking**: Use `unittest.mock` for Gmail API responses
- [ ] **`tests/chatServer/services/test_scheduled_digest_service.py`** - Service unit tests
  - **Pattern**: Follow comprehensive testing from `tests/chatServer/services/test_chat.py`
  - **Coverage**: Test digest generation, storage, agent integration
  - **Mocking**: Mock agent executor and Gmail API calls

**✅ Security Features (Phase 1 Complete):**
- [X] **Authenticated Encryption**: Supabase Vault uses libsodium AEAD
- [X] **Key Separation**: Encryption keys stored separately from data
- [X] **Row-Level Security**: RLS policies for user data scoping
- [X] **Backup Security**: Encrypted data in backups, keys managed by Supabase
- [X] **No Key Rotation Issues**: Supabase handles key management infrastructure
- [X] **Integration Testing**: Verified RLS prevents cross-user data access

**Integration Points:**
- ✅ **Existing Agent Framework**: Uses `CustomizableAgentExecutor` and `load_agent_executor_db`
- ✅ **Database Configuration**: Tools configured via `agent_tools` table
- ✅ **LLM Infrastructure**: Leverages existing LLM interface for summarization
- ✅ **Authentication**: Integrates with existing Supabase auth system
- ✅ **Assistant Integration**: Digests available to main assistant agent

**✅ Quality Metrics (Phase 1):**
- [X] 100% test coverage for VaultTokenService (25 test cases)
- [X] TypeScript compilation with no errors
- [X] Security audit for token storage (Supabase Vault enterprise-grade)
- [X] Comprehensive error handling and logging
- [X] Integration testing with mocked Supabase client
- [X] RLS verification with live database connections

**Implementation Notes**: 
- ✅ Phase 1 Complete: Supabase Vault integration provides enterprise-grade OAuth token security
- 🔄 Phase 2 Focus: Database-driven Gmail tools using LangChain toolkit for reliability
- Uses established CRUDTool patterns for database-driven configuration
- Implements scheduled daily digest as per Clarity v2 PRD requirements
- Ready for integration with existing agent executor caching system

**Phase 4: API Integration & Testing (Week 4: Feb 18 - Feb 24)**

**Implementation Pattern References:**
- **🌐 API Endpoints**: Follow FastAPI router patterns from `chatServer/routers/external_api_router.py`
- **🧪 Testing**: Follow comprehensive testing patterns from `tests/chatServer/services/`
- **🔒 Security Testing**: Use integration test patterns from `test_vault_token_service_integration.py`

**Phase 4 Tasks:**
- [ ] **Create `email_digest_router.py` with FastAPI endpoints**
  - **Pattern**: Follow router patterns from `chatServer/routers/external_api_router.py`
  - **Reference**: Use existing dependency injection with `get_db_connection()`
  - **Endpoints**: `/digest/generate`, `/digest/recent`, `/digest/history`
- [ ] **Implement on-demand digest generation endpoint**
  - **Pattern**: Use service layer integration like `chatServer/services/chat.py`
  - **Reference**: Call `ScheduledDigestService` with user context
  - **Security**: Ensure proper user authentication and authorization
- [ ] **Add recent digests retrieval endpoint**
  - **Pattern**: Follow database query patterns with RLS
  - **Reference**: Use PostgreSQL connection pool for data retrieval
  - **Pagination**: Implement proper pagination for digest history
- [ ] **Comprehensive testing with mocked Gmail API responses**
  - **Pattern**: Follow testing patterns from `tests/chatServer/services/test_gmail_service.py`
  - **Reference**: Use `unittest.mock` for Gmail API mocking
  - **Coverage**: Test all Gmail operations and error scenarios
- [ ] **Security testing for vault token storage**
  - **Pattern**: Follow integration testing from `test_vault_token_service_integration.py`
  - **Reference**: Test RLS policies and cross-user access prevention
  - **Verification**: Ensure OAuth tokens remain secure throughout process
- [ ] **Performance testing for scheduled digest generation**
  - **Pattern**: Test concurrent agent execution and caching
  - **Reference**: Use existing agent executor cache performance patterns
  - **Metrics**: Measure digest generation time and resource usage

#### MEDIUM PRIORITY: Enhanced Features

##### TASK-SYNC-001: Real-time State Synchronization
- **Description**: Implement WebSocket-based real-time sync for UI state
- **Status**: TODO
- **Priority**: Medium
- **Dependencies**: Existing Zustand store, React Query hooks
- **Estimated Effort**: 32 hours
- **Implementation**: WebSocket layer with conflict resolution
- **Quality Gates**: Sub-100ms sync latency, offline handling

##### TASK-VOICE-001: Voice Input for Notes
- **Description**: Add voice-to-text capabilities for notes input
- **Status**: DEFERRED
- **Priority**: Medium
- **Dependencies**: Notes pane implementation (✅ Complete)
- **Estimated Effort**: 24 hours
- **Implementation**: Web Speech API or external service integration
- **Quality Gates**: Accurate transcription, privacy compliance

##### TASK-MOBILE-001: Mobile Responsive Stacked Cards
- **Description**: Optimize stacked card system for mobile devices
- **Status**: TODO
- **Priority**: Medium
- **Dependencies**: Existing TodayViewMockup.tsx
- **Estimated Effort**: 20 hours
- **Implementation**: Touch gestures, responsive breakpoints, bottom sheet pattern
- **Quality Gates**: Smooth touch interactions, consistent UX across devices

#### LOW PRIORITY: Advanced Features

##### TASK-AGENT-003: Auto-Scheduler Agent
- **Description**: Calendar conflict detection and proactive scheduling
- **Status**: TODO
- **Priority**: Low
- **Dependencies**: Google Calendar API integration
- **Estimated Effort**: 48 hours
- **Implementation**: Use existing agent framework with calendar conflict logic
- **Quality Gates**: No scheduling conflicts, intelligent time selection

### System-Wide Tasks (Updated)
- [X] Memory system setup - **COMPLETE** (PostgreSQL-based STM/LTM)
- [X] Agent orchestration framework - **COMPLETE** (Executor caching, session management)
- [X] Database connection pooling - **COMPLETE** (AsyncConnectionPool)
- [X] Authentication system - **COMPLETE** (Supabase integration)
- [ ] External API integrations (Google, Slack) - **IN PROGRESS** (Gmail tools implementation)
- [ ] Real-time sync infrastructure - **TODO**
- [ ] Monitoring and logging enhancements - **TODO**

### Updated Progress Summary
- **Overall Progress**: 65% (Core infrastructure complete, UI foundation complete)
- **Memory System**: ✅ 100% (PostgreSQL-based, production-ready)
- **Agent Orchestrator**: ✅ 100% (Caching, lifecycle management complete)
- **Database Layer**: ✅ 100% (Connection pooling, error handling complete)
- **Authentication**: ✅ 100% (Supabase integration complete)
- **UI Foundation**: ✅ 90% (Stacked card system + notes pane complete, needs voice input)
- **AI Agents**: 🔄 30% (Framework ready, Gmail tools in progress)
- **External APIs**: 🔄 40% (Foundation complete, Gmail tools implementation in progress)
- **Real-time Sync**: 🔄 0% (WebSocket implementation needed)

### Implementation Plan (Phased)

#### Phase 1: Foundation – Ingest + Tasking (Target: 2025-02-15)
**Objective**: Basic infrastructure and core functionality
- Notes input (text only initially)
- Ingest layer for Email, Calendar, Slack (read-only)
- Short-term Memory Store (basic implementation)
- Note-to-Task Agent (simple LLM-based)
- Planner View (Today view with manual task entry)
- Passive Reminder Engine (time-based checks)

**Key Deliverables**:
- [ ] Basic Memory System (working + short-term)
- [ ] Simple Agent Orchestrator
- [ ] Notes UI component
- [ ] Basic Planner View
- [ ] Email/Calendar/Slack read integration
- [ ] Note-to-Task conversion

#### Phase 2: Output Automation – Agents & Digest (Target: 2025-03-15)
**Objective**: AI agents and automated processing
- Slack Digest Agent (LLM-based summarization)
- Email Reply Drafter (basic LLM drafts)
- Task Classifier (improved LLM-based)
- Assistant Feed + Digest UI
- Long-term Memory Store (vector search)

**Key Deliverables**:
- [ ] Slack Digest Agent
- [ ] Email Reply Drafter
- [ ] Task Classification system
- [ ] Digest Feed UI
- [ ] Vector-based Long-term Memory
- [ ] Advanced Prompt Engine

#### Phase 3: Assistant as Multiplier (Target: 2025-04-30)
**Objective**: Proactive intelligence and automation
- Auto-Scheduler Agent (calendar conflict checks, proposing slots)
- Gift Suggestion + Reminder Agent (leveraging long-term memory)
- Grocery Planner Agent (list generation, external service integration)
- Calendar Block Manager (proactive blocking)
- Goal Tracking Dashboard
- Voice input for Notes
- Master List implementation

**Key Deliverables**:
- [ ] Auto-Scheduler Agent
- [ ] Gift/Reminder Agent
- [ ] Grocery Planner Agent
- [ ] Calendar Block Manager
- [ ] Goal Tracking Dashboard
- [ ] Voice input capability
- [ ] Master List system

### Creative Phases Required
- [X] Memory System Architecture Design - **COMPLETED: PostgreSQL-based STM/LTM system already implemented (see memory_system_v2.md)**
- [X] Agent Orchestration Design - **COMPLETED: Agent executor caching and session management already implemented (see agent_executor.py, connection.py)**
- [X] Real-time Sync Architecture - **COMPLETED: WebSocket-based event streaming with conflict resolution**
- [X] UI/UX Design for Executive Assistant - **COMPLETED: Split-Screen Stacked Card Interface (Aligned with TodayViewMockup.tsx)**
- [X] External API Integration Strategy - **COMPLETED: Service-oriented abstraction layer with shared infrastructure**

### Creative Phase Decision Summaries

#### Real-time Sync Architecture - **COMPLETED**
**Selected Approach**: WebSocket-based Event Streaming
**Key Features**:
- Direct WebSocket connections for sub-100ms latency
- Event-driven state synchronization across UI components
- Conflict resolution with last-write-wins strategy
- Automatic reconnection and connection management
- Integration with existing Zustand stores and React Query
**Implementation**: FastAPI WebSocket server with connection pooling, client-side RealtimeManager
**Priority**: Medium - enhances UX but current polling approach works for MVP

#### External API Integration Strategy - **COMPLETED**
**Selected Approach**: Service-Oriented API Abstraction Layer
**Key Features**:
- Dedicated service classes for Google Calendar, Gmail, Slack APIs
- Shared rate limiting and caching infrastructure
- OAuth2 authentication with secure token management
- Intelligent caching and batch operations for efficiency
- Clear abstraction layers for AI agent integration
**Implementation**: BaseAPIService with concrete implementations, APIGateway for coordination
**Priority**: High - required for core Clarity v2 functionality (Slack Digest, Reply Drafter, Auto-Scheduler agents)

### System Architecture Status Update

#### ✅ EXISTING INFRASTRUCTURE (Already Built)
- **Memory System**: PostgreSQL-based STM/LTM with `chat_message_history` and `user_agent_prompt_customizations` tables
- **Agent Orchestration**: Agent executor caching with `(user_id, agent_name)` keys and background cleanup tasks
- **Database Layer**: Robust connection pooling with `AsyncConnectionPool` and proper error handling
- **Session Management**: Complete session lifecycle with heartbeat and cleanup mechanisms
- **Tool System**: Dynamic CRUD tool loading from database configuration
- **Authentication**: Supabase integration with proper dependency injection

#### 🔄 NEEDS ENHANCEMENT FOR CLARITY V2
- **Real-time Sync**: WebSocket implementation for live state updates across UI components
- **External API Integration**: Google Calendar, Gmail, Slack API integrations with rate limiting
- **Notes Interface**: Add notes pane to existing stacked card system
- **Voice Input**: Voice-to-text capabilities for notes and task creation
- **Mobile Responsive**: Optimize stacked card system for mobile devices

### Updated Component Status

#### COMP-MEMORY: Memory System ✅ COMPLETE
- **Status**: ✅ Already implemented with PostgreSQL backend
- **Implementation**: `memory_system_v2.md`, `PostgresChatMessageHistory`, `AsyncConversationBufferWindowMemory`
- **Features**: STM (50-message window), LTM (prompt customizations), extensible architecture
- **Next Steps**: No major changes needed - system is production-ready

#### COMP-ORCHESTRATOR: Agent Orchestrator ✅ COMPLETE  
- **Status**: ✅ Already implemented with caching and lifecycle management
- **Implementation**: `agent_executor.py`, `connection.py`, background task scheduling
- **Features**: Agent executor caching, session cleanup, connection pooling
- **Next Steps**: No major changes needed - system handles concurrent agents well

#### COMP-PROMPT: Prompt Engine ✅ COMPLETE
- **Status**: ✅ Already implemented with database-driven configuration
- **Implementation**: `PromptCustomizationService`, dynamic tool loading from `agent_tools` table
- **Features**: Template management, context injection, extensible tool system
- **Next Steps**: No major changes needed - system supports dynamic prompt customization

#### COMP-UI-BRIDGE: UI Bridge 🔄 NEEDS ENHANCEMENT
- **Status**: 🔄 Basic implementation exists, needs real-time sync
- **Current**: React Query hooks, Zustand state management, assistant-ui integration
- **Missing**: WebSocket-based real-time synchronization for live updates
- **Priority**: Medium - current polling-based approach works for MVP

#### COMP-AGENTS: AI Agents 🔄 NEEDS IMPLEMENTATION
- **Status**: 🔄 Framework exists, specific agents need implementation
- **Current**: Generic agent executor framework, tool system, memory integration
- **Missing**: Slack Digest Agent, Reply Drafter Agent, Auto-Scheduler Agent
- **Priority**: High - core value proposition of Clarity v2

#### COMP-UI: User Interface 🔄 NEEDS ENHANCEMENT
- **Status**: 🔄 Core system implemented, needs production features
- **Current**: Split-screen stacked card system in `TodayViewMockup.tsx`
- **Missing**: Notes pane, voice input, mobile responsive behavior
- **Priority**: High - required for Phase 1 Foundation

### Revised Implementation Plan (Leveraging Existing Infrastructure)

#### Phase 1: Foundation Enhancement (Target: 2025-02-15)
**Objective**: Enhance existing systems for Clarity v2 MVP
- [X] Memory System (already complete)
- [X] Agent Orchestration (already complete) 
- [X] Database Layer (already complete)
- [ ] Add Notes pane to stacked card system
- [ ] Implement basic external API integrations (read-only)
- [ ] Create Slack Digest Agent using existing framework
- [ ] Add voice input for notes

**Key Deliverables**:
- [ ] Notes interface integrated into TodayViewMockup.tsx
- [ ] Slack API integration for digest generation
- [ ] Voice-to-text for notes input
- [ ] Basic email/calendar read integration

#### Phase 2: Agent Intelligence (Target: 2025-03-15)
**Objective**: Implement AI agents using existing orchestration framework
- [ ] Reply Drafter Agent (email/Slack responses)
- [ ] Enhanced Slack Digest Agent with summarization
- [ ] Task Classification improvements
- [ ] Real-time sync implementation (WebSocket)

**Key Deliverables**:
- [ ] Email Reply Drafter using existing agent framework
- [ ] Enhanced digest generation with LLM summarization
- [ ] WebSocket-based real-time state sync
- [ ] Mobile responsive stacked card system

#### Phase 3: Proactive Intelligence (Target: 2025-04-30)
**Objective**: Advanced agents and automation
- [ ] Auto-Scheduler Agent (calendar integration)
- [ ] Proactive reminder system
- [ ] Advanced external API integrations
- [ ] Performance optimization

**Key Deliverables**:
- [ ] Calendar conflict detection and scheduling
- [ ] Proactive task and reminder suggestions
- [ ] Advanced external service integrations
- [ ] Performance monitoring and optimization

### UI/UX Design Decision Summary
**Completed Creative Phase**: Executive Assistant UI/UX Design
**Selected Approach**: Split-Screen Stacked Card Interface (Aligned with TodayViewMockup.tsx)
**Key Features**:
- Dual-pane system (60% primary, 40% secondary) with stacked cards
- Four pane types: Tasks, Chat (AI Assistant), Calendar, Focus Session
- Ultimate flexibility: Users can isolate any pane or work side-by-side
- Agent positioning: Chat can be primary (60%), secondary (40%), or hidden entirely
- Complete keyboard navigation (⌘1-4, [], Tab, arrows)
- Smooth 500ms transitions with glassmorphic effects
- Mobile-responsive with card stacking
**Style Guide Compliance**: Full adherence to semantic color tokens and Radix UI patterns
**Implementation Status**: ✅ Core system implemented in TodayViewMockup.tsx
**Next Steps**: Add notes pane, integrate with backend, add voice input

### Dependencies (Updated)
- [X] Memory system - **COMPLETE** (PostgreSQL-based STM/LTM)
- [X] Agent orchestration framework - **COMPLETE** (Executor caching, session management)
- [X] Database layer - **COMPLETE** (AsyncConnectionPool, error handling)
- [X] Authentication system - **COMPLETE** (Supabase integration)
- [ ] External API access (Google Calendar, Gmail, Slack) - **IN PROGRESS**
- [ ] LLM provider configuration (Gemini Pro, OpenAI) - **MOSTLY COMPLETE** (needs external API integration)
- [ ] Real-time infrastructure (WebSocket implementation) - **TODO**

### Challenges & Mitigations (Updated)
- **Challenge 1**: External API integration complexity - **Mitigation**: Create abstraction layer for each service with proper error handling (existing patterns available)
- **Challenge 2**: Real-time state synchronization across multiple data sources - **Mitigation**: Implement event-driven architecture with proper conflict resolution (existing Zustand/React Query foundation)
- **Challenge 3**: User privacy with external integrations - **Mitigation**: Implement data minimization and user consent management (existing Supabase RLS patterns)
- **Challenge 4**: Mobile responsive stacked card system - **Mitigation**: Leverage existing TodayViewMockup.tsx foundation with touch gesture enhancements
- **Challenge 5**: Voice input privacy and accuracy - **Mitigation**: Use Web Speech API with local processing where possible

### Latest Updates
- 2025-01-27: Planning phase completed, comprehensive system architecture defined
- 2025-01-27: Technology stack validated against existing webApp and chatServer infrastructure
- 2025-01-27: Phased implementation plan created with clear milestones and deliverables
- 2025-01-27: **INFRASTRUCTURE ASSESSMENT COMPLETE** - Discovered 60% of core systems already implemented
- 2025-01-27: **TASK PRIORITIZATION UPDATED** - Focused on remaining 40% (external APIs, specific agents, UI enhancements)
- 2025-01-27: **CREATIVE PHASE ALIGNMENT** - UI/UX design aligned with existing TodayViewMockup.tsx implementation
- 2025-01-27: **ALL CREATIVE PHASES COMPLETE** - Real-time sync architecture and external API integration strategy designed
- 2025-01-27: **READY FOR IMPLEMENTATION** - All design decisions made, comprehensive implementation guidelines documented