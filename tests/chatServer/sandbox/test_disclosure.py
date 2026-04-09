"""Tests for DisclosureModel — trust-tier notification formatting."""

from chatServer.sandbox.disclosure import ChangeDescription, DisclosureModel


def _make_change(**kwargs) -> ChangeDescription:
    defaults = {
        "file_path": "/user/preferences/scheduling.yaml",
        "action": "updated",
        "summary": "Changed morning briefing time from 8am to 7am",
        "commit_sha": "abc123def456",
    }
    defaults.update(kwargs)
    return ChangeDescription(**defaults)


class TestFormatChangeNotification:
    def test_inform_tier_full_transparency(self):
        model = DisclosureModel()
        change = _make_change()
        result = model.format_change_notification(change, "inform")

        assert result is not None
        assert "/user/preferences/scheduling.yaml" in result
        assert "abc123de" in result
        assert "Changed morning briefing" in result

    def test_recommend_tier_summary(self):
        model = DisclosureModel()
        change = _make_change()
        result = model.format_change_notification(change, "recommend")

        assert result is not None
        assert "preferences" in result
        assert "feels off" in result
        # Should NOT contain full diff details
        assert "abc123" not in result

    def test_act_tier_returns_none(self):
        model = DisclosureModel()
        change = _make_change()
        result = model.format_change_notification(change, "act")
        assert result is None


class TestFormatAggregatedNotification:
    def test_recommend_aggregated(self):
        model = DisclosureModel()
        changes = [
            _make_change(file_path="/user/preferences/a.yaml"),
            _make_change(file_path="/user/workflows/b.md"),
            _make_change(file_path="/user/preferences/c.yaml"),
        ]
        result = model.format_aggregated_notification(changes, "recommend")

        assert result is not None
        assert "3 adjustments" in result
        assert "preferences" in result
        assert "workflows" in result

    def test_inform_aggregated_lists_each(self):
        model = DisclosureModel()
        changes = [
            _make_change(file_path="/user/agent/greeting.md", action="created"),
            _make_change(file_path="/user/preferences/tone.yaml", action="updated"),
        ]
        result = model.format_aggregated_notification(changes, "inform")

        assert result is not None
        assert "/user/agent/greeting.md" in result
        assert "/user/preferences/tone.yaml" in result

    def test_act_aggregated_returns_none(self):
        model = DisclosureModel()
        result = model.format_aggregated_notification(
            [_make_change()], "act",
        )
        assert result is None

    def test_empty_changes_returns_none(self):
        model = DisclosureModel()
        result = model.format_aggregated_notification([], "inform")
        assert result is None


class TestFormatDigest:
    def test_digest_with_changes(self):
        model = DisclosureModel()
        changes = [
            _make_change(file_path="/user/agent/style.md"),
            _make_change(file_path="/user/memory/observations.md", action="created"),
        ]
        result = model.format_digest(changes)

        assert "2 changes" in result
        assert "/user/agent/style.md" in result
        assert "abc123de" in result

    def test_digest_empty(self):
        model = DisclosureModel()
        result = model.format_digest([])
        assert "No configuration changes" in result
