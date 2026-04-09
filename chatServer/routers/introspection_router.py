"""Introspection workflow router.

Provides a manual trigger endpoint for the introspection loop (AC-27).
Only registered when ENVIRONMENT != "production" — the route does not exist at all in prod.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/api/introspection", tags=["introspection"])


if os.getenv("ENVIRONMENT") != "production":

    @router.post("/trigger")
    async def trigger_introspection(
        user_id: str = Depends(get_current_user),
    ) -> dict:
        """Manually trigger the introspection loop for the authenticated user.

        Non-production only (AC-27). Returns the job handler result dict.
        """
        from ..services.job_handlers import handle_introspection

        try:
            result = await handle_introspection({"input": {"user_id": user_id}})
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

        return {"status": "triggered", "result": result}
