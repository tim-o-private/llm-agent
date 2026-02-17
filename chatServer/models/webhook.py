"""Webhook-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel


class SupabasePayload(BaseModel):
    type: str
    table: str
    record: Optional[dict] = None
    old_record: Optional[dict] = None
    webhook_schema: Optional[str] = None  # Renamed from schema to avoid conflict
