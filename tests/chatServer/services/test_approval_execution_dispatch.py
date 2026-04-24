"""Unit tests for SPEC-052 execution dispatch, idempotency, registry, and retry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from chatServer.services.activity_log_service import ActivityLogService
from chatServer.services.approval_service import ApprovalService


USER_A = "user-a"
CARD_ID = "card-1"


# ---------------------------------------------------------------------------
# Fake DB (same pattern as test_approval_service.py)
# ---------------------------------------------------------------------------


class _FakeQuery:
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


# ===========================================================================
# Registry
# ===========================================================================


class TestExecutorRegistry:
    def test_all_six_types_registered(self):
        from chatServer.services.approval_executors.registry import EXECUTOR_REGISTRY

        expected = {
            "email_draft",
            "calendar_hold",
            "outreach",
            "workflow_proposal",
            "config_change",
            "file_operation",
        }
        assert expected.issubset(set(EXECUTOR_REGISTRY.keys()))

    def test_get_executor_raises_for_unknown(self):
        from chatServer.services.approval_executors.registry import get_executor

        with pytest.raises(KeyError):
            get_executor("nonexistent_type")


# ===========================================================================
# Dispatch
# ===========================================================================


class TestExecutionDispatch:
    @pytest.mark.asyncio
    async def test_approve_triggers_execution(self, service, db, log_svc):
        """Approve should call _execute_after_approve, resulting in 2+ log entries."""
        from chatServer.services.approval_executors import ExecutionResult

        db.queue_rows([BASE_CARD])  # get() for _transition
        db.queue_rows([{**BASE_CARD, "status": "approved"}])  # update from _transition
        db.queue_rows([])  # update from _record_execution

        # Mock the executor to avoid Gmail API calls
        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                result={"message_id": "msg-1"},
                activity_action="Sent email to a@example.com",
            )
        )

        import chatServer.services.approval_executors.registry as registry

        original = registry.EXECUTOR_REGISTRY.get("email_draft")
        registry.EXECUTOR_REGISTRY["email_draft"] = lambda: mock_executor

        try:
            await service.approve(USER_A, CARD_ID)
        finally:
            if original is not None:
                registry.EXECUTOR_REGISTRY["email_draft"] = original

        # Two log entries: one for approval, one for execution
        assert log_svc.append.await_count == 2
        calls = log_svc.append.await_args_list

        # First call: user approval
        assert calls[0].kwargs["actor"] == "user"

        # Second call: execution
        assert calls[1].kwargs["actor"] == "approval-executor"
        assert calls[1].kwargs["status"] == "done"

    @pytest.mark.asyncio
    async def test_unknown_card_type_no_executor(self, service, db, log_svc):
        """Unknown card type should approve without execution, noted in log."""
        card = {**BASE_CARD, "card_type": "unknown_type"}
        db.queue_rows([card])
        db.queue_rows([{**card, "status": "approved"}])
        db.queue_rows([])  # _record_execution update

        await service.approve(USER_A, CARD_ID)

        # Two log entries: approval + no-executor
        assert log_svc.append.await_count == 2
        exec_call = log_svc.append.await_args_list[1]
        assert "no executor registered" in exec_call.kwargs["action"]

    @pytest.mark.asyncio
    async def test_idempotency_guard_skips_second_execution(
        self, service, db, log_svc
    ):
        """If card already has executed_at, _execute_after_approve is a no-op."""
        card_already_executed = {
            **BASE_CARD,
            "status": "approved",
            "executed_at": "2026-04-21T12:00:00Z",
        }

        # Call _execute_after_approve directly
        await service._execute_after_approve(card_already_executed, USER_A)

        # No execution log should be emitted (only the idempotency guard fires)
        log_svc.append.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_executor_exception_recorded(self, service, db, log_svc):
        """Unhandled executor exception is caught and recorded as failure."""
        card = {**BASE_CARD, "status": "approved"}

        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(side_effect=RuntimeError("boom"))

        import chatServer.services.approval_executors.registry as registry

        original = registry.EXECUTOR_REGISTRY.get("email_draft")
        registry.EXECUTOR_REGISTRY["email_draft"] = lambda: mock_executor

        db.queue_rows([])  # _record_execution update

        try:
            await service._execute_after_approve(card, USER_A)
        finally:
            if original is not None:
                registry.EXECUTOR_REGISTRY["email_draft"] = original

        log_svc.append.assert_awaited_once()
        call_kwargs = log_svc.append.await_args.kwargs
        assert call_kwargs["status"] == "failed"
        assert "boom" in call_kwargs["reasoning"]


# ===========================================================================
# Retry
# ===========================================================================


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_clears_and_redispatches(self, service, db, log_svc):
        """Retry should clear execution columns and re-dispatch."""
        from chatServer.services.approval_executors import ExecutionResult

        failed_card = {
            **BASE_CARD,
            "status": "approved",
            "executed_at": "2026-04-21T12:00:00Z",
            "execution_error": "Gmail API unavailable",
            "execution_result": None,
        }

        # 1. get() for retry pre-condition check
        db.queue_rows([failed_card])
        # 2. update() to clear execution columns
        cleared_card = {**failed_card, "executed_at": None, "execution_error": None}
        db.queue_rows([cleared_card])
        # 3. _record_execution update
        db.queue_rows([])
        # 4. get() for return value
        db.queue_rows([{**cleared_card, "executed_at": "2026-04-21T12:05:00Z"}])

        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                result={"message_id": "msg-retry"},
                activity_action="Sent email on retry",
            )
        )

        import chatServer.services.approval_executors.registry as registry

        original = registry.EXECUTOR_REGISTRY.get("email_draft")
        registry.EXECUTOR_REGISTRY["email_draft"] = lambda: mock_executor

        try:
            result = await service.retry(USER_A, CARD_ID)
        finally:
            if original is not None:
                registry.EXECUTOR_REGISTRY["email_draft"] = original

        # Verify execution columns were cleared
        clear_update = db.updates[0]
        assert clear_update["executed_at"] is None
        assert clear_update["execution_result"] is None
        assert clear_update["execution_error"] is None

    @pytest.mark.asyncio
    async def test_retry_rejects_non_approved(self, service, db):
        """Retry should reject cards that aren't approved."""
        db.queue_rows([BASE_CARD])  # status=pending

        with pytest.raises(HTTPException) as exc:
            await service.retry(USER_A, CARD_ID)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_rejects_no_execution(self, service, db):
        """Retry should reject cards that haven't been executed."""
        db.queue_rows([{**BASE_CARD, "status": "approved"}])

        with pytest.raises(HTTPException) as exc:
            await service.retry(USER_A, CARD_ID)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_retry_rejects_successful_execution(self, service, db):
        """Retry should reject cards that executed successfully."""
        db.queue_rows([{
            **BASE_CARD,
            "status": "approved",
            "executed_at": "2026-04-21T12:00:00Z",
            "execution_error": None,
        }])

        with pytest.raises(HTTPException) as exc:
            await service.retry(USER_A, CARD_ID)
        assert exc.value.status_code == 409


# ===========================================================================
# _describe_action (Stage 1 no-op removed)
# ===========================================================================


class TestDescribeActionNoNoop:
    @pytest.mark.asyncio
    async def test_approve_email_no_stage1_suffix(self, service, db, log_svc):
        """Approved email_draft no longer has 'Stage 1 no-op' suffix."""
        from chatServer.services.approval_executors import ExecutionResult

        db.queue_rows([BASE_CARD])
        db.queue_rows([{**BASE_CARD, "status": "approved"}])
        db.queue_rows([])  # _record_execution

        mock_executor = AsyncMock()
        mock_executor.execute = AsyncMock(
            return_value=ExecutionResult(success=True, result={})
        )

        import chatServer.services.approval_executors.registry as registry

        original = registry.EXECUTOR_REGISTRY.get("email_draft")
        registry.EXECUTOR_REGISTRY["email_draft"] = lambda: mock_executor

        try:
            await service.approve(USER_A, CARD_ID)
        finally:
            if original is not None:
                registry.EXECUTOR_REGISTRY["email_draft"] = original

        # Check the user-facing approval log entry
        approval_call = log_svc.append.await_args_list[0]
        assert "Stage 1 no-op" not in approval_call.kwargs["action"]
        assert "Approved" in approval_call.kwargs["action"]
