"""SelfImprovementService — orchestrates the agent self-improvement flow.

Flow: agent writes file -> GitTracker commits -> diff generated
   -> notification sent -> user approves/rejects -> revert if rejected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .disclosure import ChangeDescription, DisclosureModel, TrustTier
from .git_tracker import GitTracker
from .security_boundary import SecurityBoundary

logger = logging.getLogger(__name__)


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVERTED = "reverted"


@dataclass
class ChangeProposal:
    """A proposed configuration change from the agent."""

    id: str
    user_id: str
    file_path: str
    description: str
    git_commit_hash: str
    diff_text: str
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_approved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfImprovementService:
    """Orchestrates the self-improvement lifecycle.

    Dependencies are injected to keep this testable without a running
    database, sandbox, or notification service.
    """

    def __init__(
        self,
        security_boundary: SecurityBoundary,
        disclosure_model: DisclosureModel,
        notification_service=None,  # noqa: ANN001 — NotificationService, optional
        db_client=None,  # noqa: ANN001 — Supabase client, optional
    ) -> None:
        self._boundary = security_boundary
        self._disclosure = disclosure_model
        self._notification_service = notification_service
        self._db = db_client
        self._proposals: dict[str, ChangeProposal] = {}  # in-memory fallback

    async def propose_change(
        self,
        user_id: str,
        git_tracker: GitTracker,
        file_path: str,
        content: str,
        description: str,
        trust_tier: TrustTier = "inform",
    ) -> ChangeProposal:
        """Propose a config change: validate, write, commit, notify.

        The file should already be written to the sandbox filesystem
        before calling this method. This commits it and creates the
        proposal record.
        """
        if not self._boundary.validate_write(file_path):
            raise PermissionError(
                f"Write to {file_path} rejected by security boundary"
            )

        action = "updated"  # default; could detect create vs update
        commit_msg = f"Agent: {action} {file_path}"
        commit = await git_tracker.commit(commit_msg)

        if commit is None:
            raise ValueError("No changes to commit")

        diff_text = await git_tracker.diff(commit.sha)

        import uuid
        proposal_id = str(uuid.uuid4())

        proposal = ChangeProposal(
            id=proposal_id,
            user_id=user_id,
            file_path=file_path,
            description=description,
            git_commit_hash=commit.sha,
            diff_text=diff_text,
            metadata={
                "trust_tier": trust_tier,
                "elevated_review": self._boundary.requires_elevated_review(file_path),
            },
        )

        # Persist
        if self._db:
            await self._persist_proposal(proposal)
        self._proposals[proposal_id] = proposal

        # Notify
        await self._send_notification(proposal, trust_tier)

        return proposal

    async def approve_change(self, proposal_id: str) -> ChangeProposal | None:
        """Mark a proposal as approved by the user."""
        proposal = await self._get_proposal(proposal_id)
        if not proposal:
            return None

        proposal.status = ProposalStatus.APPROVED
        proposal.user_approved = True
        await self._update_proposal_status(proposal)
        return proposal

    async def reject_change(
        self,
        proposal_id: str,
        git_tracker: GitTracker,
    ) -> ChangeProposal | None:
        """Reject a proposal and revert the commit."""
        proposal = await self._get_proposal(proposal_id)
        if not proposal:
            return None

        revert_commit = await git_tracker.revert(proposal.git_commit_hash)
        if revert_commit:
            proposal.status = ProposalStatus.REVERTED
            proposal.metadata["revert_commit"] = revert_commit.sha
        else:
            proposal.status = ProposalStatus.REJECTED
            logger.warning(
                "Revert failed for proposal %s (commit %s)",
                proposal_id,
                proposal.git_commit_hash,
            )

        await self._update_proposal_status(proposal)
        return proposal

    async def auto_rollback_check(
        self,
        user_id: str,
        git_tracker: GitTracker,
        metrics: dict[str, Any] | None = None,
    ) -> ChangeProposal | None:
        """Check behavioral metrics and revert if degraded.

        Returns the reverted proposal, or None if no rollback needed.

        Conservative: only triggers on >2 sigma degradation attributable
        to a specific commit. User-approved commits are never rolled back.
        """
        recent = [
            p for p in self._proposals.values()
            if p.user_id == user_id
            and p.status in (ProposalStatus.PENDING, ProposalStatus.APPROVED)
            and not p.user_approved
        ]
        if not recent:
            return None

        if not metrics:
            return None

        degradation = metrics.get("degradation_sigma", 0.0)
        if degradation <= 2.0:
            return None

        causal_id = metrics.get("causal_proposal_id")
        if not causal_id:
            # Can't attribute — notify without reverting
            if self._notification_service:
                await self._notification_service.notify_user(
                    user_id=user_id,
                    title="Possible quality degradation",
                    body=(
                        "I noticed some quality metrics have dropped, but I can't "
                        "attribute it to a specific change. You may want to review "
                        "recent config changes."
                    ),
                    category="auto_rollback",
                    type="notify",
                )
            return None

        proposal = await self._get_proposal(causal_id)
        if not proposal or proposal.user_approved:
            return None

        revert_commit = await git_tracker.revert(proposal.git_commit_hash)
        if revert_commit:
            proposal.status = ProposalStatus.REVERTED
            proposal.metadata["revert_commit"] = revert_commit.sha
            proposal.metadata["auto_rollback"] = True
            proposal.metadata["degradation_sigma"] = degradation
            await self._update_proposal_status(proposal)

            if self._notification_service:
                await self._notification_service.notify_user(
                    user_id=user_id,
                    title="Auto-reverted a recent change",
                    body=(
                        f"I noticed my recent change to {proposal.file_path} "
                        f"wasn't working well. I've reverted it."
                    ),
                    category="auto_rollback",
                    type="notify",
                )

        return proposal

    # -- internal helpers -----------------------------------------------------

    async def _get_proposal(self, proposal_id: str) -> ChangeProposal | None:
        # Check in-memory cache first
        if proposal_id in self._proposals:
            return self._proposals[proposal_id]

        # Fall back to DB (handles restart — proposals persist across restarts)
        if not self._db:
            return None

        try:
            result = await self._db.table("config_change_proposals").select("*").eq(
                "id", proposal_id,
            ).execute()
            rows = result.data
            if not rows:
                return None
            row = rows[0]
            proposal = ChangeProposal(
                id=row["id"],
                user_id=row["user_id"],
                file_path=row["file_path"],
                description=row["change_description"],
                git_commit_hash=row["git_commit_hash"],
                diff_text=row.get("diff_text", ""),  # not stored in DB — empty on reload
                status=ProposalStatus(row["status"]),
            )
            self._proposals[proposal_id] = proposal
            return proposal
        except Exception:
            logger.warning("Failed to load proposal %s from DB", proposal_id, exc_info=True)
            return None

    async def _persist_proposal(self, proposal: ChangeProposal) -> None:
        """Write proposal to config_change_proposals table."""
        try:
            await self._db.table("config_change_proposals").insert({
                "id": proposal.id,
                "user_id": proposal.user_id,
                "file_path": proposal.file_path,
                "change_description": proposal.description,
                "git_commit_hash": proposal.git_commit_hash,
                "status": proposal.status.value,
            }).execute()
        except Exception:
            logger.warning("Failed to persist proposal %s", proposal.id, exc_info=True)

    async def _update_proposal_status(self, proposal: ChangeProposal) -> None:
        if self._db:
            try:
                await self._db.table("config_change_proposals").update({
                    "status": proposal.status.value,
                }).eq("id", proposal.id).execute()
            except Exception:
                logger.warning("Failed to update proposal %s", proposal.id, exc_info=True)

    async def _send_notification(
        self,
        proposal: ChangeProposal,
        trust_tier: TrustTier,
    ) -> None:
        if not self._notification_service:
            return

        change = ChangeDescription(
            file_path=proposal.file_path,
            action="updated",
            summary=proposal.description,
            commit_sha=proposal.git_commit_hash,
        )

        body = self._disclosure.format_change_notification(change, trust_tier)
        if body is None:
            # Act tier — silent, no notification
            return

        notification_type = "notify" if trust_tier == "inform" else "silent"
        await self._notification_service.notify_user(
            user_id=proposal.user_id,
            title="Configuration change",
            body=body,
            category="config_change",
            type=notification_type,
            metadata={
                "proposal_id": proposal.id,
                "commit_sha": proposal.git_commit_hash,
                "file_path": proposal.file_path,
                "actions": ["approve", "revert"],
            },
        )
