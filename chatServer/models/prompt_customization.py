"""Prompt customization Pydantic models."""

from typing import Dict, Any
from pydantic import BaseModel, ConfigDict


class PromptCustomizationBase(BaseModel):
    agent_name: str
    customization_type: str = 'instruction_set'
    content: Dict[str, Any]  # JSONB content
    is_active: bool = True
    priority: int = 0


class PromptCustomizationCreate(PromptCustomizationBase):
    pass


class PromptCustomization(PromptCustomizationBase):
    id: str  # UUID as string
    user_id: str  # UUID as string
    created_at: Any  # datetime, will be serialized to string
    updated_at: Any  # datetime

    model_config = ConfigDict(from_attributes=True) 