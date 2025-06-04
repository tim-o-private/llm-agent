# System Patterns

> **⚠️ IMPORTANT**: This file has been restructured. System patterns are now organized in dedicated pattern files by area. See [`README.md`](README.md) for navigation.

## Current Pattern Organization

### 📁 **Pattern Files by Area**
- **Frontend**: [`patterns/ui-patterns.md`](patterns/ui-patterns.md) - React, Radix UI, TailwindCSS patterns
- **Backend**: [`patterns/api-patterns.md`](patterns/api-patterns.md) - FastAPI, service layer patterns  
- **Agents**: [`patterns/agent-patterns.md`](patterns/agent-patterns.md) - LangChain, CRUD tool patterns
- **Database**: [`patterns/data-patterns.md`](patterns/data-patterns.md) - PostgreSQL, migration patterns

### 🔧 **Machine-Readable Rules**
- **Frontend**: [`rules/ui-rules.json`](rules/ui-rules.json) - Automated UI constraints
- **Backend**: [`rules/api-rules.json`](rules/api-rules.json) - Automated API constraints
- **Agents**: [`rules/agent-rules.json`](rules/agent-rules.json) - Automated agent constraints  
- **Database**: [`rules/data-rules.json`](rules/data-rules.json) - Automated DB constraints

## System-Wide Architectural Principles

### 1. **Separation of Concerns**
- **Frontend (`webApp/`)**: React UI with Radix + Tailwind
- **Backend (`chatServer/`)**: FastAPI service layer
- **Agents (`src/core/`)**: LangChain-based AI agents
- **Database (`supabase/`)**: PostgreSQL with RLS

### 2. **Established Integration Patterns**
- **State Management**: Zustand (client) + React Query (server)
- **Authentication**: Supabase OAuth with RLS
- **Memory System**: PostgreSQL-based STM/LTM
- **Agent Orchestration**: Executor caching with session management

### 3. **Documentation Strategy**
- **40 total patterns** with DO/DON'T examples
- **40 total rules** for automated validation
- **File limits**: All files under 400 lines
- **Validation**: `npm run docs:check-all`

## Migration from Legacy Content

This file previously contained high-level architectural diagrams and patterns that have been:

1. **Distributed** into area-specific pattern files
2. **Enhanced** with concrete DO/DON'T examples
3. **Validated** against current codebase implementation
4. **Structured** for both human and AI agent consumption

### For Historical Context
- **Legacy diagrams**: Available in `archive/deprecated-patterns/`
- **Migration details**: See `CONSOLIDATION_COMPLETE.md`
- **Current status**: All patterns validated and organized

## Usage Guidelines

### For System-Wide Changes
1. **Check multiple pattern files** if change spans areas
2. **Update relevant rule files** for new constraints
3. **Validate with automated checks** before committing
4. **Document cross-cutting concerns** in appropriate pattern files

### For Architecture Decisions
1. **Consult existing patterns** before designing new approaches
2. **Follow established integration patterns** between areas
3. **Update pattern files** when introducing new architectural decisions
4. **Maintain consistency** with documented principles

---

**Last Updated**: 2025-01-27  
**Status**: ✅ Restructured and aligned with current organization  
**Primary Reference**: [`README.md`](README.md) for navigation and quick rules 