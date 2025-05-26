"""Authentication dependencies."""

from typing import Optional
from fastapi import HTTPException, Request, status
from jose import jwt, JWTError

try:
    from ..config.settings import get_settings
except ImportError:
    from chatServer.config.settings import get_settings


def get_current_user(request: Request) -> str:
    """Extract and validate the current user from JWT token."""
    settings = get_settings()
    
    auth_header = request.headers.get("Authorization")
    print("Authorization header:", auth_header)
    print("JWT secret (first 8 chars):", settings.supabase_jwt_secret[:8] if settings.supabase_jwt_secret else "None")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
        print("Decoded payload:", payload)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        return user_id
    except JWTError as e:
        print("JWTError:", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_jwt_from_request_context(request_for_token: Request) -> Optional[str]:
    """Extract JWT token from request context for agent loader."""
    auth_header = request_for_token.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None 