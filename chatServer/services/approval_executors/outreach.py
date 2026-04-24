"""OutreachExecutor — dispatch outbound message by channel.

Channels:
- ``email`` — sends via Gmail (same path as ``email_draft`` without thread_ref).
- ``telegram`` — sends via ``TelegramBotService.send_notification``.
- ``other`` — approve-only; no execution, manual follow-up noted.
"""

from __future__ import annotations

import logging

from . import ExecutionResult
from .registry import register_executor

logger = logging.getLogger(__name__)


@register_executor("outreach")
class OutreachExecutor:
    """Send an outreach message via the specified channel."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        recipient = payload.get("recipient")
        message = payload.get("message")
        channel = payload.get("channel")

        if not recipient or not message or not channel:
            missing = [k for k in ("recipient", "message", "channel") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        if channel == "email":
            return await self._send_email(user_id, recipient, message, card)
        elif channel == "telegram":
            return await self._send_telegram(recipient, message, card)
        elif channel == "other":
            return ExecutionResult(
                success=True,
                result={"channel": "other", "recipient": recipient, "sent": False},
                activity_action=(
                    f"Outreach approved but channel 'other' has no executor "
                    f"— manual follow-up needed for {recipient}"
                ),
            )
        else:
            return ExecutionResult(
                success=False,
                error=f"Unknown outreach channel: {channel}",
            )

    async def _send_email(
        self, user_id: str, recipient: str, message: str, card: dict
    ) -> ExecutionResult:
        """Send outreach via Gmail."""
        try:
            credentials = await self._resolve_gmail_credentials(user_id)
            svc = self._build_compose_service(credentials)
            result = svc.send_new(
                to=[recipient],
                subject="Message from Clarity",
                body=message,
            )

            return ExecutionResult(
                success=True,
                result={
                    "channel": "email",
                    "recipient": recipient,
                    "sent": True,
                    "message_id": result.get("message_id"),
                },
                activity_action=f"Sent outreach email to {recipient}",
            )
        except Exception as exc:
            logger.error("Outreach email failed for user %s: %s", user_id, exc)
            return ExecutionResult(
                success=False,
                error=f"Failed to send outreach email: {exc}",
            )

    async def _send_telegram(
        self, recipient: str, message: str, card: dict
    ) -> ExecutionResult:
        """Send outreach via Telegram."""
        try:
            bot_svc = self._build_telegram_service()
            if bot_svc is None:
                return ExecutionResult(
                    success=False,
                    error="Telegram bot not configured. Set TELEGRAM_BOT_TOKEN.",
                )
            await bot_svc.send_notification(chat_id=recipient, text=message)

            return ExecutionResult(
                success=True,
                result={
                    "channel": "telegram",
                    "recipient": recipient,
                    "sent": True,
                },
                activity_action=f"Sent Telegram message to {recipient}",
            )
        except Exception as exc:
            logger.error("Outreach telegram failed: %s", exc)
            return ExecutionResult(
                success=False,
                error=f"Failed to send Telegram message: {exc}",
            )

    async def _resolve_gmail_credentials(self, user_id: str):
        """Resolve the user's first Gmail credentials."""
        from chatServer.tools.gmail_tools import GmailToolProvider

        providers = await GmailToolProvider.get_all_providers(user_id, "user")
        if not providers:
            raise ValueError(
                "Gmail not connected. Connect Gmail in Settings > Integrations."
            )
        provider = providers[0]
        return await provider._get_google_credentials()

    def _build_compose_service(self, credentials):
        """Create a GmailComposeService. Factored out for testability."""
        from chatServer.services.gmail_compose_service import GmailComposeService

        return GmailComposeService(credentials)

    def _build_telegram_service(self):
        """Create a TelegramBotService if configured. Returns None otherwise."""
        import os

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return None

        from chatServer.channels.telegram_bot import TelegramBotService

        return TelegramBotService(token)
