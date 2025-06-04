# Memory Bank Navigation Guide

> **For AI Agents**: This file tells you exactly what to read for your current task. No more hunting through multiple files.

## Quick Start by Project Area

### 🎨 Frontend Development (`webApp/`)
**Read these files in order:**
1. `patterns/ui-patterns.md` - All UI implementation patterns
2. `rules/ui-rules.json` - Enforceable UI rules
3. `schemas/ui-types.ts` - Component type definitions

**Quick Rules:**
- Use Radix UI primitives + Tailwind CSS
- Follow accessibility patterns (WCAG 2.1 AA)
- Use semantic color tokens only (no hardcoded colors)
- Implement consistent error/loading states

### 🔧 Backend Development (`chatServer/`)
**Read these files in order:**
1. `patterns/api-patterns.md` - All API implementation patterns  
2. `rules/api-rules.json` - Enforceable API rules
3. `schemas/database-schema.sql` - Current database schema
4. `schemas/api-types.ts` - API type definitions

**Quick Rules:**
- Use FastAPI with Pydantic models
- Validate JWT tokens for authentication
- Follow RLS patterns for data access
- Use dependency injection for database connections

### 🤖 Agent Development (`src/core/`)
**Read these files in order:**
1. `patterns/agent-patterns.md` - All agent implementation patterns
2. `rules/agent-rules.json` - Enforceable agent rules
3. `schemas/database-schema.sql` - Database schema for tools

**Quick Rules:**
- Use generic LangChain tool calling (not OpenAI-specific)
- Follow CRUD tool patterns from database config
- Validate message formatting for tool calls
- Use `PostgresChatMessageHistory` for memory

### 📊 Database Work (`supabase/migrations/`)
**Read these files in order:**
1. `patterns/data-patterns.md` - Database and RLS patterns
2. `rules/data-rules.json` - Enforceable data rules
3. `schemas/database-schema.sql` - Current schema reference

**Quick Rules:**
- All DDL changes via Supabase migrations
- Implement RLS using `public.is_record_owner` helper
- Use consistent naming conventions
- Test RLS policies thoroughly

## File Descriptions

### Core Files
- `project-context.md` - Project vision, architecture, tech stack
- `active-tasks.md` - Current tasks only (no completed tasks)

### Pattern Files (Implementation Guidance)
- `patterns/ui-patterns.md` - Frontend component patterns
- `patterns/api-patterns.md` - Backend API patterns
- `patterns/data-patterns.md` - Database and RLS patterns
- `patterns/agent-patterns.md` - Agent tool patterns

### Rule Files (Machine-Readable)
- `rules/ui-rules.json` - Structured UI rules
- `rules/api-rules.json` - Structured API rules
- `rules/data-rules.json` - Structured database rules
- `rules/agent-rules.json` - Structured agent rules

### Schema Files (Current State)
- `schemas/database-schema.sql` - Current database DDL
- `schemas/api-types.ts` - API type definitions
- `schemas/ui-types.ts` - UI component types

### Archive (Historical)
- `archive/completed-tasks/` - Completed task history
- `archive/deprecated-patterns/` - Old patterns for reference
- `archive/chat-history/` - Historical conversations

## Agent Workflow

1. **Identify your work area** (webApp, chatServer, src/core, supabase)
2. **Read the relevant pattern file** for implementation guidance
3. **Check the rule file** for enforceable constraints
4. **Reference schema files** for current types/structure
5. **Update active-tasks.md** with your progress

## Emergency Rules (Always Apply)

1. **Read entire files** before making changes
2. **Follow established patterns** - don't reinvent
3. **Use existing types/schemas** - don't duplicate
4. **Test your changes** before marking complete
5. **Update documentation** if you change patterns

## Getting Help

- **Can't find a pattern?** Check if it exists in the archive first
- **Pattern seems outdated?** Propose updates in active-tasks.md
- **Need new pattern?** Document it in the appropriate pattern file
- **Conflicting rules?** Escalate to human for clarification 