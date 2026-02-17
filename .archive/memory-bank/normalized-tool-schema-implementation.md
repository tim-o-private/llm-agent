# Normalized Tool Schema Implementation

## Overview

We've implemented a normalized database schema for tools that addresses the fundamental issues with the previous design:

### Previous Issues
1. **No uniqueness constraint** on tool names - unmanageable duplicates
2. **No reusability** - each agent needed its own tool config copy  
3. **Maintenance nightmare** - updating a tool required updating every agent

### New Architecture

**Pattern**: `agents -> agent_tools -> tools` (following `<parent>_<children>` convention)

```sql
-- Tools registry (reusable tool definitions)
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,  -- e.g., 'gmail_digest', 'gmail_search'
    type agent_tool_type NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent-tool linking table (many-to-many with overrides)
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_configurations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    config_override JSONB DEFAULT '{}',  -- Agent-specific config overrides
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Key Benefits

### 1. **Reusability**
- Tools defined once in `tools` table
- Multiple agents can use the same tool
- No duplication of tool definitions

### 2. **Maintainability** 
- Update tool definition in one place
- All agents using that tool get the update
- Agent-specific overrides when needed

### 3. **Proper Constraints**
- `UNIQUE(name)` on tools table prevents duplicates
- Partial unique index on `agent_tools(agent_id, tool_id) WHERE is_deleted = FALSE` handles soft deletes
- Foreign key constraints ensure data integrity

### 4. **Soft Delete Support**
- Both tables have `is_deleted` columns
- Partial unique indexes only apply to non-deleted records
- Allows "undeleting" records without constraint violations

### 5. **Security**
- Service role only access via RLS policies
- No direct user access to tool configurations

## Migration Strategy

### Phase 1: Schema Creation
```sql
-- 1. Create new tables (tools, agent_tools)
-- 2. Create indexes and constraints
-- 3. Set up RLS policies
-- 4. Create triggers for updated_at
```

### Phase 2: Data Migration
```sql
-- 1. Extract unique tools from current agent_tools -> tools
-- 2. Rename current agent_tools -> agent_tools_backup  
-- 3. Create new agent_tools as linking table
-- 4. Populate linking table from backup
```

### Phase 3: Code Updates
- Updated `agent_loader_db.py` to use normalized schema
- Added JOIN query to get complete tool information
- Config merging: `tools.config` + `agent_tools.config_override`

### Phase 4: Testing
- New test data using normalized schema
- Integration tests with agent loading
- Verification of tool reusability

## Files Created/Modified

### Database Migrations
- `supabase/migrations/20250129000000_normalize_tool_schema.sql` - Complete migration
- `tests/fixtures/test_email_digest_agent_normalized.sql` - Test data for new schema

### Code Updates  
- `src/core/agent_loader_db.py` - Updated to use normalized schema with JOIN queries
- `tests/fixtures/tool-linking-schema.sql` - Schema design document

### Documentation
- `memory-bank/normalized-tool-schema-implementation.md` - This document

## Testing Strategy

### 1. **Schema Migration Testing**
```bash
# Run migration on development database
source .env && psql $SUPABASE_PGURL -f supabase/migrations/20250129000000_normalize_tool_schema.sql

# Verify tables created correctly
psql $SUPABASE_PGURL -c "\d tools"
psql $SUPABASE_PGURL -c "\d agent_tools"
```

### 2. **Test Data Creation**
```bash
# Create test agent with Gmail tools using new schema
source .env && psql $SUPABASE_PGURL -f tests/fixtures/test_email_digest_agent_normalized.sql
```

### 3. **Integration Testing**
```python
# Test agent loading with normalized schema
from src.core.agent_loader_db import load_agent_executor_db

agent_executor = load_agent_executor_db(
    agent_name="test_email_digest_agent",
    user_id="test-user-id",
    session_id="test-session-id"
)

# Verify tools loaded correctly
assert len(agent_executor.tools) == 2
assert any(tool.name == "gmail_digest" for tool in agent_executor.tools)
assert any(tool.name == "gmail_search" for tool in agent_executor.tools)
```

### 4. **Tool Reusability Testing**
```sql
-- Create second agent using same tools
INSERT INTO agent_configurations (agent_name, system_prompt, llm_config)
VALUES ('test_agent_2', 'Another test agent', '{"model": "gpt-4"}');

-- Assign same tools to second agent (reusability test)
INSERT INTO agent_tools (agent_id, tool_id, is_active)
SELECT 
    (SELECT id FROM agent_configurations WHERE agent_name = 'test_agent_2'),
    t.id,
    true
FROM tools t
WHERE t.name IN ('gmail_digest', 'gmail_search');
```

## Next Steps

### 1. **Run Migration** (Current Priority)
```bash
source .env && psql $SUPABASE_PGURL -f supabase/migrations/20250129000000_normalize_tool_schema.sql
```

### 2. **Create Test Data**
```bash
source .env && psql $SUPABASE_PGURL -f tests/fixtures/test_email_digest_agent_normalized.sql
```

### 3. **Integration Testing**
- Test agent loading with new schema
- Verify Gmail tools integration
- Test config override functionality

### 4. **Production Deployment**
- Backup current database
- Run migration on production
- Verify all agents load correctly
- Drop backup table after verification

## Rollback Plan

If issues arise:
1. **Restore from backup**: `ALTER TABLE agent_tools_backup RENAME TO agent_tools;`
2. **Drop new tables**: `DROP TABLE tools CASCADE;`
3. **Revert code changes**: Git revert agent_loader_db.py changes

## Success Criteria

- ✅ **Schema Migration**: New tables created successfully
- ✅ **Data Migration**: All existing tools migrated without loss
- ✅ **Code Integration**: Agent loader works with new schema
- ✅ **Tool Reusability**: Multiple agents can share tools
- ✅ **Config Overrides**: Agent-specific customizations work
- ✅ **Soft Deletes**: Proper constraint handling with is_deleted
- ✅ **Security**: Service role only access enforced

## Impact Assessment

### Positive Impacts
- **Reduced Storage**: No tool definition duplication
- **Easier Maintenance**: Single source of truth for tools
- **Better Performance**: Proper indexing and constraints
- **Improved Security**: Centralized access control

### Breaking Changes
- **Database Schema**: Complete restructure of tool storage
- **Agent Loader**: Updated to use JOIN queries
- **Test Data**: New format required for testing

### Migration Effort
- **Database**: ~30 minutes (schema + data migration)
- **Code**: ~2 hours (agent loader updates + testing)
- **Testing**: ~4 hours (comprehensive integration testing)
- **Total**: ~6.5 hours for complete migration

This normalized schema provides a solid foundation for scalable tool management while maintaining backward compatibility through the migration strategy. 