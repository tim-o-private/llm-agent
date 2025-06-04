# Chat router for AI orchestration
# This router handles chat requests and orchestrates AI agents with router-proxied tools

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import time

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ai.agent_orchestrator import AgentOrchestrator
from chat_types.chat import ChatRequest, ChatResponse, AgentAction
from dependencies.auth import get_current_user_id

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequestModel(BaseModel):
    """Chat request model for API"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    agent_name: str = Field(default="assistant", description="Agent to use")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")

class ChatResponseModel(BaseModel):
    """Chat response model for API"""
    message: str = Field(..., description="AI response message")
    session_id: str = Field(..., description="Chat session ID")
    agent_name: str = Field(..., description="Agent that processed the request")
    timestamp: str = Field(..., description="Response timestamp")
    actions: List[Dict[str, Any]] = Field(default=[], description="Actions performed")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")

@router.post("/", response_model=ChatResponseModel)
async def chat_endpoint(
    request: ChatRequestModel,
    user_id: str = Depends(get_current_user_id)
) -> ChatResponseModel:
    """
    Main chat endpoint for AI orchestration
    
    This endpoint:
    1. Receives chat requests from frontend
    2. Orchestrates AI agents with router-proxied tools
    3. Returns structured responses with actions
    """
    
    start_time = time.time()
    session_id = request.session_id or f"chat_{user_id}_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"=== CHAT REQUEST START ===")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Agent: {request.agent_name}")
    logger.info(f"Message: {request.message[:100]}...")
    logger.info(f"Context: {request.context}")
    
    try:
        logger.debug(f"Creating AgentOrchestrator for user {user_id}")
        orchestrator_start = time.time()
        
        # Create agent orchestrator
        orchestrator = AgentOrchestrator(user_id)
        
        orchestrator_time = time.time() - orchestrator_start
        logger.debug(f"AgentOrchestrator created in {orchestrator_time:.2f}s")
        
        logger.debug(f"Processing message through orchestrator...")
        process_start = time.time()
        
        # Process message through AI orchestration
        response = await orchestrator.process_message(
            message=request.message,
            session_id=session_id,
            agent_name=request.agent_name,
            context=request.context or {}
        )
        
        process_time = time.time() - process_start
        total_time = time.time() - start_time
        
        logger.info(f"Message processed in {process_time:.2f}s")
        logger.info(f"Total request time: {total_time:.2f}s")
        logger.info(f"Response: {response.message[:100]}...")
        logger.info(f"Actions: {len(response.actions)}")
        logger.info(f"=== CHAT REQUEST END ===")
        
        # Convert to API response format
        return ChatResponseModel(
            message=response.message,
            session_id=session_id,
            agent_name=request.agent_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            actions=[action.dict() if hasattr(action, 'dict') else action for action in response.actions],
            metadata=response.metadata or {}
        )
        
    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"Chat processing failed for user {user_id} after {error_time:.2f}s: {e}", exc_info=True)
        
        # Return error response in expected format
        return ChatResponseModel(
            message=f"I apologize, but I encountered an error processing your request: {str(e)}",
            session_id=session_id,
            agent_name=request.agent_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            actions=[],
            metadata={"error": True, "error_message": str(e), "processing_time": error_time}
        )

@router.get("/health")
async def chat_health():
    """Health check for chat router"""
    return {
        "status": "healthy",
        "service": "chat-router",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    } 