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

# Basic configuration
# Use Supabase hosted PostgREST API
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://dsyakikfxlhjszyhlmaa.supabase.co")
POSTGREST_URL = f"{SUPABASE_URL}/rest/v1"
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Clarity v2 Router starting up...")
    logger.info(f"PostgREST URL: {POSTGREST_URL}")
    logger.info(f"CORS Origins: {CORS_ORIGINS}")
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
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "clarity-v2-router",
        "version": "2.0.0",
        "postgrest_url": POSTGREST_URL,
        "supabase_url": SUPABASE_URL
    }

# PostgREST proxy for data operations
@app.api_route("/api/{table:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def postgrest_proxy(table: str, request: Request):
    """Proxy all data requests to PostgREST with validation and rate limiting"""
    
    # Basic validation
    if not table.replace('/', '').replace('_', '').isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    # Construct PostgREST URL
    postgrest_url = f"{POSTGREST_URL}/{table}"
    
    # Forward query parameters
    query_params = str(request.url.query)
    if query_params:
        postgrest_url += f"?{query_params}"
    
    # Prepare headers for PostgREST
    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "apikey": SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY
    }
    
    # Forward authorization header if present, otherwise use service key for server-side requests
    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    elif SUPABASE_SERVICE_KEY:
        headers["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Forward request to PostgREST
            if request.method == "GET":
                response = await client.get(postgrest_url, headers=headers)
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(postgrest_url, headers=headers, content=body)
            elif request.method == "PATCH":
                body = await request.body()
                response = await client.patch(postgrest_url, headers=headers, content=body)
            elif request.method == "DELETE":
                response = await client.delete(postgrest_url, headers=headers)
            
            # Return PostgREST response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"PostgREST request failed: {e}")
        raise HTTPException(status_code=503, detail=f"PostgREST unavailable: {str(e)}")

# Chat gateway for AI orchestration
@app.post("/chat")
async def chat_gateway(request: Dict[str, Any]):
    """Chat gateway for AI orchestration - placeholder for Phase 4"""
    
    message = request.get("message", "")
    session_id = request.get("session_id")
    agent_name = request.get("agent_name", "assistant")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # TODO: Phase 4 - Implement AI orchestration
    # For now, return a simple response
    return {
        "message": f"Echo: {message}",
        "session_id": session_id or "temp-session",
        "agent_name": agent_name,
        "timestamp": "2025-01-30T00:00:00Z",
        "actions": [],
        "metadata": {"status": "placeholder"}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 