from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class EmailProcessingJobResponse(BaseModel):
    id: str
    user_id: str
    connection_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
