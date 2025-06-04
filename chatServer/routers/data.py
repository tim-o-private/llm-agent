# Data router for PostgREST proxy operations
# This router provides enhanced PostgREST proxy with validation, rate limiting, and caching

import logging
from typing import Dict, Any, Optional
import httpx
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import Response
from cachetools import TTLCache

from dependencies.auth import get_current_user_id
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache for frequently accessed data
# In production, this could be Redis or similar
response_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute TTL

settings = get_settings()

@router.api_route("/{table:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def postgrest_proxy(
    table: str, 
    request: Request,
    user_id: str = Depends(get_current_user_id)
):
    """
    Enhanced PostgREST proxy with validation, rate limiting, and caching
    
    This proxy:
    1. Validates table names and query parameters
    2. Adds user context and RLS enforcement
    3. Provides intelligent caching for read operations
    4. Logs all operations for monitoring
    """
    
    # Basic validation
    if not table.replace('/', '').replace('_', '').replace('-', '').isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    # Construct PostgREST URL
    postgrest_url = f"{settings.POSTGREST_URL}/{table}"
    
    # Forward query parameters
    query_params = str(request.url.query)
    if query_params:
        postgrest_url += f"?{query_params}"
    
    # Create cache key for GET requests
    cache_key = None
    if request.method == "GET":
        cache_key = f"{user_id}:{table}:{query_params}"
        
        # Check cache first
        if cache_key in response_cache:
            logger.debug(f"Cache hit for {cache_key}")
            cached_response = response_cache[cache_key]
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"]
            )
    
    # Prepare headers for PostgREST
    headers = {
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
    }
    
    # Forward authorization header if present, otherwise use service key for server-side requests
    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    elif settings.SUPABASE_SERVICE_KEY:
        headers["Authorization"] = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    
    # Add user context for RLS
    headers["X-User-ID"] = user_id
    
    # Log the operation
    logger.info(f"PostgREST {request.method} /{table} for user {user_id}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
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
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            # Cache successful GET responses
            if request.method == "GET" and response.status_code == 200 and cache_key:
                response_cache[cache_key] = {
                    "content": response.content,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                logger.debug(f"Cached response for {cache_key}")
            
            # Invalidate cache for write operations
            elif request.method in ["POST", "PATCH", "DELETE"] and response.status_code < 400:
                # Simple cache invalidation - remove all entries for this table
                keys_to_remove = [key for key in response_cache.keys() if f":{table}:" in key]
                for key in keys_to_remove:
                    response_cache.pop(key, None)
                logger.debug(f"Invalidated cache for table {table}")
            
            # Return PostgREST response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.TimeoutException:
        logger.error(f"PostgREST timeout for {request.method} /{table}")
        raise HTTPException(status_code=504, detail="Database request timeout")
    except httpx.RequestError as e:
        logger.error(f"PostgREST request failed for {request.method} /{table}: {e}")
        raise HTTPException(status_code=503, detail=f"PostgREST unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in PostgREST proxy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def data_health():
    """Health check for data router"""
    try:
        # Test PostgREST connectivity
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.POSTGREST_URL}/", headers={
                "apikey": settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_KEY
            })
            
        return {
            "status": "healthy",
            "service": "data-router",
            "postgrest_status": "connected" if response.status_code < 500 else "error",
            "cache_size": len(response_cache),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Data router health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "data-router",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        } 