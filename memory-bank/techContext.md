# Tech Context

> **⚠️ IMPORTANT**: This file has been restructured. For current implementation patterns and constraints, see [`README.md`](README.md) and the organized pattern files.

## Quick Navigation

### 🎯 **Current Tech Stack & Patterns**
**Primary Source**: [`README.md`](README.md) - Contains up-to-date navigation and quick rules

### 🎨 **Frontend (`webApp/`)**
- **Patterns**: [`patterns/ui-patterns.md`](patterns/ui-patterns.md)
- **Rules**: [`rules/ui-rules.json`](rules/ui-rules.json)
- **Stack**: React 18+, Radix UI Themes + Primitives, TailwindCSS, Zustand, React Query, Vite
- **Key Constraints**: Semantic colors only, centralized overlays, React Query hooks

### 🔧 **Backend (`chatServer/`)**
- **Patterns**: [`patterns/api-patterns.md`](patterns/api-patterns.md)
- **Rules**: [`rules/api-rules.json`](rules/api-rules.json)
- **Stack**: FastAPI, PostgreSQL (Supabase), Service layer architecture
- **Key Constraints**: Single DB, prescribed connections only, avoid unnecessary endpoints

### 🤖 **Agent (`src/core/`)**
- **Patterns**: [`patterns/agent-patterns.md`](patterns/agent-patterns.md)
- **Rules**: [`rules/agent-rules.json`](rules/agent-rules.json)
- **Stack**: LangChain, PostgresChatMessageHistory, Generic CRUD tools
- **Key Constraints**: CRUD from DB config, avoid hardcoded tools

### 📊 **Database (`supabase/`)**
- **Patterns**: [`patterns/data-patterns.md`](patterns/data-patterns.md)
- **Rules**: [`rules/data-rules.json`](rules/data-rules.json)
- **Stack**: PostgreSQL, Supabase migrations, Row Level Security
- **Key Constraints**: Migrations only, RLS with `is_record_owner`, consistent naming

## Core Architecture Principles

### 1. **Modular Organization**
- Clear separation between frontend, backend, agents, and database
- Each area has dedicated pattern files with DO/DON'T examples
- Machine-readable rules for automated validation

### 2. **Established Patterns**
- **40 total patterns** with concrete implementation examples
- **40 total rules** for automated constraint checking
- **Emergency rules**: Read entire files, follow patterns, test changes

### 3. **Documentation Strategy**
- **Pattern files**: Implementation examples with DO/DON'T
- **Rule files**: Machine-readable constraints
- **README.md**: Navigation and quick reference
- **File limits**: All files under 400 lines for maintainability

## Current System Status

### ✅ **Implemented & Documented**
- **Memory System**: PostgreSQL-based STM/LTM with chat history
- **Agent Orchestration**: Executor caching, session management
- **UI Foundation**: Radix + Tailwind with assistant-ui integration
- **Database Layer**: Connection pooling, RLS, migrations
- **Authentication**: Supabase OAuth integration

### 🔄 **In Progress (Clarity v2)**
- **External API Integration**: Google Calendar, Gmail, Slack
- **Real-time Sync**: WebSocket-based state synchronization
- **AI Agents**: Slack Digest, Reply Drafter, Auto-Scheduler
- **Notes Interface**: Voice input, mobile responsive

## Migration from Legacy Documentation

This file previously contained detailed technical specifications that have been:

1. **Reorganized** into focused pattern files by area
2. **Updated** to reflect current implementation reality
3. **Validated** against actual codebase state
4. **Structured** for AI agent consumption

### For Historical Context
- **Legacy content**: Archived in `archive/deprecated-patterns/`
- **Migration summary**: See `CONSOLIDATION_COMPLETE.md`
- **Validation status**: All checks passing per README.md

## Usage Guidelines

### For AI Agents
1. **Start with README.md** for navigation
2. **Read relevant pattern file** for your work area
3. **Check rule file** for constraints
4. **Follow emergency rules** for all changes

### For Developers
1. **Consult pattern files** before implementing
2. **Update patterns** when adding new approaches
3. **Run validation** with `npm run docs:check-all`
4. **Keep files under 400 lines** for maintainability

---

**Last Updated**: 2025-01-27  
**Status**: ✅ Aligned with current implementation  
**Validation**: All pattern files and rules verified against codebase 