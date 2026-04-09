"""Tests for ChangelogService (SPEC-040)."""

from unittest.mock import AsyncMock

import pytest

from chatServer.sandbox.changelog import ChangelogService
from chatServer.sandbox.git_tracker import CommitInfo, GitTracker


@pytest.fixture
def mock_git_tracker():
    tracker = AsyncMock(spec=GitTracker)
    tracker.log.return_value = []
    tracker.get_changelog.return_value = ""
    tracker.diff.return_value = ""
    tracker.diff_files.return_value = []
    return tracker


@pytest.fixture
def changelog_service(mock_git_tracker):
    return ChangelogService(mock_git_tracker)


class TestGetChangelog:
    @pytest.mark.asyncio
    async def test_returns_no_changes_when_empty(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = []
        result = await changelog_service.get_changelog(user_id="user-123")
        assert "No changes recorded" in result

    @pytest.mark.asyncio
    async def test_groups_by_category(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = [
            CommitInfo(sha="aaa11111", message="Updated prompt instructions", timestamp="2026-04-01T10:00:00Z"),
            CommitInfo(sha="bbb22222", message="Changed preference for briefing length", timestamp="2026-04-01T09:00:00Z"),  # noqa: E501
            CommitInfo(sha="ccc33333", message="Added workflow for calendar sync", timestamp="2026-04-01T08:00:00Z"),
        ]

        result = await changelog_service.get_changelog(user_id="user-123")
        assert "Prompt Changes" in result
        assert "Preference Changes" in result
        assert "Workflow Changes" in result
        assert "aaa11111" in result

    @pytest.mark.asyncio
    async def test_uses_since_parameter(self, changelog_service, mock_git_tracker):
        mock_git_tracker.get_changelog.return_value = "- some change (abc, 2 days ago)"
        result = await changelog_service.get_changelog(user_id="user-123", since="abc123")
        mock_git_tracker.get_changelog.assert_called_once_with(since="abc123")
        assert "some change" in result


class TestGetChangeDetail:
    @pytest.mark.asyncio
    async def test_returns_detail(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = [
            CommitInfo(sha="aaa11111bbbccc", message="Updated soul prompt", timestamp="2026-04-01T10:00:00Z"),
        ]
        mock_git_tracker.diff.return_value = "- old line\n+ new line"
        mock_git_tracker.diff_files.return_value = ["agent/soul.md"]

        result = await changelog_service.get_change_detail("aaa11111")
        assert result["sha"] == "aaa11111"
        assert result["message"] == "Updated soul prompt"
        assert "old line" in result["diff"]
        assert "agent/soul.md" in result["files"]

    @pytest.mark.asyncio
    async def test_handles_unknown_commit(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = []
        mock_git_tracker.diff.return_value = ""
        mock_git_tracker.diff_files.return_value = []

        result = await changelog_service.get_change_detail("unknown123")
        assert result["message"] == "Unknown commit"


class TestGetRecentSummary:
    @pytest.mark.asyncio
    async def test_returns_summary_with_counts(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = [
            CommitInfo(sha="a1", message="Updated prompt", timestamp=""),
            CommitInfo(sha="a2", message="Updated prompt style", timestamp=""),
            CommitInfo(sha="b1", message="Changed preference", timestamp=""),
        ]

        result = await changelog_service.get_recent_summary()
        assert "3 changes" in result
        assert "Prompt Changes" in result
        assert "Preference Changes" in result

    @pytest.mark.asyncio
    async def test_handles_no_changes(self, changelog_service, mock_git_tracker):
        mock_git_tracker.log.return_value = []
        result = await changelog_service.get_recent_summary()
        assert "haven't made any changes" in result


class TestCategorizeCommit:
    def test_categorizes_prompt(self, changelog_service):
        commit = CommitInfo(sha="abc", message="Updated prompt instructions", timestamp="")
        entry = changelog_service._categorize_commit(commit)
        assert entry.category == "prompt"

    def test_categorizes_preference(self, changelog_service):
        commit = CommitInfo(sha="abc", message="Changed preference for email", timestamp="")
        entry = changelog_service._categorize_commit(commit)
        assert entry.category == "preference"

    def test_categorizes_workflow(self, changelog_service):
        commit = CommitInfo(sha="abc", message="New workflow template", timestamp="")
        entry = changelog_service._categorize_commit(commit)
        assert entry.category == "workflow"

    def test_categorizes_memory(self, changelog_service):
        commit = CommitInfo(sha="abc", message="Updated memory observations", timestamp="")
        entry = changelog_service._categorize_commit(commit)
        assert entry.category == "memory"

    def test_categorizes_other(self, changelog_service):
        commit = CommitInfo(sha="abc", message="Miscellaneous fix", timestamp="")
        entry = changelog_service._categorize_commit(commit)
        assert entry.category == "other"
