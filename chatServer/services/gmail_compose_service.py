"""Gmail compose service — send email replies via the Gmail API.

Thin wrapper around the Gmail API send endpoint. Follows the CalendarService pattern.
"""

import base64
import email.mime.text
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailComposeService:
    """Send email replies via the Gmail API."""

    def __init__(self, credentials: Credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def send_reply(
        self,
        original_message_id: str,
        body: str,
        subject_override: Optional[str] = None,
    ) -> dict:
        """Send a reply to an existing email message.

        Args:
            original_message_id: Gmail message ID to reply to.
            body: Plain text reply body.
            subject_override: Override the Re: subject line.

        Returns:
            Dict with sent message id, threadId, to, and subject.
        """
        # 1. Fetch original message headers
        original = self.service.users().messages().get(
            userId="me", id=original_message_id, format="metadata",
            metadataHeaders=["Subject", "From", "Message-ID", "References"],
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in original.get("payload", {}).get("headers", [])
        }
        thread_id = original.get("threadId")

        # 2. Construct reply headers
        to = headers.get("From", "")
        subject = subject_override or f"Re: {headers.get('Subject', '')}"
        in_reply_to = headers.get("Message-ID", "")
        references = headers.get("References", "")
        if in_reply_to:
            references = f"{references} {in_reply_to}".strip()

        # 3. Build MIME message
        mime_message = email.mime.text.MIMEText(body, "plain")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        mime_message["In-Reply-To"] = in_reply_to
        mime_message["References"] = references

        raw = base64.urlsafe_b64encode(
            mime_message.as_bytes()
        ).decode("ascii")

        # 4. Send via Gmail API
        sent = self.service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": thread_id},
        ).execute()

        return {
            "message_id": sent.get("id"),
            "thread_id": sent.get("threadId"),
            "to": to,
            "subject": subject,
        }
