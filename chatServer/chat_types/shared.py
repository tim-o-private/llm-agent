# Shared Pydantic models for Clarity v2 backend
# Common types used across multiple modules

from typing import Optional, List, Dict, Any, Generic, TypeVar, Literal
from pydantic import BaseModel
from datetime import datetime

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None
    status: Literal['success', 'error']

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    count: int
    page: int
    limit: int
    total_pages: int

class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class FilterOptions(BaseModel):
    search: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class SortOptions(BaseModel):
    field: str
    direction: Literal['asc', 'desc'] = 'asc' 