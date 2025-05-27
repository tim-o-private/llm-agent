# Data Patterns

**Files**: [`20250520_agent_memory_v2_schemas.sql`](../supabase/migrations/20250520_agent_memory_v2_schemas.sql) [`connection.py`](../chatServer/database/connection.py)
**Rules**: [data-001](../rules/data-rules.json#data-001) [data-002](../rules/data-rules.json#data-002) [data-003](../rules/data-rules.json#data-003)

## Pattern 1: Single Database Principle

```sql
-- ✅ DO: Use PostgreSQL on Supabase for all data
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ❌ DON'T: Create additional databases
-- SQLite for local storage
-- Redis for caching
-- MongoDB for documents
```

## Pattern 2: Row Level Security (RLS) Pattern

```sql
-- ✅ DO: Create reusable RLS helper function (once per database)
CREATE OR REPLACE FUNCTION public.is_record_owner(record_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT auth.uid() = record_user_id;
$$;

-- ✅ DO: Apply consistent RLS pattern to all user tables
-- Step 1: Enable RLS
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Step 2: Create policy using helper function
CREATE POLICY "Enable full access for record owners on tasks"
ON tasks
FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

-- ✅ DO: Apply same pattern to other tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on projects"
ON projects
FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

-- ✅ DO: Test RLS policies in SQL editor
SET ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub":"user-uuid", "role":"authenticated"}', true);
SELECT * FROM tasks; -- Should only return user's tasks

-- ✅ DO: Use migrations for all RLS changes
-- supabase/migrations/20250101_setup_rls_tasks.sql
-- Contains the above RLS setup

-- ❌ DON'T: Hardcode auth.uid() in every policy
CREATE POLICY "bad_policy" ON tasks USING (auth.uid() = user_id);

-- ❌ DON'T: Rely on application-level filtering only
-- No RLS policies, manual user_id filtering in code

-- ❌ DON'T: Skip testing RLS policies
-- Deploy without verifying user isolation works
```

## Pattern 3: Consistent Table Structure

```sql
-- ✅ DO: Follow consistent naming and structure
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Standard columns: id, user_id, created_at, updated_at
-- Foreign key to auth.users with CASCADE
-- JSONB for flexible configuration

-- ❌ DON'T: Inconsistent naming or missing standard columns
CREATE TABLE tools (
    tool_id SERIAL PRIMARY KEY,  -- Inconsistent ID type
    userId TEXT,                 -- No foreign key constraint
    toolName VARCHAR(50),        -- Inconsistent naming
    settings TEXT                -- No created_at/updated_at
);
```

## Pattern 4: Migration-Only Schema Changes

```sql
-- ✅ DO: All schema changes through migrations
-- supabase/migrations/20250101_add_priority_to_tasks.sql
ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 1;

CREATE INDEX idx_tasks_priority ON tasks(priority);

COMMENT ON COLUMN tasks.priority IS 'Task priority level (1-5)';

-- ❌ DON'T: Direct database modifications
-- Manual ALTER TABLE in production
-- Schema changes outside migration system
```

## Pattern 5: JSONB Configuration Pattern

```sql
-- ✅ DO: Use JSONB for flexible configuration
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Example config:
INSERT INTO agent_tools (name, config) VALUES 
('create_task', {
    "table_name": "tasks",
    "method": "create",
    "field_map": {"task_title": "title", "task_desc": "description"},
    "validation": {"title": {"required": true, "max_length": 100}}
});

-- ❌ DON'T: Separate tables for configuration
CREATE TABLE tool_configs (
    tool_id UUID REFERENCES agent_tools(id),
    config_key TEXT,
    config_value TEXT
);
```

## Pattern 6: Proper Foreign Key Constraints

```sql
-- ✅ DO: Use proper foreign key constraints with CASCADE
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ❌ DON'T: Missing or weak foreign key constraints
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- No foreign key constraint
    agent_name TEXT
);
```

## Pattern 7: Timestamp and Audit Patterns

```sql
-- ✅ DO: Include audit timestamps with triggers
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Auto-update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ❌ DON'T: Missing audit timestamps
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL
    -- No created_at or updated_at
);
```

## Pattern 8: Index Strategy

```sql
-- ✅ DO: Create indexes for common query patterns
-- User-scoped queries (most common)
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);

-- Agent-specific queries
CREATE INDEX idx_agent_tools_user_agent ON agent_tools(user_id, agent_name);

-- JSONB queries
CREATE INDEX idx_agent_tools_config_gin ON agent_tools USING GIN(config);

-- ❌ DON'T: Over-index or under-index
-- No indexes on frequently queried columns
-- Indexes on every column regardless of usage
```

## Pattern 9: Data Access Patterns

```python
# ✅ DO: Let RLS handle filtering automatically
async def get_user_tasks(db: AsyncClient, user_id: str):
    # RLS automatically filters by user_id
    result = await db.table('tasks').select('*').execute()
    return result.data

# ✅ DO: Use connection pooling
async def get_tasks_with_pool(conn: psycopg.AsyncConnection):
    async with conn.cursor() as cur:
        await cur.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        return await cur.fetchall()

# ❌ DON'T: Manual user_id filtering when RLS exists
async def get_user_tasks_manual(db: AsyncClient, user_id: str):
    # Redundant - RLS already handles this
    result = await db.table('tasks').select('*').eq('user_id', user_id).execute()
    return result.data

# ❌ DON'T: Create new connections
import psycopg
conn = psycopg.connect(DATABASE_URL)  # Bypasses pool
```

## Pattern 10: Schema Documentation

```sql
-- ✅ DO: Document tables and columns
COMMENT ON TABLE agent_tools IS 'Configuration-driven tools for agents';
COMMENT ON COLUMN agent_tools.config IS 'JSONB configuration defining tool behavior';
COMMENT ON COLUMN agent_tools.agent_name IS 'Agent identifier (e.g., "assistant", "architect")';

-- Document constraints
COMMENT ON CONSTRAINT unique_user_agent_tool ON agent_tools 
IS 'Ensures unique tool names per user/agent combination';

-- ❌ DON'T: Undocumented schema
CREATE TABLE tools (
    id UUID PRIMARY KEY,
    data JSONB
    -- No comments explaining purpose or structure
);
```

## Complete Examples

### Table Creation with Full Pattern
```sql
-- Complete table following all patterns
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT unique_user_agent_prefs UNIQUE (user_id, agent_name)
);

-- Enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Users can manage own preferences"
ON user_preferences
FOR ALL
USING (is_record_owner(user_id))
WITH CHECK (is_record_owner(user_id));

-- Create indexes
CREATE INDEX idx_user_preferences_user_agent ON user_preferences(user_id, agent_name);
CREATE INDEX idx_user_preferences_config_gin ON user_preferences USING GIN(preferences);

-- Create update trigger
CREATE TRIGGER update_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add documentation
COMMENT ON TABLE user_preferences IS 'User-specific preferences for agent behavior';
COMMENT ON COLUMN user_preferences.preferences IS 'JSONB object containing preference settings';
COMMENT ON CONSTRAINT unique_user_agent_prefs ON user_preferences 
IS 'One preference set per user/agent combination';
```

### Data Access Service
```python
# chatServer/services/data_service.py
from typing import List, Optional
from supabase import AsyncClient
import psycopg

class DataService:
    def __init__(self, db: AsyncClient, pg_conn: psycopg.AsyncConnection):
        self.db = db  # For Supabase operations
        self.pg_conn = pg_conn  # For direct PostgreSQL operations
    
    async def create_with_rls(self, table: str, data: dict) -> dict:
        """Create record - RLS handles user scoping automatically"""
        result = await self.db.table(table).insert(data).execute()
        return result.data[0]
    
    async def fetch_with_rls(self, table: str, filters: dict = None) -> List[dict]:
        """Fetch records - RLS handles user scoping automatically"""
        query = self.db.table(table).select('*')
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        result = await query.execute()
        return result.data
    
    async def raw_query(self, sql: str, params: tuple = None) -> List[dict]:
        """Direct PostgreSQL query using connection pool"""
        async with self.pg_conn.cursor() as cur:
            await cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description]
            rows = await cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
```

## Quick Reference

**Database Rules**:
- Single PostgreSQL database on Supabase only
- All schema changes through migrations
- RLS enabled on all user-scoped tables
- Consistent table structure (id, user_id, created_at, updated_at)

**RLS Patterns**:
- `USING (auth.uid() = user_id)` for user-scoped access
- `WITH CHECK (auth.uid() = user_id)` for user-scoped writes
- Use `is_record_owner()` helper function for complex checks

**Performance**:
- Index on (user_id, created_at DESC) for common queries
- GIN indexes for JSONB columns
- Connection pooling for all database access 