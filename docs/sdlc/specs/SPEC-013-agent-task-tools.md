# SPEC-013: Agent Task Tools

## Status: Implemented (pending migration + deploy)

## Problem

Agents cannot read, create, or modify tasks. The `tasks` table and frontend CRUD are fully built, but no agent tools exist — the LLM has zero visibility into the user's task list. Approval tiers for `create_task`, `get_tasks`, `update_task`, and `delete_task` are pre-registered in `chatServer/security/approval_tiers.py` but have no backing implementation.

This means the agent can't:
- See what's on the user's plate today
- Add a task when the user says "add X to my to-do list"
- Break a task into subtasks
- Mark tasks complete during conversation
- Use task context for coaching or planning

## Design Decision: CRUDTool vs. Dedicated BaseTool Subclasses

The codebase has two tool patterns. This spec must choose one.

### Option A: CRUDTool (DB-configured generic tool)

How it works: A single `CRUDTool` Python class reads its behavior from JSONB config in the `agent_tools` table. Each tool instance is configured with `table_name`, `method` (create/fetch/update/delete), `field_map`, and `runtime_args_schema`. The agent loader dynamically creates Pydantic models for input validation.

Pros:
- No new Python code for basic CRUD — just DB rows
- Adding a new field to a tool = updating a JSONB column, no deploy
- Consistent pattern for simple data operations

Cons:
- **Poor LLM ergonomics** — the agent sees generic `data: dict` and `filters: dict` args. It must guess which keys to pass. Dynamic Pydantic schemas help but are complex to configure correctly in JSONB.
- **No business logic hooks** — CRUDTool does raw insert/select/update/delete. Can't validate `status` transitions, enforce `parent_task_id` consistency, auto-set `position`, or format output for readability.
- **Synchronous** — CRUDTool uses the sync Supabase client (`create_client`), not the shared async client. This blocks the event loop, contrary to the project's async direction (SPEC-011).
- **Hard to test** — each tool's behavior lives in JSONB config + dynamic class generation. Unit testing requires reconstructing the full loader pipeline.
- **Subtask semantics don't fit** — creating a subtask requires setting `parent_task_id` and `subtask_position` relative to siblings. CRUDTool has no concept of "calculate next position" or "validate parent exists."

### Option B: Dedicated BaseTool subclasses (like reminder_tools.py)

How it works: Each tool is a Python class inheriting `BaseTool` with explicit `args_schema`, typed fields, and async `_arun` method. Registered in `TOOL_REGISTRY` and `agent_tools` table.

Pros:
- **Explicit args_schema** — LLM sees named, typed, described parameters (`title: str`, `status: TaskStatus`, `parent_task_id: Optional[str]`). Much better tool-use accuracy.
- **Business logic** — can validate status transitions, auto-calculate position, format output as readable summaries, handle subtask semantics.
- **Async-native** — uses `get_supabase_client()` (shared async client), non-blocking.
- **Testable** — standard pytest with mock DB client.
- **Service layer** — business logic lives in `TaskService`, reusable by future API endpoints.

Cons:
- New Python files per resource (tool + service + tests)
- Adding a field requires a code change + deploy

### Decision: Option B (Dedicated BaseTool subclasses)

Tasks are not a simple CRUD resource — they have hierarchical structure (subtasks), status transitions, position ordering, and rich query needs (filter by date, status, parent). The CRUDTool pattern is appropriate for simple flat-table operations but doesn't fit here.

Additionally, this establishes a **recommended pattern for future tools**: any resource with business logic, relationships, or non-trivial queries should use dedicated BaseTool subclasses with a service layer. CRUDTool remains available for truly generic flat-table CRUD.

### Pattern Guidance (for backend-patterns skill update)

After this spec, update the backend-patterns skill to document when to use each pattern:

| Use CRUDTool when... | Use dedicated BaseTool when... |
|-----------------------|-------------------------------|
| Flat table, no relationships | Hierarchical or relational data |
| No business logic beyond insert/select | Status transitions, computed fields, validation |
| Schema is stable and simple | Rich query filtering (date ranges, status, parent) |
| Tool is low-priority / experimental | Tool is core to agent UX |
| Async is not required | Must be async (event loop safety) |

## Solution

### Functional Unit 1: TaskService

New service encapsulating all task business logic.

**File:** `chatServer/services/task_service.py`

```python
class TaskService:
    def __init__(self, db_client):
        self.db = db_client

    async def list_tasks(self, user_id: str, ...) -> list[dict]
    async def get_task(self, user_id: str, task_id: str) -> dict
    async def create_task(self, user_id: str, ...) -> dict
    async def update_task(self, user_id: str, task_id: str, ...) -> dict
    async def delete_task(self, user_id: str, task_id: str) -> dict
```

Key behaviors:
- `list_tasks`: filter by `status`, `due_date`, `parent_task_id` (null = top-level only). Default: non-deleted, non-completed, ordered by position. Include subtask count.
- `get_task`: return single task with its subtasks nested.
- `create_task`: accept optional `parent_task_id`. Auto-calculate `position` (top-level) or `subtask_position` (subtask) as max+1 among siblings. Validate parent exists if specified.
- `update_task`: support `title`, `description`, `status`, `priority`, `due_date`, `notes`. Validate task belongs to user (RLS handles this). On status change to `completed`, set `completed = true`.
- `delete_task`: soft delete (set `deleted = true`). Cascade to subtasks.

### Functional Unit 2: Agent Tools

Five tools following the `reminder_tools.py` pattern.

**File:** `chatServer/tools/task_tools.py`

| Tool name | Class | Description | Approval tier |
|-----------|-------|-------------|---------------|
| `get_tasks` | `GetTasksTool` | List user's tasks with optional filters | AUTO_APPROVE |
| `get_task` | `GetTaskTool` | Get a single task with its subtasks | AUTO_APPROVE |
| `create_task` | `CreateTaskTool` | Create a task or subtask | USER_CONFIGURABLE (default: AUTO_APPROVE) |
| `update_task` | `UpdateTaskTool` | Update task fields (title, status, priority, etc.) | USER_CONFIGURABLE (default: AUTO_APPROVE) |
| `delete_task` | `DeleteTaskTool` | Soft-delete a task and its subtasks | USER_CONFIGURABLE (default: REQUIRES_APPROVAL) |

#### Tool Schemas

**GetTasksTool** input:
```python
class GetTasksInput(BaseModel):
    status: Optional[str] = Field(None, description="Filter: 'pending', 'in_progress', 'completed', 'skipped', 'deferred'")
    due_date: Optional[str] = Field(None, description="Filter: ISO date string, returns tasks due on or before this date")
    include_completed: bool = Field(False, description="Include completed tasks (excluded by default)")
    include_subtasks: bool = Field(False, description="Include subtasks inline (default: top-level only)")
    limit: int = Field(20, ge=1, le=50, description="Max tasks to return")
```

**GetTaskTool** input:
```python
class GetTaskInput(BaseModel):
    task_id: str = Field(..., description="UUID of the task to retrieve")
```

**CreateTaskTool** input:
```python
class CreateTaskInput(BaseModel):
    title: str = Field(..., description="Task title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Longer description or notes")
    priority: int = Field(2, ge=1, le=5, description="1=lowest, 5=highest")
    due_date: Optional[str] = Field(None, description="Due date as ISO date string (YYYY-MM-DD)")
    status: str = Field("pending", description="Initial status: 'pending' or 'planning'")
    parent_task_id: Optional[str] = Field(None, description="UUID of parent task to create this as a subtask")
    category: Optional[str] = Field(None, description="Category label")
```

**UpdateTaskTool** input:
```python
class UpdateTaskInput(BaseModel):
    task_id: str = Field(..., description="UUID of the task to update")
    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    status: Optional[str] = Field(None, description="New status: pending, planning, in_progress, completed, skipped, deferred")
    priority: Optional[int] = Field(None, ge=1, le=5, description="New priority")
    due_date: Optional[str] = Field(None, description="New due date (YYYY-MM-DD) or empty string to clear")
    notes: Optional[str] = Field(None, description="Additional notes")
    completion_note: Optional[str] = Field(None, description="Note on how/why the task was completed")
```

**DeleteTaskTool** input:
```python
class DeleteTaskInput(BaseModel):
    task_id: str = Field(..., description="UUID of the task to delete")
```

#### Output Formatting

Tools return human-readable text summaries, not raw JSON. Examples:

```
# get_tasks output
You have 4 tasks:

1. [HIGH] Fix login bug (due: Feb 20) — in_progress
   └─ 2 subtasks (1 completed)
2. [MED] Write weekly report (due: Feb 21) — pending
3. [MED] Review PR #45 — pending
4. [LOW] Update docs — deferred

# create_task output
Created task: "Fix login bug" (priority: high, due: 2026-02-20, status: pending)

# update_task output
Updated "Fix login bug": status → completed ✓
```

### Functional Unit 3: Tool Registration

**Migration:** Register tools in `agent_tools` table and add enum values.

```sql
-- Add enum values
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'GetTasksTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'GetTaskTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'CreateTaskTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'UpdateTaskTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'DeleteTaskTool';

-- Register on assistant agent
INSERT INTO agent_tools (agent_id, tool_name, tool_type, tool_config, is_active, "order")
SELECT id, 'get_tasks', 'GetTasksTool', '{}', true, 14
FROM agent_configurations WHERE agent_name = 'assistant';
-- ... (repeat for each tool)
```

**Python:** Add to `TOOL_REGISTRY` in `src/core/agent_loader_db.py`:
```python
from chatServer.tools.task_tools import (
    GetTasksTool, GetTaskTool, CreateTaskTool, UpdateTaskTool, DeleteTaskTool
)

TOOL_REGISTRY: Dict[str, Type] = {
    ...
    "GetTasksTool": GetTasksTool,
    "GetTaskTool": GetTaskTool,
    "CreateTaskTool": CreateTaskTool,
    "UpdateTaskTool": UpdateTaskTool,
    "DeleteTaskTool": DeleteTaskTool,
}
```

**Approval tiers:** Already registered in `approval_tiers.py`. Add `get_task` entry:
```python
"get_task": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
```

### Functional Unit 4: Tests

**File:** `tests/chatServer/tools/test_task_tools.py`
- Test each tool's `_arun` with mocked `TaskService`
- Test input validation (bad status, missing task_id, invalid dates)
- Test output formatting

**File:** `tests/chatServer/services/test_task_service.py`
- Test `list_tasks` filtering (status, due_date, top-level vs subtasks)
- Test `create_task` position auto-calculation
- Test `create_task` with `parent_task_id` (subtask creation)
- Test `update_task` status transition sets `completed` flag
- Test `delete_task` cascades to subtasks
- Test error cases (task not found, invalid parent)

### Functional Unit 5: Documentation Update

Update `backend-patterns` skill with CRUDTool vs. dedicated tool guidance (the table from the Design Decision section above).

## Files

| File | Action | FU |
|------|--------|----|
| `chatServer/services/task_service.py` | Create | 1 |
| `chatServer/tools/task_tools.py` | Create | 2 |
| `supabase/migrations/YYYYMMDDHHMMSS_register_task_tools.sql` | Create | 3 |
| `src/core/agent_loader_db.py` | Modify (add to TOOL_REGISTRY) | 3 |
| `chatServer/security/approval_tiers.py` | Modify (add get_task) | 3 |
| `tests/chatServer/tools/test_task_tools.py` | Create | 4 |
| `tests/chatServer/services/test_task_service.py` | Create | 4 |
| `.claude/skills/backend-patterns/SKILL.md` | Modify | 5 |
| `.claude/skills/backend-patterns/reference.md` | Modify | 5 |

## Execution Order

FU1 (TaskService) → FU2 (Tools, depends on service) → FU3 (Registration) → FU4 (Tests, can partially parallel with FU2-3) → FU5 (Docs)

Database-dev handles FU3 migration. Backend-dev handles FU1 + FU2 + FU4. Reviewer handles FU5 or team lead.

## Testing

1. All existing tests pass
2. New unit tests for TaskService (≥8 test cases)
3. New unit tests for each tool (≥5 test cases per tool)
4. Manual verification: agent can list, create, update, and delete tasks via conversation

## Out of Scope

- Task reordering via agent (drag-drop is a UI concern)
- Focus session tools (separate spec if needed)
- Task API router (frontend uses Supabase client directly; agent tools go through service layer)
- Modifying the existing `tasks` table schema (it's sufficient as-is)
