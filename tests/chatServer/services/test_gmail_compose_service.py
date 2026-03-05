"""Tests for GmailComposeService — SPEC-029 AC-12, AC-13, AC-14, AC-22."""

import base64
import email
from unittest.mock import MagicMock, patch

import pytest

from chatServer.services.gmail_compose_service import GmailComposeService


@pytest.fixture
def mock_credentials():
    return MagicMock()


@pytest.fixture
def mock_gmail_service(mock_credentials):
    """Build a GmailComposeService with a mocked Gmail API service."""
    with patch("chatServer.services.gmail_compose_service.build") as mock_build:
        mock_api = MagicMock()
        mock_build.return_value = mock_api
        svc = GmailComposeService(mock_credentials)
        yield svc, mock_api


def _setup_original_message(mock_api, headers=None, thread_id="thread-abc"):
    """Configure the mock to return an original message with specified headers."""
    default_headers = {
        "Subject": "Renovation Timeline",
        "From": "mike@example.com",
        "Message-ID": "<msg-123@mail.gmail.com>",
        "References": "<prev-msg@mail.gmail.com>",
    }
    if headers:
        default_headers.update(headers)

    header_list = [{"name": k, "value": v} for k, v in default_headers.items()]

    mock_api.users().messages().get().execute.return_value = {
        "threadId": thread_id,
        "payload": {"headers": header_list},
    }

    # Also set up send response
    mock_api.users().messages().send().execute.return_value = {
        "id": "sent-msg-456",
        "threadId": thread_id,
    }


class TestSendReply:
    def test_happy_path(self, mock_gmail_service):
        """AC-12: send_reply constructs and sends a reply."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api)

        result = svc.send_reply(
            original_message_id="msg-123",
            body="Sounds good — let's aim for Thursday.",
        )

        assert result["message_id"] == "sent-msg-456"
        assert result["thread_id"] == "thread-abc"
        assert result["to"] == "mike@example.com"
        assert result["subject"] == "Re: Renovation Timeline"

    def test_re_prefix_on_subject(self, mock_gmail_service):
        """AC-13: Subject gets Re: prefix."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api, {"Subject": "Meeting Tomorrow"})

        result = svc.send_reply(original_message_id="msg-123", body="OK")

        assert result["subject"] == "Re: Meeting Tomorrow"

    def test_subject_override(self, mock_gmail_service):
        """AC-13: subject_override replaces the default."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api)

        result = svc.send_reply(
            original_message_id="msg-123",
            body="OK",
            subject_override="Custom Subject",
        )

        assert result["subject"] == "Custom Subject"

    def test_preserves_thread_id(self, mock_gmail_service):
        """AC-13: threadId is preserved in the send request."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api, thread_id="thread-xyz")

        svc.send_reply(original_message_id="msg-123", body="OK")

        # Find the send call with userId/body kwargs (the real call, not the chain setup)
        send_mock = mock_api.users().messages().send
        # Get the last call with keyword args
        found = False
        for call in send_mock.call_args_list:
            kwargs = call[1] if call[1] else {}
            if "body" in kwargs:
                assert kwargs["body"]["threadId"] == "thread-xyz"
                found = True
                break
        assert found, "send() was not called with body kwarg"

    def test_threading_headers(self, mock_gmail_service):
        """AC-13: In-Reply-To and References headers are set correctly."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api)

        svc.send_reply(original_message_id="msg-123", body="Hello")

        # Extract the raw MIME message from the send call
        send_call = mock_api.users().messages().send
        call_kwargs = send_call.call_args
        body_arg = call_kwargs[1]["body"] if call_kwargs[1] else call_kwargs[0][0]
        raw_bytes = base64.urlsafe_b64decode(body_arg["raw"])
        msg = email.message_from_bytes(raw_bytes)

        assert msg["In-Reply-To"] == "<msg-123@mail.gmail.com>"
        assert "<msg-123@mail.gmail.com>" in msg["References"]
        assert "<prev-msg@mail.gmail.com>" in msg["References"]

    def test_rfc2822_encoding(self, mock_gmail_service):
        """AC-14, AC-22: Message body is text/plain MIME and base64url encoded."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api)

        svc.send_reply(original_message_id="msg-123", body="Test body with unicode: café")

        send_call = mock_api.users().messages().send
        call_kwargs = send_call.call_args
        body_arg = call_kwargs[1]["body"] if call_kwargs[1] else call_kwargs[0][0]

        # Should be valid base64url
        raw_bytes = base64.urlsafe_b64decode(body_arg["raw"])
        msg = email.message_from_bytes(raw_bytes)

        assert msg.get_content_type() == "text/plain"
        # Body should contain our text
        payload = msg.get_payload(decode=True).decode()
        assert "café" in payload

    def test_missing_from_header(self, mock_gmail_service):
        """AC-22: Handles missing From header gracefully (empty To)."""
        svc, mock_api = mock_gmail_service
        _setup_original_message(mock_api, {"From": None})

        # Remove the From header explicitly
        mock_api.users().messages().get().execute.return_value = {
            "threadId": "thread-abc",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "Message-ID", "value": "<msg@test>"},
                ]
            },
        }

        result = svc.send_reply(original_message_id="msg-123", body="OK")
        assert result["to"] == ""

    def test_missing_subject_header(self, mock_gmail_service):
        """AC-22: Handles missing Subject header gracefully."""
        svc, mock_api = mock_gmail_service
        mock_api.users().messages().get().execute.return_value = {
            "threadId": "thread-abc",
            "payload": {
                "headers": [
                    {"name": "From", "value": "someone@test.com"},
                    {"name": "Message-ID", "value": "<msg@test>"},
                ]
            },
        }
        mock_api.users().messages().send().execute.return_value = {
            "id": "sent-1", "threadId": "thread-abc",
        }

        result = svc.send_reply(original_message_id="msg-123", body="OK")
        assert result["subject"] == "Re: "
