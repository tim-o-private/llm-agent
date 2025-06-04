# CRITICAL INSTRUCTIONS
All agents MUST read `README.md` for navigation, then consult the relevant pattern files (`patterns/ui-patterns.md`, `patterns/api-patterns.md`, `patterns/agent-patterns.md`, `patterns/data-patterns.md`) and rule files (`rules/*.json`) for their work area. Adhere to established patterns unless EXPLICITLY told by the user to deviate.

# Active Tasks

This file tracks current tasks for the **Clarity v2** project - an executive-function assistant that filters noise, multiplies output, and eliminates manual data entry.

## 🎯 PROJECT FOCUS: CLARITY V2

**Current Objective**: Implement Clarity v2 using **PostgREST + Minimal Chat Gateway** architecture  
**Architecture Document**: `creative/clarity-v2-postgrest-architecture.md`

**Project Vision**: Create an executive-function assistant that:
- **Filters inbound noise** so users stop paying attention to what doesn't matter
- **Multiplies outbound output** so goals are met with less effort  
- **Eliminates manual data entry** and returns attention to the user

## 📋 CURRENT TASK: TASK-CLARITY-002 - PostgREST Architecture Implementation

**Status**: 🔄 IN PROGRESS - Planning complete, ready for technology validation  
**Complexity**: Level 4 (Complex System - Multi-phase implementation)  
**Priority**: HIGH - Foundation for all future development  
**Planning Methodology**: Memory Bank Level 4 Architectural Planning

### 📋 REQUIREMENTS ANALYSIS

#### Core Requirements
- [x] **R1**: Eliminate custom API layer - Use router-proxied PostgREST for all data operations
- [x] **R2**: Establish consistent typing - Auto-generated types + custom chat types
- [x] **R3**: Implement controlled DB access - Rate limiting and caching built into stores
- [x] **R4**: Create minimal backend - Router with PostgREST proxy + chat gateway
- [x] **R5**: Maintain data freshness - Periodic polling via router
- [x] **R6**: Preserve existing UI patterns - Assistant-UI + Radix components
- [x] **R7**: Enable rapid feature development - Tool = router → PostgREST HTTP call

#### Technical Constraints
- [x] **C1**: Must use existing Supabase database schema
- [x] **C2**: Must maintain compatibility with existing frontend components
- [x] **C3**: Must preserve AI agent orchestration capabilities
- [x] **C4**: Must support data updates via periodic polling through router
- [x] **C5**: Must eliminate 80%+ of custom backend code
- [x] **C6**: Must maintain database isolation - no direct frontend access

#### Non-Functional Requirements
- **Performance**: Response time < 200ms for data operations
- **Scalability**: Support 100+ concurrent users with controlled query limits
- **Maintainability**: Reduce codebase complexity by 80%
- **Type Safety**: 100% type coverage via auto-generation
- **Reliability**: 99.9% uptime with built-in error handling

### 🏗️ ARCHITECTURAL ANALYSIS

#### System Components Affected
1. **Frontend Layer (webApp/)**
   - Components: Chat, Tasks, Memory, UI (Radix)
   - Stores: Zustand stores with router-proxied PostgREST calls
   - Hooks: Custom hooks for typed interfaces
   - Types: Auto-generated + custom chat types

2. **Backend Layer (chatServer/)**
   - Minimal FastAPI app with routing
   - Chat gateway for AI orchestration
   - PostgREST proxy for data operations
   - AI orchestration system
   - Tool system (PostgREST-based)
   - Type definitions (Pydantic)

3. **Data Layer (Supabase)**
   - PostgREST API (auto-generated)
   - PostgreSQL with RLS
   - Periodic data polling
   - Authentication

4. **Integration Layer**
   - External APIs (Gmail, Calendar, Slack)
   - Tool execution engine
   - Type consistency validation

#### Dependencies & Integration Points
- **Frontend ↔ Router**: HTTP calls to our FastAPI router
- **Router ↔ PostgREST**: Proxied PostgREST calls with validation
- **Chat Gateway ↔ AI System**: Agent orchestration and tool execution
- **Tools ↔ PostgREST**: Direct HTTP calls via router proxy
- **Data Updates ↔ Frontend**: Periodic polling via router
- **Types ↔ All Layers**: Auto-generated types ensure consistency

### 🔧 TECHNOLOGY STACK VALIDATION

#### Selected Technologies
- **Frontend Framework**: Next.js with TypeScript
- **State Management**: Zustand stores
- **UI Components**: Assistant-UI + Radix
- **Backend Framework**: FastAPI (minimal router + chat gateway)
- **Database API**: Router-proxied Supabase PostgREST
- **Type Generation**: Supabase CLI
- **Data Updates**: Periodic polling via router
- **AI Integration**: Existing agent system

#### Technology Validation Checkpoints
- [ ] **TV1**: Supabase CLI type generation verified
- [ ] **TV2**: Router-proxied PostgREST calls from frontend validated
- [ ] **TV3**: FastAPI router with PostgREST proxy functional
- [ ] **TV4**: Zustand + router integration tested
- [ ] **TV5**: Periodic polling via router working
- [ ] **TV6**: Tool → router → PostgREST HTTP calls validated
- [ ] **TV7**: Type consistency across all layers verified
- [ ] **TV8**: End-to-end build process successful

### 📊 IMPLEMENTATION STRATEGY

#### Phased Implementation Approach
```mermaid
graph TD
    P0["Phase 0: Foundation<br>(Day 1)"] --> P1["Phase 1: Router<br>(Day 2)"]
    P1 --> P2["Phase 2: Types<br>(Day 3)"]
    P2 --> P3["Phase 3: Frontend Migration<br>(Day 4-5)"]
    P3 --> P4["Phase 4: Backend Migration<br>(Day 6-7)"]
    P4 --> P5["Phase 5: Cleanup<br>(Day 8)"]
    
    P0 -.-> TV["Technology Validation<br>Continuous"]
    P1 -.-> TV
    P2 -.-> TV
    P3 -.-> TV
    P4 -.-> TV
```

#### Detailed Implementation Steps

##### ✅ Phase 0: Foundation Setup (Day 1) - NEXT
**Objective**: Establish new simplified directory structure and basic configuration

**Technology Validation Required**: Project initialization and Supabase setup

**Tasks**:
- [ ] **0.1 Directory Structure Creation**
  ```bash
  # Frontend structure
  mkdir -p webApp/src/{components/{chat,tasks,memory,ui},stores,hooks,lib,types}
  # Backend structure (minimal)
  mkdir -p chatServer/{routers,ai,tools,types,config,dependencies}
  ```

- [ ] **0.2 Supabase Type Generation Setup**
  ```bash
  # Install Supabase CLI if needed
  npm install -g supabase
  # Generate initial TypeScript types
  npx supabase gen types typescript --project-id YOUR_PROJECT_ID > webApp/src/types/database.ts
  ```

- [ ] **0.3 Basic Configuration Files**
  - Create Supabase client configuration (`webApp/src/lib/supabase.ts`)
  - Create minimal FastAPI app skeleton (`chatServer/main.py`)
  - Set up environment variables and configuration

**Technology Validation Checkpoints**:
- [ ] Supabase CLI installed and functional
- [ ] Type generation produces valid TypeScript
- [ ] Directory structure created successfully
- [ ] Basic configuration files compile without errors

##### 📅 Phase 1: Minimal Router (Day 2)
**Objective**: Create FastAPI router with PostgREST proxy and chat gateway

**Technology Validation Required**: FastAPI setup with PostgREST proxy

**Tasks**:
- [ ] **1.1 FastAPI Router with PostgREST Proxy**
  - Create FastAPI app with dual routing: `/chat` and `/api/*`
  - Implement PostgREST proxy for `/api/*` routes
  - Configure CORS for frontend access
  - Add health check endpoint (`/health`)
  - Basic error handling and request validation

- [ ] **1.2 Routing Validation**
  - Test routing: `/chat` → AI gateway, `/api/*` → PostgREST proxy
  - Verify frontend can reach both endpoints
  - Confirm database isolation (no direct access)
  - Test CORS configuration
  - Validate request/response proxying

**Technology Validation Checkpoints**:
- [ ] FastAPI app starts without errors
- [ ] Health endpoint returns 200 status
- [ ] PostgREST proxy routes requests correctly
- [ ] CORS allows frontend requests
- [ ] Chat endpoint accepts POST requests
- [ ] Frontend cannot access database directly

##### 📅 Phase 2: Type System (Day 3)
**Objective**: Establish consistent typing across all layers

**Technology Validation Required**: Type generation and compilation

**Tasks**:
- [ ] **2.1 Auto-Generated Database Types**
  - Generate TypeScript types from Supabase schema
  - Create type generation script for CI/CD
  - Validate type accuracy against database
  - Set up type watching for development

- [ ] **2.2 Custom Chat Types**
  - Create chat-specific TypeScript types
  - Create corresponding Pydantic models
  - Validate type consistency between frontend/backend
  - Test type compilation and imports

**Technology Validation Checkpoints**:
- [ ] Database types generate without errors
- [ ] Custom types compile successfully
- [ ] Type imports work across modules
- [ ] Pydantic models validate correctly
- [ ] No type conflicts or circular dependencies

##### 📅 Phase 3: Frontend Migration (Day 4-5)
**Objective**: Convert frontend to router-proxied PostgREST calls with controlled access

**Technology Validation Required**: Zustand + Router integration

**Tasks**:
- [ ] **3.1 Zustand Store Migration**
  - Convert `taskStore` to router-proxied PostgREST calls
  - Implement controlled DB access patterns (limits, caching)
  - Add periodic polling for data updates via router
  - Implement staleness detection and cache management

- [ ] **3.2 Custom Hook Migration**
  - Update `useTasks` hook for router integration
  - Implement caching and error handling
  - Add optimistic updates for better UX
  - Test frontend-to-router-to-database flow end-to-end

- [ ] **3.3 UI Component Integration**
  - Connect task components to new stores
  - Test periodic data refresh via router
  - Verify controlled DB access (query limits)
  - Validate type safety in components

**Technology Validation Checkpoints**:
- [ ] Zustand stores connect to router successfully
- [ ] Periodic polling retrieves data updates via router
- [ ] Query limits prevent excessive DB calls
- [ ] Caching reduces redundant requests
- [ ] UI updates reflect database changes via router polling
- [ ] Type safety maintained throughout

##### 📅 Phase 4: Backend Migration (Day 6-7)
**Objective**: Convert AI tools to router-proxied PostgREST calls

**Technology Validation Required**: Tool → Router → PostgREST integration

**Tasks**:
- [ ] **4.1 Tool System Migration**
  - Convert `CreateTaskTool` to router-proxied PostgREST calls
  - Convert `GetTasksTool` to router-proxied PostgREST calls
  - Implement controlled error handling and retries
  - Add tool execution logging and monitoring

- [ ] **4.2 Chat Gateway Integration**
  - Implement chat endpoint with AI orchestration
  - Integrate tools with agent orchestrator via router
  - Add request/response validation
  - Implement rate limiting for chat requests

- [ ] **4.3 End-to-End Validation**
  - Test complete flow: chat → AI → tools → router → PostgREST → database
  - Verify periodic polling updates reach frontend via router
  - Validate type safety throughout entire stack
  - Performance testing under load

**Technology Validation Checkpoints**:
- [ ] Tools make successful router-proxied PostgREST calls
- [ ] Agent orchestrator integrates with tools via router
- [ ] Chat endpoint processes requests correctly
- [ ] End-to-end flow completes successfully
- [ ] Periodic polling updates propagate via router to frontend
- [ ] Performance meets requirements

##### 📅 Phase 5: System Cleanup (Day 8)
**Objective**: Remove all custom API layer code and finalize system

**Technology Validation Required**: Complete system validation

**Tasks**:
- [ ] **5.1 Code Removal**
  - Delete `chatServer/routers/` (except `chat.py`)
  - Delete `chatServer/services/`
  - Delete `chatServer/models/`
  - Clean up unused dependencies
  - Update documentation

- [ ] **5.2 Final System Validation**
  - Test complete system functionality
  - Verify type safety end-to-end
  - Performance testing and optimization
  - Security validation
  - Documentation update and review

**Technology Validation Checkpoints**:
- [ ] System functions without deleted components
- [ ] All tests pass after cleanup
- [ ] Performance meets success metrics
- [ ] Security requirements satisfied
- [ ] Documentation is complete and accurate

### 🎨 CREATIVE PHASES REQUIRED

#### Architecture Design Phase
- **Component**: System Architecture
- **Decisions Required**: 
  - PostgREST integration patterns
  - Tool execution architecture
  - Error handling strategies
- **Status**: ✅ COMPLETE (documented in architecture.md)

#### Data Flow Design Phase
- **Component**: Data Synchronization via Polling
- **Decisions Required**:
  - Optimistic update patterns
  - Polling frequency strategies
  - Cache invalidation logic
- **Status**: 🔄 REQUIRED during Phase 3

#### Tool Integration Design Phase
- **Component**: AI Tool → PostgREST Integration
- **Decisions Required**:
  - HTTP client patterns
  - Error handling and retries
  - Authentication flow
- **Status**: 🔄 REQUIRED during Phase 4

### ⚠️ CHALLENGES & MITIGATIONS

#### Challenge 1: Type Consistency Across Layers
- **Risk**: Type mismatches between auto-generated and custom types
- **Mitigation**: Automated type validation in CI/CD pipeline
- **Validation**: Compile-time type checking + runtime validation

#### Challenge 2: Data Update Performance
- **Risk**: Periodic polling may impact performance or user experience
- **Mitigation**: Intelligent polling frequency with exponential backoff and cache optimization
- **Validation**: Performance testing with polling frequency optimization

#### Challenge 3: Tool Error Handling
- **Risk**: PostgREST HTTP calls may fail or timeout
- **Mitigation**: Robust retry logic with exponential backoff
- **Validation**: Fault injection testing

#### Challenge 4: Database Query Control
- **Risk**: Uncontrolled queries may impact database performance
- **Mitigation**: Built-in query limits and caching in stores
- **Validation**: Query monitoring and performance metrics

### 📊 SUCCESS METRICS

#### Code Reduction Metrics
- **Target**: Eliminate 80%+ of custom backend code
- **Measurement**: Lines of code before/after migration
- **Current**: ~5000 LOC → Target: <1000 LOC

#### Type Safety Metrics
- **Target**: 100% shared types via auto-generation
- **Measurement**: TypeScript compilation without `any` types
- **Validation**: Automated type checking in CI/CD

#### Performance Metrics
- **Target**: Response time < 200ms for data operations
- **Measurement**: API response time monitoring
- **Validation**: Load testing with 100+ concurrent users

#### Development Velocity Metrics
- **Target**: New features = database change + tool
- **Measurement**: Time to implement new feature
- **Validation**: Feature development time tracking

### 🔄 MEMORY BANK INTEGRATION

#### Files Updated During Planning
- [x] **tasks.md**: Comprehensive implementation plan
- [x] **creative/clarity-v2-postgrest-architecture.md**: Architecture documentation
- [ ] **activeContext.md**: Current implementation focus
- [ ] **progress.md**: Implementation progress tracking

#### Next Mode Recommendation
**NEXT MODE**: IMPLEMENT MODE (Technology Validation Phase)
- Technology validation checkpoints must be completed before full implementation
- Focus on Phase 0: Foundation Setup with technology validation
- Validate Supabase type generation and basic FastAPI setup

### 🚨 PLANNING VERIFICATION CHECKLIST

```
✓ LEVEL 4 PLANNING VERIFICATION CHECKLIST

Requirements Analysis
- [x] Functional requirements analyzed and documented
- [x] Non-functional requirements specified with metrics
- [x] Technical constraints identified and addressed
- [x] Domain model and component identification complete

Architectural Analysis
- [x] System components and affected areas identified
- [x] Dependencies and integration points documented
- [x] Technology stack selected and justified
- [x] Architectural decisions documented with rationales

Implementation Strategy
- [x] Phased implementation approach defined
- [x] Detailed steps for each phase documented
- [x] Technology validation checkpoints established
- [x] Success metrics and validation criteria defined

Creative Phases
- [x] Architecture design phase completed
- [x] Data flow design phase identified for Phase 3
- [x] Tool integration design phase identified for Phase 4
- [x] Creative phase requirements documented

Risk Management
- [x] Key challenges identified with specific mitigations
- [x] Validation strategies defined for each risk
- [x] Contingency plans documented
- [x] Performance and security considerations addressed

Memory Bank Integration
- [x] Planning documentation complete in tasks.md
- [x] Architecture documentation in creative/ folder
- [x] Next mode recommendation provided
- [x] Progress tracking structure established

→ PLANNING COMPLETE: Ready for IMPLEMENT MODE with Technology Validation