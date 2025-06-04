# Pydantic models for chat types in Clarity v2
# These correspond to the TypeScript types in webApp/src/types/chat.ts

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    agent_name: str = Field(default="assistant", description="Agent to use")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

class AgentAction(BaseModel):
    """Action performed by an agent"""
    type: str = Field(..., description="Type of action (e.g., 'tool_create_task', 'response')")
    data: Dict[str, Any] = Field(default={}, description="Action data")
    status: str = Field(..., description="Action status (completed, failed, pending)")
    timestamp: Optional[str] = Field(default=None, description="Action timestamp")
    
    def __init__(self, **kwargs):
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.utcnow().isoformat() + "Z"
        super().__init__(**kwargs)

class ChatResponse(BaseModel):
    """Chat response to frontend"""
    message: str = Field(..., description="AI response message")
    actions: List[AgentAction] = Field(default=[], description="Actions performed")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ChatSession(BaseModel):
    """Chat session information"""
    id: str = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    message_count: int = Field(default=0, description="Number of messages in session")

class ChatMessage(BaseModel):
    """Individual chat message"""
    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Message role (user, assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class ToolResult(BaseModel):
    id: str
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 