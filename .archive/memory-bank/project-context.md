# Project Context

> **Essential project information** - Architecture, tech stack, goals

## Project Overview

**Dual-purpose system**: Local LLM Terminal Environment (CLI) + Clarity Web Application

### Local LLM Terminal Environment (CLI)
- **Purpose**: Python-based terminal for structured LLM interactions
- **Target**: Technical users, developers
- **Key Features**: Agent configuration, file-based context, REPL interface, tool usage

### Clarity Web Application  
- **Purpose**: Planning and executive function assistant for adults with ADHD
- **Target**: Adults with ADHD needing executive function support
- **Key Features**: Task planning, AI coaching, distraction management, Google integrations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Chat Server   │    │   Agent Core    │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Python)      │
│   webApp/       │    │   chatServer/   │    │   src/core/     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Supabase      │    │   PostgreSQL    │    │   Local Files   │
│   (Auth/DB)     │    │   (SINGLE DB)   │    │   (Context)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Tech Stack

### Frontend (`webApp/`)
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: TailwindCSS + Radix UI Primitives (NOT @radix-ui/themes components)
- **State**: Zustand (global) + React Query (API) + React Hook Form (forms)
- **Routing**: React Router v6
- **Validation**: Zod schemas

### Backend (`chatServer/`)
- **Framework**: FastAPI + Pydantic v2
- **Database**: Supabase (PostgreSQL with RLS)
- **Authentication**: JWT validation via Supabase
- **Architecture**: Service layer pattern (services/, models/, protocols/)

### Agent Core (`src/core/`)
- **Framework**: LangChain + Python 3.12
- **Memory**: PostgresChatMessageHistory (langchain-postgres)
- **Tools**: Generic CRUDTool + DB-configured tools
- **Models**: Gemini Pro (primary), OpenAI (fallback)

### Infrastructure
- **Database**: Single PostgreSQL database hosted on Supabase with RLS
- **Deployment**: Vercel (frontend) + Railway (backend)
- **Environment**: Development on Linux, production containerized

## Key Patterns

### UI Development
- **Components**: Radix primitives + Tailwind semantic tokens
- **Colors**: Semantic tokens only (bg-ui-element-bg, text-text-primary)
- **State**: React Query hooks for API, Zustand for global state
- **Forms**: React Hook Form + Zod validation
- **Overlays**: Centralized useOverlayStore

### API Development  
- **Structure**: FastAPI + Pydantic models + service layer
- **Authentication**: JWT middleware with user context
- **Database**: RLS patterns with `is_record_owner(user_id)`
- **Error Handling**: Structured HTTP exceptions

### Agent Development
- **Tools**: Generic CRUDTool configured via `agent_tools` table
- **Memory**: PostgresChatMessageHistory with session management
- **Loading**: DB-driven tool instantiation with runtime values
- **Patterns**: LangChain tool abstractions

## Current Status

### Completed
- ✅ Core architecture and service layer
- ✅ Session management with executor caching
- ✅ CRUD tool migration to DB configuration
- ✅ Memory Bank simplification (Phase 2 in progress)

### In Progress
- 🔄 Memory Bank documentation consolidation
- 🔄 ChatServer main.py decomposition (Phase 3)
- 🔄 Integration testing for session management

### Pending
- ⏳ Agent tool loading refactor
- ⏳ Additional agent tools (web search, documents, calendar)
- ⏳ Frontend UI enhancements

## Development Guidelines

### File Organization
- **Frontend**: `webApp/src/components/ui/` (shared), `webApp/src/components/features/` (specific)
- **Backend**: `chatServer/services/` (business logic), `chatServer/models/` (data)
- **Agents**: `src/core/agents/` (agent configs), `src/core/tools/` (tool implementations)
- **Documentation**: `memory-bank/patterns/` (implementation), `memory-bank/rules/` (constraints)

### Quality Standards
- **Testing**: Comprehensive unit tests for all services
- **Documentation**: Bidirectional linking between code and docs
- **Validation**: Automated link checking and file length limits
- **Patterns**: Follow established patterns, don't reinvent

### Key Constraints
- **Database**: Single PostgreSQL database only (hosted on Supabase)
- **Connections**: Use prescribed connection methods only (get_db_connection, get_supabase_client)
- **UI**: No hardcoded colors, use semantic tokens only
- **API**: RLS for all data access, JWT validation required, avoid unnecessary endpoints
- **Agents**: Generic tools configured via database
- **Documentation**: File length limits enforced automatically

## Quick Reference

**Start Development**:
1. Read `memory-bank/README.md` for navigation
2. Check `memory-bank/active-tasks.md` for current work
3. Follow patterns in `memory-bank/patterns/` for implementation
4. Validate with `node memory-bank/tools/link-checker.js`

**Key Files**:
- Navigation: `memory-bank/README.md`
- Tasks: `memory-bank/active-tasks.md`  
- Patterns: `memory-bank/patterns/*.md`
- Rules: `memory-bank/rules/*.json`
- Schemas: `memory-bank/schemas/*.sql` 