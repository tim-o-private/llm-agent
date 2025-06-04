# API Patterns

**Files**: [`main.py`](../chatServer/main.py) [`connection.py`](../chatServer/database/connection.py) [`supabase_client.py`](../chatServer/database/supabase_client.py)
**Rules**: [api-001](../rules/api-rules.json#api-001) [api-002](../rules/api-rules.json#api-002) [api-003](../rules/api-rules.json#api-003)

## Pattern 1: Single Database - Use Prescribed Connections

```python
# ✅ DO: Use dependency injection for database connections
from chatServer.database.connection import get_db_connection
from chatServer.database.supabase_client import get_supabase_client

@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    db = Depends(get_supabase_client)  # Use prescribed connection
):
    result = await db.table('tasks').insert(task_data.model_dump()).execute()
    return result.data

# ❌ DON'T: Create new connections in files
from supabase import create_client
db = create_client(url, key)  # Creates new connection pool

# ❌ DON'T: Direct psycopg connections
import psycopg
conn = psycopg.connect(DATABASE_URL)  # Bypasses connection pool
```

## Pattern 2: Avoid New APIs - Use React Query

```tsx
// ✅ DO: Use React Query hooks for data fetching
import { useTaskHooks } from '@/api/hooks/useTaskHooks';

export function TaskList() {
  const { data: tasks, isLoading } = useTaskHooks.useFetchTasks();
  const { mutate: createTask } = useTaskHooks.useCreateTask();
  
  return (
    <div>
      {tasks?.map(task => <TaskCard key={task.id} task={task} />)}
      <Button onClick={() => createTask(newTaskData)}>Add Task</Button>
    </div>
  );
}

// ❌ DON'T: Create new API endpoints for simple CRUD
// chatServer/main.py
@app.get("/api/tasks/user/{user_id}")  # Unnecessary endpoint
async def get_user_tasks(user_id: str):
    # React Query can handle filtering client-side
```

## Pattern 3: Service Layer Pattern

```python
# ✅ DO: Extract business logic into services
# chatServer/services/task_service.py
class TaskService:
    def __init__(self, db_client):
        self.db = db_client
    
    async def create_task_with_validation(self, task_data: dict, user_id: str):
        # Business logic here
        validated_data = self._validate_task_data(task_data)
        validated_data['user_id'] = user_id
        
        result = await self.db.table('tasks').insert(validated_data).execute()
        return result.data[0]
    
    def _validate_task_data(self, data: dict) -> dict:
        # Validation logic
        return data

# chatServer/main.py
@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    return await task_service.create_task_with_validation(
        task_data.model_dump(), user_id
    )

# ❌ DON'T: Put business logic in endpoints
@app.post("/api/tasks")
async def create_task(task_data: TaskCreate, user_id: str = Depends(get_current_user)):
    # Validation logic mixed with endpoint logic
    if not task_data.title:
        raise HTTPException(400, "Title required")
    if len(task_data.title) > 100:
        raise HTTPException(400, "Title too long")
    # Database logic mixed in
    result = await db.table('tasks').insert({...}).execute()
    # More business logic...
```

## Pattern 4: Dependency Injection Pattern

```python
# ✅ DO: Use FastAPI dependency injection
from fastapi import Depends

def get_task_service(db = Depends(get_supabase_client)) -> TaskService:
    return TaskService(db)

@app.post("/api/tasks")
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    return await task_service.create_task(task_data, user_id)

# ❌ DON'T: Instantiate services in endpoints
@app.post("/api/tasks")
async def create_task(task_data: TaskCreate):
    db = get_supabase_client()  # Manual instantiation
    service = TaskService(db)   # Creates new instance each time
```

## Pattern 5: Pydantic Models for Validation

```python
# ✅ DO: Use Pydantic models for request/response validation
from pydantic import BaseModel, Field, validator

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    priority: int = Field(default=1, ge=1, le=5)
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    priority: int
    created_at: str
    user_id: str

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    # Validation happens automatically
    pass

# ❌ DON'T: Manual validation in endpoints
@app.post("/api/tasks")
async def create_task(request: Request):
    data = await request.json()
    if 'title' not in data:
        raise HTTPException(400, "Title required")
    if len(data['title']) > 100:
        raise HTTPException(400, "Title too long")
```

## Pattern 6: RLS (Row Level Security) Pattern

```python
# ✅ DO: Rely on RLS for data scoping
@app.get("/api/tasks")
async def get_tasks(
    user_id: str = Depends(get_current_user),
    db = Depends(get_supabase_client)
):
    # RLS automatically filters by user_id
    result = await db.table('tasks').select('*').execute()
    return result.data

# ❌ DON'T: Manual user_id filtering when RLS exists
@app.get("/api/tasks")
async def get_tasks(user_id: str = Depends(get_current_user), db = Depends(get_supabase_client)):
    # Redundant filtering - RLS already handles this
    result = await db.table('tasks').select('*').eq('user_id', user_id).execute()
```

## Pattern 7: Error Handling Pattern

```python
# ✅ DO: Structured error handling with proper HTTP status codes
from fastapi import HTTPException, status

class TaskService:
    async def get_task(self, task_id: str, user_id: str):
        try:
            result = await self.db.table('tasks').select('*').eq('id', task_id).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )
            return result.data[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Database error getting task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve task"
            )

# ❌ DON'T: Generic error handling
async def get_task(task_id: str):
    try:
        result = await db.table('tasks').select('*').eq('id', task_id).execute()
        return result.data[0]  # Could raise IndexError
    except:
        return {"error": "Something went wrong"}  # No status code, vague message
```

## Pattern 8: Abstraction and Parameterization (CRUDTool Example)

```python
# ✅ DO: Create generic, configurable tools
class CRUDTool(BaseTool):
    """Generic CRUD tool configured via database"""
    table_name: str
    method: str  # 'create', 'fetch', 'update', 'delete'
    field_map: Dict[str, str]
    
    def _run(self, data: Optional[Dict] = None, filters: Optional[Dict] = None):
        # Generic implementation that works for any table
        if self.method == "create":
            return self._create(data)
        elif self.method == "fetch":
            return self._fetch(filters)
        # ... other methods

# Database configuration drives behavior
INSERT INTO agent_tools (name, config) VALUES 
('create_task', {
    "table_name": "tasks",
    "method": "create", 
    "field_map": {"task_title": "title", "task_desc": "description"}
});

# ❌ DON'T: Create separate classes for each table
class TaskCRUDTool(BaseTool):
    def _run(self, data):
        return self.db.table('tasks').insert(data).execute()

class NoteCRUDTool(BaseTool):
    def _run(self, data):
        return self.db.table('notes').insert(data).execute()
```

## Pattern 9: Separation of Concerns

```python
# ✅ DO: Separate concerns into focused modules
# models/task.py - Data models only
class Task(BaseModel):
    id: str
    title: str
    user_id: str

# services/task_service.py - Business logic only  
class TaskService:
    async def create_task(self, data: TaskCreate, user_id: str):
        # Business logic here
        pass

# routers/tasks.py - HTTP handling only
@router.post("/tasks")
async def create_task_endpoint(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    service: TaskService = Depends(get_task_service)
):
    return await service.create_task(task_data, user_id)

# ❌ DON'T: Mix concerns in single file
# main.py with everything mixed together
class Task(BaseModel):  # Model
    pass

class TaskService:      # Service
    pass

@app.post("/tasks")     # Router
async def create_task():
    # Business logic mixed with HTTP handling
    pass
```

## Pattern 10: Configuration-Driven Development

```python
# ✅ DO: Use configuration to drive behavior
# Database-driven tool configuration
tool_config = {
    "table_name": "tasks",
    "method": "create",
    "field_map": {"title": "title", "desc": "description"},
    "validation_rules": {"title": {"required": True, "max_length": 100}}
}

class ConfigurableTool:
    def __init__(self, config: dict):
        self.config = config
        self.table_name = config["table_name"]
        self.method = config["method"]
    
    def execute(self, data: dict):
        # Behavior driven by configuration
        if self.method == "create":
            return self._create(data)

# ❌ DON'T: Hardcode behavior in classes
class TaskCreateTool:
    def execute(self, data):
        # Hardcoded to tasks table
        return db.table('tasks').insert(data).execute()
```

## Complete Examples

### Service with Dependency Injection
```python
# chatServer/services/task_service.py
from typing import List
from supabase import AsyncClient
from ..models.task import Task, TaskCreate

class TaskService:
    def __init__(self, db: AsyncClient):
        self.db = db
    
    async def create_task(self, task_data: TaskCreate, user_id: str) -> Task:
        data = task_data.model_dump()
        data['user_id'] = user_id
        
        result = await self.db.table('tasks').insert(data).execute()
        return Task(**result.data[0])
    
    async def get_user_tasks(self, user_id: str) -> List[Task]:
        result = await self.db.table('tasks').select('*').execute()
        return [Task(**task) for task in result.data]

# chatServer/dependencies/services.py
def get_task_service(db: AsyncClient = Depends(get_supabase_client)) -> TaskService:
    return TaskService(db)

# chatServer/routers/tasks.py
@router.post("/tasks", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    user_id: str = Depends(get_current_user),
    service: TaskService = Depends(get_task_service)
):
    return await service.create_task(task_data, user_id)
```

## Pattern 11: FastAPI Project Structure

```python
# ✅ DO: Organize FastAPI project with clear structure
# chatServer/
# ├── main.py              # FastAPI app instantiation
# ├── routers/             # API route groupings
# │   ├── chat_router.py
# │   └── agent_actions_router.py
# ├── services/            # Business logic layer
# │   ├── task_service.py
# │   └── agent_service.py
# ├── models/              # Pydantic models
# │   ├── task_models.py
# │   └── response_models.py
# ├── database/            # Database setup
# │   └── connection.py
# └── core/                # Core configurations
#     └── settings.py

# main.py
from fastapi import FastAPI
from .routers import chat_router, agent_actions_router

app = FastAPI(title="Clarity Chat Server")
app.include_router(chat_router.router, prefix="/api/chat")
app.include_router(agent_actions_router.router, prefix="/api/agent")

# routers/chat_router.py
from fastapi import APIRouter, Depends
from ..models.task_models import TaskCreate, TaskResponse
from ..services.task_service import TaskService

router = APIRouter()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    service: TaskService = Depends(get_task_service)
):
    return await service.create_task(task, user_id)

# ❌ DON'T: Put everything in main.py
# main.py with 500+ lines of routes, models, and business logic
```

## Pattern 12: FastAPI Authentication & Authorization

```python
# ✅ DO: Use dependency injection for auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user_id(token: str = Depends(security)) -> str:
    try:
        payload = jwt.decode(
            token.credentials, 
            settings.supabase_jwt_secret, 
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/tasks")
async def get_tasks(user_id: str = Depends(get_current_user_id)):
    # user_id automatically injected and validated
    return await task_service.get_user_tasks(user_id)

# ❌ DON'T: Manual token validation in each endpoint
@router.get("/tasks")
async def get_tasks(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401)
    
    token = authorization.replace("Bearer ", "")
    # Manual validation repeated in every endpoint...
```

## Pattern 13: FastAPI Error Handling

```python
# ✅ DO: Use global exception handlers
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": "validation_error"}
    )

@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError):
    return JSONResponse(
        status_code=403,
        content={"detail": "Access denied", "type": "permission_error"}
    )

# Service layer raises domain exceptions
class TaskService:
    async def create_task(self, task_data: dict, user_id: str):
        if len(task_data['title']) > 100:
            raise ValueError("Task title too long")
        
        if not await self.user_can_create_tasks(user_id):
            raise PermissionError("User cannot create tasks")

# ❌ DON'T: Inconsistent error responses
@router.post("/tasks")
async def create_task(task: TaskCreate):
    try:
        return await service.create_task(task)
    except ValueError as e:
        return {"error": str(e)}  # Inconsistent format
    except Exception as e:
        return {"message": "Something went wrong"}  # No details
```

## Quick Reference

**Database Connections**:
- PostgreSQL: `get_db_connection()` dependency
- Supabase: `get_supabase_client()` dependency
- Never create new connections in files

**API Development**:
- Use React Query hooks instead of new endpoints
- Service layer for business logic
- Pydantic models for validation
- Dependency injection for services
- Global exception handlers
- JWT validation via dependencies

**FastAPI Structure**:
- `main.py` - App setup only
- `routers/` - Route definitions
- `services/` - Business logic
- `models/` - Pydantic schemas
- `dependencies/` - Shared dependencies

**Key Principles**:
- One database (PostgreSQL on Supabase)
- Prescribed connection methods only
- Reduce interfaces, increase abstraction
- Configuration over hardcoding 