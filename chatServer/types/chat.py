# Pydantic models for chat types in Clarity v2
# These correspond to the TypeScript types in webApp/src/types/chat.ts

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class AgentAction(BaseModel):
    type: str
    data: Dict[str, Any]
    status: Literal['pending', 'in_progress', 'completed', 'failed']
    result: Optional[Any] = None
    error: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    agent_name: str
    actions: Optional[List[AgentAction]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class ToolResult(BaseModel):
    id: str
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 