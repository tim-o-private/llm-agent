"""EmailDraftExecutor — send email via Gmail API.

Supports both reply (``thread_ref`` present) and new email (``thread_ref`` absent).
Uses the user's first connected Gmail account (Option B per SPEC-052).
"""

from __future__ import annotations

import logging

from . import ExecutionResult
from .registry import register_executor

logger = logging.getLogger(__name__)

COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


@register_executor("email_draft")
class EmailDraftExecutor:
    """Send an email via GmailComposeService."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        to = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        thread_ref = payload.get("thread_ref")

        if not to or not subject or not body:
            missing = [k for k in ("to", "subject", "body") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        try:
            credentials = await self._resolve_credentials(user_id)
        except Exception as exc:
            return ExecutionResult(
                success=False,
                error=f"Gmail credentials unavailable: {exc}",
            )

        try:
            # Check compose scope
            scope_error = await self._check_scope(user_id)
            if scope_error:
                return ExecutionResult(success=False, error=scope_error)

            svc = self._build_compose_service(credentials)

            if thread_ref:
                result = svc.send_reply(
                    original_message_id=thread_ref,
                    body=body,
                    subject_override=subject,
                )
            else:
                result = svc.send_new(
                    to=to if isinstance(to, list) else [to],
                    subject=subject,
                    body=body,
                )

            title = card.get("title", "email")
            recipients = ", ".join(to) if isinstance(to, list) else to
            return ExecutionResult(
                success=True,
                result=result,
                activity_action=f"Sent email to {recipients} (Re: {subject})",
            )
        except Exception as exc:
            logger.error("EmailDraftExecutor failed for user %s: %s", user_id, exc)
            return ExecutionResult(
                success=False,
                error=f"Gmail API error: {exc}",
            )

    def _build_compose_service(self, credentials):
        """Create a GmailComposeService. Factored out for testability."""
        from chatServer.services.gmail_compose_service import GmailComposeService

        return GmailComposeService(credentials)

    async def _resolve_credentials(self, user_id: str):
        """Resolve the user's first Gmail credentials."""
        from chatServer.tools.gmail_tools import GmailToolProvider

        providers = await GmailToolProvider.get_all_providers(user_id, "user")
        if not providers:
            raise ValueError(
                "Gmail not connected. Connect Gmail in Settings > Integrations."
            )
        provider = providers[0]
        return await provider._get_google_credentials()

    async def _check_scope(self, user_id: str) -> str | None:
        """Check if the user has compose scope. Returns error string or None."""
        try:
            from chatServer.tools.gmail_tools import GmailToolProvider

            connections = await GmailToolProvider._get_gmail_connections(user_id)
            if not connections:
                return "Gmail not connected. Connect Gmail in Settings > Integrations."

            conn = connections[0]
            scopes = conn.get("scopes", [])
            if COMPOSE_SCOPE not in scopes:
                return (
                    "Gmail compose permission missing. Reconnect Gmail in "
                    "Settings > Integrations to enable sending."
                )
            return None
        except Exception as exc:
            return f"Failed to check Gmail permissions: {exc}"
