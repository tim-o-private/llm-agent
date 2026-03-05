"""Gmail compose tools: draft and send email replies.

Stub implementation — logic filled in by FU-2 (GmailComposeService + _arun).
"""

from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class DraftEmailReplyInput(BaseModel):
    """Input schema for DraftEmailReplyTool."""

    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account")
    instructions: Optional[str] = Field(
        default=None,
        description="Optional guidance for the reply (e.g., 'tell them I agree but need more time')",
    )


class DraftEmailReplyTool(BaseTool):
    """Fetch an email and the user's writing style to prepare a reply.

    Returns the original email content and writing style profile as context.
    The agent then composes the draft using this context.
    """

    name: str = "draft_email_reply"
    description: str = (
        "Fetch an email and the user's writing style to prepare a reply. "
        "Returns the original email content and writing style profile as context. "
        "The agent then composes the draft using this context."
    )
    args_schema: Type[BaseModel] = DraftEmailReplyInput

    # Injected fields (populated by agent loader)
    user_id: str = Field(...)
    agent_name: str = Field(...)
    supabase_url: str = Field(...)
    supabase_key: str = Field(...)

    async def _arun(  # noqa: E501
        self, message_id: str, account: str, instructions: Optional[str] = None
    ) -> str:
        raise NotImplementedError("Implemented in FU-2")

    def _run(self, *args, **kwargs) -> str:  # type: ignore[override]
        raise NotImplementedError("Use async _arun")

    @classmethod
    def prompt_section(cls, channel: str) -> Optional[str]:
        if channel in ("web", "telegram"):
            return (
                "Email Replies: When the user asks to reply to an email, use draft_email_reply "
                "to fetch the original email and your writing style context. Then compose a draft "
                "reply in the user's voice based on that context. Present the draft and wait for approval. "  # noqa: E501
                "If they request changes, regenerate with updated instructions. "
                "Only use send_email_reply after explicit approval. "
                "Never send without showing the draft first. "
                "After presenting each draft, include a hint: 'You can ask me to revise it "
                "(e.g., \"make it shorter\", \"more formal\"), or say \"send it\" to approve.'"
            )
        return None


class SendEmailReplyInput(BaseModel):
    """Input schema for SendEmailReplyTool."""

    message_id: str = Field(..., description="Gmail message ID to reply to")
    account: str = Field(..., description="Email address of the Gmail account to send from")
    body: str = Field(..., description="The approved reply text to send")
    subject: Optional[str] = Field(default=None, description="Override reply subject line")


class SendEmailReplyTool(BaseTool):
    """Send an approved email reply via Gmail.

    This action requires user approval. Only call after the user has
    reviewed and approved the draft.
    """

    name: str = "send_email_reply"
    description: str = (
        "Send an approved email reply. This action requires user approval. "
        "Only call this after the user has reviewed and approved the draft."
    )
    args_schema: Type[BaseModel] = SendEmailReplyInput

    # Injected fields (populated by agent loader)
    user_id: str = Field(...)
    agent_name: str = Field(...)
    supabase_url: str = Field(...)
    supabase_key: str = Field(...)

    async def _arun(  # noqa: E501
        self, message_id: str, account: str, body: str, subject: Optional[str] = None
    ) -> str:
        raise NotImplementedError("Implemented in FU-2")

    def _run(self, *args, **kwargs) -> str:  # type: ignore[override]
        raise NotImplementedError("Use async _arun")
