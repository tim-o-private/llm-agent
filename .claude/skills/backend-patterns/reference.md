# Backend Patterns — Full Reference

## 1. Database Connections — Use Prescribed Methods Only

```python
# ✅ Dependency injection
from chatServer.database.connection import get_db_connection
from chatServer.database.supabase_client import get_supabase_client

@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    db=Depends(get_supabase_client),
):
    ...

# ❌ NEVER create new connections
from supabase import create_client
db = create_client(url, key)  # Bypasses pool
```

## 2. Service Layer Pattern

```python
# services/task_service.py
class TaskService:
    def __init__(self, db_client):
        self.db = db_client

    async def create_task(self, task_data: TaskCreate, user_id: str) -> Task:
        data = task_data.model_dump()
        data["user_id"] = user_id
        result = await self.db.table("tasks").insert(data).execute()
        return Task(**result.data[0])

# dependencies/services.py
def get_task_service(db=Depends(get_supabase_client)) -> TaskService:
    return TaskService(db)

# routers/tasks.py
@router.post("/tasks", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
):
    return await service.create_task(task_data, user_id)
```

## 3. Pydantic Models for Validation

```python
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    priority: int = Field(default=1, ge=1, le=5)

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    priority: int
    created_at: str
    user_id: str

@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    ...  # Validation happens automatically
```

**Never use `request.json()` with manual validation. Always use Pydantic models.**

## 4. RLS — Let the Database Filter

```python
# ✅ RLS handles user scoping automatically
result = await db.table("tasks").select("*").execute()

# ❌ Redundant when RLS exists
result = await db.table("tasks").select("*").eq("user_id", user_id).execute()
```

## 5. Error Handling

```python
class TaskService:
    async def get_task(self, task_id: str) -> Task:
        try:
            result = await self.db.table("tasks").select("*").eq("id", task_id).execute()
            if not result.data:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            return result.data[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error getting task {task_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve task")
```

**Re-raise HTTPException explicitly. Log unexpected errors. Never bare `except:` with vague messages.**

## 5b. Integration Testing Patterns

Test new API endpoints with `httpx.AsyncClient` against the FastAPI app:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from chatServer.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_get_notifications_requires_auth(client):
    response = await client.get("/api/notifications")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_notifications_returns_list(client, auth_headers):
    response = await client.get("/api/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

Test service methods by mocking the database client:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.table.return_value = db
    db.select.return_value = db
    db.insert.return_value = db
    db.eq.return_value = db
    db.execute.return_value = MagicMock(data=[{"id": "test-id"}])
    return db

@pytest.mark.asyncio
async def test_notify_user_stores_notification(mock_db):
    service = NotificationService(mock_db)
    result = await service.notify_user("user-1", "Title", "Body")
    mock_db.table.assert_called_with("notifications")
```

## 6. Authentication (ES256 JWT)

Supabase issues **ES256** tokens. `chatServer/dependencies/auth.py` handles both ES256 (JWKS) and HS256 (fallback). The `get_current_user` dependency extracts `sub` from JWT.

```python
@router.get("/tasks")
async def get_tasks(user_id: str = Depends(get_current_user)):
    ...  # user_id injected and validated
```

**Never manually parse Authorization headers in endpoints.**

## 7. Generic CRUDTool (Agent Tools)

Tools are configured in the database, not hardcoded:

```python
# ✅ Database-driven tool config
INSERT INTO agent_tools (agent_id, name, description, config) VALUES
('agent-uuid', 'create_task', 'Creates a task', {
    "table_name": "tasks",
    "method": "create",
    "field_map": {"task_title": "title"},
    "runtime_args_schema": {
        "data": {"type": "dict", "optional": false, "description": "Task data"}
    }
});

# ❌ NEVER create separate tool classes per table
class TaskCreateTool(BaseTool): ...
class NoteCreateTool(BaseTool): ...
```

## 8. Database-Driven Tool Loading

```python
class AgentLoaderDB:
    async def load_tools_for_agent(self, agent_name: str, user_id: str):
        tools_query = """
            SELECT name, description, config
            FROM agent_tools
            WHERE user_id = %s AND agent_name = %s
        """
        async with self.db_connection.cursor() as cur:
            await cur.execute(tools_query, (user_id, agent_name))
            return [self._create_tool_from_config(row) for row in await cur.fetchall()]
```

## 9. PostgresChatMessageHistory

```python
from langchain_postgres import PostgresChatMessageHistory

self.memory = PostgresChatMessageHistory(
    connection_string=DATABASE_URL,
    session_id=f"{user_id}:{agent_name}:{session_id}",
    table_name="chat_history",
)
```

**Never manage chat memory manually. Always use PostgresChatMessageHistory.**

## 10. Agent Executor Caching

```python
from cachetools import TTLCache

AGENT_EXECUTOR_CACHE = TTLCache(maxsize=100, ttl=900)  # 15 min TTL

async def get_agent_executor(user_id: str, agent_name: str):
    cache_key = (user_id, agent_name)
    if cache_key in AGENT_EXECUTOR_CACHE:
        return AGENT_EXECUTOR_CACHE[cache_key]
    executor = await _create_agent_executor(user_id, agent_name)
    AGENT_EXECUTOR_CACHE[cache_key] = executor
    return executor
```

## 11. Content Block Normalization

Newer `langchain-anthropic` returns content block lists instead of strings:

```python
response = await agent_executor.ainvoke({"input": message})
ai_response = response.get("output", "No output from agent.")

if isinstance(ai_response, list):
    ai_response = "".join(
        block.get("text", "") for block in ai_response
        if isinstance(block, dict) and block.get("type") == "text"
    ) or "No text content in response."
```

## 12. Tool Error Handling

```python
from langchain_core.tools import ToolException

class CRUDTool(BaseTool):
    def _run(self, data=None, filters=None) -> str:
        try:
            self._validate_inputs(data, filters)
            result = self._execute_operation(data, filters)
            return f"Success: {result}"
        except ValidationError as e:
            raise ToolException(f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"CRUDTool error: {e}")
            raise ToolException(f"Database operation failed: {e}")
```
