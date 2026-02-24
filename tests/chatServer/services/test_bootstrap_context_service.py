"""Tests for BootstrapContextService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.bootstrap_context_service import (
    BootstrapContext,
    BootstrapContextService,
)


class TestBootstrapContext:
    """Tests for BootstrapContext dataclass."""

    def test_render_all_populated(self):
        ctx = BootstrapContext(
            tasks_summary="3 active task(s)",
            reminders_summary="2 upcoming reminder(s). Next: 'Call dentist'",
            email_summary="1 account(s) connected: alice@example.com",
        )
        rendered = ctx.render()
        assert "Tasks: 3 active" in rendered
        assert "Reminders: 2 upcoming" in rendered
        assert "Email: 1 account" in rendered

    def test_render_with_unavailable(self):
        ctx = BootstrapContext(
            tasks_summary="No active tasks.",
            reminders_summary="(unavailable)",
            email_summary="No email connected.",
        )
        rendered = ctx.render()
        assert "Tasks: No active tasks." in rendered
        assert "Reminders: (unavailable)" in rendered
        assert "Email: No email connected." in rendered

    def test_render_all_unavailable(self):
        ctx = BootstrapContext()
        rendered = ctx.render()
        assert "Tasks: (unavailable)" in rendered
        assert "Reminders: (unavailable)" in rendered
        assert "Email: (unavailable)" in rendered


@pytest.mark.asyncio
class TestBootstrapContextService:
    """Tests for BootstrapContextService.gather()."""

    async def test_gather_returns_summaries(self):
        """AC-12: Verify gather() returns task/reminder/email summaries."""
        service = BootstrapContextService(MagicMock())

        async def fake_tasks(user_id):
            return "2 active task(s)"

        async def fake_reminders(user_id):
            return "1 upcoming reminder(s). Next: 'Team standup'"

        async def fake_email(user_id):
            return "1 account(s) connected: alice@example.com"

        service._get_tasks_summary = fake_tasks
        service._get_reminders_summary = fake_reminders
        service._get_email_summary = fake_email

        ctx = await service.gather("user-123")

        assert "active task" in ctx.tasks_summary
        assert "reminder" in ctx.reminders_summary
        assert "alice@example.com" in ctx.email_summary

    async def test_gather_handles_task_failure(self):
        """AC-13: Task query fails, other sources still work."""
        service = BootstrapContextService(MagicMock())

        async def fail_tasks(user_id):
            raise Exception("DB error")

        async def fake_reminders(user_id):
            return "No upcoming reminders."

        async def fake_email(user_id):
            return "No email connected."

        service._get_tasks_summary = fail_tasks
        service._get_reminders_summary = fake_reminders
        service._get_email_summary = fake_email

        ctx = await service.gather("user-123")

        assert ctx.tasks_summary == "(unavailable)"
        assert ctx.reminders_summary == "No upcoming reminders."
        assert ctx.email_summary == "No email connected."

    async def test_gather_handles_all_failures(self):
        """AC-13: All queries fail, all fields are (unavailable)."""
        service = BootstrapContextService(MagicMock())

        async def fail(user_id):
            raise Exception("Connection lost")

        service._get_tasks_summary = fail
        service._get_reminders_summary = fail
        service._get_email_summary = fail

        ctx = await service.gather("user-123")

        assert ctx.tasks_summary == "(unavailable)"
        assert ctx.reminders_summary == "(unavailable)"
        assert ctx.email_summary == "(unavailable)"

    async def test_empty_tasks(self):
        resp = MagicMock()
        resp.data = []
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_tasks_summary("user-123")
        assert result == "No active tasks."

    async def test_overdue_tasks(self):
        resp = MagicMock()
        resp.data = [
            {"id": "1", "title": "Overdue thing", "status": "pending", "due_date": "2020-01-01", "priority": 4},
            {"id": "2", "title": "Not overdue", "status": "pending", "due_date": "2099-12-31", "priority": 2},
        ]
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_tasks_summary("user-123")
        assert "2 active" in result
        assert "1 overdue" in result
        assert "Overdue thing" in result

    async def test_no_upcoming_reminders(self):
        resp = MagicMock()
        resp.data = []
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_reminders_summary("user-123")
        assert result == "No upcoming reminders."

    async def test_upcoming_reminder_shows_next(self):
        resp = MagicMock()
        resp.data = [
            {"id": "r1", "title": "Call dentist", "remind_at": "2026-03-01T10:00:00+00:00"},
            {"id": "r2", "title": "Pay bills", "remind_at": "2026-03-05T09:00:00+00:00"},
        ]
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_reminders_summary("user-123")
        assert "2 upcoming" in result
        assert "Call dentist" in result

    async def test_no_email_connected(self):
        resp = MagicMock()
        resp.data = []
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_email_summary("user-123")
        assert result == "No email connected."

    async def test_email_connected_shows_accounts(self):
        resp = MagicMock()
        resp.data = [
            {"id": "c1", "service_user_email": "alice@example.com"},
            {"id": "c2", "service_user_email": "bob@example.com"},
        ]
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = AsyncMock(return_value=resp)  # noqa: E501

        service = BootstrapContextService(mock_db)
        result = await service._get_email_summary("user-123")
        assert "2 account(s)" in result
        assert "alice@example.com" in result
        assert "bob@example.com" in result
