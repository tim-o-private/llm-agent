# CRITICAL INSTRUCTIONS
All agents MUST read `README.md` for navigation, then consult the relevant pattern files (`patterns/ui-patterns.md`, `patterns/api-patterns.md`, `patterns/agent-patterns.md`, `patterns/data-patterns.md`) and rule files (`rules/*.json`) for their work area. Adhere to established patterns unless EXPLICITLY told by the user to deviate.

# Tasks

This file tracks the current tasks, steps, checklists, and component lists for the Local LLM Terminal Environment and the Clarity web application. It consolidates information from previous implementation plans and backlog documents.

## PENDING / ACTIVE TASKS

**CURRENT TASK: VAN-ARCH-001: Email Digest System Architecture Iteration**
*   **Status:** PLAN Mode - Level 3 Comprehensive Implementation Planning
*   **Complexity:** 3 (Intermediate Feature - System architecture refinement with existing components)
*   **Objective:** Create detailed implementation plan for the unified Email Digest System architecture leveraging existing infrastructure
*   **Context:** Architecture analysis complete. Need comprehensive implementation plan for unified service approach with scheduled and on-demand execution.

## 📋 Requirements Analysis

### Core Requirements
- [X] **REQ-001**: Scheduled agent execution system for daily email digests - ✅ **ANALYZED**
- [X] **REQ-002**: On-demand email digest generation via chat interface - ✅ **ANALYZED**
- [X] **REQ-003**: Latency optimization through parallel execution - ✅ **ANALYZED**
- [X] **REQ-004**: Leverage existing BackgroundTaskService infrastructure - ✅ **ANALYZED**
- [X] **REQ-005**: Unified service architecture with shared entry point - ✅ **ANALYZED**

### Technical Constraints
- [X] **CONST-001**: Must use existing LangChain Gmail toolkit (no custom wrappers) - ✅ **VALIDATED**
- [X] **CONST-002**: Must integrate with existing VaultTokenService for OAuth - ✅ **VALIDATED**
- [X] **CONST-003**: Must extend BackgroundTaskService (no new orchestrator) - ✅ **VALIDATED**
- [X] **CONST-004**: Must maintain agent executor caching patterns - ✅ **VALIDATED**

## 🔍 Component Analysis

### Affected Components
- **BackgroundTaskService** (`chatServer/services/background_tasks.py`)
  - Changes needed: Add scheduled agent execution capability
  - Dependencies: Agent executor cache, EmailDigestService
  
- **Gmail Tools** (`chatServer/tools/gmail_tools.py`)
  - Changes needed: Replace with simplified LangChain toolkit provider
  - Dependencies: VaultTokenService, LangChain Gmail toolkit
  
- **EmailDigestService** (NEW: `chatServer/services/email_digest_service.py`)
  - Changes needed: Create unified service for both scheduled and on-demand execution
  - Dependencies: SimpleGmailToolProvider, PostgreSQL storage
  
- **EmailDigestTool** (NEW: `chatServer/tools/email_digest_tool.py`)
  - Changes needed: Create tool wrapper for assistant agent
  - Dependencies: EmailDigestService
  
- **ChatService** (`chatServer/services/chat.py`)
  - Changes needed: No changes needed - tool automatically available to assistant agent
  - Dependencies: EmailDigestTool via agent framework

## 🎨 Design Decisions

### Architecture Decisions
- [X] **ARCH-DEC-001**: Unified service pattern with context parameter - ✅ **DECIDED**
- [X] **ARCH-DEC-002**: Tool layer → Service layer → Infrastructure layer separation - ✅ **DECIDED**
- [X] **ARCH-DEC-003**: Shared Gmail provider caching within service instance - ✅ **DECIDED**
- [X] **ARCH-DEC-004**: BackgroundTaskService extension vs new orchestrator - ✅ **DECIDED**

### Implementation Decisions
- [X] **IMPL-DEC-001**: LangChain Gmail toolkit direct usage - ✅ **DECIDED**
- [X] **IMPL-DEC-002**: Async execution patterns for all components - ✅ **DECIDED**
- [X] **IMPL-DEC-003**: PostgreSQL storage for digest results - ✅ **DECIDED**
- [X] **IMPL-DEC-004**: Error handling and logging patterns - ✅ **DECIDED**

## ⚙️ Implementation Strategy

### Phase 1: BackgroundTaskService Extension (Days 1-2)
1. [X] **PHASE1-001**: Analyze existing BackgroundTaskService patterns - ✅ **COMPLETE**
2. [ ] **PHASE1-002**: Add scheduled agent execution capability
   - [ ] Add `run_scheduled_agents()` method
   - [ ] Add agent schedule management
   - [ ] Add agent executor cache integration
3. [ ] **PHASE1-003**: Create schedule configuration system
   - [ ] Database schema for agent schedules
   - [ ] Schedule validation logic
   - [ ] Schedule persistence layer

### Phase 2: Gmail Tools Simplification (Day 3)
1. [ ] **PHASE2-001**: Backup existing gmail_tools.py implementation
2. [ ] **PHASE2-002**: Create SimpleGmailToolProvider
   - [ ] LangChain Gmail toolkit integration
   - [ ] VaultTokenService authentication
   - [ ] Async tool retrieval
3. [ ] **PHASE2-003**: Replace existing Gmail tools
   - [ ] Remove bloated implementation
   - [ ] Update imports and references
   - [ ] Verify tool loading

### Phase 3: Unified Email Digest Service (Days 4-5)
1. [ ] **PHASE3-001**: Create EmailDigestService
   - [ ] Unified `generate_digest()` method
   - [ ] Context-aware execution (scheduled vs on-demand)
   - [ ] Gmail provider caching
   - [ ] Error handling and logging
2. [ ] **PHASE3-002**: Create EmailDigestTool
   - [ ] LangChain BaseTool implementation
   - [ ] Service integration
   - [ ] Input validation schema
3. [ ] **PHASE3-003**: Integrate with BackgroundTaskService
   - [ ] Scheduled execution implementation
   - [ ] Result storage
   - [ ] Error handling

### Phase 4: Integration & Testing (Day 6)
1. [ ] **PHASE4-001**: End-to-end integration testing
   - [ ] Scheduled digest execution
   - [ ] On-demand digest via chat
   - [ ] Error scenario handling
2. [ ] **PHASE4-002**: Performance optimization
   - [ ] Parallel execution verification
   - [ ] Caching effectiveness
   - [ ] Latency measurement
3. [ ] **PHASE4-003**: Configuration and deployment
   - [ ] Environment configuration
   - [ ] Database migrations
   - [ ] Documentation updates

## 🧪 Testing Strategy

### Unit Tests
- [ ] **TEST-UNIT-001**: EmailDigestService unit tests
  - [ ] Digest generation with different contexts
  - [ ] Error handling scenarios
  - [ ] Gmail provider caching
- [ ] **TEST-UNIT-002**: EmailDigestTool unit tests
  - [ ] Tool execution
  - [ ] Input validation
  - [ ] Service integration
- [ ] **TEST-UNIT-003**: BackgroundTaskService extension tests
  - [ ] Scheduled agent execution
  - [ ] Schedule management
  - [ ] Error handling

### Integration Tests
- [ ] **TEST-INT-001**: End-to-end scheduled digest test
  - [ ] Schedule configuration
  - [ ] Agent execution
  - [ ] Result storage
- [ ] **TEST-INT-002**: End-to-end on-demand digest test
  - [ ] Chat interface integration
  - [ ] Tool execution
  - [ ] Response generation
- [ ] **TEST-INT-003**: Gmail API integration test
  - [ ] OAuth authentication
  - [ ] Email retrieval
  - [ ] Error handling

## 📚 Documentation Plan

- [ ] **DOC-001**: Architecture documentation update
  - [ ] Unified service pattern explanation
  - [ ] Component interaction diagrams
  - [ ] Deployment guide
- [ ] **DOC-002**: API documentation
  - [ ] EmailDigestService interface
  - [ ] EmailDigestTool schema
  - [ ] Configuration options
- [ ] **DOC-003**: User guide updates
  - [ ] Scheduled digest configuration
  - [ ] On-demand digest usage
  - [ ] Troubleshooting guide

## 🎨 Creative Phases Required

- [ ] **CREATIVE-001**: 🏗️ Architecture Design - ✅ **COMPLETE** (Unified service architecture decided)
- [ ] **CREATIVE-002**: ⚙️ Algorithm Design - ⏳ **NOT REQUIRED** (Standard service patterns)
- [ ] **CREATIVE-003**: 🎨 UI/UX Design - ⏳ **NOT REQUIRED** (Chat interface integration only)

## ✅ Checkpoints

- [X] **CP-001**: Requirements verified - ✅ **COMPLETE**
- [X] **CP-002**: Architecture decisions made - ✅ **COMPLETE**
- [X] **CP-003**: Implementation plan detailed - ✅ **COMPLETE**
- [X] **CP-004**: Testing strategy defined - ✅ **COMPLETE**
- [X] **CP-005**: Documentation plan ready - ✅ **COMPLETE**

## 📊 Current Status
- **Phase**: PLAN Mode - Level 3 Comprehensive Planning
- **Status**: ✅ **PLANNING COMPLETE** - Ready for implementation
- **Blockers**: None - Authentication architecture verified as correct
- **Next Steps**: Transition to IMPLEMENT mode for Phase 1 implementation

✅ **AUTHENTICATION ARCHITECTURE VERIFIED & CLEANED**:
- **UI Context**: FastAPI with JWT auth → `authenticated` role → RLS applies → `get_oauth_tokens()` RPC function
- **Background Context**: Direct postgres connection → postgres role with RLS bypass policy → `get_oauth_tokens_for_scheduler()` RPC function  
- **Testing Confirmed**: Both RPC functions work correctly with proper security isolation
- **Cruft Cleanup**: Eliminated direct table access, single VaultTokenService with context parameter
- **Implementation**: VaultTokenService(conn, context="user|scheduler") provides unified interface
- **Architecture Status**: ✅ **COMPLETE** - Clean, secure, ready for implementation

## 🔄 Dependencies

### Internal Dependencies
- **BackgroundTaskService** - Existing service to extend
- **VaultTokenService** - OAuth token management
- **Agent executor cache** - Existing caching system
- **PostgreSQL connection pool** - Database infrastructure

### External Dependencies
- **LangChain Gmail toolkit** - Gmail API integration
- **Google OAuth credentials** - Authentication
- **Gmail API access** - Email data retrieval

## ⚠️ Challenges & Mitigations

- **CHALLENGE-001**: LangChain Gmail toolkit integration complexity
  - **Mitigation**: Use existing VaultTokenService patterns, comprehensive testing
- **CHALLENGE-002**: BackgroundTaskService extension without breaking existing functionality
  - **Mitigation**: Careful extension design, backward compatibility testing
- **CHALLENGE-003**: Parallel execution optimization
  - **Mitigation**: Leverage LangChain's built-in parallelization, performance monitoring
- **CHALLENGE-004**: Error handling across service boundaries
  - **Mitigation**: Consistent error handling patterns, comprehensive logging

## 📋 Technology Stack

### Framework & Tools
- **Backend Framework**: FastAPI (existing)
- **Agent Framework**: LangChain (existing)
- **Database**: PostgreSQL (existing)
- **Authentication**: Supabase Vault (existing)

### Technology Validation Checkpoints
- [X] **TECH-001**: LangChain Gmail toolkit compatibility verified
- [X] **TECH-002**: BackgroundTaskService extension feasibility confirmed
- [X] **TECH-003**: VaultTokenService integration validated
- [X] **TECH-004**: Agent executor caching patterns verified
- [X] **TECH-005**: PostgreSQL storage patterns confirmed

## 📋 Files to Create/Modify

### New Files
- [ ] **`chatServer/services/email_digest_service.py`** - Unified email digest service
- [ ] **`chatServer/tools/email_digest_tool.py`** - LangChain tool wrapper
- [ ] **`supabase/migrations/20250130000001_email_digest_schedules.sql`** - Schedule configuration schema

### Modified Files
- [ ] **`chatServer/services/background_tasks.py`** - Add scheduled agent execution
- [ ] **`chatServer/tools/gmail_tools.py`** - Replace with simplified provider
- [ ] **`chatServer/main.py`** - Register new tool if needed

### Backup Files
- [ ] **`memory-bank/archive/gmail-tools-backup/`** - Backup existing implementation

## 🚨 Implementation Readiness

✅ **LEVEL 3 COMPREHENSIVE PLANNING COMPLETE**
- [X] Requirements analysis complete
- [X] Component analysis complete  
- [X] Architecture decisions made
- [X] Technology stack validated
- [X] Implementation strategy detailed
- [X] Testing strategy defined
- [X] Documentation plan ready
- [X] Creative phases identified (Architecture design complete)
- [X] Dependencies documented
- [X] Challenges and mitigations addressed

**PLANNING COMPLETE**: All Level 3 planning requirements satisfied

**NEXT RECOMMENDED MODE**: **IMPLEMENT MODE** - Begin Phase 1 BackgroundTaskService extension

**Implementation Notes**: 
- ✅ Phase 1 Complete: Supabase Vault integration provides enterprise-grade OAuth token security
- ✅ **PLAN MODE COMPLETE**: Comprehensive Level 3 architectural planning following enterprise standards
- **Implementation Ready**: All design decisions made, detailed task breakdown complete
- Uses established CRUDTool patterns for database-driven configuration
- Implements scheduled daily digest as per Clarity v2 PRD requirements
- Ready for integration with existing agent executor caching system