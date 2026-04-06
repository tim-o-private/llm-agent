"""Tests for GitTracker — git operations via mocked subprocess."""

from pathlib import Path

import pytest

from chatServer.sandbox.git_tracker import GitTracker


def _mock_run(return_code: int = 0, stdout: str = "", stderr: str = ""):
    """Create a mock for GitTracker._run."""
    async def _run(*args):
        return (return_code, stdout, stderr)
    return _run


class TestCommit:
    @pytest.mark.asyncio
    async def test_commit_with_changes(self):
        tracker = GitTracker(Path("/fake/user"))
        calls = []

        async def mock_run(*args):
            calls.append(args)
            if args == ("git", "diff", "--cached", "--quiet"):
                return (1, "", "")  # changes exist
            if args[0:2] == ("git", "log"):
                return (0, "abc123|Agent: updated file.md|2026-04-06T00:00:00+00:00", "")
            return (0, "", "")

        tracker._run = mock_run
        result = await tracker.commit("test commit")

        assert result is not None
        assert result.sha == "abc123"
        assert ("git", "add", "-A") in calls

    @pytest.mark.asyncio
    async def test_commit_no_changes(self):
        tracker = GitTracker(Path("/fake/user"))

        async def mock_run(*args):
            if args == ("git", "diff", "--cached", "--quiet"):
                return (0, "", "")  # no changes
            return (0, "", "")

        tracker._run = mock_run
        result = await tracker.commit("empty commit")
        assert result is None


class TestLog:
    @pytest.mark.asyncio
    async def test_log_returns_commits(self):
        tracker = GitTracker(Path("/fake/user"))
        log_output = (
            "abc123|First commit|2026-04-06T00:00:00+00:00\n"
            "def456|Second commit|2026-04-05T00:00:00+00:00\n"
        )
        tracker._run = _mock_run(0, log_output)
        result = await tracker.log(limit=10)

        assert len(result) == 2
        assert result[0].sha == "abc123"
        assert result[1].message == "Second commit"

    @pytest.mark.asyncio
    async def test_log_empty_repo(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(128, "", "fatal: no commits")
        result = await tracker.log()
        assert result == []


class TestDiff:
    @pytest.mark.asyncio
    async def test_diff_with_commit_hash(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(0, "+new line\n-old line\n")
        result = await tracker.diff("abc123")
        assert "+new line" in result

    @pytest.mark.asyncio
    async def test_diff_default_head(self):
        tracker = GitTracker(Path("/fake/user"))
        calls = []

        async def mock_run(*args):
            calls.append(args)
            return (0, "diff output", "")

        tracker._run = mock_run
        await tracker.diff()
        assert calls[0] == ("git", "diff", "HEAD~1", "HEAD")


class TestDiffFiles:
    @pytest.mark.asyncio
    async def test_diff_files_returns_list(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(0, "agent/style.md\npreferences/tone.yaml\n")
        result = await tracker.diff_files("abc123")
        assert result == ["agent/style.md", "preferences/tone.yaml"]

    @pytest.mark.asyncio
    async def test_diff_files_empty(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(0, "")
        result = await tracker.diff_files()
        assert result == []


class TestRevert:
    @pytest.mark.asyncio
    async def test_revert_success(self):
        tracker = GitTracker(Path("/fake/user"))
        call_count = 0

        async def mock_run(*args):
            nonlocal call_count
            call_count += 1
            if args[0:2] == ("git", "revert"):
                return (0, "", "")
            if args[0:2] == ("git", "log"):
                return (0, "rev789|Revert: something|2026-04-06T01:00:00+00:00", "")
            return (0, "", "")

        tracker._run = mock_run
        result = await tracker.revert("abc123")
        assert result is not None
        assert result.sha == "rev789"

    @pytest.mark.asyncio
    async def test_revert_failure(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(1, "", "error: could not revert")
        result = await tracker.revert("abc123")
        assert result is None


class TestGetHeadSha:
    @pytest.mark.asyncio
    async def test_get_head_sha(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(0, "abc123def456\n")
        result = await tracker.get_head_sha()
        assert result == "abc123def456"

    @pytest.mark.asyncio
    async def test_get_head_sha_no_commits(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(128, "", "fatal: bad default revision")
        result = await tracker.get_head_sha()
        assert result is None


class TestGetChangelog:
    @pytest.mark.asyncio
    async def test_changelog_since(self):
        tracker = GitTracker(Path("/fake/user"))
        calls = []

        async def mock_run(*args):
            calls.append(args)
            return (0, "- Updated tone (abc1234, 2 hours ago)", "")

        tracker._run = mock_run
        result = await tracker.get_changelog(since="old_sha")
        assert "Updated tone" in result
        # Verify the since..HEAD range was used
        assert "old_sha..HEAD" in calls[0][2]

    @pytest.mark.asyncio
    async def test_changelog_default(self):
        tracker = GitTracker(Path("/fake/user"))
        tracker._run = _mock_run(0, "- First change (abc, 1 day ago)")
        result = await tracker.get_changelog()
        assert "First change" in result
