"""Authentication dependencies."""

import base64
import json
import logging
import urllib.request
from typing import Optional

from fastapi import HTTPException, Request, status
from jose import JWTError, jwk, jwt

try:
    from ..config.settings import get_settings
except ImportError:
    from chatServer.config.settings import get_settings

logger = logging.getLogger(__name__)

# Cache the JWKS keys in memory
_jwks_cache: dict | None = None


def _get_token_header(token: str) -> dict:
    """Decode the JWT header without verification."""
    try:
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        return json.loads(base64.urlsafe_b64decode(header_b64))
    except Exception:
        return {}


def _get_jwks(supabase_url: str) -> dict:
    """Fetch and cache JWKS from Supabase."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        _jwks_cache = json.loads(resp.read())
    return _jwks_cache


def _get_es256_key(supabase_url: str, kid: str | None = None):
    """Get the ES256 public key from JWKS."""
    jwks_data = _get_jwks(supabase_url)
    for key_data in jwks_data.get("keys", []):
        if kid and key_data.get("kid") != kid:
            continue
        if key_data.get("alg") == "ES256":
            return jwk.construct(key_data, "ES256")
    raise JWTError("No matching ES256 key found in JWKS")


def get_current_user(request: Request) -> str:
    """Extract and validate the current user from JWT token."""
    settings = get_settings()
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Missing or invalid authorization header")
    token = auth_header.split(" ")[1]
    header = _get_token_header(token)
    alg = header.get("alg", "HS256")
    try:
        if alg == "ES256":
            kid = header.get("kid")
            key = _get_es256_key(settings.supabase_url, kid)
            payload = jwt.decode(token, key, algorithms=["ES256"],
                                 audience="authenticated")
        else:
            payload = jwt.decode(token, settings.supabase_jwt_secret,
                                 algorithms=["HS256"], audience="authenticated")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="User ID not found in token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token")


async def get_jwt_from_request_context(request_for_token: Request) -> Optional[str]:
    auth_header = request_for_token.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None
