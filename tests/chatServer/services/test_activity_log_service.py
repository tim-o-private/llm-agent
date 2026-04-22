"""Unit tests for ActivityLogService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.activity_log_service import ActivityLogService

USER_A = "user-a"


def _system_with_insert_echo():
    """Return a mock SystemClient whose ``.insert()`` echoes the row."""
    captured: dict = {}

    def table(_name):
        tbl = MagicMock()

        def insert(payload):
            captured["payload"] = payload
            exec_mock = AsyncMock(return_value=MagicMock(data=[payload]))
            ret = MagicMock()
            ret.execute = exec_mock
            return ret

        tbl.insert = insert
        return tbl

    client = MagicMock()
    client.table.side_effect = table
    return client, captured


@pytest.mark.asyncio
async def test_append_writes_row_with_required_fields():
    system, captured = _system_with_insert_echo()
    svc = ActivityLogService(system_client=system)

    result = await svc.append(
        user_id=USER_A,
        actor="user",
        action="Approved email_draft: hello",
        status="done",
        subject_path=None,
        reasoning=None,
    )

    assert captured["payload"]["user_id"] == USER_A
    assert captured["payload"]["actor"] == "user"
    assert captured["payload"]["action"].startswith("Approved")
    assert captured["payload"]["status"] == "done"
    assert "created_at" in captured["payload"]
    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_append_rejects_bad_status():
    system, _ = _system_with_insert_echo()
    svc = ActivityLogService(system_client=system)
    with pytest.raises(ValueError):
        await svc.append(
            user_id=USER_A,
            actor="user",
            action="x",
            status="bogus",
        )


@pytest.mark.asyncio
async def test_list_recent_calls_user_scoped_client():
    user = MagicMock()
    chain = user.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "1"}]))

    system = MagicMock()
    svc = ActivityLogService(system_client=system, user_client=user)

    result = await svc.list_recent(USER_A)
    assert result == [{"id": "1"}]
    user.table.assert_called_with("activity_log")
