"""Unit tests for ThreadService — creation, status transitions, listing, frontmatter.

Uses a real VaultService backed by tmp_path (no mocks on the filesystem layer).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chatServer.services.thread_service import (
    VALID_TRANSITIONS,
    ThreadService,
    _parse_frontmatter,
)
from chatServer.services.vault_service import VaultService


def _make_vault(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


USER = "test-user"


def _prep_user(tmp_path: Path) -> Path:
    user_root = tmp_path / "sandboxes" / USER
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


class TestCreateThread:
    @pytest.mark.asyncio
    async def test_basic_creation(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER,
            title="Santa Fe Trip Planning",
            trigger="User said 'plan the Santa Fe trip'",
            initiated_by="agent",
            goal="Plan a 4-day trip to Santa Fe.",
        )

        assert rel_path.startswith("_threads/")
        assert "santa-fe-trip-planning" in rel_path
        assert rel_path.endswith(".md")

        # Read it back and verify frontmatter
        content = await vault.read_file(USER, rel_path)
        fm, body = _parse_frontmatter(content)
        assert fm["doc_type"] == "thread"
        assert fm["title"] == "Santa Fe Trip Planning"
        assert fm["status"] == "active"
        assert fm["initiated_by"] == "agent"
        assert fm["trigger"] == "User said 'plan the Santa Fe trip'"
        assert "## Goal" in body
        assert "Plan a 4-day trip" in body

    @pytest.mark.asyncio
    async def test_filename_collision(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        path1 = await service.create_thread(
            USER, title="Test Thread", trigger="test"
        )
        path2 = await service.create_thread(
            USER, title="Test Thread", trigger="test again"
        )

        assert path1 != path2
        assert "-2" in path2

    @pytest.mark.asyncio
    async def test_empty_title_gets_untitled(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="", trigger="test"
        )
        assert "untitled" in rel_path

    @pytest.mark.asyncio
    async def test_body_has_all_sections(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="Test", trigger="test", goal="The goal"
        )
        content = await vault.read_file(USER, rel_path)

        for section in ("Goal", "Plan", "Progress", "Findings", "Open Questions", "Notes"):
            assert f"## {section}" in content


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_valid_transitions(self, tmp_path):
        """All transitions in VALID_TRANSITIONS should succeed."""
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        for from_status, valid_targets in VALID_TRANSITIONS.items():
            for to_status in valid_targets:
                # Create a thread and manually set its status
                rel_path = await service.create_thread(
                    USER,
                    title=f"test-{from_status}-{to_status}",
                    trigger="test",
                )
                # Manually patch the status to from_status
                content = await vault.read_file(USER, rel_path)
                content = content.replace("status: active", f"status: {from_status}")
                await vault.update_body(USER, rel_path, content)

                # Now transition
                await service.change_status(USER, rel_path, to_status)

                # Verify
                updated = await vault.read_file(USER, rel_path)
                fm, _ = _parse_frontmatter(updated)
                assert fm["status"] == to_status

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(self, tmp_path):
        """completed -> active should be rejected."""
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="test-invalid", trigger="test"
        )
        # Set to completed
        content = await vault.read_file(USER, rel_path)
        content = content.replace("status: active", "status: completed")
        await vault.update_body(USER, rel_path, content)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(USER, rel_path, "active")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_status_rejected(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="test-unknown", trigger="test"
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(USER, rel_path, "invalid_status")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_status_change_updates_timestamp(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="test-ts", trigger="test"
        )
        content = await vault.read_file(USER, rel_path)
        fm_before, _ = _parse_frontmatter(content)

        await service.change_status(USER, rel_path, "watching")

        content = await vault.read_file(USER, rel_path)
        fm_after, _ = _parse_frontmatter(content)
        assert fm_after["updated_at"] >= fm_before["updated_at"]


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


class TestListActiveThreads:
    @pytest.mark.asyncio
    async def test_empty_vault(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        result = await service.list_active_threads(USER)
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_status(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        await service.create_thread(USER, title="Active Thread", trigger="test")
        p2 = await service.create_thread(USER, title="Paused Thread", trigger="test")
        await service.change_status(USER, p2, "paused")

        result = await service.list_active_threads(USER)
        # Only the active thread should appear (paused is excluded)
        assert len(result) == 1
        assert result[0]["title"] == "Active Thread"
        assert result[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_includes_watching(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        p1 = await service.create_thread(USER, title="Watch Thread", trigger="test")
        await service.change_status(USER, p1, "watching")

        result = await service.list_active_threads(USER)
        assert len(result) == 1
        assert result[0]["status"] == "watching"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestUpdateThread:
    @pytest.mark.asyncio
    async def test_update_next_action(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="Update Test", trigger="test"
        )
        await service.update_thread(
            USER, rel_path, {"next_action": "Research flights"}
        )

        content = await vault.read_file(USER, rel_path)
        fm, _ = _parse_frontmatter(content)
        assert fm["next_action"] == "Research flights"

    @pytest.mark.asyncio
    async def test_append_progress(self, tmp_path):
        _prep_user(tmp_path)
        vault = _make_vault(tmp_path)
        service = ThreadService(vault)

        rel_path = await service.create_thread(
            USER, title="Progress Test", trigger="test"
        )
        await service.update_thread(
            USER, rel_path, {"progress_line": "Found 3 flight options."}
        )

        content = await vault.read_file(USER, rel_path)
        assert "Found 3 flight options." in content
        assert "## Progress" in content


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


class TestFrontmatterHelpers:
    def test_round_trip(self):
        from chatServer.services.thread_service import (
            _parse_frontmatter,
            _serialize_frontmatter_doc,
        )

        fm = {"title": "Test", "status": "active", "tags": ["a", "b"]}
        body = "## Goal\nDo stuff\n"
        content = _serialize_frontmatter_doc(fm, body)

        fm2, body2 = _parse_frontmatter(content)
        assert fm2["title"] == "Test"
        assert fm2["status"] == "active"
        assert "## Goal" in body2

    def test_no_frontmatter(self):
        fm, body = _parse_frontmatter("Just a plain document.")
        assert fm == {}
        assert body == "Just a plain document."
