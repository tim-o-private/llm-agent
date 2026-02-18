"""Unit tests for background task service."""

import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.background_tasks import BackgroundTaskService, get_background_task_service


class TestBackgroundTaskService(unittest.TestCase):
    """Test cases for BackgroundTaskService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = BackgroundTaskService()

        # Reset global instance
        import chatServer.services.background_tasks
        chatServer.services.background_tasks._background_task_service = None

    def test_background_task_service_initialization(self):
        """Test BackgroundTaskService initialization."""
        self.assertIsNone(self.service.deactivate_task)
        self.assertIsNone(self.service.evict_task)
        self.assertIsNone(self.service.reminder_task)
        self.assertIsNone(self.service._agent_executor_cache)

    def test_set_agent_executor_cache(self):
        """Test setting agent executor cache."""
        mock_cache = {("user1", "agent1"): MagicMock()}
        self.service.set_agent_executor_cache(mock_cache)
        self.assertEqual(self.service._agent_executor_cache, mock_cache)

    def test_start_background_tasks(self):
        """Test starting background tasks."""
        with patch('asyncio.create_task') as mock_create_task:
            # Mock the async methods to avoid "coroutine was never awaited" warnings
            with patch.object(self.service, 'deactivate_stale_chat_session_instances', new_callable=AsyncMock):
                with patch.object(self.service, 'evict_inactive_executors', new_callable=AsyncMock):
                    with patch.object(self.service, 'run_scheduled_agents', new_callable=AsyncMock):
                        with patch.object(self.service, 'check_due_reminders', new_callable=AsyncMock):
                            mock_task1 = MagicMock()
                            mock_task2 = MagicMock()
                            mock_task3 = MagicMock()
                            mock_task4 = MagicMock()
                            mock_create_task.side_effect = [mock_task1, mock_task2, mock_task3, mock_task4]

                            self.service.start_background_tasks()

                            self.assertEqual(mock_create_task.call_count, 4)
                            self.assertEqual(self.service.deactivate_task, mock_task1)
                            self.assertEqual(self.service.evict_task, mock_task2)
                            self.assertEqual(self.service.scheduled_agents_task, mock_task3)
                            self.assertEqual(self.service.reminder_task, mock_task4)


class TestBackgroundTaskServiceGlobal(unittest.TestCase):
    """Test cases for global background task service functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global instance
        import chatServer.services.background_tasks
        chatServer.services.background_tasks._background_task_service = None

    def test_get_background_task_service_creates_instance(self):
        """Test that get_background_task_service creates a new instance."""
        service = get_background_task_service()
        self.assertIsInstance(service, BackgroundTaskService)

    def test_get_background_task_service_returns_same_instance(self):
        """Test that get_background_task_service returns the same instance."""
        service1 = get_background_task_service()
        service2 = get_background_task_service()
        self.assertIs(service1, service2)

    def test_get_background_task_service_singleton_pattern(self):
        """Test singleton pattern behavior."""
        # First call creates instance
        service1 = get_background_task_service()

        # Subsequent calls return same instance
        service2 = get_background_task_service()
        service3 = get_background_task_service()

        self.assertIs(service1, service2)
        self.assertIs(service2, service3)


# Async tests using pytest-asyncio
class TestBackgroundTaskServiceAsync:
    """Async test cases for BackgroundTaskService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = BackgroundTaskService()

        # Reset global instance
        import chatServer.services.background_tasks
        chatServer.services.background_tasks._background_task_service = None

    @pytest.mark.asyncio
    async def test_stop_background_tasks_no_tasks(self):
        """Test stopping background tasks when no tasks exist."""
        # Should not raise any exceptions
        await self.service.stop_background_tasks()

    @patch('chatServer.services.background_tasks.get_database_manager')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_deactivate_stale_chat_session_instances_no_pool(self, mock_sleep, mock_get_db_manager):
        """Test deactivation task when database pool is not available."""
        mock_db_manager = MagicMock()
        mock_db_manager.pool = None
        mock_get_db_manager.return_value = mock_db_manager

        # Make sleep raise an exception after first iteration to break the loop
        mock_sleep.side_effect = [None, Exception("Break loop")]

        with pytest.raises(Exception, match="Break loop"):
            await self.service.deactivate_stale_chat_session_instances()

    @patch('chatServer.services.background_tasks.get_database_manager')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_evict_inactive_executors_no_cache(self, mock_sleep, mock_get_db_manager):
        """Test eviction task when cache is not available."""
        mock_db_manager = MagicMock()
        mock_db_manager.pool = MagicMock()
        mock_get_db_manager.return_value = mock_db_manager

        # Cache is None by default

        # Make sleep raise an exception after first iteration to break the loop
        mock_sleep.side_effect = [None, Exception("Break loop")]

        with pytest.raises(Exception, match="Break loop"):
            await self.service.evict_inactive_executors()

    @pytest.mark.asyncio
    async def test_background_task_service_basic_functionality(self):
        """Test basic functionality of background task service."""
        # Test that we can create a service and set cache
        service = BackgroundTaskService()
        cache = {("user1", "agent1"): MagicMock()}
        service.set_agent_executor_cache(cache)

        assert service._agent_executor_cache == cache

        # Test that start_background_tasks creates tasks
        with patch('asyncio.create_task') as mock_create_task:
            # Mock the async methods to avoid "coroutine was never awaited" warnings
            with patch.object(service, 'deactivate_stale_chat_session_instances', new_callable=AsyncMock):
                with patch.object(service, 'evict_inactive_executors', new_callable=AsyncMock):
                    with patch.object(service, 'run_scheduled_agents', new_callable=AsyncMock):
                        with patch.object(service, 'check_due_reminders', new_callable=AsyncMock):
                            mock_task1 = MagicMock()
                            mock_task2 = MagicMock()
                            mock_task3 = MagicMock()
                            mock_task4 = MagicMock()
                            mock_create_task.side_effect = [mock_task1, mock_task2, mock_task3, mock_task4]

                            service.start_background_tasks()

                            assert mock_create_task.call_count == 4
                            assert service.deactivate_task == mock_task1
                            assert service.evict_task == mock_task2
                            assert service.scheduled_agents_task == mock_task3
                            assert service.reminder_task == mock_task4


class TestCheckDueReminders:
    """Tests for the reminder delivery loop."""

    def setup_method(self):
        self.service = BackgroundTaskService()
        # Create mock module for reminder_service (not yet on main — PR #31)
        self._mock_reminder_module = types.ModuleType("chatServer.services.reminder_service")
        self._mock_reminder_cls = MagicMock()
        self._mock_reminder_module.ReminderService = self._mock_reminder_cls

    def _patch_imports(self, mock_reminder_service_instance, mock_notification_service_instance, mock_db_client):
        """Return a context manager stack that patches all imports needed by check_due_reminders."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            mock_reminder_cls = MagicMock(return_value=mock_reminder_service_instance)
            mock_notification_cls = MagicMock(return_value=mock_notification_service_instance)

            # Inject a fake reminder_service module into sys.modules so the lazy import resolves
            fake_mod = types.ModuleType("chatServer.services.reminder_service")
            fake_mod.ReminderService = mock_reminder_cls
            saved = sys.modules.get("chatServer.services.reminder_service")
            sys.modules["chatServer.services.reminder_service"] = fake_mod

            with patch(
                "chatServer.services.background_tasks.get_supabase_client",
                new_callable=AsyncMock,
                return_value=mock_db_client,
            ):
                with patch(
                    "chatServer.services.notification_service.NotificationService",
                    mock_notification_cls,
                ):
                    yield

            # Restore
            if saved is None:
                sys.modules.pop("chatServer.services.reminder_service", None)
            else:
                sys.modules["chatServer.services.reminder_service"] = saved

        return _ctx()

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_check_due_reminders_fires_notifications(self, mock_sleep):
        """Test that due reminders trigger notifications and are marked sent."""
        mock_sleep.side_effect = [None, Exception("Break loop")]

        mock_db_client = AsyncMock()

        mock_reminder_service = AsyncMock()
        mock_reminder_service.get_due_reminders.return_value = [
            {
                "id": "rem-1",
                "user_id": "user-1",
                "title": "Call Sarah",
                "body": "Follow up on the proposal",
                "recurrence": None,
            },
            {
                "id": "rem-2",
                "user_id": "user-2",
                "title": "Team standup",
                "body": None,
                "recurrence": "daily",
            },
        ]

        mock_notification_service = AsyncMock()

        with self._patch_imports(mock_reminder_service, mock_notification_service, mock_db_client):
            with pytest.raises(Exception, match="Break loop"):
                await self.service.check_due_reminders()

        # Both reminders should have triggered notifications
        assert mock_notification_service.notify_user.call_count == 2

        # Check first notification
        call_1 = mock_notification_service.notify_user.call_args_list[0]
        assert call_1.kwargs["user_id"] == "user-1"
        assert call_1.kwargs["title"] == "Reminder: Call Sarah"
        assert call_1.kwargs["body"] == "Follow up on the proposal"
        assert call_1.kwargs["category"] == "reminder"
        assert call_1.kwargs["metadata"] == {"reminder_id": "rem-1"}

        # Check second notification (body is None, falls back to title)
        call_2 = mock_notification_service.notify_user.call_args_list[1]
        assert call_2.kwargs["user_id"] == "user-2"
        assert call_2.kwargs["body"] == "Team standup"

        # Both should be marked sent
        assert mock_reminder_service.mark_sent.call_count == 2
        mock_reminder_service.mark_sent.assert_any_call("rem-1")
        mock_reminder_service.mark_sent.assert_any_call("rem-2")

        # Recurrence should be handled for both
        assert mock_reminder_service.handle_recurrence.call_count == 2

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_check_due_reminders_handles_individual_failure(self, mock_sleep):
        """Test that one bad reminder doesn't block others."""
        mock_sleep.side_effect = [None, Exception("Break loop")]

        mock_db_client = AsyncMock()

        mock_reminder_service = AsyncMock()
        mock_reminder_service.get_due_reminders.return_value = [
            {"id": "rem-bad", "user_id": "user-1", "title": "Bad one", "body": None},
            {"id": "rem-good", "user_id": "user-2", "title": "Good one", "body": "Works fine"},
        ]

        mock_notification_service = AsyncMock()
        # First call raises, second succeeds
        mock_notification_service.notify_user.side_effect = [
            Exception("Notification failed"),
            "notif-id-123",
        ]

        with self._patch_imports(mock_reminder_service, mock_notification_service, mock_db_client):
            with pytest.raises(Exception, match="Break loop"):
                await self.service.check_due_reminders()

        # Both notifications attempted
        assert mock_notification_service.notify_user.call_count == 2

        # First reminder failed, so mark_sent should NOT have been called for it
        # Second reminder succeeded, so mark_sent should have been called
        assert mock_reminder_service.mark_sent.call_count == 1
        mock_reminder_service.mark_sent.assert_called_once_with("rem-good")

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_check_due_reminders_no_due_reminders(self, mock_sleep):
        """Test that the loop handles no due reminders gracefully."""
        mock_sleep.side_effect = [None, Exception("Break loop")]

        mock_db_client = AsyncMock()
        mock_reminder_service = AsyncMock()
        mock_reminder_service.get_due_reminders.return_value = []

        mock_notification_service = AsyncMock()

        with self._patch_imports(mock_reminder_service, mock_notification_service, mock_db_client):
            with pytest.raises(Exception, match="Break loop"):
                await self.service.check_due_reminders()

        mock_notification_service.notify_user.assert_not_called()
        mock_reminder_service.mark_sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
