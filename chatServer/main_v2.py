# Clarity v2 - Minimal FastAPI Router + Chat Gateway
# This replaces the complex chatServer/main.py with a simple router that:
# 1. Proxies PostgREST calls for data operations (/api/*)
# 2. Provides chat gateway for AI orchestration (/chat)

import os
import logging
from typing import Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx

# Import new router components
from routers.chat import router as chat_router
from routers.data import router as data_router
from config.settings import get_settings

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Clarity v2 Router starting up...")
    logger.info(f"PostgREST URL: {settings.POSTGREST_URL}")
    logger.info(f"CORS Origins: {settings.ALLOWED_ORIGINS}")
    
    # Validate required settings
    missing_settings = settings.validate_required_settings()
    if missing_settings:
        logger.warning(f"Missing settings: {missing_settings}")
        logger.warning("Some features may not work correctly")
    
    yield
    logger.info("Clarity v2 Router shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Clarity v2 Router",
    description="Router with PostgREST proxy + AI chat gateway for Clarity v2",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(data_router, prefix="/api", tags=["data"])

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    
    # Check PostgREST connectivity
    postgrest_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.POSTGREST_URL}/", headers={
                "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
            })
            postgrest_status = "connected" if response.status_code < 500 else "error"
    except Exception as e:
        logger.error(f"PostgREST health check failed: {e}")
        postgrest_status = "error"
    
    return {
        "status": "healthy",
        "service": "clarity-v2-router",
        "version": "2.0.0",
        "components": {
            "postgrest": postgrest_status,
            "chat_gateway": "active",
            "data_proxy": "active"
        },
        "configuration": {
            "supabase_url": settings.SUPABASE_URL,
            "postgrest_url": settings.POSTGREST_URL,
            "development_mode": settings.DEVELOPMENT_MODE,
            "cors_origins": len(settings.ALLOWED_ORIGINS)
        }
    }

# Legacy compatibility endpoint (for existing frontend)
@app.post("/chat")
async def legacy_chat_endpoint(request: Dict[str, Any]):
    """
    Legacy chat endpoint for backward compatibility
    
    This endpoint redirects to the new chat router while maintaining
    compatibility with existing frontend code.
    """
    
    logger.info("Legacy chat endpoint called, redirecting to new router")
    
    # Forward to new chat router
    from routers.chat import chat_endpoint
    from dependencies.auth import get_current_user_id
    from routers.chat import ChatRequestModel
    
    try:
        # Convert legacy request to new format
        chat_request = ChatRequestModel(
            message=request.get("message", ""),
            session_id=request.get("session_id"),
            agent_name=request.get("agent_name", "assistant"),
            context=request.get("context")
        )
        
        # Get user ID (using default for legacy compatibility)
        user_id = "2bd2f515-d866-4b26-a3ec-67e0bef0676a"  # Default user
        
        # Call new chat endpoint
        response = await chat_endpoint(chat_request, user_id)
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Legacy chat endpoint error: {e}")
        return {
            "message": f"I apologize, but I encountered an error: {str(e)}",
            "session_id": request.get("session_id", "error"),
            "agent_name": request.get("agent_name", "assistant"),
            "timestamp": "2025-01-30T00:00:00Z",
            "actions": [],
            "metadata": {"error": True, "legacy_endpoint": True}
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.ROUTER_HOST, 
        port=settings.ROUTER_PORT,
        log_level=settings.LOG_LEVEL.lower()
    ) 