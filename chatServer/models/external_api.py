"""Pydantic models for external API connections."""
# @docs memory-bank/patterns/api-patterns.md#pattern-5-pydantic-models-for-validation
# @rules memory-bank/rules/api-rules.json#api-005

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class ServiceName(str, Enum):
    """Supported external API services."""
    GMAIL = "gmail"
    GOOGLE_CALENDAR = "google_calendar"
    SLACK = "slack"


class ExternalAPIConnectionCreate(BaseModel):
    """Model for creating a new external API connection."""
    service_name: ServiceName
    access_token: str = Field(..., min_length=1)
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)
    service_user_id: Optional[str] = None
    service_user_email: Optional[str] = None

    @validator('access_token')
    def access_token_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Access token cannot be empty')
        return v.strip()


class ExternalAPIConnectionUpdate(BaseModel):
    """Model for updating an external API connection."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    service_user_id: Optional[str] = None
    service_user_email: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('access_token')
    def access_token_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Access token cannot be empty')
        return v.strip() if v else v


class ExternalAPIConnectionResponse(BaseModel):
    """Model for external API connection responses."""
    id: str
    user_id: str
    service_name: ServiceName
    token_expires_at: Optional[datetime]
    scopes: List[str]
    service_user_id: Optional[str]
    service_user_email: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool

    # Note: access_token and refresh_token are intentionally excluded from responses
    # for security reasons


class EmailMessage(BaseModel):
    """Model for email message data from Gmail API."""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    body: str
    date: datetime
    is_read: bool = False
    labels: List[str] = Field(default_factory=list)


class EmailThread(BaseModel):
    """Model for email thread data from Gmail API."""
    id: str
    subject: str
    messages: List[EmailMessage]
    participants: List[str]
    last_message_date: datetime
    message_count: int
    is_unread: bool = False


class EmailDigestRequest(BaseModel):
    """Model for requesting email digest generation."""
    hours_back: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    max_threads: int = Field(default=20, ge=1, le=100)
    include_read: bool = Field(default=False)

    @validator('hours_back')
    def validate_hours_back(cls, v):
        if v < 1 or v > 168:  # 1 week max
            raise ValueError('hours_back must be between 1 and 168 (1 week)')
        return v


class EmailDigestResponse(BaseModel):
    """Model for email digest response."""
    summary: str
    thread_count: int
    unread_count: int
    important_threads: List[EmailThread]
    generated_at: datetime
    time_period_hours: int
