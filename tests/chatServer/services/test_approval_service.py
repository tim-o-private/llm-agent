"""Unit tests for ApprovalService — state machine + activity_log side effects."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from chatServer.services.activity_log_service import ActivityLogService
from chatServer.services.approval_service import ApprovalService

USER_A = "user-a"
OTHER_USER = "user-b"
CARD_ID = "card-1"


class _FakeQuery:
    """Minimal chainable fake for Supabase queries.

    Each instance remembers what operation it represents and returns
    configured rows from ``.execute()``. ``eq`` returns ``self`` so chains
    compose cleanly; ``update`` stores the patch on the parent for assertions.
    """

    def __init__(self, parent):
        self.parent = parent
        self._patch = None

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        self.parent.inserts.append(data)
        return self

    def update(self, patch):
        self.parent.updates.append(patch)
        self._patch = patch
        return self

    async def execute(self):
        rows = self.parent.next_rows()
        return MagicMock(data=rows, count=len(rows))


class FakeDb:
    """Fake user-scoped client. Queue rows via ``queue_rows``."""

    def __init__(self):
        self._row_queue: list[list[dict]] = []
        self.inserts: list = []
        self.updates: list = []

    def queue_rows(self, rows: list[dict]):
        self._row_queue.append(rows)

    def next_rows(self) -> list[dict]:
        if self._row_queue:
            return self._row_queue.pop(0)
        return []

    def table(self, _name):
        return _FakeQuery(self)


@pytest.fixture
def db():
    return FakeDb()


@pytest.fixture
def log_svc():
    svc = MagicMock(spec=ActivityLogService)
    svc.append = AsyncMock(return_value={"id": "log-1"})
    return svc


@pytest.fixture
def service(db, log_svc):
    return ApprovalService(user_client=db, activity_log=log_svc)


BASE_CARD = {
    "id": CARD_ID,
    "user_id": USER_A,
    "card_type": "email_draft",
    "title": "Reply to Alice",
    "payload": {"to": ["a@example.com"], "subject": "hi", "body": "hey"},
    "status": "pending",
}


@pytest.mark.asyncio
async def test_approve_pending_sets_decided_fields_and_logs(service, db, log_svc):
    db.queue_rows([BASE_CARD])  # get()
    db.queue_rows([{**BASE_CARD, "status": "approved", "decided_by": USER_A}])  # update (status)
    db.queue_rows([])  # update (execution columns from _record_execution)

    updated = await service.approve(USER_A, CARD_ID, decision_note="LGTM")

    assert updated["status"] == "approved"
    assert db.updates[0]["status"] == "approved"
    assert db.updates[0]["decided_by"] == USER_A
    assert db.updates[0]["decision_note"] == "LGTM"
    # Two log entries: approval + execution attempt (SPEC-052)
    assert log_svc.append.await_count == 2
    approval_kwargs = log_svc.append.await_args_list[0].kwargs
    assert approval_kwargs["status"] == "done"
    assert approval_kwargs["actor"] == "user"
    assert "Approved" in approval_kwargs["action"]
    # Stage 1 no-op suffix removed by SPEC-052.
    assert "Stage 1 no-op" not in approval_kwargs["action"]


@pytest.mark.asyncio
async def test_approve_non_pending_raises_409(service, db, log_svc):
    db.queue_rows([{**BASE_CARD, "status": "approved"}])
    with pytest.raises(HTTPException) as exc:
        await service.approve(USER_A, CARD_ID)
    assert exc.value.status_code == 409
    log_svc.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_sets_status_and_records_reason(service, db, log_svc):
    db.queue_rows([BASE_CARD])
    db.queue_rows([{**BASE_CARD, "status": "rejected"}])

    updated = await service.reject(USER_A, CARD_ID, reason="wrong tone")

    assert updated["status"] == "rejected"
    log_kwargs = log_svc.append.await_args.kwargs
    assert "Rejected" in log_kwargs["action"]
    assert log_kwargs["reasoning"] == "wrong tone"
    # Rejection doesn't carry the Stage-1 no-op marker.
    assert "Stage 1 no-op" not in log_kwargs["action"]


@pytest.mark.asyncio
async def test_edit_merges_payload_and_keeps_status_pending(service, db, log_svc):
    db.queue_rows([BASE_CARD])
    db.queue_rows([
        {**BASE_CARD, "payload": {**BASE_CARD["payload"], "body": "new"}},
    ])

    updated = await service.edit(USER_A, CARD_ID, {"body": "new"})

    assert updated["payload"]["body"] == "new"
    assert updated["payload"]["subject"] == "hi"  # original merged in
    assert updated["status"] == "pending"
    log_kwargs = log_svc.append.await_args.kwargs
    assert log_kwargs["status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_edit_rejects_empty_patch(service, log_svc):
    with pytest.raises(HTTPException) as exc:
        await service.edit(USER_A, CARD_ID, {})
    assert exc.value.status_code == 400
    log_svc.append.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_on_decided_card_raises_409(service, db):
    db.queue_rows([{**BASE_CARD, "status": "approved"}])
    with pytest.raises(HTTPException) as exc:
        await service.edit(USER_A, CARD_ID, {"body": "x"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_get_missing_returns_404(service, db):
    db.queue_rows([])  # get() sees no rows
    with pytest.raises(HTTPException) as exc:
        await service.get(USER_A, CARD_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_approve_config_change_has_no_stage1_noop_suffix(service, db, log_svc):
    card = {**BASE_CARD, "card_type": "config_change", "payload": {"file_path": "agents/x.md"}}
    db.queue_rows([card])
    db.queue_rows([{**card, "status": "approved"}])
    db.queue_rows([])  # execution update
    await service.approve(USER_A, CARD_ID)
    # No outbound markers — SPEC-052 removed all Stage-1 no-op suffixes.
    approval_kwargs = log_svc.append.await_args_list[0].kwargs
    assert "Stage 1 no-op" not in approval_kwargs["action"]
    assert approval_kwargs["subject_path"] == "agents/x.md"
