# Database Patterns — Full Reference

## 1. Row Level Security (RLS)

Every user-scoped table MUST have RLS enabled using the `is_record_owner()` helper:

```sql
-- Helper function (already exists, created once)
CREATE OR REPLACE FUNCTION public.is_record_owner(record_user_id uuid)
RETURNS boolean
LANGUAGE sql SECURITY DEFINER SET search_path = public
AS $$ SELECT auth.uid() = record_user_id; $$;

-- Apply to every user table:
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on my_table"
ON my_table FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));
```

**Never skip RLS. Never hardcode `auth.uid()` in every policy — use `is_record_owner()`.**

### Testing RLS

```sql
SET ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub":"user-uuid", "role":"authenticated"}', true);
SELECT * FROM my_table;  -- Should only return that user's rows
```

## 2. Consistent Table Structure

Every table follows this template:

```sql
CREATE TABLE example_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- domain columns here --
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
```

**Required columns:** `id` (UUID), `user_id` (FK to auth.users with CASCADE), `created_at`, `updated_at`.

**Naming:** snake_case for tables and columns. No camelCase. No SERIAL — use UUID.

## 3. Migration-Only Schema Changes

All schema changes go through Supabase migrations in `supabase/migrations/`:

```sql
-- supabase/migrations/20250601_add_priority_to_tasks.sql
ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 1;
CREATE INDEX idx_tasks_priority ON tasks(priority);
COMMENT ON COLUMN tasks.priority IS 'Task priority level (1-5)';
```

**Never modify schema directly in production. Never skip the migration system.**

## 4. JSONB for Flexible Configuration

```sql
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Example config:
INSERT INTO agent_tools (name, config) VALUES
('create_task', '{
    "table_name": "tasks",
    "method": "create",
    "field_map": {"task_title": "title"}
}');
```

**Use JSONB for flexible/dynamic data. Don't create separate key-value tables.**

## 5. Foreign Key Constraints

```sql
-- ✅ Always use proper FK with CASCADE
user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE

-- ❌ Never skip constraints
user_id UUID  -- No FK, no NOT NULL
```

## 6. Timestamps with Auto-Update Trigger

```sql
-- Create trigger function (once per database)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to each table
CREATE TRIGGER update_example_table_updated_at
BEFORE UPDATE ON example_table
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 7. Index Strategy

```sql
-- User-scoped queries (most common pattern)
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);

-- Agent-specific queries
CREATE INDEX idx_agent_tools_user_agent ON agent_tools(user_id, agent_name);

-- JSONB queries
CREATE INDEX idx_agent_tools_config_gin ON agent_tools USING GIN(config);
```

**Index columns used in WHERE clauses. Use GIN for JSONB. Don't over-index.**

## 8. Data Access in Python

```python
# ✅ RLS handles filtering — no manual user_id filter needed
result = await db.table("tasks").select("*").execute()

# ✅ Use connection pooling via prescribed methods
from chatServer.database.connection import get_db_connection
from chatServer.database.supabase_client import get_supabase_client

# ❌ Never create new connections
import psycopg
conn = psycopg.connect(DATABASE_URL)  # Bypasses pool
```

## 9. Schema Documentation

```sql
COMMENT ON TABLE agent_tools IS 'Configuration-driven tools for agents';
COMMENT ON COLUMN agent_tools.config IS 'JSONB configuration defining tool behavior';
COMMENT ON CONSTRAINT unique_user_agent_tool ON agent_tools
IS 'Ensures unique tool names per user/agent combination';
```

**Document every table, non-obvious column, and constraint.**

## 10. Migration and RLS Testing

### Testing Migrations Apply Cleanly

```bash
# Reset and re-apply all migrations (test environment only)
supabase db reset

# Verify a specific migration
supabase migration up --include-all
```

### Testing RLS Policies

Test that RLS correctly restricts access by simulating different users:

```sql
-- Test as authenticated user (owner)
SET ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub":"user-uuid-1", "role":"authenticated"}', true);
INSERT INTO notifications (user_id, title, body, category)
VALUES ('user-uuid-1', 'Test', 'Body', 'info');
-- Should succeed (owner)

-- Verify owner can read their own rows
SELECT * FROM notifications;
-- Should return only user-uuid-1's rows

-- Test as different user (non-owner)
SELECT set_config('request.jwt.claims', '{"sub":"user-uuid-2", "role":"authenticated"}', true);
SELECT * FROM notifications;
-- Should return empty (not owner)

-- Test UPDATE restriction
UPDATE notifications SET read = true WHERE user_id = 'user-uuid-1';
-- Should affect 0 rows (non-owner)
```

### Testing RLS in Python

```python
@pytest.mark.asyncio
async def test_rls_restricts_to_owner(supabase_client_user1, supabase_client_user2):
    # User 1 creates a notification
    await supabase_client_user1.table("notifications").insert({
        "user_id": "user-1", "title": "Test", "body": "Body", "category": "info"
    }).execute()

    # User 2 should not see it
    result = await supabase_client_user2.table("notifications").select("*").execute()
    assert len(result.data) == 0
```
