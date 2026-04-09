"""Tests for the gather_metrics service node (SPEC-040)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db_client():
    """Create a mock Supabase client with chainable query builder."""
    client = AsyncMock()

    def make_query_chain(data=None):
        """Build a chainable mock that ends with .execute()."""
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.maybe_single.return_value = chain

        result = MagicMock()
        result.data = data or []
        chain.execute = AsyncMock(return_value=result)
        return chain

    client._query_chains = {}
    client.table = MagicMock(side_effect=lambda name: client._query_chains.get(name, make_query_chain()))
    return client, make_query_chain


class TestGatherMetrics:
    @pytest.mark.asyncio
    async def test_returns_error_without_user_id(self):
        from chatServer.workflows.nodes.gather_metrics import gather_metrics

        state = {"parameters": {}}
        result = await gather_metrics(state)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_returns_structured_metrics(self):
        from chatServer.workflows.nodes.gather_metrics import gather_metrics

        state = {
            "parameters": {
                "user_id": "user-123",
                "period_days": 7,
                "focus_areas": ["briefing"],
            }
        }

        p1 = patch("chatServer.workflows.nodes.gather_metrics._collect_feedback", new_callable=AsyncMock)
        p2 = patch("chatServer.workflows.nodes.gather_metrics._collect_interaction_metrics", new_callable=AsyncMock)
        p3 = patch("chatServer.workflows.nodes.gather_metrics._collect_workflow_runs", new_callable=AsyncMock)

        with p1 as mock_fb, p2 as mock_im, p3 as mock_wr:
            mock_fb.return_value = {"total": 5, "positive": 3, "negative": 2}
            mock_im.return_value = {"total_messages": 100}
            mock_wr.return_value = {"total": 10}

            result = await gather_metrics(state)
            data = json.loads(result)

            assert data["period"]["days"] == 7
            assert data["focus_areas"] == ["briefing"]
            assert data["feedback"]["total"] == 5
            assert data["interaction_metrics"]["total_messages"] == 100
            assert data["workflow_runs"]["total"] == 10

    @pytest.mark.asyncio
    async def test_defaults_period_to_7_days(self):
        from chatServer.workflows.nodes.gather_metrics import gather_metrics

        state = {"parameters": {"user_id": "user-123"}}

        p1 = patch("chatServer.workflows.nodes.gather_metrics._collect_feedback", new_callable=AsyncMock)
        p2 = patch("chatServer.workflows.nodes.gather_metrics._collect_interaction_metrics", new_callable=AsyncMock)
        p3 = patch("chatServer.workflows.nodes.gather_metrics._collect_workflow_runs", new_callable=AsyncMock)

        with p1 as mock_fb, p2 as mock_im, p3 as mock_wr:
            mock_fb.return_value = {}
            mock_im.return_value = {}
            mock_wr.return_value = {}

            result = await gather_metrics(state)
            data = json.loads(result)
            assert data["period"]["days"] == 7


class TestCollectFeedback:
    @pytest.mark.asyncio
    async def test_aggregates_feedback_by_sentiment(self):
        from datetime import datetime, timezone

        from chatServer.workflows.nodes.gather_metrics import _collect_feedback

        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain

        result_mock = MagicMock()
        result_mock.data = [
            {"category": "briefing", "sentiment": "positive"},
            {"category": "briefing", "sentiment": "negative"},
            {"category": "email", "sentiment": "positive"},
            {"category": "email", "sentiment": "positive"},
            {"category": "general", "sentiment": "neutral"},
        ]
        chain.execute = AsyncMock(return_value=result_mock)
        mock_client.table.return_value = chain

        with patch("chatServer.database.supabase_client.create_system_client", new_callable=AsyncMock, return_value=mock_client):  # noqa: E501
            result = await _collect_feedback("user-123", datetime.now(timezone.utc))

        assert result["total"] == 5
        assert result["positive"] == 3
        assert result["negative"] == 1
        assert result["neutral"] == 1
        assert result["by_category"]["briefing"]["positive"] == 1
        assert result["by_category"]["briefing"]["negative"] == 1
        assert result["by_category"]["email"]["positive"] == 2

    @pytest.mark.asyncio
    async def test_handles_no_feedback(self):
        from datetime import datetime, timezone

        from chatServer.workflows.nodes.gather_metrics import _collect_feedback

        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain

        result_mock = MagicMock()
        result_mock.data = []
        chain.execute = AsyncMock(return_value=result_mock)
        mock_client.table.return_value = chain

        with patch("chatServer.database.supabase_client.create_system_client", new_callable=AsyncMock, return_value=mock_client):  # noqa: E501
            result = await _collect_feedback("user-123", datetime.now(timezone.utc))

        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_handles_db_error(self):
        from datetime import datetime, timezone

        from chatServer.workflows.nodes.gather_metrics import _collect_feedback

        with patch("chatServer.database.supabase_client.create_system_client", new_callable=AsyncMock, side_effect=Exception("DB down")):  # noqa: E501
            result = await _collect_feedback("user-123", datetime.now(timezone.utc))

        assert "error" in result


class TestCollectInteractionMetrics:
    @pytest.mark.asyncio
    async def test_counts_messages_by_type(self):
        from datetime import datetime, timezone

        from chatServer.workflows.nodes.gather_metrics import _collect_interaction_metrics

        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain

        result_mock = MagicMock()
        result_mock.data = [
            {"type": "human"},
            {"type": "human"},
            {"type": "ai"},
            {"type": "ai"},
            {"type": "ai"},
            {"type": "tool"},
        ]
        chain.execute = AsyncMock(return_value=result_mock)
        mock_client.table.return_value = chain

        with patch("chatServer.database.supabase_client.create_system_client", new_callable=AsyncMock, return_value=mock_client):  # noqa: E501
            result = await _collect_interaction_metrics("user-123", datetime.now(timezone.utc))

        assert result["total_messages"] == 6
        assert result["by_type"]["human"] == 2
        assert result["by_type"]["ai"] == 3
        assert result["by_type"]["tool"] == 1


class TestCollectWorkflowRuns:
    @pytest.mark.asyncio
    async def test_aggregates_runs(self):
        from datetime import datetime, timezone

        from chatServer.workflows.nodes.gather_metrics import _collect_workflow_runs

        mock_client = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain

        result_mock = MagicMock()
        result_mock.data = [
            {"template_name": "morning-briefing", "status": "completed"},
            {"template_name": "morning-briefing", "status": "completed"},
            {"template_name": "email-triage", "status": "failed"},
        ]
        chain.execute = AsyncMock(return_value=result_mock)
        mock_client.table.return_value = chain

        with patch("chatServer.database.supabase_client.create_system_client", new_callable=AsyncMock, return_value=mock_client):  # noqa: E501
            result = await _collect_workflow_runs("user-123", datetime.now(timezone.utc))

        assert result["total"] == 3
        assert result["by_template"]["morning-briefing"] == 2
        assert result["by_template"]["email-triage"] == 1
        assert result["by_status"]["completed"] == 2
        assert result["by_status"]["failed"] == 1
