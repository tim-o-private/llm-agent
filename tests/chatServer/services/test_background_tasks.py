"""Unit tests for background task service."""

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
                        mock_task1 = MagicMock()
                        mock_task2 = MagicMock()
                        mock_task3 = MagicMock()
                        mock_create_task.side_effect = [mock_task1, mock_task2, mock_task3]

                        self.service.start_background_tasks()

                        self.assertEqual(mock_create_task.call_count, 3)
                        self.assertEqual(self.service.deactivate_task, mock_task1)
                        self.assertEqual(self.service.evict_task, mock_task2)
                        self.assertEqual(self.service.scheduled_agents_task, mock_task3)


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
                        mock_task1 = MagicMock()
                        mock_task2 = MagicMock()
                        mock_task3 = MagicMock()
                        mock_create_task.side_effect = [mock_task1, mock_task2, mock_task3]

                        service.start_background_tasks()

                        assert mock_create_task.call_count == 3
                        assert service.deactivate_task == mock_task1
                        assert service.evict_task == mock_task2
                        assert service.scheduled_agents_task == mock_task3


if __name__ == "__main__":
    unittest.main()
