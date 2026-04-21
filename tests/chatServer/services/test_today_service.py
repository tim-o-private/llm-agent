"""Unit tests for TodayService — composition over vault + approvals."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from chatServer.services.today_service import TodayService
from chatServer.services.vault_service import RecentEntry

USER_A = "user-a"

TODAY_BODY = """# Today

## Header

Shipping SPEC-045.

## Your day

- [[notes/meeting]] 10am standup

## To do

- [ ] Write tests
- [x] Ship the spec

## Notes

- [2026-04-20T12:00:00Z] Found a bug

## Agent

No sessions yet.

## Approvals

Nothing awaiting approval.

## Recent

No recent activity.
"""


@pytest.fixture
def vault():
    v = MagicMock()
    v.seed_if_missing = AsyncMock(return_value=None)
    v.read_file = AsyncMock(return_value=TODAY_BODY)
    stat = MagicMock()
    stat.st_mtime = 1234567890.0
    v.stat_file = AsyncMock(return_value=stat)
    v.update_body = AsyncMock(return_value=1234567891.0)
    v.list_recent = AsyncMock(return_value=[
        RecentEntry(path="notes/meeting.md", updated_at="2026-04-20T11:00:00Z"),
    ])
    return v


@pytest.fixture
def approvals():
    a = MagicMock()
    a.list_pending = AsyncMock(return_value=[{"id": "card-1", "status": "pending"}])
    return a


@pytest.fixture
def service(vault, approvals):
    return TodayService(vault=vault, approvals=approvals)


@pytest.mark.asyncio
async def test_get_today_composes_sections_and_sidebars(service, vault, approvals):
    result = await service.get_today(USER_A)

    assert result["header"]["framing"] == "Shipping SPEC-045."
    assert result["your_day"][0]["text"].startswith("[[notes/meeting]]")
    assert len(result["to_do"]) == 2
    assert result["to_do"][0]["text"] == "Write tests"
    assert result["to_do"][0]["checked"] is False
    assert result["to_do"][1]["checked"] is True
    assert result["notes"][0]["created_at"] == "2026-04-20T12:00:00Z"
    assert result["approvals"] == [{"id": "card-1", "status": "pending"}]
    assert result["recent"] == [{"path": "notes/meeting.md", "updated_at": "2026-04-20T11:00:00Z"}]
    assert result["source_mtime"] == 1234567890.0
    assert result["agent"] == {"running": [], "watching": [], "recent": [], "blocked": []}
    # Seeds today.md if missing.
    vault.seed_if_missing.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_today_handles_empty_state(service, vault):
    vault.read_file.return_value = "# Today\n\n## Header\n\nNo framing yet.\n\n"
    result = await service.get_today(USER_A)
    # Empty-state marker returns None for framing.
    assert result["header"]["framing"] is None


@pytest.mark.asyncio
async def test_get_source_returns_raw_body_and_mtime(service):
    result = await service.get_source(USER_A)
    assert result["body"] == TODAY_BODY
    assert result["source_mtime"] == 1234567890.0


@pytest.mark.asyncio
async def test_append_note_rejects_empty(service):
    with pytest.raises(HTTPException) as exc:
        await service.append_note(USER_A, "   ")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_append_note_writes_to_notes_section(service, vault):
    result = await service.append_note(USER_A, "remember to file tps")
    vault.update_body.assert_awaited_once()
    _, called_args, called_kwargs = vault.update_body.await_args_list[0][0], vault.update_body.await_args_list[0], None
    # update_body was called with (user_id, rel_path, new_body)
    args = vault.update_body.await_args.args
    new_body = args[2]
    assert "remember to file tps" in new_body
    assert result["text"] == "remember to file tps"
    assert result["source_mtime"] == 1234567891.0


@pytest.mark.asyncio
async def test_toggle_todo_roundtrip(service, vault):
    # Compute real line_id for "Write tests" in known body.
    from chatServer.services.markdown_sections import extract_todos

    todos = extract_todos(TODAY_BODY)
    line_id = todos[0]["line_id"]

    result = await service.toggle_todo(USER_A, line_id, checked=True, expected_mtime=1234567890.0)
    assert result["checked"] is True
    assert result["line_id"] == line_id
    # expected_mtime was forwarded to update_body.
    kwargs = vault.update_body.await_args.kwargs
    assert kwargs.get("expected_mtime") == 1234567890.0


@pytest.mark.asyncio
async def test_toggle_todo_missing_line_raises_409(service):
    with pytest.raises(HTTPException) as exc:
        await service.toggle_todo(USER_A, "deadbeefdeadbeef", checked=True)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_regenerate_dispatches_and_returns_run_id(service):
    db = MagicMock()
    anthropic = MagicMock()
    with patch(
        "chatServer.services.today_service.dispatch_workflow",
        new=AsyncMock(
            return_value="Started workflow 'regenerate-today' (run_id: run-123). I'll keep you updated on progress.",
        ),
    ) as mock_dispatch:
        run_id = await service.regenerate(USER_A, db, anthropic)

    assert run_id == "run-123"
    mock_dispatch.assert_awaited_once()
    kwargs = mock_dispatch.await_args.kwargs
    assert kwargs["args"] == {"workflow_name": "regenerate-today", "parameters": {}}
    assert kwargs["user_id"] == USER_A
    assert kwargs["db_client"] is db
    assert kwargs["anthropic_client"] is anthropic


@pytest.mark.asyncio
async def test_regenerate_failure_raises_503(service):
    with patch(
        "chatServer.services.today_service.dispatch_workflow",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(HTTPException) as exc:
            await service.regenerate(USER_A, MagicMock(), MagicMock())
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_regenerate_failure_message_raises_503(service):
    """Dispatch returned an error-shaped string (no run_id parseable)."""
    with patch(
        "chatServer.services.today_service.dispatch_workflow",
        new=AsyncMock(return_value="Failed to start workflow: boom"),
    ):
        with pytest.raises(HTTPException) as exc:
            await service.regenerate(USER_A, MagicMock(), MagicMock())
    assert exc.value.status_code == 503
