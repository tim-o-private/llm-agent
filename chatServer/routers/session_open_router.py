from fastapi import APIRouter, Depends

from ..dependencies.auth import get_current_user
from ..models.session_open import SessionOpenRequest, SessionOpenResponse
from ..services.session_open_service import SessionOpenService

router = APIRouter(prefix="/api/chat", tags=["session-open"])


@router.post("/session_open", response_model=SessionOpenResponse)
async def session_open(
    request: SessionOpenRequest,
    user_id: str = Depends(get_current_user),
) -> SessionOpenResponse:
    service = SessionOpenService()
    result = await service.run(
        user_id=user_id,
        agent_name=request.agent_name,
        session_id=request.session_id,
    )
    return SessionOpenResponse(**result)
