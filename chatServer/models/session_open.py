from pydantic import BaseModel


class SessionOpenRequest(BaseModel):
    agent_name: str
    session_id: str


class SessionOpenResponse(BaseModel):
    session_id: str
    response: str      # May be "WAKEUP_SILENT"
    is_new_user: bool
    silent: bool       # True if response starts with WAKEUP_SILENT
