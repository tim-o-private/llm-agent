"""Gmail compose tools — draft and send email replies.

DraftEmailReplyTool: Fetches original email + writing style context for the agent to compose a draft.
SendEmailReplyTool: Sends an approved email reply via Gmail (REQUIRES_APPROVAL).
"""

import json
import logging
import os
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


def _get_gmail_compose_service():
    """Lazy import to avoid circular dependency via chatServer.services.__init__."""
    from chatServer.services.gmail_compose_service import GmailComposeService
    return GmailComposeService


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class DraftEmailReplyInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account")
    instructions: Optional[str] = Field(
        default=None,
        description="Optional guidance for the reply (e.g., 'tell them I agree but need more time')",
    )


class SendEmailReplyInput(BaseModel):
    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account to send from")
    body: str = Field(..., description="The approved reply text to send")
    subject: Optional[str] = Field(default=None, description="Override reply subject line")


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseGmailComposeTool(BaseTool):
    """Base class for Gmail compose tools."""

    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for context")
    supabase_url: str = Field(..., description="Supabase URL")
    supabase_key: str = Field(..., description="Supabase key")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _check_compose_scope(self, account: str) -> Optional[str]:
        """Check if the Gmail connection has compose scope.

        Returns None if scope is present, or an error message if missing.
        """
        try:
            from chatServer.tools.gmail_tools import GmailToolProvider
            connections = await GmailToolProvider._get_gmail_connections(self.user_id)
            for conn in connections:
                if conn.get("service_user_email") == account:
                    scopes = conn.get("scopes", [])
                    if COMPOSE_SCOPE not in scopes:
                        return (
                            f"I need send permission to reply from {account}. "
                            "Please re-connect your Gmail in Settings > Integrations to enable sending."
                        )
                    return None
            return (
                f"No Gmail connection found for {account}. "
                "Please connect this account in Settings > Integrations."
            )
        except Exception as e:
            logger.error(f"Failed to check compose scope: {e}")
            return f"Failed to check Gmail permissions: {e}"

    async def _get_provider(self, account: str):
        """Get GmailToolProvider for the specified account."""
        from chatServer.tools.gmail_tools import GmailToolProvider
        context = "scheduler" if "background" in self.agent_name.lower() else "user"
        return await GmailToolProvider.get_provider_for_account(
            self.user_id, account, context
        )


# ---------------------------------------------------------------------------
# Draft Email Reply Tool
# ---------------------------------------------------------------------------

class DraftEmailReplyTool(BaseGmailComposeTool):
    """Fetch an email and the user's writing style to prepare a reply."""

    name: str = "draft_email_reply"
    description: str = (
        "Fetch an email and the user's writing style to prepare a reply. "
        "Returns the original email content and writing style profile as context. "
        "The agent then composes the draft using this context."
    )
    args_schema: Type[BaseModel] = DraftEmailReplyInput

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        if channel in ("web", "telegram"):
            return (
                "Email Replies: When the user asks to reply to an email, use draft_email_reply "
                "to fetch the original email and your writing style context. Then compose a draft "
                "reply in the user's voice based on that context. Present the draft clearly as:\n"
                "---\n**To:** [recipient]\n**Subject:** [subject]\n\n[draft body]\n---\n"
                "Wait for approval. If they request changes, regenerate with updated instructions. "
                "Only use send_email_reply after explicit approval. "
                "Never send without showing the draft first. "
                "After presenting each draft, include: 'You can ask me to revise it "
                "(e.g., \"make it shorter\", \"more formal\"), or say \"send it\" to approve.'"
            )
        return None

    def _run(self, message_id: str, account: str, instructions: Optional[str] = None) -> str:
        return "draft_email_reply requires async execution. Use the async version (_arun)."

    async def _arun(self, message_id: str, account: str, instructions: Optional[str] = None) -> str:
        """Fetch original email and writing style context for the agent to compose a draft."""
        try:
            # 1. Check compose scope
            scope_error = await self._check_compose_scope(account)
            if scope_error:
                return scope_error

            # 2. Fetch original email via get_gmail pattern
            from chatServer.tools.gmail_rate_limiter import GmailRateLimiter

            rate_msg = GmailRateLimiter.check_and_increment(self.user_id, account, 1)
            if rate_msg:
                return rate_msg

            provider = await self._get_provider(account)
            gmail_tools = await provider.get_gmail_tools()
            get_tool = next(
                (t for t in gmail_tools if "get" in t.name.lower() and "message" in t.name.lower()),
                None,
            )
            if not get_tool:
                return "Gmail get message tool not available."

            original_email = await get_tool.arun({"message_id": message_id})

            # 3. Retrieve writing style from memory
            writing_style = await self._get_writing_style()

            # 4. Build structured context
            context = {
                "original_email": original_email,
                "account": account,
                "message_id": message_id,
            }

            if writing_style:
                context["writing_style"] = writing_style
            else:
                context["writing_style_note"] = (
                    "I don't have enough data on your writing style yet. "
                    "This draft will use a neutral tone. Connect more email for style learning."
                )

            if instructions:
                context["user_instructions"] = instructions

            return json.dumps(context, indent=2)

        except Exception as e:
            logger.error(f"draft_email_reply failed for user {self.user_id}: {e}")
            if "not found" in str(e).lower() or "404" in str(e):
                return "I couldn't find that email — it may have been deleted."
            return f"Failed to prepare email reply context: {e}"

    async def _get_writing_style(self) -> Optional[str]:
        """Retrieve the user's writing style from memory."""
        try:
            from chatServer.services.memory_client import MemoryClient
            mem_url = os.getenv("MIN_MEMORY_BASE_URL", "")
            mem_key = os.getenv("MIN_MEMORY_BACKEND_KEY", "")
            if not mem_url or not mem_key:
                return None
            client = MemoryClient(base_url=mem_url, backend_key=mem_key, user_id=self.user_id)
            result = await client.call_tool("search", {
                "query": "writing style communication tone",
                "limit": 1,
            })
            if result and str(result).strip() and "no memories found" not in str(result).lower():
                return str(result)
            return None
        except Exception as e:
            logger.warning(f"Failed to retrieve writing style: {e}")
            return None


# ---------------------------------------------------------------------------
# Send Email Reply Tool
# ---------------------------------------------------------------------------

class SendEmailReplyTool(BaseGmailComposeTool):
    """Send an approved email reply via Gmail. Requires user approval."""

    name: str = "send_email_reply"
    description: str = (
        "Send an approved email reply. This action requires user approval. "
        "Only call this after the user has reviewed and approved the draft."
    )
    args_schema: Type[BaseModel] = SendEmailReplyInput

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        # Prompt section is on DraftEmailReplyTool — no need to duplicate
        return None

    def _run(self, message_id: str, account: str, body: str, subject: Optional[str] = None) -> str:
        return "send_email_reply requires async execution. Use the async version (_arun)."

    async def _arun(self, message_id: str, account: str, body: str, subject: Optional[str] = None) -> str:
        """Send an email reply via Gmail."""
        try:
            # 1. Check compose scope
            scope_error = await self._check_compose_scope(account)
            if scope_error:
                return scope_error

            # 2. Get credentials
            provider = await self._get_provider(account)
            credentials = await provider._get_google_credentials()

            # 3. Send via GmailComposeService
            compose_svc = _get_gmail_compose_service()(credentials)
            result = compose_svc.send_reply(
                original_message_id=message_id,
                body=body,
                subject_override=subject,
            )

            return (
                f"Email sent successfully.\n"
                f"To: {result['to']}\n"
                f"Subject: {result['subject']}\n"
                f"Message ID: {result['message_id']}"
            )

        except Exception as e:
            logger.error(f"send_email_reply failed for user {self.user_id}: {e}")
            if "not found" in str(e).lower() or "404" in str(e):
                return "I couldn't find that email — it may have been deleted."
            return f"Failed to send email reply: {e}"

    async def get_approval_context(self, **kwargs) -> dict:
        """Return extra context metadata for the pending action.

        Called by the tool wrapper when queuing this tool for approval.
        Populates original_subject and original_sender for the frontend preview.
        """
        try:
            message_id = kwargs.get("message_id", "")
            account = kwargs.get("account", "")
            if not message_id or not account:
                return {}

            provider = await self._get_provider(account)
            credentials = await provider._get_google_credentials()

            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=credentials)
            original = service.users().messages().get(
                userId="me", id=message_id, format="metadata",
                metadataHeaders=["Subject", "From"],
            ).execute()

            headers = {
                h["name"]: h["value"]
                for h in original.get("payload", {}).get("headers", [])
            }

            return {
                "original_subject": headers.get("Subject", ""),
                "original_sender": headers.get("From", ""),
            }
        except Exception as e:
            logger.warning(f"Failed to get approval context: {e}")
            return {}
