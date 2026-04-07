"""
Config proposal router — approve/revert agent-proposed config changes.

Completes the self-improvement feedback loop:
  Agent writes file → GitTracker commits → notification sent
  → User approves/reverts here → SyncService pushes to Supabase Storage.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_user_scoped_client
from ..dependencies.auth import get_current_user
from ..services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


class ProposalActionResponse(BaseModel):
    success: bool
    message: str
    synced_files: list[str] = []
    error: Optional[str] = None


def _build_services(db: UserScopedClient):
    """Build SelfImprovementService + SyncService for this request."""
    from ..sandbox.disclosure import DisclosureModel
    from ..sandbox.security_boundary import SecurityBoundary
    from ..sandbox.self_improvement import SelfImprovementService
    from ..sandbox.sync import SyncService
    from ..services.config_service import get_config_service

    security_boundary = SecurityBoundary()
    config_service = get_config_service()

    self_improvement = SelfImprovementService(
        security_boundary=security_boundary,
        disclosure_model=DisclosureModel(),
        db_client=db,
    )
    sync_service = SyncService(
        security_boundary=security_boundary,
        config_service=config_service,
    )

    return self_improvement, sync_service


def _get_sandbox(user_id: str):
    """Get provisioner + user_dir + git_tracker for a user's sandbox."""
    from ..sandbox.git_tracker import GitTracker
    from ..sandbox.provisioner import get_provisioner

    provisioner = get_provisioner()
    user_dir = provisioner.get_user_dir(user_id)
    git_tracker = GitTracker(user_dir)
    return provisioner, user_dir, git_tracker


@router.post("/{proposal_id}/approve", response_model=ProposalActionResponse)
async def approve_proposal(
    proposal_id: str,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Approve a config change proposal and sync to Supabase Storage."""
    self_improvement, sync_service = _build_services(db)

    # 1. Approve (updates status in DB + in-memory)
    proposal = await self_improvement.approve_change(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your proposal")

    # 2. Sync approved changes to Supabase Storage
    synced_files: list[str] = []
    try:
        provisioner, user_dir, git_tracker = _get_sandbox(user_id)
        await provisioner.get_or_create(user_id)
        synced_files = await sync_service.sync_to_storage(
            user_id=user_id,
            git_tracker=git_tracker,
            user_dir=user_dir,
            commit_hash=proposal.git_commit_hash,
        )
    except RuntimeError as e:
        # Sandbox not available — approval still recorded, sync skipped
        logger.warning("Sandbox unavailable for sync after approval: %s", e)

    # 3. Resolve the notification (via NotificationService — no DB in router)
    try:
        notif_service = NotificationService(db)
        await notif_service.resolve_proposal_notification(proposal_id, user_id, "approved")
    except Exception as e:
        logger.warning("Failed to resolve notification for proposal %s: %s", proposal_id, e)

    return ProposalActionResponse(
        success=True,
        message=f"Proposal approved. {len(synced_files)} file(s) synced to storage.",
        synced_files=synced_files,
    )


@router.post("/{proposal_id}/revert", response_model=ProposalActionResponse)
async def revert_proposal(
    proposal_id: str,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Revert a config change proposal (reject + git revert)."""
    self_improvement, _ = _build_services(db)

    # Need git_tracker for the revert
    try:
        provisioner, user_dir, git_tracker = _get_sandbox(user_id)
        await provisioner.get_or_create(user_id)
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Sandbox unavailable — cannot revert: {e}",
        )

    proposal = await self_improvement.reject_change(proposal_id, git_tracker)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your proposal")

    # Resolve the notification
    try:
        notif_service = NotificationService(db)
        await notif_service.resolve_proposal_notification(proposal_id, user_id, "reverted")
    except Exception as e:
        logger.warning("Failed to resolve notification for proposal %s: %s", proposal_id, e)

    return ProposalActionResponse(
        success=True,
        message="Proposal reverted.",
    )
