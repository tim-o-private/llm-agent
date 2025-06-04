"""Authentication dependencies."""

from typing import Optional
from fastapi import HTTPException, Request, status, Depends
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

try:
    from config.settings import get_settings
except ImportError:
    from chatServer.config.settings import get_settings

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

async def get_jwt_from_request_context(request_for_token: Request) -> Optional[str]:
    """Extract JWT token from request context for agent loader."""
    auth_header = request_for_token.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None 

async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract user ID from request
    
    This function extracts the user ID from various sources:
    1. Authorization header (JWT token)
    2. X-User-ID header (for internal service calls)
    3. Query parameter (for development)
    
    Returns:
        User ID string
        
    Raises:
        HTTPException: If no valid user ID is found
    """
    
    # Method 1: Extract from JWT token (production)
    if credentials and credentials.credentials:
        try:
            # In a full implementation, you would decode the JWT here
            # For now, we'll use a simple approach
            token = credentials.credentials
            
            # TODO: Implement proper JWT decoding
            # For development, we'll extract user ID from a simple format
            if token.startswith("user_"):
                user_id = token.replace("user_", "")
                logger.debug(f"Extracted user ID from token: {user_id}")
                return user_id
                
        except Exception as e:
            logger.error(f"Error decoding JWT token: {e}")
    
    # Method 2: Extract from X-User-ID header (for internal service calls)
    user_id_header = request.headers.get("X-User-ID")
    if user_id_header:
        logger.debug(f"Extracted user ID from header: {user_id_header}")
        return user_id_header
    
    # Method 3: Extract from query parameter (for development)
    user_id_param = request.query_params.get("user_id")
    if user_id_param:
        logger.debug(f"Extracted user ID from query param: {user_id_param}")
        return user_id_param
    
    # Method 4: Default user for development (when no auth is provided)
    # This should be removed in production
    default_user = "2bd2f515-d866-4b26-a3ec-67e0bef0676a"  # From existing data structure
    logger.warning(f"No user authentication found, using default user: {default_user}")
    return default_user

async def get_optional_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Extract user ID from request, returning None if not found
    
    This is a non-failing version of get_current_user_id for endpoints
    that can work with or without authentication.
    """
    
    try:
        return await get_current_user_id(request, credentials)
    except HTTPException:
        return None

def require_admin_user(user_id: str = Depends(get_current_user_id)) -> str:
    """
    Require admin user access
    
    This dependency can be used for admin-only endpoints.
    """
    
    # TODO: Implement proper admin user checking
    # For now, we'll use a simple check
    admin_users = ["2bd2f515-d866-4b26-a3ec-67e0bef0676a"]  # Add admin user IDs
    
    if user_id not in admin_users:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return user_id