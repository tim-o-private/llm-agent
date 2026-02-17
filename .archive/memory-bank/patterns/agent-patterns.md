# Agent Patterns

**Files**: [`crud_tool.py`](../src/core/tools/crud_tool.py) [`agent_loader_db.py`](../src/core/agents/agent_loader_db.py)
**Rules**: [agent-001](../rules/agent-rules.json#agent-001) [agent-002](../rules/agent-rules.json#agent-002) [agent-003](../rules/agent-rules.json#agent-003)

## Pattern 1: Generic CRUDTool Configuration

```python
# ✅ DO: Use generic CRUDTool with detailed runtime_args_schema
# Example: Create memory tool
INSERT INTO agent_tools (agent_id, name, description, config) VALUES 
('agent-uuid', 'create_agent_long_term_memory', 
'Creates a new agent long-term memory record. Requires memory_content in data.', 
{
    "table_name": "agent_long_term_memory",
    "method": "create",
    "field_map": {"memory_content": "notes"},
    "runtime_args_schema": {
        "data": {
            "type": "dict",
            "optional": false,
            "description": "The data for the new memory. Must contain a 'memory_content' field.",
            "properties": {
                "memory_content": {
                    "type": "str",
                    "optional": false,
                    "description": "The actual text content of the memory to save."
                }
            }
        }
    }
});

# ✅ DO: Fetch memory by ID tool
INSERT INTO agent_tools (agent_id, name, description, config) VALUES 
('agent-uuid', 'fetch_memory_by_id',
'Fetches a specific memory by ID. Requires id in filters.',
{
    "table_name": "agent_long_term_memory", 
    "method": "fetch",
    "runtime_args_schema": {
        "filters": {
            "type": "dict",
            "optional": false,
            "description": "Filters to specify the memory. Must contain an 'id'.",
            "properties": {
                "id": {
                    "type": "str",
                    "optional": false,
                    "description": "The UUID of the memory to fetch."
                }
            }
        }
    }
});

# ✅ DO: Fetch all memories tool (optional filters)
INSERT INTO agent_tools (agent_id, name, description, config) VALUES 
('agent-uuid', 'fetch_all_memories',
'Fetches all accessible memories. Filters are optional.',
{
    "table_name": "agent_long_term_memory",
    "method": "fetch", 
    "runtime_args_schema": {
        "filters": {
            "type": "dict",
            "optional": true,
            "description": "Optional filters. If omitted, fetches all accessible memories.",
            "properties": {
                "id": {
                    "type": "str", 
                    "optional": true,
                    "description": "Optional UUID of a specific memory to fetch."
                }
            }
        }
    }
});

# ✅ DO: Dynamic tool class generation from runtime_args_schema
def _create_dynamic_crud_tool_class(config):
    runtime_schema = config.get('runtime_args_schema', {})
    
    # Generate Pydantic model from schema
    fields = {}
    for arg_name, arg_config in runtime_schema.items():
        field_type = _get_pydantic_type(arg_config['type'])
        default = ... if not arg_config.get('optional', False) else None
        fields[arg_name] = (field_type, Field(default=default, description=arg_config.get('description', '')))
    
    DynamicArgsSchema = create_model('DynamicCRUDToolInput', **fields)
    
    class DynamicCRUDTool(CRUDTool):
        args_schema = DynamicArgsSchema
    
    return DynamicCRUDTool

# ❌ DON'T: Create separate tool classes for each table
class TaskCreateTool(BaseTool):
    def _run(self, data):
        return self.db.table('tasks').insert(data).execute()

class NoteCreateTool(BaseTool):
    def _run(self, data):
        return self.db.table('notes').insert(data).execute()

# ❌ DON'T: Hardcode args_schema without runtime configuration
class StaticCRUDTool(BaseTool):
    args_schema = CRUDToolInput  # Same schema for all operations
```

## Pattern 2: Database-Driven Tool Loading

```python
# ✅ DO: Load tools from database configuration
class AgentLoaderDB:
    async def load_tools_for_agent(self, agent_name: str, user_id: str):
        # Query database for tool configurations
        tools_query = """
            SELECT name, description, config 
            FROM agent_tools 
            WHERE user_id = %s AND agent_name = %s
        """
        
        tools = []
        async with self.db_connection.cursor() as cur:
            await cur.execute(tools_query, (user_id, agent_name))
            for row in await cur.fetchall():
                tool = self._create_tool_from_config(row)
                tools.append(tool)
        
        return tools
    
    def _create_tool_from_config(self, config_row):
        name, description, config = config_row
        
        if config.get('tool_type') == 'crud':
            return CRUDTool(
                name=name,
                description=description,
                **config  # Spread config into tool parameters
            )

# ❌ DON'T: Hardcode tool instantiation
def get_agent_tools():
    return [
        TaskCreateTool(),
        TaskFetchTool(),
        NoteCreateTool(),
        # ... hardcoded list
    ]
```

## Pattern 3: PostgresChatMessageHistory Pattern

```python
# ✅ DO: Use PostgresChatMessageHistory for session management
from langchain_postgres import PostgresChatMessageHistory

class AgentExecutor:
    def __init__(self, user_id: str, agent_name: str, session_id: str):
        self.memory = PostgresChatMessageHistory(
            connection_string=DATABASE_URL,
            session_id=f"{user_id}:{agent_name}:{session_id}",
            table_name="chat_history"
        )
    
    async def process_message(self, message: str):
        # Memory automatically persists to PostgreSQL
        response = await self.agent.ainvoke({
            "input": message,
            "chat_history": self.memory.messages
        })
        
        # Add to memory (auto-persisted)
        self.memory.add_user_message(message)
        self.memory.add_ai_message(response["output"])
        
        return response

# ❌ DON'T: Manual memory management
class AgentExecutor:
    def __init__(self):
        self.messages = []  # In-memory only
    
    async def process_message(self, message: str):
        # Manual memory management
        self.messages.append({"role": "user", "content": message})
        response = await self.agent.ainvoke({"input": message})
        self.messages.append({"role": "assistant", "content": response})
        
        # Manual persistence (error-prone)
        await self.save_messages_to_db()
```

## Pattern 4: LangChain Tool Abstraction

```python
# ✅ DO: Extend BaseTool with proper abstractions
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class CRUDToolInput(BaseModel):
    data: Optional[Dict[str, Any]] = Field(default=None)
    filters: Optional[Dict[str, Any]] = Field(default=None)

class CRUDTool(BaseTool):
    name: str = "crud_tool"
    description: str = "Generic CRUD operations"
    args_schema: Type[BaseModel] = CRUDToolInput
    
    # Configuration fields
    table_name: str
    method: str
    field_map: Dict[str, str] = Field(default_factory=dict)
    
    def _run(self, data: Optional[Dict] = None, filters: Optional[Dict] = None) -> str:
        # Generic implementation that works for any table/method
        return self._execute_crud_operation(data, filters)
    
    async def _arun(self, data: Optional[Dict] = None, filters: Optional[Dict] = None) -> str:
        return self._run(data, filters)

# ❌ DON'T: Bypass LangChain abstractions
class CustomTool:
    def __init__(self, name: str):
        self.name = name
    
    def execute(self, input_data):
        # Custom interface, not compatible with LangChain
        pass
```

## Pattern 5: Agent Configuration Pattern

```python
# ✅ DO: Use configuration-driven agent setup
agent_config = {
    "name": "task_assistant",
    "description": "Helps manage tasks and notes",
    "model": "gemini-pro",
    "tools": [
        {"name": "create_task", "type": "crud"},
        {"name": "fetch_tasks", "type": "crud"},
        {"name": "web_search", "type": "external"}
    ],
    "system_prompt": "You are a helpful task management assistant...",
    "memory_config": {
        "type": "postgresql",
        "table_name": "chat_history"
    }
}

class ConfigurableAgent:
    def __init__(self, config: dict, user_id: str):
        self.config = config
        self.user_id = user_id
        self.tools = self._load_tools_from_config()
        self.memory = self._setup_memory()
        self.agent = self._create_agent()
    
    def _load_tools_from_config(self):
        # Load tools based on configuration
        pass

# ❌ DON'T: Hardcode agent configuration
class TaskAgent:
    def __init__(self):
        self.tools = [TaskCreateTool(), TaskFetchTool()]  # Hardcoded
        self.model = "gpt-4"  # Hardcoded
        self.prompt = "You are a task assistant"  # Hardcoded
```

## Pattern 6: Error Handling in Tools

```python
# ✅ DO: Proper error handling with ToolException
from langchain_core.tools import ToolException

class CRUDTool(BaseTool):
    def _run(self, data: Optional[Dict] = None, filters: Optional[Dict] = None) -> str:
        try:
            self._validate_inputs(data, filters)
            result = self._execute_operation(data, filters)
            return f"Success: {result}"
        
        except ValidationError as e:
            raise ToolException(f"Invalid input: {e}")
        except DatabaseError as e:
            logger.error(f"Database error in {self.name}: {e}")
            raise ToolException(f"Database operation failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in {self.name}: {e}")
            raise ToolException(f"Tool execution failed: {e}")

# ❌ DON'T: Silent failures or generic errors
class BadTool(BaseTool):
    def _run(self, data):
        try:
            return self.db.table('tasks').insert(data).execute()
        except:
            return "Error occurred"  # No details, no proper exception
```

## Pattern 7: Tool Input Validation

```python
# ✅ DO: Use Pydantic models for tool input validation
from pydantic import BaseModel, Field, validator

class TaskCreateInput(BaseModel):
    data: Dict[str, Any] = Field(..., description="Task data to create")
    
    @validator('data')
    def validate_task_data(cls, v):
        if 'title' not in v:
            raise ValueError('Task title is required')
        if len(v['title']) > 100:
            raise ValueError('Task title too long')
        return v

class TaskCreateTool(BaseTool):
    args_schema: Type[BaseModel] = TaskCreateInput
    
    def _run(self, data: Dict[str, Any]) -> str:
        # Input already validated by Pydantic
        pass

# ❌ DON'T: Manual validation in tool execution
class BadTaskTool(BaseTool):
    def _run(self, data):
        if not data:
            return "Error: No data provided"
        if 'title' not in data:
            return "Error: Title required"
        # Manual validation mixed with business logic
```

## Pattern 8: Abstraction Layers

```python
# ✅ DO: Create abstraction layers for common patterns
class DatabaseTool(BaseTool):
    """Base class for database-related tools"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_client = self._get_db_client()
    
    def _get_db_client(self):
        # Centralized database connection logic
        return get_supabase_client()
    
    def _apply_user_scoping(self, data: dict, user_id: str):
        # Common user scoping logic
        data['user_id'] = user_id
        return data

class CRUDTool(DatabaseTool):
    """Specialized for CRUD operations"""
    
    def _run(self, data: Optional[Dict] = None, filters: Optional[Dict] = None) -> str:
        # Inherits database connection and user scoping
        scoped_data = self._apply_user_scoping(data, self.user_id)
        return self._execute_crud(scoped_data, filters)

# ❌ DON'T: Duplicate common logic across tools
class TaskTool(BaseTool):
    def _run(self, data):
        db = get_supabase_client()  # Duplicated
        data['user_id'] = self.user_id  # Duplicated
        return db.table('tasks').insert(data).execute()

class NoteTool(BaseTool):
    def _run(self, data):
        db = get_supabase_client()  # Duplicated
        data['user_id'] = self.user_id  # Duplicated
        return db.table('notes').insert(data).execute()
```

## Pattern 9: Agent Executor Caching

```python
# ✅ DO: Cache agent executors for performance
from cachetools import TTLCache

class AgentManager:
    def __init__(self):
        self.executor_cache = TTLCache(maxsize=100, ttl=900)  # 15 min TTL
    
    async def get_agent_executor(self, user_id: str, agent_name: str):
        cache_key = (user_id, agent_name)
        
        if cache_key in self.executor_cache:
            return self.executor_cache[cache_key]
        
        # Create new executor
        executor = await self._create_agent_executor(user_id, agent_name)
        self.executor_cache[cache_key] = executor
        
        return executor
    
    async def _create_agent_executor(self, user_id: str, agent_name: str):
        # Load configuration and create executor
        pass

# ❌ DON'T: Create new executors for every request
async def get_agent(user_id: str, agent_name: str):
    # Creates new executor every time (expensive)
    return AgentExecutor(user_id, agent_name)
```

## Pattern 10: Tool Registration System

```python
# ✅ DO: Use registry pattern for tool discovery
class ToolRegistry:
    def __init__(self):
        self.tool_factories = {}
    
    def register_tool_type(self, tool_type: str, factory_func):
        self.tool_factories[tool_type] = factory_func
    
    def create_tool(self, tool_config: dict):
        tool_type = tool_config.get('tool_type', 'crud')
        factory = self.tool_factories.get(tool_type)
        
        if not factory:
            raise ValueError(f"Unknown tool type: {tool_type}")
        
        return factory(tool_config)

# Register tool types
registry = ToolRegistry()
registry.register_tool_type('crud', lambda config: CRUDTool(**config))
registry.register_tool_type('web_search', lambda config: WebSearchTool(**config))

# ❌ DON'T: Hardcode tool type mapping
def create_tool(tool_config):
    if tool_config['type'] == 'crud':
        return CRUDTool(**tool_config)
    elif tool_config['type'] == 'web_search':
        return WebSearchTool(**tool_config)
    # ... hardcoded if/elif chain
```

## Complete Examples

### Database-Configured CRUD Tool
```python
# src/core/tools/crud_tool.py
class CRUDTool(BaseTool):
    """Generic CRUD tool configured via database"""
    
    # Configuration from database
    table_name: str
    method: str  # 'create', 'fetch', 'update', 'delete'
    field_map: Dict[str, str] = Field(default_factory=dict)
    user_id: str
    
    def _run(self, data: Optional[Dict] = None, filters: Optional[Dict] = None) -> str:
        try:
            # Validate inputs
            self._validate_runtime_inputs(data, filters)
            
            # Apply user scoping
            final_filters = self._apply_mandatory_filters(filters)
            
            # Prepare data payload
            if self.method in ["create", "update"]:
                final_data = self._prepare_data_payload(data)
            
            # Execute operation
            result = self._execute_database_operation(final_data, final_filters)
            
            return f"{self.method.title()}: {result}"
            
        except Exception as e:
            logger.error(f"CRUDTool error: {e}")
            raise ToolException(f"Database operation failed: {e}")
```

### Agent with PostgreSQL Memory
```python
# src/core/agents/customizable_agent.py
from langchain_postgres import PostgresChatMessageHistory

class CustomizableAgentExecutor:
    def __init__(self, user_id: str, agent_name: str, session_id: str):
        self.user_id = user_id
        self.agent_name = agent_name
        
        # PostgreSQL-backed memory
        self.memory = PostgresChatMessageHistory(
            connection_string=DATABASE_URL,
            session_id=f"{user_id}:{agent_name}:{session_id}",
            table_name="chat_history"
        )
        
        # Load tools from database
        self.tools = await self._load_tools()
        
        # Create agent
        self.agent = self._create_agent()
    
    async def _load_tools(self):
        loader = AgentLoaderDB()
        return await loader.load_tools_for_agent(self.agent_name, self.user_id)
```

## Quick Reference

**Tool Development**:
- Extend `BaseTool` from LangChain
- Use database configuration over hardcoding
- Proper error handling with `ToolException`
- Pydantic models for input validation

**Agent Patterns**:
- `PostgresChatMessageHistory` for memory
- Configuration-driven agent setup
- Executor caching for performance
- Tool registry for extensibility

**Key Principles**:
- Generic tools configured via database
- LangChain abstractions for compatibility
- Abstraction layers to reduce duplication
- Database-driven tool loading 