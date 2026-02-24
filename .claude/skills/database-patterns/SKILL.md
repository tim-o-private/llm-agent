---
name: database-patterns
description: PostgreSQL and Supabase database patterns. Use when writing SQL migrations, creating tables, modifying schemas, or working with data access code. Covers RLS with is_record_owner(), table structure, migrations, JSONB, indexes, timestamps, and schema documentation.
---

# Database Patterns

## Core Rule

All data lives in one PostgreSQL database on Supabase. No SQLite, Redis, MongoDB, or additional data stores.

## Step 0: Read the Current Schema

Before any database work, read `supabase/schema.sql` — this is the **single source of truth** for the current production DDL. It contains all tables, functions, indexes, RLS policies, and comments in one file.

If the file is missing or stale, regenerate it:
```bash
./scripts/dump-schema.sh
```

**Always check the existing schema before creating new tables or columns.** The schema file prevents duplicating existing structures or misunderstanding current column types/constraints.

## Quick Checklist

Before writing database code, verify:
- [ ] RLS enabled with `is_record_owner()` policy
- [ ] UUID primary key with `gen_random_uuid()`
- [ ] `user_id` FK to `auth.users(id) ON DELETE CASCADE`
- [ ] `created_at` and `updated_at` TIMESTAMPTZ columns
- [ ] Auto-update trigger on `updated_at`
- [ ] Schema change is in a migration file under `supabase/migrations/`
- [ ] Indexes on user_id and common query columns
- [ ] Agent references use `agent_id UUID FK` → `agent_configurations(id)`, NOT `agent_name TEXT`
- [ ] JSONB for flexible config (not key-value tables)
- [ ] Table and column COMMENT statements
- [ ] snake_case naming throughout

## Table Template (Quick Copy)

```sql
CREATE TABLE example_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT unique_user_example UNIQUE (user_id, name)
);

ALTER TABLE example_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on example_table"
ON example_table FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE INDEX idx_example_table_user ON example_table(user_id);

CREATE TRIGGER update_example_table_updated_at
BEFORE UPDATE ON example_table
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE example_table IS 'Description of what this table stores';
```

## Migration Timestamp Uniqueness

Migration files are named `YYYYMMDDHHMMSS_descriptive_name.sql`. When agents work in parallel worktrees, timestamp collisions cause merge failures.

**Rules:**
1. **Never invent a prefix.** Use the one assigned by the orchestrator in the task contract.
2. If no prefix was assigned, derive the next available one from existing migrations:
   ```bash
   ls supabase/migrations/ | grep -oP '^\d{14}' | sort | tail -1
   ```
   Then increment by 1.
3. The `validate-patterns.sh` hook will warn if a collision is detected against the main repo.

## Key Gotchas

1. **PostgREST upsert** — Supabase PostgREST `ON CONFLICT` requires a real UNIQUE constraint (not partial unique indexes). Use select-then-insert if needed.
2. **PostgREST function overloads** — PostgREST can't disambiguate overloaded SQL functions (same name, different arg counts). When adding a new overload of a function called via PostgREST, **drop the old signature in the same migration**. Leaving both causes PGRST203 errors at runtime.
3. **`ON CONFLICT DO UPDATE` must include `type`** — Upserts on the `tools` table must include `type = EXCLUDED.type` in the SET clause. Omitting it leaves stale `type` values (e.g., `CRUDTool` instead of `CreateTaskTool`), silently breaking tool loading. The `validate-patterns.sh` hook enforces this.
4. **Service-role key bypasses RLS** — The `service_role` key used by backend services bypasses all RLS policies. User data isolation is enforced at the API layer via `UserScopedClient` (SPEC-017), with RLS as defense-in-depth. Never use raw `get_supabase_client` in services — use `get_user_scoped_client` or `get_system_client`.

## Detailed Reference

For full patterns with examples (RLS testing, JSONB config, index strategy, data access in Python), see [reference.md](reference.md).
