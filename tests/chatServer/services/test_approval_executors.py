"""Unit tests for SPEC-052 approval card executors.

One test class per executor. External APIs (Gmail, Calendar, Telegram) are mocked.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.approval_executors import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _card(card_type: str, payload: dict, **overrides) -> dict:
    return {
        "id": "card-1",
        "user_id": "user-a",
        "card_type": card_type,
        "title": f"Test {card_type}",
        "status": "approved",
        "payload": payload,
        **overrides,
    }


# ===========================================================================
# EmailDraftExecutor
# ===========================================================================


class TestEmailDraftExecutor:
    @pytest.mark.asyncio
    async def test_success_new_email(self):
        from chatServer.services.approval_executors.email_draft import EmailDraftExecutor

        executor = EmailDraftExecutor()
        card = _card("email_draft", {
            "to": ["alice@example.com"],
            "subject": "Hello",
            "body": "Hi Alice",
        })

        mock_svc = MagicMock()
        mock_svc.send_new.return_value = {
            "message_id": "msg-1",
            "thread_id": "thr-1",
            "to": "alice@example.com",
            "subject": "Hello",
        }

        with (
            patch.object(executor, "_resolve_credentials", new=AsyncMock(return_value=MagicMock())),
            patch.object(executor, "_check_scope", new=AsyncMock(return_value=None)),
            patch.object(executor, "_build_compose_service", return_value=mock_svc),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["message_id"] == "msg-1"
        mock_svc.send_new.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_reply(self):
        from chatServer.services.approval_executors.email_draft import EmailDraftExecutor

        executor = EmailDraftExecutor()
        card = _card("email_draft", {
            "to": ["bob@example.com"],
            "subject": "Re: Meeting",
            "body": "Sure",
            "thread_ref": "orig-msg-123",
        })

        mock_svc = MagicMock()
        mock_svc.send_reply.return_value = {
            "message_id": "msg-2",
            "thread_id": "thr-2",
            "to": "bob@example.com",
            "subject": "Re: Meeting",
        }

        with (
            patch.object(executor, "_resolve_credentials", new=AsyncMock(return_value=MagicMock())),
            patch.object(executor, "_check_scope", new=AsyncMock(return_value=None)),
            patch.object(executor, "_build_compose_service", return_value=mock_svc),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is True
        mock_svc.send_reply.assert_called_once_with(
            original_message_id="orig-msg-123",
            body="Sure",
            subject_override="Re: Meeting",
        )

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        from chatServer.services.approval_executors.email_draft import EmailDraftExecutor

        executor = EmailDraftExecutor()
        card = _card("email_draft", {"to": ["a@b.com"]})

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "subject" in result.error
        assert "body" in result.error

    @pytest.mark.asyncio
    async def test_credentials_unavailable(self):
        from chatServer.services.approval_executors.email_draft import EmailDraftExecutor

        executor = EmailDraftExecutor()
        card = _card("email_draft", {
            "to": ["a@b.com"],
            "subject": "Hi",
            "body": "Hello",
        })

        with patch.object(
            executor,
            "_resolve_credentials",
            new=AsyncMock(side_effect=ValueError("Gmail not connected")),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "Gmail credentials unavailable" in result.error

    @pytest.mark.asyncio
    async def test_scope_missing(self):
        from chatServer.services.approval_executors.email_draft import EmailDraftExecutor

        executor = EmailDraftExecutor()
        card = _card("email_draft", {
            "to": ["a@b.com"],
            "subject": "Hi",
            "body": "Hello",
        })

        with (
            patch.object(executor, "_resolve_credentials", new=AsyncMock(return_value=MagicMock())),
            patch.object(executor, "_check_scope", new=AsyncMock(return_value="Compose scope missing")),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "Compose scope missing" in result.error


# ===========================================================================
# CalendarHoldExecutor
# ===========================================================================


class TestCalendarHoldExecutor:
    @pytest.mark.asyncio
    async def test_success(self):
        from chatServer.services.approval_executors.calendar_hold import CalendarHoldExecutor

        executor = CalendarHoldExecutor()
        card = _card("calendar_hold", {
            "title": "Standup",
            "start_at": "2026-04-21T09:00:00",
            "end_at": "2026-04-21T09:30:00",
        })

        mock_svc = MagicMock()
        mock_svc.create_event.return_value = {
            "event_id": "ev-1",
            "html_link": "https://calendar.google.com/ev-1",
        }

        with (
            patch.object(executor, "_resolve_credentials", new=AsyncMock(return_value=MagicMock())),
            patch.object(executor, "_build_calendar_service", return_value=mock_svc),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["event_id"] == "ev-1"

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        from chatServer.services.approval_executors.calendar_hold import CalendarHoldExecutor

        executor = CalendarHoldExecutor()
        card = _card("calendar_hold", {"title": "Standup"})

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "start_at" in result.error

    @pytest.mark.asyncio
    async def test_no_calendar_connected(self):
        from chatServer.services.approval_executors.calendar_hold import CalendarHoldExecutor

        executor = CalendarHoldExecutor()
        card = _card("calendar_hold", {
            "title": "Standup",
            "start_at": "2026-04-21T09:00:00",
            "end_at": "2026-04-21T09:30:00",
        })

        with patch.object(executor, "_resolve_credentials", new=AsyncMock(return_value=None)):
            result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "not connected" in result.error.lower()


# ===========================================================================
# OutreachExecutor
# ===========================================================================


class TestOutreachExecutor:
    @pytest.mark.asyncio
    async def test_channel_other_approve_only(self):
        from chatServer.services.approval_executors.outreach import OutreachExecutor

        executor = OutreachExecutor()
        card = _card("outreach", {
            "recipient": "someone",
            "message": "Hello",
            "channel": "other",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["sent"] is False
        assert "manual follow-up" in result.activity_action

    @pytest.mark.asyncio
    async def test_channel_email_sends(self):
        from chatServer.services.approval_executors.outreach import OutreachExecutor

        executor = OutreachExecutor()
        card = _card("outreach", {
            "recipient": "alice@test.com",
            "message": "Hello there",
            "channel": "email",
        })

        mock_svc = MagicMock()
        mock_svc.send_new.return_value = {"message_id": "msg-1"}

        with (
            patch.object(executor, "_resolve_gmail_credentials", new=AsyncMock(return_value=MagicMock())),
            patch.object(executor, "_build_compose_service", return_value=mock_svc),
        ):
            result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["channel"] == "email"

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        from chatServer.services.approval_executors.outreach import OutreachExecutor

        executor = OutreachExecutor()
        card = _card("outreach", {"recipient": "someone"})

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "message" in result.error


# ===========================================================================
# WorkflowProposalExecutor
# ===========================================================================


class TestWorkflowProposalExecutor:
    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        from chatServer.services.approval_executors.workflow_proposal import (
            WorkflowProposalExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a"
        user_root.mkdir(parents=True)

        executor = WorkflowProposalExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("workflow_proposal", {
            "filename": "daily-review.flow.md",
            "body": "# Daily Review\nSteps here",
            "pattern_observed": "Every day the user reviews",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["path"] == "_workflows/daily-review.flow.md"
        assert (user_root / "_workflows" / "daily-review.flow.md").exists()

    @pytest.mark.asyncio
    async def test_refuses_overwrite(self, tmp_path):
        from chatServer.services.approval_executors.workflow_proposal import (
            WorkflowProposalExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a" / "_workflows"
        user_root.mkdir(parents=True)
        (user_root / "existing.flow.md").write_text("old content")

        executor = WorkflowProposalExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("workflow_proposal", {
            "filename": "existing.flow.md",
            "body": "new content",
            "pattern_observed": "pattern",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "already exists" in result.error

    @pytest.mark.asyncio
    async def test_invalid_extension(self):
        from chatServer.services.approval_executors.workflow_proposal import (
            WorkflowProposalExecutor,
        )

        executor = WorkflowProposalExecutor()
        card = _card("workflow_proposal", {
            "filename": "script.py",
            "body": "print('hello')",
            "pattern_observed": "pattern",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "extension" in result.error.lower()


# ===========================================================================
# ConfigChangeExecutor
# ===========================================================================


class TestConfigChangeExecutor:
    @pytest.mark.asyncio
    async def test_success(self, tmp_path):
        from chatServer.services.approval_executors.config_change import (
            ConfigChangeExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a" / "agents"
        user_root.mkdir(parents=True)
        (user_root / "assistant.md").write_text("old content")

        executor = ConfigChangeExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("config_change", {
            "file_path": "agents/assistant.md",
            "diff": "new content with changes",
            "summary": "Updated agent config",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["path"] == "agents/assistant.md"
        assert result.result["previous_size"] == len(b"old content")
        assert (user_root / "assistant.md").read_text() == "new content with changes"

    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path):
        from chatServer.services.approval_executors.config_change import (
            ConfigChangeExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a"
        user_root.mkdir(parents=True)

        executor = ConfigChangeExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("config_change", {
            "file_path": "nonexistent.md",
            "diff": "new content",
            "summary": "test",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "not found" in result.error.lower()


# ===========================================================================
# FileOperationExecutor
# ===========================================================================


class TestFileOperationExecutor:
    @pytest.mark.asyncio
    async def test_delete_success(self, tmp_path):
        from chatServer.services.approval_executors.file_operation import (
            FileOperationExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a"
        user_root.mkdir(parents=True)
        (user_root / "notes.md").write_text("some notes")

        executor = FileOperationExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("file_operation", {
            "operation": "delete",
            "source": "notes.md",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["operation"] == "delete"
        assert not (user_root / "notes.md").exists()

    @pytest.mark.asyncio
    async def test_move_success(self, tmp_path):
        from chatServer.services.approval_executors.file_operation import (
            FileOperationExecutor,
        )
        from chatServer.services.vault_service import VaultService

        vault = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "user-a"
        user_root.mkdir(parents=True)
        (user_root / "old.md").write_text("content")

        executor = FileOperationExecutor()
        executor._get_vault_service = lambda: vault

        card = _card("file_operation", {
            "operation": "move",
            "source": "old.md",
            "target": "archive/old.md",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is True
        assert result.result["target"] == "archive/old.md"
        assert not (user_root / "old.md").exists()
        assert (user_root / "archive" / "old.md").exists()

    @pytest.mark.asyncio
    async def test_rejects_protected_today(self):
        from chatServer.services.approval_executors.file_operation import (
            FileOperationExecutor,
        )

        executor = FileOperationExecutor()
        card = _card("file_operation", {
            "operation": "delete",
            "source": "today.md",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "protected" in result.error.lower()

    @pytest.mark.asyncio
    async def test_rejects_protected_workflows(self):
        from chatServer.services.approval_executors.file_operation import (
            FileOperationExecutor,
        )

        executor = FileOperationExecutor()
        card = _card("file_operation", {
            "operation": "delete",
            "source": "_workflows/important.flow.md",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "protected" in result.error.lower()

    @pytest.mark.asyncio
    async def test_move_without_target(self):
        from chatServer.services.approval_executors.file_operation import (
            FileOperationExecutor,
        )

        executor = FileOperationExecutor()
        card = _card("file_operation", {
            "operation": "move",
            "source": "old.md",
        })

        result = await executor.execute(card, "user-a")

        assert result.success is False
        assert "target" in result.error.lower()
