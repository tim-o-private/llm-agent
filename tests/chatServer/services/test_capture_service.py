"""Unit tests for CaptureService — capture routing into the vault."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from chatServer.services.capture_service import CaptureService
from chatServer.services.vault_service import TreeNode

USER_A = "user-a"


# --- Fixtures ---------------------------------------------------------------


def _tree_node(name: str, path: str, typ: str = "file", children=None):
    return TreeNode(
        name=name,
        path=path,
        type=typ,
        mtime="2026-04-20T12:00:00Z",
        size=100,
        children=children,
    )


SAMPLE_TREE = [
    _tree_node("today.md", "today.md"),
    _tree_node("projects", "projects", "folder", children=[
        _tree_node("acme.md", "projects/acme.md"),
        _tree_node("website.md", "projects/website.md"),
    ]),
    _tree_node("lists", "lists", "folder", children=[
        _tree_node("groceries.md", "lists/groceries.md"),
    ]),
]

TODAY_BODY = """# Today

## Header

Test day.

## To do

- [ ] Write tests

## Notes

- [2026-04-20T12:00:00Z] Previous note
"""


@pytest.fixture
def vault():
    v = MagicMock()
    v.list_tree = AsyncMock(return_value=SAMPLE_TREE)
    v.read_file = AsyncMock(return_value=TODAY_BODY)
    v.update_body = AsyncMock(return_value=1234567891.0)
    v.seed_if_missing = AsyncMock(return_value=None)
    stat = MagicMock()
    stat.st_mtime = 1234567890.0
    v.stat_file = AsyncMock(return_value=stat)
    return v


@pytest.fixture
def today(vault):
    from chatServer.services.approval_service import ApprovalService

    approvals = MagicMock(spec=ApprovalService)
    approvals.list_pending = AsyncMock(return_value=[])

    from chatServer.services.today_service import TodayService

    return TodayService(vault=vault, approvals=approvals)


@pytest.fixture
def activity_log():
    al = MagicMock()
    al.append = AsyncMock(return_value={"id": "log-1"})
    return al


class _ChainableMock:
    """A mock that returns itself for any chained method call, with async execute."""

    def __init__(self, execute_data=None):
        self._execute_data = execute_data or [{}]

    def __getattr__(self, name):
        if name == "execute":
            resp = MagicMock()
            resp.data = self._execute_data
            return AsyncMock(return_value=resp)
        # Any other method returns self for chaining.
        return MagicMock(return_value=self)


@pytest.fixture
def system_client():
    """Mock system client for DB operations."""
    client = MagicMock()

    def _table(name):
        table = MagicMock()

        # INSERT: returns a row with an id.
        insert_chain = _ChainableMock(
            execute_data=[{"id": "cap-123", "user_id": USER_A, "text": "test", "source": "today", "status": "routing"}]
        )
        table.insert = MagicMock(return_value=insert_chain)

        # UPDATE: returns empty success.
        update_chain = _ChainableMock(execute_data=[{}])
        table.update = MagicMock(return_value=update_chain)

        return table

    client.table = MagicMock(side_effect=_table)
    return client


@pytest.fixture
def user_client():
    """Mock user-scoped client for reads."""
    client = MagicMock()
    return client


def _setup_user_select(user_client, rows):
    """Configure the user_client mock to return rows on SELECT."""
    resp = MagicMock()
    resp.data = rows
    execute_mock = AsyncMock(return_value=resp)

    # Chain: table().select().eq().eq().execute()
    eq2 = MagicMock()
    eq2.execute = execute_mock
    eq1 = MagicMock()
    eq1.eq = MagicMock(return_value=eq2)
    select_mock = MagicMock()
    select_mock.eq = MagicMock(return_value=eq1)
    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_mock)
    user_client.table = MagicMock(return_value=table_mock)


@pytest.fixture
def service(vault, today, system_client, user_client, activity_log):
    return CaptureService(
        vault=vault,
        today=today,
        system_client=system_client,
        user_client=user_client,
        activity_log=activity_log,
    )


# --- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_capture_routes_to_notes_fallback(service, vault, user_client):
    """A generic note with no keywords should fall back to today.md Notes."""
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "random thought",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "today.md",
        "target_section": "Notes",
        "method": "append",
        "reasoning": "No specific target identified; falling back to today.md Notes.",
        "fallback": True,
        "confirmation": "Added to `today.md` under Notes",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }])

    result = await service.create_capture(USER_A, "random thought", "today")

    assert result["status"] == "placed"
    assert result["target_path"] == "today.md"


@pytest.mark.asyncio
async def test_create_capture_routes_todo(service, vault, user_client):
    """Text starting with 'todo:' should route to today.md To do section."""
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "todo: buy milk",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "today.md",
        "target_section": "To do",
        "method": "append",
        "reasoning": "Text starts with 'todo:' — routing to To do.",
        "fallback": False,
        "confirmation": "Added to `today.md` under To do",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }])

    result = await service.create_capture(USER_A, "todo: buy milk", "today")

    assert result["status"] == "placed"
    assert result["target_path"] == "today.md"
    assert result["target_section"] == "To do"


@pytest.mark.asyncio
async def test_create_capture_rejects_empty_text(service):
    """Empty text should be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        await service.create_capture(USER_A, "", "today")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_capture_rejects_whitespace_only(service):
    """Whitespace-only text should be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        await service.create_capture(USER_A, "   ", "today")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_capture_rejects_invalid_source(service):
    """Invalid source should be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        await service.create_capture(USER_A, "hello", "invalid")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_capture_rejects_oversized_text(service):
    """Text over 10KB should be rejected with 413."""
    big_text = "x" * 11000
    with pytest.raises(HTTPException) as exc_info:
        await service.create_capture(USER_A, big_text, "today")
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_fallback_on_routing_error(service, vault, user_client, today, activity_log):
    """If routing fails, capture should fall back to today.md Notes."""
    # Make vault.list_tree raise an error to simulate routing failure.
    vault.list_tree = AsyncMock(side_effect=RuntimeError("tree failed"))

    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "thought during error",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "today.md",
        "target_section": "Notes",
        "method": "append",
        "fallback": True,
        "confirmation": "Added to `today.md` under Notes (fallback)",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "reasoning": None,
        "error_detail": "tree failed",
    }])

    result = await service.create_capture(USER_A, "thought during error", "today")

    assert result["status"] == "placed"
    assert result["fallback"] is True


@pytest.mark.asyncio
async def test_redirect_updates_target(service, vault, user_client, activity_log):
    """Redirect should move content to the new target."""
    # First, set up a placed capture.
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "meeting notes",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "today.md",
        "target_section": "Notes",
        "method": "append",
        "reasoning": "Fallback",
        "fallback": True,
        "confirmation": "Added to `today.md` under Notes",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }])

    await service.redirect_capture(USER_A, "cap-123", "projects/acme.md")

    # Verify vault operations were called
    vault.read_file.assert_called()
    vault.update_body.assert_called()
    activity_log.append.assert_called()


@pytest.mark.asyncio
async def test_redirect_rejects_routing_status(service, user_client):
    """Cannot redirect a capture that is still routing."""
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "still routing",
        "source": "today",
        "context": None,
        "status": "routing",
        "target_path": None,
        "target_section": None,
        "method": None,
        "reasoning": None,
        "fallback": False,
        "confirmation": None,
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": None,
        "error_detail": None,
    }])

    with pytest.raises(HTTPException) as exc_info:
        await service.redirect_capture(USER_A, "cap-123", "today")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_redirect_rejects_already_redirected(service, user_client):
    """Cannot redirect a capture that has already been redirected (Stage 2)."""
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "already moved",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "projects/acme.md",
        "target_section": "Notes",
        "method": "append",
        "reasoning": "Explicit path",
        "fallback": False,
        "confirmation": "Added to `projects/acme.md`",
        "redirect": {"from_path": "today.md", "target_hint": "acme"},
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }])

    with pytest.raises(HTTPException) as exc_info:
        await service.redirect_capture(USER_A, "cap-123", "elsewhere")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_activity_log_entries(service, vault, user_client, activity_log):
    """Capture placement should log to activity_log."""
    _setup_user_select(user_client, [{
        "id": "cap-123",
        "user_id": USER_A,
        "text": "logging test",
        "source": "today",
        "context": None,
        "status": "placed",
        "target_path": "today.md",
        "target_section": "Notes",
        "method": "append",
        "reasoning": "Fallback",
        "fallback": True,
        "confirmation": "Added to today.md",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }])

    await service.create_capture(USER_A, "logging test", "today")

    # activity_log.append should have been called
    activity_log.append.assert_called()
    call_kwargs = activity_log.append.call_args
    assert call_kwargs.kwargs["actor"] == "capture-router"
    assert call_kwargs.kwargs["user_id"] == USER_A


# --- Rule-based routing unit tests ------------------------------------------


class TestRuleBasedRouting:
    """Test the internal _rule_based_route method."""

    @pytest.fixture
    def svc(self, vault, today, system_client, user_client, activity_log):
        return CaptureService(
            vault=vault,
            today=today,
            system_client=system_client,
            user_client=user_client,
            activity_log=activity_log,
        )

    def test_explicit_path_existing(self, svc):
        result = svc._rule_based_route(
            "add to projects/acme.md: review contract",
            SAMPLE_TREE,
            {},
        )
        assert result["target_path"] == "projects/acme.md"
        assert result["method"] == "append"
        assert result["confidence"] >= 0.9

    def test_explicit_path_new_file(self, svc):
        result = svc._rule_based_route(
            "add to ideas/new-thing.md: great idea",
            SAMPLE_TREE,
            {},
        )
        assert result["target_path"] == "ideas/new-thing.md"
        assert result["method"] == "create"

    def test_todo_prefix(self, svc):
        for prefix in ["todo:", "todo ", "task:", "to-do:"]:
            result = svc._rule_based_route(f"{prefix} buy groceries", SAMPLE_TREE, {})
            assert result["target_path"] == "today.md"
            assert result["target_section"] == "To do"

    def test_fallback_to_notes(self, svc):
        result = svc._rule_based_route("something random", SAMPLE_TREE, {})
        assert result["target_path"] == "today.md"
        assert result["target_section"] == "Notes"
        assert result["confidence"] < _CONFIDENCE_THRESHOLD

    def test_keyword_match(self, svc):
        result = svc._rule_based_route(
            "review acme projects contract",
            SAMPLE_TREE,
            {},
        )
        # "acme" and "projects" should match projects/acme.md
        assert result["target_path"] == "projects/acme.md"

    def test_folder_affinity(self, svc):
        result = svc._rule_based_route(
            "quick note about something",
            SAMPLE_TREE,
            {"current_path": "projects/acme.md"},
        )
        # Should route to a file in projects/ due to folder affinity
        assert result["target_path"].startswith("projects/")


# Import the threshold constant for tests.
from chatServer.services.capture_service import _CONFIDENCE_THRESHOLD  # noqa: E402
