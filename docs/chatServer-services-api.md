# ChatServer Services API Documentation

## Overview

This document provides comprehensive API documentation for the service layer implemented in Phase 3 of the chatServer decomposition project. The services provide clean, testable business logic separated from the FastAPI endpoints.

## Service Architecture

```
chatServer/services/
├── __init__.py          # Service exports
├── background_tasks.py  # Background task management
├── chat.py             # Chat processing logic
└── prompt_customization.py  # Prompt management
```

## BackgroundTaskService

### Class: `BackgroundTaskService`

Manages scheduled background tasks for session cleanup and cache eviction.

#### Constructor

```python
def __init__(self) -> None
```

Initializes the service with empty task references and cache.

**Attributes:**
- `deactivate_task: Optional[asyncio.Task]` - Task for session deactivation
- `evict_task: Optional[asyncio.Task]` - Task for cache eviction
- `_agent_executor_cache: Optional[Dict[Tuple[str, str], Any]]` - Cache reference

#### Methods

##### `set_agent_executor_cache`

```python
def set_agent_executor_cache(self, cache: Dict[Tuple[str, str], Any]) -> None
```

Sets the agent executor cache reference for eviction tasks.

**Parameters:**
- `cache`: Dictionary mapping (user_id, agent_name) tuples to agent executors

**Usage:**
```python
service = get_background_task_service()
service.set_agent_executor_cache(agent_executor_cache)
```

##### `deactivate_stale_chat_session_instances`

```python
async def deactivate_stale_chat_session_instances(self) -> None
```

Periodically deactivates stale chat session instances based on TTL.

**Behavior:**
- Runs continuously with `SCHEDULED_TASK_INTERVAL_SECONDS` intervals
- Updates `chat_sessions` table to set `is_active = false` for stale sessions
- Uses `SESSION_INSTANCE_TTL_SECONDS` to determine staleness
- Logs deactivation count when sessions are found

**Database Query:**
```sql
UPDATE chat_sessions 
SET is_active = false, updated_at = %s 
WHERE is_active = true AND updated_at < %s
```

##### `evict_inactive_executors`

```python
async def evict_inactive_executors(self) -> None
```

Periodically evicts agent executors if no active session instances exist.

**Behavior:**
- Runs continuously with `SCHEDULED_TASK_INTERVAL_SECONDS + 30` intervals (staggered)
- Checks for active sessions for each cached executor
- Removes executors from cache when no active sessions exist
- Logs eviction events

**Database Query:**
```sql
SELECT 1 FROM chat_sessions 
WHERE user_id = %s AND agent_name = %s AND is_active = true LIMIT 1
```

##### `start_background_tasks`

```python
def start_background_tasks(self) -> None
```

Starts all background tasks using `asyncio.create_task`.

**Creates:**
- `deactivate_task`: Session deactivation task
- `evict_task`: Cache eviction task

**Usage:**
```python
service.start_background_tasks()
logger.info("Background tasks started")
```

##### `stop_background_tasks`

```python
async def stop_background_tasks(self) -> None
```

Stops all background tasks gracefully with proper cancellation handling.

**Behavior:**
- Cancels both tasks if they exist
- Waits for cancellation to complete
- Handles `asyncio.CancelledError` exceptions
- Logs cancellation status

**Usage:**
```python
await service.stop_background_tasks()
logger.info("Background tasks stopped")
```

#### Global Function

##### `get_background_task_service`

```python
def get_background_task_service() -> BackgroundTaskService
```

Returns the global singleton instance of BackgroundTaskService.

**Returns:** `BackgroundTaskService` instance

---

## ChatService

### Class: `ChatService`

Handles all chat-related business logic including memory management, agent loading, and message processing.

#### Constructor

```python
def __init__(self, agent_executor_cache: Dict[Tuple[str, str], Any]) -> None
```

Initializes the service with an agent executor cache reference.

**Parameters:**
- `agent_executor_cache`: Dictionary for caching agent executors

#### Methods

##### `create_chat_memory`

```python
def create_chat_memory(self, session_id: str, pg_connection: Any) -> AsyncConversationBufferWindowMemory
```

Creates PostgreSQL-backed chat memory with window limits.

**Parameters:**
- `session_id`: Unique session identifier
- `pg_connection`: PostgreSQL connection for chat history

**Returns:** `AsyncConversationBufferWindowMemory` instance

**Configuration:**
- Window size: 50 message pairs (k=50)
- Memory key: "chat_history"
- Input key: "input"
- Returns messages as objects (not strings)

**Usage:**
```python
memory = service.create_chat_memory("session_123", pg_connection)
```

##### `get_or_load_agent_executor`

```python
def get_or_load_agent_executor(
    self,
    user_id: str,
    agent_name: str,
    session_id: str,
    agent_loader_module: Any,
    memory: Any
) -> Any
```

Retrieves agent executor from cache or loads a new one.

**Parameters:**
- `user_id`: User identifier
- `agent_name`: Name of the agent
- `session_id`: Session identifier (for logging)
- `agent_loader_module`: Module with `load_agent_executor` method
- `memory`: Memory instance to attach to executor

**Returns:** Agent executor instance

**Behavior:**
- Checks cache using `(user_id, agent_name)` key
- Updates memory on cache hit
- Loads new executor on cache miss
- Validates executor interface (`ainvoke` and `memory` attributes)
- Caches newly loaded executors

**Raises:**
- `HTTPException(500)`: If agent loading fails or interface is invalid

**Usage:**
```python
executor = service.get_or_load_agent_executor(
    user_id="user_123",
    agent_name="assistant",
    session_id="session_123",
    agent_loader_module=agent_loader,
    memory=memory
)
```

##### `extract_tool_info`

```python
def extract_tool_info(self, response_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]
```

Extracts tool information from agent response data.

**Parameters:**
- `response_data`: Agent response dictionary

**Returns:** Tuple of `(tool_name, tool_input)` or `(None, None)`

**Behavior:**
- Looks for `intermediate_steps` in response
- Extracts tool name and input from first step
- Handles malformed steps gracefully

**Usage:**
```python
tool_name, tool_input = service.extract_tool_info(response_data)
if tool_name:
    logger.info(f"Tool used: {tool_name}")
```

##### `process_chat`

```python
async def process_chat(
    self,
    chat_input: ChatRequest,
    user_id: str,
    pg_connection: Any,
    agent_loader_module: Any,
    request: Request
) -> ChatResponse
```

Main chat processing method that orchestrates the entire chat workflow.

**Parameters:**
- `chat_input`: Chat request with agent_name, message, session_id
- `user_id`: User identifier
- `pg_connection`: PostgreSQL connection
- `agent_loader_module`: Agent loading module
- `request`: FastAPI request object

**Returns:** `ChatResponse` with session_id, response, tool info, and error

**Workflow:**
1. Validates session_id is provided
2. Creates chat memory for session
3. Gets or loads agent executor
4. Invokes agent with user message
5. Extracts tool information
6. Returns formatted response

**Error Handling:**
- Missing session_id: `HTTPException(400)`
- Agent execution errors: Logged and returned in response
- Other errors: `HTTPException(500)`

**Usage:**
```python
response = await service.process_chat(
    chat_input=ChatRequest(
        agent_name="assistant",
        message="Hello",
        session_id="session_123"
    ),
    user_id="user_123",
    pg_connection=pg_connection,
    agent_loader_module=agent_loader,
    request=request
)
```

#### Global Function

##### `get_chat_service`

```python
def get_chat_service(agent_executor_cache: Dict[Tuple[str, str], Any]) -> ChatService
```

Returns the global singleton instance of ChatService.

**Parameters:**
- `agent_executor_cache`: Cache dictionary for agent executors

**Returns:** `ChatService` instance

---

## AsyncConversationBufferWindowMemory

### Class: `AsyncConversationBufferWindowMemory`

Custom async-compatible memory implementation extending LangChain's ConversationBufferWindowMemory.

#### Constructor

```python
def __init__(self, chat_memory: BaseChatMessageHistory, k: int = 5, **kwargs) -> None
```

Inherits from `ConversationBufferWindowMemory` with async support.

#### Methods

##### `aload_memory_variables`

```python
async def aload_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]
```

Asynchronously loads memory variables with window limit applied.

**Parameters:**
- `inputs`: Input dictionary (typically empty for memory loading)

**Returns:** Dictionary with memory key containing message list

**Behavior:**
- Fetches messages asynchronously from chat memory
- Applies window limit (k * 2 messages for k conversation pairs)
- Returns most recent messages within window

**Usage:**
```python
memory_vars = await memory.aload_memory_variables({})
messages = memory_vars["chat_history"]
```

##### `messages_to_string`

```python
def messages_to_string(self, messages: List[BaseMessage]) -> str
```

Converts message list to formatted string representation.

**Parameters:**
- `messages`: List of LangChain BaseMessage objects

**Returns:** Formatted string with human/AI prefixes

**Usage:**
```python
formatted = memory.messages_to_string(messages)
```

---

## PromptCustomizationService

### Class: `PromptCustomizationService`

Manages prompt customization operations including creation, retrieval, and updates.

#### Constructor

```python
def __init__(self) -> None
```

Initializes the service (no parameters required).

#### Methods

##### `create_prompt_customization`

```python
async def create_prompt_customization(
    self,
    customization_data: PromptCustomizationCreate,
    user_id: str,
    supabase_client: Any
) -> PromptCustomization
```

Creates a new prompt customization.

**Parameters:**
- `customization_data`: Pydantic model with customization details
- `user_id`: User identifier
- `supabase_client`: Supabase client instance

**Returns:** Created `PromptCustomization` object

**Database Operation:**
```python
await supabase_client.table("user_agent_prompt_customizations").insert({
    "user_id": user_id,
    "agent_name": customization_data.agent_name,
    "customization_type": customization_data.customization_type,
    "content": customization_data.content,
    "is_active": customization_data.is_active,
    "priority": customization_data.priority
}).execute()
```

**Raises:**
- `HTTPException(500)`: If creation fails or no data returned

**Usage:**
```python
customization = await service.create_prompt_customization(
    customization_data=PromptCustomizationCreate(
        agent_name="assistant",
        customization_type="system_prompt",
        content={"prompt": "You are a helpful assistant"},
        is_active=True,
        priority=1
    ),
    user_id="user_123",
    supabase_client=supabase_client
)
```

##### `get_prompt_customizations_for_agent`

```python
async def get_prompt_customizations_for_agent(
    self,
    agent_name: str,
    user_id: str,
    supabase_client: Any
) -> List[PromptCustomization]
```

Retrieves prompt customizations for a specific agent.

**Parameters:**
- `agent_name`: Name of the agent
- `user_id`: User identifier
- `supabase_client`: Supabase client instance

**Returns:** List of `PromptCustomization` objects (empty list if none found)

**Database Query:**
```python
await supabase_client.table("user_agent_prompt_customizations") \
    .select("*") \
    .eq("user_id", user_id) \
    .eq("agent_name", agent_name) \
    .eq("is_active", True) \
    .order("priority", desc=False) \
    .execute()
```

**Raises:**
- `HTTPException(500)`: If database query fails

**Usage:**
```python
customizations = await service.get_prompt_customizations_for_agent(
    agent_name="assistant",
    user_id="user_123",
    supabase_client=supabase_client
)
```

##### `update_prompt_customization`

```python
async def update_prompt_customization(
    self,
    customization_id: str,
    customization_data: PromptCustomizationCreate,
    user_id: str,
    supabase_client: Any
) -> PromptCustomization
```

Updates an existing prompt customization.

**Parameters:**
- `customization_id`: ID of customization to update
- `customization_data`: Updated customization data
- `user_id`: User identifier (for RLS enforcement)
- `supabase_client`: Supabase client instance

**Returns:** Updated `PromptCustomization` object

**Database Operation:**
```python
update_payload = customization_data.model_dump()
update_payload["updated_at"] = "now()"

await supabase_client.table("user_agent_prompt_customizations") \
    .update(update_payload) \
    .eq("id", customization_id) \
    .eq("user_id", user_id) \
    .execute()
```

**Raises:**
- `HTTPException(404)`: If customization not found or access denied
- `HTTPException(500)`: If update operation fails

**Usage:**
```python
updated = await service.update_prompt_customization(
    customization_id="custom_123",
    customization_data=PromptCustomizationCreate(
        agent_name="assistant",
        customization_type="system_prompt",
        content={"prompt": "Updated prompt"},
        is_active=True,
        priority=1
    ),
    user_id="user_123",
    supabase_client=supabase_client
)
```

#### Global Function

##### `get_prompt_customization_service`

```python
def get_prompt_customization_service() -> PromptCustomizationService
```

Returns the global singleton instance of PromptCustomizationService.

**Returns:** `PromptCustomizationService` instance

---

## Error Handling

### Common Error Patterns

All services implement consistent error handling:

```python
try:
    # Service operation
    result = await some_operation()
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Service error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### HTTP Status Codes

- **400 Bad Request**: Missing required parameters (e.g., session_id)
- **404 Not Found**: Resource not found or access denied
- **500 Internal Server Error**: Service errors, database failures

### Logging

All services use structured logging:

```python
import logging
logger = logging.getLogger(__name__)

# Info level for normal operations
logger.info(f"Created prompt customization for agent {agent_name}")

# Error level for exceptions
logger.error(f"Error in service operation: {e}", exc_info=True)

# Debug level for detailed tracing
logger.debug("Running background task cycle")
```

---

## Configuration

### Constants Used

From `chatServer/config/constants.py`:

- `SESSION_INSTANCE_TTL_SECONDS`: TTL for chat sessions
- `SCHEDULED_TASK_INTERVAL_SECONDS`: Background task interval
- `CHAT_MESSAGE_HISTORY_TABLE_NAME`: Database table name

### Dependencies

Services depend on:

- **Database**: PostgreSQL connection pools
- **Supabase**: Async client for prompt customizations
- **LangChain**: Memory and agent interfaces
- **FastAPI**: HTTP exception handling
- **Pydantic**: Data validation and serialization

---

## Testing

### Test Coverage

Each service has comprehensive unit tests:

- **Initialization tests**: Service creation and setup
- **Success path tests**: Normal operation scenarios
- **Error handling tests**: Exception and edge cases
- **Mock integration tests**: External dependency mocking

### Running Tests

```bash
# Run all service tests
pytest tests/chatServer/services/ -v

# Run specific service tests
pytest tests/chatServer/services/test_chat.py -v
pytest tests/chatServer/services/test_background_tasks.py -v
pytest tests/chatServer/services/test_prompt_customization.py -v
```

### Test Examples

```python
# Testing async service methods
@pytest.mark.asyncio
async def test_process_chat_success():
    service = ChatService({})
    result = await service.process_chat(...)
    assert result.session_id == "session_123"

# Testing error scenarios
def test_invalid_agent_executor():
    service = ChatService({})
    with pytest.raises(HTTPException) as exc_info:
        service.get_or_load_agent_executor(...)
    assert exc_info.value.status_code == 500
``` 