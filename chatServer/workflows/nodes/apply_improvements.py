"""Apply improvements service node for introspection workflow.

Takes proposed improvements from the analysis steps and applies
each change via SelfImprovementService. When the bwrap sandbox is
available, each proposal is written to the user's sandbox dir, committed
via GitTracker, and a ChangeProposal is created (with user notification
at the configured trust tier). When the sandbox is not available
(BWRAP_ENABLED=false or provisioner not yet initialized), proposals are
logged and recorded as "proposed" status for later execution.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def apply_improvements(state: dict) -> str:
    """Apply proposed config changes from the introspection loop.

    Reads proposals from step_outputs["propose-changes"],
    applies each via SelfImprovementService.propose_change().
    """
    from ...sandbox.disclosure import DisclosureModel, TrustTier
    from ...sandbox.security_boundary import SecurityBoundary

    step_outputs = state.get("step_outputs", {})
    parameters = state.get("parameters", {})
    trust_tier: TrustTier = parameters.get("trust_tier", "inform")
    user_id: str = parameters.get("user_id", "")

    proposals_raw = step_outputs.get("propose-changes", "")
    if not proposals_raw:
        return json.dumps({"applied": [], "skipped": [], "failed": [], "message": "No proposals to apply"})

    proposals = _parse_proposals(proposals_raw)
    if not proposals:
        return json.dumps({"applied": [], "skipped": [], "failed": [], "message": "Could not parse proposals"})

    results: dict[str, list[dict[str, Any]]] = {
        "applied": [],
        "skipped": [],
        "failed": [],
    }

    security_boundary = SecurityBoundary()

    # Attempt to get the sandbox — degrade gracefully if unavailable
    provisioner = None
    self_improvement_service = None
    git_tracker = None

    if user_id:
        try:
            from ...sandbox.git_tracker import GitTracker
            from ...sandbox.provisioner import SandboxNotAvailableError, get_provisioner
            from ...sandbox.self_improvement import SelfImprovementService

            provisioner = get_provisioner()
            await provisioner.get_or_create(user_id)
            user_dir = provisioner.get_user_dir(user_id)
            git_tracker = GitTracker(user_dir)
            self_improvement_service = SelfImprovementService(
                security_boundary=security_boundary,
                disclosure_model=DisclosureModel(),
            )
            logger.info("Sandbox ready for user %s — proposals will be committed", user_id)
        except (RuntimeError, SandboxNotAvailableError) as e:
            logger.info(
                "Sandbox not available (user=%s): %s — proposals will be logged only",
                user_id, e,
            )

    for proposal in proposals:
        file_path = proposal.get("file_path", "")
        change_type = proposal.get("change_type", "update")
        rationale = proposal.get("rationale", "Introspection improvement")
        elevated = proposal.get("elevated", False)

        # Skip capability requests — those need a different flow
        if proposal.get("type") == "capability_request":
            results["skipped"].append({
                "file_path": "N/A",
                "reason": f"Capability request for {proposal.get('tool_name', 'unknown')} — requires manual review",
            })
            continue

        # Validate path against security boundary
        if not security_boundary.validate_write(file_path):
            results["skipped"].append({
                "file_path": file_path,
                "reason": "Security boundary: path is not mutable",
            })
            continue

        # Skip elevated changes unless trust tier allows
        if elevated and trust_tier == "inform":
            results["skipped"].append({
                "file_path": file_path,
                "reason": "Elevated change requires explicit approval at inform tier",
            })
            continue

        try:
            if self_improvement_service and git_tracker and provisioner:
                # Execute in sandbox: write file, commit, create proposal
                content = proposal.get("content") or proposal.get("diff_preview", "")
                user_dir = provisioner.get_user_dir(user_id)
                # Strip /user/ prefix to get path relative to user dir
                rel_path = file_path.lstrip("/")
                if rel_path.startswith("user/"):
                    rel_path = rel_path[len("user/"):]
                local_path = user_dir / rel_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(content)

                change_proposal = await self_improvement_service.propose_change(
                    user_id=user_id,
                    git_tracker=git_tracker,
                    file_path=file_path,
                    content=content,
                    description=rationale,
                    trust_tier=trust_tier,
                )
                results["applied"].append({
                    "file_path": file_path,
                    "change_type": change_type,
                    "rationale": rationale,
                    "status": "committed",
                    "proposal_id": change_proposal.id,
                    "commit_sha": change_proposal.git_commit_hash,
                })
            else:
                # Sandbox unavailable — log for later execution
                logger.info(
                    "Introspection proposal (sandbox unavailable): %s %s — %s",
                    change_type, file_path, rationale,
                )
                results["applied"].append({
                    "file_path": file_path,
                    "change_type": change_type,
                    "rationale": rationale,
                    "status": "proposed",
                })

        except Exception as e:
            logger.error("Failed to apply proposal for %s: %s", file_path, e)
            results["failed"].append({
                "file_path": file_path,
                "error": str(e),
            })

    return json.dumps(results, default=str)


def _parse_proposals(raw: str) -> list[dict[str, Any]]:
    """Extract proposal JSON objects from LLM output.

    The LLM may return proposals as a JSON array, individual JSON objects,
    or embedded in markdown code blocks.
    """
    import re

    # Try parsing as a direct JSON array
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            # Single proposal or wrapper
            if "proposals" in parsed:
                return parsed["proposals"]
            return [parsed]
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    code_blocks = re.findall(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    proposals = []
    for block in code_blocks:
        try:
            parsed = json.loads(block)
            if isinstance(parsed, list):
                proposals.extend(parsed)
            elif isinstance(parsed, dict):
                proposals.append(parsed)
        except json.JSONDecodeError:
            continue

    if proposals:
        return proposals

    # Try line-by-line JSON objects
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                proposals.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return proposals
