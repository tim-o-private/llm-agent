"""Base API service for external API integrations."""
# @docs memory-bank/patterns/api-patterns.md#pattern-3-service-layer-pattern
# @rules memory-bank/rules/api-rules.json#api-003

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import httpx
from supabase import AsyncClient

try:
    from ..models.external_api import ServiceName, ExternalAPIConnectionResponse
except ImportError:
    from chatServer.models.external_api import ServiceName, ExternalAPIConnectionResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limiting information for an API service."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    current_minute_count: int = 0
    current_hour_count: int = 0
    current_day_count: int = 0
    minute_reset_time: float = field(default_factory=time.time)
    hour_reset_time: float = field(default_factory=time.time)
    day_reset_time: float = field(default_factory=time.time)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    data: Any
    expires_at: float
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class BaseAPIService(ABC):
    """Base class for external API services with rate limiting and caching."""
    
    def __init__(self, db_client: AsyncClient, service_name: ServiceName):
        """Initialize the base API service.
        
        Args:
            db_client: Supabase client for database operations
            service_name: Name of the external service
        """
        self.db_client = db_client
        self.service_name = service_name
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # In-memory rate limiting (per-user)
        self.rate_limits: Dict[str, RateLimitInfo] = {}
        
        # In-memory caching
        self.cache: Dict[str, CacheEntry] = {}
        
        # Service-specific rate limits (to be overridden by subclasses)
        self.default_rate_limits = RateLimitInfo(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.aclose()
    
    async def get_connection(self, user_id: str) -> Optional[ExternalAPIConnectionResponse]:
        """Get the API connection for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            API connection if exists and active, None otherwise
        """
        try:
            result = await self.db_client.table('external_api_connections').select('*').eq(
                'user_id', user_id
            ).eq('service_name', self.service_name.value).eq('is_active', True).execute()
            
            if result.data:
                connection_data = result.data[0]
                return ExternalAPIConnectionResponse(**connection_data)
            return None
        except Exception as e:
            logger.error(f"Error getting API connection for user {user_id}: {e}")
            return None
    
    async def update_tokens(self, user_id: str, access_token: str, 
                          refresh_token: Optional[str] = None,
                          expires_at: Optional[datetime] = None) -> bool:
        """Update OAuth tokens for a user connection.
        
        Args:
            user_id: User ID
            access_token: New access token
            refresh_token: New refresh token (optional)
            expires_at: Token expiration time (optional)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            update_data = {'access_token': access_token}
            if refresh_token:
                update_data['refresh_token'] = refresh_token
            if expires_at:
                update_data['token_expires_at'] = expires_at.isoformat()
            
            result = await self.db_client.table('external_api_connections').update(
                update_data
            ).eq('user_id', user_id).eq('service_name', self.service_name.value).execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error updating tokens for user {user_id}: {e}")
            return False
    
    def _get_rate_limit_info(self, user_id: str) -> RateLimitInfo:
        """Get or create rate limit info for a user."""
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = RateLimitInfo(
                requests_per_minute=self.default_rate_limits.requests_per_minute,
                requests_per_hour=self.default_rate_limits.requests_per_hour,
                requests_per_day=self.default_rate_limits.requests_per_day
            )
        return self.rate_limits[user_id]
    
    def _reset_rate_limit_counters(self, rate_limit: RateLimitInfo) -> None:
        """Reset rate limit counters if time windows have passed."""
        current_time = time.time()
        
        # Reset minute counter
        if current_time - rate_limit.minute_reset_time >= 60:
            rate_limit.current_minute_count = 0
            rate_limit.minute_reset_time = current_time
        
        # Reset hour counter
        if current_time - rate_limit.hour_reset_time >= 3600:
            rate_limit.current_hour_count = 0
            rate_limit.hour_reset_time = current_time
        
        # Reset day counter
        if current_time - rate_limit.day_reset_time >= 86400:
            rate_limit.current_day_count = 0
            rate_limit.day_reset_time = current_time
    
    async def _check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[float]]:
        """Check if request is within rate limits.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (is_allowed, wait_time_seconds)
        """
        rate_limit = self._get_rate_limit_info(user_id)
        self._reset_rate_limit_counters(rate_limit)
        
        # Check minute limit
        if rate_limit.current_minute_count >= rate_limit.requests_per_minute:
            wait_time = 60 - (time.time() - rate_limit.minute_reset_time)
            return False, max(0, wait_time)
        
        # Check hour limit
        if rate_limit.current_hour_count >= rate_limit.requests_per_hour:
            wait_time = 3600 - (time.time() - rate_limit.hour_reset_time)
            return False, max(0, wait_time)
        
        # Check day limit
        if rate_limit.current_day_count >= rate_limit.requests_per_day:
            wait_time = 86400 - (time.time() - rate_limit.day_reset_time)
            return False, max(0, wait_time)
        
        return True, None
    
    def _increment_rate_limit_counters(self, user_id: str) -> None:
        """Increment rate limit counters for a user."""
        rate_limit = self._get_rate_limit_info(user_id)
        rate_limit.current_minute_count += 1
        rate_limit.current_hour_count += 1
        rate_limit.current_day_count += 1
    
    def _get_cache_key(self, user_id: str, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        params_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{self.service_name.value}:{user_id}:{endpoint}:{params_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                return entry.data
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl_seconds: int) -> None:
        """Set data in cache with TTL."""
        expires_at = time.time() + ttl_seconds
        self.cache[cache_key] = CacheEntry(data=data, expires_at=expires_at)
    
    async def make_request(self, user_id: str, method: str, url: str, 
                          headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None,
                          json_data: Optional[Dict[str, Any]] = None,
                          cache_ttl: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Make an authenticated API request with rate limiting and caching.
        
        Args:
            user_id: User ID
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Additional headers
            params: Query parameters
            json_data: JSON request body
            cache_ttl: Cache TTL in seconds (for GET requests only)
            
        Returns:
            Response data or None if request failed
        """
        # Check rate limits
        is_allowed, wait_time = await self._check_rate_limit(user_id)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {user_id}, wait time: {wait_time}s")
            if wait_time and wait_time < 60:  # Only wait for short delays
                await asyncio.sleep(wait_time)
            else:
                return None
        
        # Check cache for GET requests
        if method.upper() == 'GET' and cache_ttl:
            cache_key = self._get_cache_key(user_id, url, params or {})
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data
        
        # Get connection and access token
        connection = await self.get_connection(user_id)
        if not connection:
            logger.error(f"No active connection found for user {user_id} and service {self.service_name}")
            return None
        
        # Check if token is expired and refresh if needed
        if connection.token_expires_at and datetime.now() >= connection.token_expires_at:
            refreshed = await self.refresh_token(user_id, connection)
            if not refreshed:
                logger.error(f"Failed to refresh token for user {user_id}")
                return None
            # Get updated connection
            connection = await self.get_connection(user_id)
            if not connection:
                return None
        
        # Prepare headers
        request_headers = headers or {}
        request_headers.update(await self._get_auth_headers(connection))
        
        try:
            # Make the request
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data
            )
            
            # Increment rate limit counters
            self._increment_rate_limit_counters(user_id)
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache GET responses
                if method.upper() == 'GET' and cache_ttl:
                    cache_key = self._get_cache_key(user_id, url, params or {})
                    self._set_cache(cache_key, data, cache_ttl)
                
                return data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None
    
    @abstractmethod
    async def _get_auth_headers(self, connection: ExternalAPIConnectionResponse) -> Dict[str, str]:
        """Get authentication headers for API requests.
        
        Args:
            connection: API connection with tokens
            
        Returns:
            Dictionary of authentication headers
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, user_id: str, connection: ExternalAPIConnectionResponse) -> bool:
        """Refresh OAuth token for a connection.
        
        Args:
            user_id: User ID
            connection: Current API connection
            
        Returns:
            True if refresh successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def test_connection(self, user_id: str) -> bool:
        """Test if the API connection is working.
        
        Args:
            user_id: User ID
            
        Returns:
            True if connection is working, False otherwise
        """
        pass 