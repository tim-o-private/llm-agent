# Memory Bank Navigation

> **For AI Agents**: Read exactly what you need for your task. No more hunting.

## Quick Start by Area

### 🎨 Frontend (`webApp/`)
**Read**: [`patterns/ui-patterns.md`](patterns/ui-patterns.md) → [`rules/ui-rules.json`](rules/ui-rules.json)
**Quick Rules**: Radix primitives + Tailwind, semantic colors only, React Query hooks, centralized overlays

### 🔧 Backend (`chatServer/`)
**Read**: [`patterns/api-patterns.md`](patterns/api-patterns.md) → [`rules/api-rules.json`](rules/api-rules.json)
**Quick Rules**: Single PostgreSQL DB, prescribed connections only, service layer, avoid unnecessary endpoints

### 🤖 Agent (`src/core/`)
**Read**: [`patterns/agent-patterns.md`](patterns/agent-patterns.md) → [`rules/agent-rules.json`](rules/agent-rules.json)
**Quick Rules**: Generic LangChain tools, CRUD from DB config, PostgresChatMessageHistory

### 📊 Database (`supabase/`)
**Read**: [`patterns/data-patterns.md`](patterns/data-patterns.md) → [`schemas/database-schema.sql`](schemas/database-schema.sql)
**Quick Rules**: Migrations only, RLS with `is_record_owner`, consistent naming

## Core Files

- [`project-context.md`](project-context.md) - Project vision, architecture, tech stack
- [`active-tasks.md`](active-tasks.md) - Current tasks only (no history)

## Pattern Files (Implementation Examples)

- [`patterns/ui-patterns.md`](patterns/ui-patterns.md) - Frontend DO/DON'T examples
- [`patterns/api-patterns.md`](patterns/api-patterns.md) - Backend DO/DON'T examples  
- [`patterns/data-patterns.md`](patterns/data-patterns.md) - Database DO/DON'T examples
- [`patterns/agent-patterns.md`](patterns/agent-patterns.md) - Agent DO/DON'T examples

## Rule Files (Machine-Readable)

- [`rules/ui-rules.json`](rules/ui-rules.json) - Enforceable UI rules
- [`rules/api-rules.json`](rules/api-rules.json) - Enforceable API rules
- [`rules/data-rules.json`](rules/data-rules.json) - Enforceable DB rules
- [`rules/agent-rules.json`](rules/agent-rules.json) - Enforceable agent rules

## Schema Files (Current State)

- [`schemas/database-schema.sql`](schemas/database-schema.sql) - Current DDL
- [`schemas/api-types.ts`](schemas/api-types.ts) - API type definitions
- [`schemas/ui-types.ts`](schemas/ui-types.ts) - UI component types

## Agent Workflow

1. **Identify work area** (webApp, chatServer, src/core, supabase)
2. **Read pattern file** for implementation examples
3. **Check rule file** for constraints
4. **Reference schemas** for types/structure
5. **Update active-tasks.md** with progress

## Emergency Rules

1. **Read entire files** before making changes
2. **Follow established patterns** - don't reinvent
3. **Use existing types/schemas** - don't duplicate
4. **Test changes** before marking complete
5. **Update docs** if you change patterns

## Getting Help

- **Missing pattern?** Check [`archive/deprecated-patterns/`](archive/deprecated-patterns/)
- **Pattern outdated?** Update in [`active-tasks.md`](active-tasks.md)
- **Need new pattern?** Add to appropriate pattern file
- **Rule conflicts?** Escalate to human

## Validation

Run `npm run docs:check-all` to validate:
- File length limits
- Bidirectional links
- Rule references
- Unused files

## Status ✅

- **File Limits**: All files under 400 lines
- **Links**: No broken references in active docs
- **Patterns**: 40 total patterns with DO/DON'T examples
- **Rules**: 40 total machine-readable rules
- **@docs Headers**: Added to key implementation files
- **Legacy Content**: Safely archived (12 files, ~60KB)
- **Validation**: All checks passing 