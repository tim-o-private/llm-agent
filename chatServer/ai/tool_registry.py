# Tool registry for router-proxied tools
# Manages tool creation and registration for router-based architecture

import logging
from typing import Dict, Any, List, Optional, Type
import httpx
from datetime import datetime

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class RouterProxiedTool(BaseTool):
    """
    Base class for tools that make router-proxied HTTP calls
    
    This tool makes HTTP calls to our FastAPI router, which then
    proxies them to PostgREST or other services.
    """
    
    name: str = "router_tool"
    description: str = "A tool that makes router-proxied calls"
    
    # Router configuration
    router_base_url: str = Field(default="http://localhost:8000")
    user_id: str = Field(..., description="User ID for scoping")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client for router calls"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.router_base_url,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "X-User-ID": self.user_id,
                    "X-Client-Info": "clarity-v2-tools"
                }
            )
        return self._client
    
    async def _make_router_call(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make a router-proxied call
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., '/api/tasks')
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
        """
        
        try:
            logger.debug(f"Making {method} request to {endpoint}")
            
            if method.upper() == "GET":
                response = await self.client.get(endpoint, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(endpoint, json=data, params=params)
            elif method.upper() == "PATCH":
                response = await self.client.patch(endpoint, json=data, params=params)
            elif method.upper() == "DELETE":
                response = await self.client.delete(endpoint, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in router call: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Router call failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error in router call: {e}")
            raise RuntimeError(f"Router call failed: {str(e)}")
    
    def _run(self, *args, **kwargs) -> str:
        """Synchronous run - not implemented for async tools"""
        raise NotImplementedError("Use async _arun method")
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async run - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _arun")

class CreateTaskTool(RouterProxiedTool):
    """Tool for creating tasks via router-proxied PostgREST calls"""
    
    name: str = "create_task"
    description: str = "Create a new task for the user"
    
    class CreateTaskInput(BaseModel):
        title: str = Field(..., description="Task title")
        description: Optional[str] = Field(None, description="Task description")
        priority: str = Field(default="medium", description="Task priority (low, medium, high, urgent)")
        due_date: Optional[str] = Field(None, description="Due date in ISO format")
    
    args_schema: Type[BaseModel] = CreateTaskInput
    
    async def _arun(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[str] = None
    ) -> str:
        """Create a task via router-proxied PostgREST call"""
        
        try:
            task_data = {
                "user_id": self.user_id,
                "title": title,
                "description": description,
                "priority": priority,
                "status": "pending",
                "due_date": due_date
            }
            
            # Remove None values
            task_data = {k: v for k, v in task_data.items() if v is not None}
            
            # Make router-proxied call
            result = await self._make_router_call("POST", "/api/tasks", data=task_data)
            
            return f"Created task: {result.get('title', title)} (ID: {result.get('id', 'unknown')})"
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return f"Failed to create task: {str(e)}"

class GetTasksTool(RouterProxiedTool):
    """Tool for getting tasks via router-proxied PostgREST calls"""
    
    name: str = "get_tasks"
    description: str = "Get user's tasks with optional filtering"
    
    class GetTasksInput(BaseModel):
        status: Optional[str] = Field(None, description="Filter by status (pending, in_progress, completed)")
        limit: int = Field(default=10, description="Maximum number of tasks to return")
    
    args_schema: Type[BaseModel] = GetTasksInput
    
    async def _arun(
        self,
        status: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Get tasks via router-proxied PostgREST call"""
        
        try:
            # Build query parameters
            params = {
                "user_id": f"eq.{self.user_id}",
                "order": "created_at.desc",
                "limit": str(limit)
            }
            
            if status:
                params["status"] = f"eq.{status}"
            
            # Make router-proxied call
            tasks = await self._make_router_call("GET", "/api/tasks", params=params)
            
            if not tasks:
                return "No tasks found."
            
            # Format response
            task_list = []
            for task in tasks:
                task_info = f"- {task.get('title', 'Untitled')} ({task.get('status', 'unknown')})"
                if task.get('due_date'):
                    task_info += f" - Due: {task['due_date']}"
                task_list.append(task_info)
            
            return f"Found {len(tasks)} tasks:\n" + "\n".join(task_list)
            
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return f"Failed to get tasks: {str(e)}"

class ToolRegistry:
    """
    Registry for managing router-proxied tools
    
    This registry provides tools that make HTTP calls to our router,
    which then proxies them to PostgREST or other services.
    """
    
    def __init__(self, user_id: str, router_base_url: str = "http://localhost:8000"):
        self.user_id = user_id
        self.router_base_url = router_base_url
        self._tool_cache = {}
    
    async def get_basic_tools(self) -> List[BaseTool]:
        """
        Get basic tools for fallback agent
        
        Returns a minimal set of tools that work via router-proxied calls
        """
        
        if "basic" in self._tool_cache:
            return self._tool_cache["basic"]
        
        tools = [
            CreateTaskTool(
                user_id=self.user_id,
                router_base_url=self.router_base_url
            ),
            GetTasksTool(
                user_id=self.user_id,
                router_base_url=self.router_base_url
            )
        ]
        
        self._tool_cache["basic"] = tools
        logger.info(f"Created {len(tools)} basic tools for user {self.user_id}")
        
        return tools
    
    async def get_tools_for_agent(self, agent_name: str) -> List[BaseTool]:
        """
        Get tools for a specific agent
        
        This method could be enhanced to load agent-specific tools
        from the database or configuration.
        """
        
        cache_key = f"agent_{agent_name}"
        
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]
        
        # For now, return basic tools for all agents
        # This could be enhanced to load agent-specific tools from database
        tools = await self.get_basic_tools()
        
        # Add agent-specific tools based on agent name
        if agent_name == "email_digest_agent":
            # Could add email-specific tools here
            pass
        elif agent_name == "task_agent":
            # Could add additional task tools here
            pass
        
        self._tool_cache[cache_key] = tools
        return tools
    
    def clear_cache(self):
        """Clear tool cache"""
        self._tool_cache.clear()
        logger.info(f"Cleared tool cache for user {self.user_id}")
    
    async def create_custom_tool(
        self,
        name: str,
        description: str,
        endpoint: str,
        method: str = "POST",
        input_schema: Optional[Type[BaseModel]] = None
    ) -> RouterProxiedTool:
        """
        Create a custom router-proxied tool
        
        This allows dynamic creation of tools for specific endpoints
        """
        
        class CustomTool(RouterProxiedTool):
            name: str = name
            description: str = description
            args_schema: Type[BaseModel] = input_schema or BaseModel
            
            async def _arun(self, **kwargs) -> str:
                try:
                    result = await self._make_router_call(method, endpoint, data=kwargs)
                    return f"Operation completed: {result}"
                except Exception as e:
                    return f"Operation failed: {str(e)}"
        
        return CustomTool(
            user_id=self.user_id,
            router_base_url=self.router_base_url
        ) 