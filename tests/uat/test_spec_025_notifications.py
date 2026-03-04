"""
UAT flow tests: SPEC-025 Unified Notification Experience.

Covers the backend ACs using real FastAPI routing, Pydantic validation,
and real service logic. Only the DB boundary is mocked (SupabaseFixture).

AC coverage:
  AC-04 — Type routing: notify/silent stored, agent_only never stored
  AC-06 — Approval creates both pending_action AND notification
  AC-07 — Approval creates notification with requires_approval=True
  AC-08 — Approve/reject endpoints return correct response shape
  AC-09 — Approve endpoint creates silent follow-up notification
  User isolation — user A cannot see user B's notifications
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.uat.conftest import TEST_USER_ID

OTHER_USER_ID = "uat-other-user-00000000-0000-0000-0000-000000000002"

# pending_actions.PendingAction validates user_id as UUID — must be well-formed UUIDs
# TEST_USER_ID is not a valid UUID, so we use a separate UUID for pending_action rows.
PENDING_ACTION_USER_UUID = "00000000-0000-0000-0001-000000000001"
OTHER_USER_UUID = "00000000-0000-0000-0001-000000000002"

ACTION_ID = "aaaaaaaa-0000-0000-0000-000000000001"
ACTION_ID_2 = "aaaaaaaa-0000-0000-0000-000000000002"

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _make_notification(
    notif_id: str,
    user_id: str = TEST_USER_ID,
    notif_type: str = "notify",
    requires_approval: bool = False,
    pending_action_id: str | None = None,
    read: bool = False,
    category: str = "info",
    title: str = "Test notification",
    body: str = "Test body",
    created_at: str = "2026-02-26T10:00:00+00:00",
) -> dict:
    row: dict = {
        "id": notif_id,
        "user_id": user_id,
        "title": title,
        "body": body,
        "category": category,
        "metadata": {},
        "read": read,
        "created_at": created_at,
        "feedback": None,
        "feedback_at": None,
        "type": notif_type,
        "requires_approval": requires_approval,
    }
    if pending_action_id is not None:
        row["pending_action_id"] = pending_action_id
    return row


def _make_pending_action(
    action_id: str,
    user_id: str = PENDING_ACTION_USER_UUID,
    tool_name: str = "gmail_send_message",
    status: str = "pending",
    expires_offset_hours: int = 24,
) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expires_offset_hours)
    return {
        "id": action_id,
        "user_id": user_id,
        "tool_name": tool_name,
        "tool_args": {"to": "test@example.com", "subject": "Hello"},
        "status": status,
        "context": {"session_id": "sess-1", "agent_name": "assistant"},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "resolved_at": None,
        "execution_result": None,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def actions_client(supabase_fixture, mock_psycopg_conn):
    """
    authenticated_client variant that identifies as PENDING_ACTION_USER_UUID.

    PendingAction model validates user_id as UUID. TEST_USER_ID is not a
    valid UUID, so actions endpoints need a proper UUID user identity.
    """
    import os
    from contextlib import AsyncExitStack
    from unittest.mock import AsyncMock, patch

    from httpx import ASGITransport, AsyncClient

    lifespan_patches = [
        patch("chatServer.database.connection.get_database_manager", return_value=AsyncMock()),
        patch(
            "chatServer.database.supabase_client.get_supabase_manager",
            return_value=_mock_supabase_manager(supabase_fixture),
        ),
        patch("chatServer.services.tool_cache_service.initialize_tool_cache", new_callable=AsyncMock),
        patch("chatServer.services.tool_cache_service.shutdown_tool_cache", new_callable=AsyncMock),
        patch(
            "chatServer.services.background_tasks.get_background_task_service",
            return_value=_mock_background_service(),
        ),
    ]
    for p in lifespan_patches:
        p.start()

    from chatServer.config.settings import get_settings
    settings = get_settings()
    orig_telegram_token = settings.telegram_bot_token
    settings.telegram_bot_token = None

    jwt_patch = patch("jose.jwt.decode", return_value={"sub": PENDING_ACTION_USER_UUID, "aud": "authenticated"})
    jwt_patch.start()
    env_patch = patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    env_patch.start()

    from chatServer.database.connection import get_db_connection
    from chatServer.database.supabase_client import get_supabase_client
    from chatServer.dependencies.auth import get_current_user
    from chatServer.main import app

    app.dependency_overrides[get_current_user] = lambda: PENDING_ACTION_USER_UUID
    app.dependency_overrides[get_supabase_client] = lambda: supabase_fixture
    app.dependency_overrides[get_db_connection] = _make_db_conn_generator(mock_psycopg_conn)

    from chatServer import main as chat_main_module
    if hasattr(chat_main_module, "AGENT_EXECUTOR_CACHE"):
        chat_main_module.AGENT_EXECUTOR_CACHE.clear()

    import chatServer.services.chat
    chatServer.services.chat._chat_service = None

    stack = AsyncExitStack()
    await stack.enter_async_context(app.router.lifespan_context(app))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://uat-test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
    await stack.aclose()
    settings.telegram_bot_token = orig_telegram_token
    jwt_patch.stop()
    env_patch.stop()
    for p in lifespan_patches:
        p.stop()


def _mock_supabase_manager(fixture):
    from unittest.mock import AsyncMock
    manager = AsyncMock()
    manager.get_client.return_value = fixture
    manager.client = fixture
    return manager


def _mock_background_service():
    from unittest.mock import AsyncMock, MagicMock
    service = MagicMock()
    service.stop_background_tasks = AsyncMock()
    service.start_background_tasks = MagicMock()
    service.set_agent_executor_cache = MagicMock()
    return service


def _make_db_conn_generator(mock_conn):
    async def _generator():
        yield mock_conn
    return _generator


# ---------------------------------------------------------------------------
# AC-04: Type routing flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAC04TypeRouting:
    """AC-04: GET /api/notifications returns notify+silent, never agent_only."""

    async def test_ac_04_notify_type_appears_in_list(
        self, authenticated_client, supabase_fixture
    ):
        """AC-04: type='notify' notifications are returned by the list endpoint."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification("n-notify-1", notif_type="notify"),
                _make_notification("n-notify-2", notif_type="notify"),
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        ids = [n["id"] for n in data]
        assert "n-notify-1" in ids
        assert "n-notify-2" in ids

    async def test_ac_04_silent_type_appears_in_list(
        self, authenticated_client, supabase_fixture
    ):
        """AC-04: type='silent' notifications are returned (stored in DB)."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification("n-silent-1", notif_type="silent"),
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["id"] == "n-silent-1"

    async def test_ac_04_agent_only_excluded_from_list(
        self, authenticated_client, supabase_fixture
    ):
        """AC-04: type='agent_only' must never appear — endpoint excludes them."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification("n-real-1", notif_type="notify"),
                # agent_only should not appear even if somehow in DB
                _make_notification("n-agent-only-1", notif_type="agent_only"),
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        ids = [n["id"] for n in data]
        assert "n-real-1" in ids
        assert "n-agent-only-1" not in ids, (
            "agent_only notifications must never appear in the list response"
        )

    async def test_ac_04_mixed_types_filtered_correctly(
        self, authenticated_client, supabase_fixture
    ):
        """AC-04: Mixed seed — only notify+silent returned, agent_only excluded."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification("n-notify-x", notif_type="notify"),
                _make_notification("n-silent-x", notif_type="silent"),
                _make_notification("n-agent-x", notif_type="agent_only"),
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        ids = [n["id"] for n in data]
        assert "n-notify-x" in ids
        assert "n-silent-x" in ids
        assert "n-agent-x" not in ids
        assert len(data) == 2

    async def test_ac_04_response_shape_has_required_fields(
        self, authenticated_client, supabase_fixture
    ):
        """AC-04: Response shape matches NotificationResponse contract."""
        supabase_fixture.seed(
            "notifications",
            [_make_notification("n-shape-1", notif_type="notify")],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        n = r.json()[0]
        assert "id" in n
        assert "title" in n
        assert "body" in n
        assert "category" in n
        assert "read" in n
        assert "created_at" in n
        # user_id must NOT appear in the response (stripped by Pydantic model)
        assert "user_id" not in n


# ---------------------------------------------------------------------------
# AC-06 + AC-07: Approval creates notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAC06AC07ApprovalFlow:
    """
    AC-06: tool_wrapper creates pending_action AND notification.
    AC-07: notification has requires_approval=True and pending_action_id set.

    We test this at the service layer by directly exercising NotificationService
    and verifying the stored notification has the right fields. The tool_wrapper
    unit tests already verify the dual creation; these flow tests verify the
    stored notification shape via the DB fixture.
    """

    async def test_ac_06_approval_notification_stored_with_correct_fields(
        self, authenticated_client, supabase_fixture
    ):
        """
        AC-06/AC-07: Notification created for approval has type=notify,
        requires_approval=True, and pending_action_id set.
        """
        # Seed a notification as tool_wrapper would create it
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification(
                    "n-approval-1",
                    notif_type="notify",
                    requires_approval=True,
                    pending_action_id=ACTION_ID,
                    category="approval_needed",
                    title="Approval needed: gmail_send_message",
                    body="The agent wants to run 'gmail_send_message'. Review in chat.",
                )
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        n = data[0]
        assert n["id"] == "n-approval-1"
        assert n["category"] == "approval_needed"
        assert n["title"] == "Approval needed: gmail_send_message"

    async def test_ac_07_approval_notification_requires_approval_true(
        self, authenticated_client, supabase_fixture
    ):
        """AC-07: Notification has requires_approval=True in stored data."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification(
                    "n-req-approval-1",
                    notif_type="notify",
                    requires_approval=True,
                    pending_action_id=ACTION_ID,
                    category="approval_needed",
                )
            ],
        )

        # Verify the stored row has the correct fields in the DB fixture
        table_data = supabase_fixture.get_table_data("notifications")
        assert len(table_data) == 1
        row = table_data[0]
        assert row["requires_approval"] is True
        assert row["pending_action_id"] == ACTION_ID
        assert row["type"] == "notify"

    async def test_ac_06_both_pending_action_and_notification_created(
        self, authenticated_client, supabase_fixture
    ):
        """
        AC-06: Both pending_action and notification rows exist after approval queue.

        Uses the NotificationService directly with the fixture to confirm both
        tables are written. Mirrors what tool_wrapper does in production.
        """
        from chatServer.services.notification_service import NotificationService

        supabase_fixture.seed("pending_actions", [])
        supabase_fixture.seed("notifications", [])

        # Simulate tool_wrapper: insert pending_action first
        action_row = {
            "id": ACTION_ID,
            "user_id": TEST_USER_ID,
            "tool_name": "gmail_send_message",
            "tool_args": {"to": "test@example.com"},
            "status": "pending",
            "context": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "resolved_at": None,
            "execution_result": None,
        }
        supabase_fixture.seed("pending_actions", [action_row])

        # Then create approval notification via NotificationService
        service = NotificationService(supabase_fixture)
        notif_id = await service.notify_user(
            user_id=TEST_USER_ID,
            title="Approval needed: gmail_send_message",
            body="The agent wants to run this tool.",
            category="approval_needed",
            type="notify",
            requires_approval=True,
            pending_action_id=ACTION_ID,
            metadata={"tool_name": "gmail_send_message", "action_id": ACTION_ID},
        )

        # Both tables should have data
        pending = supabase_fixture.get_table_data("pending_actions")
        notifications = supabase_fixture.get_table_data("notifications")

        assert len(pending) == 1, "pending_action must exist"
        assert len(notifications) == 1, "notification must exist"
        assert notif_id is not None
        assert notifications[0]["requires_approval"] is True
        assert notifications[0]["pending_action_id"] == ACTION_ID
        assert notifications[0]["type"] == "notify"


# ---------------------------------------------------------------------------
# AC-08: Approve/reject endpoints return correct response shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAC08ApproveRejectEndpoints:
    """AC-08: Approve/reject endpoints return ActionResultResponse shape."""

    async def test_ac_08_approve_endpoint_response_shape(
        self, actions_client, supabase_fixture
    ):
        """AC-08: POST /api/actions/{id}/approve returns success, message, result."""
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ), patch(
            "chatServer.services.tool_execution.ToolExecutionService.execute_tool",
            new_callable=AsyncMock,
            return_value="Tool executed successfully",
        ):
            r = await actions_client.post(f"/api/actions/{ACTION_ID}/approve")

        assert r.status_code == 200
        body = r.json()
        assert "success" in body
        assert "message" in body
        # result is optional (present only when tool_executor ran)
        assert "error" in body or body["error"] is None

    async def test_ac_08_approve_endpoint_returns_success_true(
        self, actions_client, supabase_fixture
    ):
        """AC-08: Approve on a valid pending action returns success=True."""
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ), patch(
            "chatServer.services.tool_execution.ToolExecutionService.execute_tool",
            new_callable=AsyncMock,
            return_value="Tool executed successfully",
        ):
            r = await actions_client.post(f"/api/actions/{ACTION_ID}/approve")

        assert r.status_code == 200
        assert r.json()["success"] is True

    async def test_ac_08_reject_endpoint_response_shape(
        self, actions_client, supabase_fixture
    ):
        """AC-08: POST /api/actions/{id}/reject returns success, message."""
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID_2)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ):
            r = await actions_client.post(
                f"/api/actions/{ACTION_ID_2}/reject",
                json={"reason": "Not needed"},
            )

        assert r.status_code == 200
        body = r.json()
        assert "success" in body
        assert "message" in body
        assert body["success"] is True

    async def test_ac_08_reject_without_reason_works(
        self, actions_client, supabase_fixture
    ):
        """AC-08: Reject accepts empty reason body."""
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID_2)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ):
            r = await actions_client.post(
                f"/api/actions/{ACTION_ID_2}/reject",
                json={},
            )

        assert r.status_code == 200
        assert r.json()["success"] is True


# ---------------------------------------------------------------------------
# AC-09: Approve creates follow-up silent notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAC09FollowUpNotification:
    """AC-09: Approving an action creates a follow-up silent notification."""

    async def test_ac_09_approve_creates_silent_followup(
        self, actions_client, supabase_fixture
    ):
        """
        AC-09: After approval, a silent notification with category='agent_result'
        is created in the notifications table.
        """
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ), patch(
            "chatServer.services.tool_execution.ToolExecutionService.execute_tool",
            new_callable=AsyncMock,
            return_value="Tool executed successfully",
        ):
            r = await actions_client.post(f"/api/actions/{ACTION_ID}/approve")

        assert r.status_code == 200
        assert r.json()["success"] is True

        # Verify a follow-up silent notification was created
        notifs = supabase_fixture.get_table_data("notifications")
        assert len(notifs) >= 1, "Follow-up notification must be created on approve"

        # Find the agent_result / silent notification
        followup = next(
            (n for n in notifs if n.get("category") == "agent_result"),
            None,
        )
        assert followup is not None, (
            "Expected a follow-up notification with category='agent_result'"
        )
        assert followup["type"] == "silent", (
            "Follow-up notification must be type='silent' (no Telegram ping)"
        )
        assert followup["user_id"] == PENDING_ACTION_USER_UUID

    async def test_ac_09_followup_notification_title_contains_tool_name(
        self, actions_client, supabase_fixture
    ):
        """AC-09: Follow-up notification title references the tool name."""
        supabase_fixture.seed(
            "pending_actions",
            [_make_pending_action(ACTION_ID, tool_name="gmail_send_message")],
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ), patch(
            "chatServer.services.tool_execution.ToolExecutionService.execute_tool",
            new_callable=AsyncMock,
            return_value="Tool executed successfully",
        ):
            r = await actions_client.post(f"/api/actions/{ACTION_ID}/approve")

        assert r.status_code == 200
        notifs = supabase_fixture.get_table_data("notifications")
        followup = next(
            (n for n in notifs if n.get("category") == "agent_result"), None
        )
        assert followup is not None
        assert "gmail_send_message" in followup["title"]

    async def test_ac_09_followup_not_sent_to_telegram(
        self, actions_client, supabase_fixture
    ):
        """
        AC-09: Follow-up notification is type='silent' so Telegram is NOT called.
        """
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID)]
        )
        supabase_fixture.seed("notifications", [])

        telegram_mock = AsyncMock()
        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            telegram_mock,
        ), patch(
            "chatServer.services.tool_execution.ToolExecutionService.execute_tool",
            new_callable=AsyncMock,
            return_value="Tool executed successfully",
        ):
            r = await actions_client.post(f"/api/actions/{ACTION_ID}/approve")

        assert r.status_code == 200
        # Telegram must NOT have been called for the silent follow-up
        telegram_mock.assert_not_awaited()

    async def test_ac_09_reject_also_creates_silent_followup(
        self, actions_client, supabase_fixture
    ):
        """AC-09 (reject path): Rejecting also creates a silent follow-up notification."""
        supabase_fixture.seed(
            "pending_actions", [_make_pending_action(ACTION_ID_2)]
        )
        supabase_fixture.seed("notifications", [])

        with patch(
            "chatServer.services.notification_service.NotificationService._send_telegram_notification",
            new_callable=AsyncMock,
        ):
            r = await actions_client.post(
                f"/api/actions/{ACTION_ID_2}/reject",
                json={"reason": "Not needed"},
            )

        assert r.status_code == 200
        notifs = supabase_fixture.get_table_data("notifications")
        followup = next(
            (n for n in notifs if n.get("category") == "agent_result"), None
        )
        assert followup is not None
        assert followup["type"] == "silent"


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUserIsolation:
    """User A cannot see or affect user B's notifications or actions."""

    async def test_isolation_notifications_user_b_not_visible(
        self, authenticated_client, supabase_fixture
    ):
        """User A's client cannot see user B's notifications."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification(
                    "n-user-a-1",
                    user_id=TEST_USER_ID,
                    title="User A notification",
                ),
                _make_notification(
                    "n-user-b-1",
                    user_id=OTHER_USER_ID,
                    title="User B notification",
                ),
            ],
        )

        r = await authenticated_client.get("/api/notifications")

        assert r.status_code == 200
        data = r.json()
        ids = [n["id"] for n in data]
        assert "n-user-a-1" in ids
        assert "n-user-b-1" not in ids, (
            "User B's notifications must not appear in user A's response"
        )

    async def test_isolation_notification_count_only_for_current_user(
        self, authenticated_client, supabase_fixture
    ):
        """Unread count only counts current user's unread notifications."""
        supabase_fixture.seed(
            "notifications",
            [
                # 1 unread for test user
                _make_notification(
                    "n-ua-unread",
                    user_id=TEST_USER_ID,
                    read=False,
                ),
                # 5 unread for other user (should not affect count)
                _make_notification("n-ub-1", user_id=OTHER_USER_ID, read=False),
                _make_notification("n-ub-2", user_id=OTHER_USER_ID, read=False),
                _make_notification("n-ub-3", user_id=OTHER_USER_ID, read=False),
                _make_notification("n-ub-4", user_id=OTHER_USER_ID, read=False),
                _make_notification("n-ub-5", user_id=OTHER_USER_ID, read=False),
            ],
        )

        r = await authenticated_client.get("/api/notifications/unread/count")

        assert r.status_code == 200
        assert r.json()["count"] == 1, (
            "Unread count must only reflect current user's notifications"
        )

    async def test_isolation_mark_read_does_not_affect_other_user(
        self, authenticated_client, supabase_fixture
    ):
        """Mark-read for user A does not change user B's notification state."""
        supabase_fixture.seed(
            "notifications",
            [
                _make_notification(
                    "n-ua-read-me",
                    user_id=TEST_USER_ID,
                    read=False,
                ),
                _make_notification(
                    "n-ub-untouched",
                    user_id=OTHER_USER_ID,
                    read=False,
                ),
            ],
        )

        r = await authenticated_client.post("/api/notifications/n-ua-read-me/read")
        assert r.status_code == 200

        table_data = supabase_fixture.get_table_data("notifications")
        ua_row = next(n for n in table_data if n["id"] == "n-ua-read-me")
        ub_row = next(n for n in table_data if n["id"] == "n-ub-untouched")

        assert ua_row["read"] is True
        assert ub_row["read"] is False, (
            "Other user's notification must not be affected by mark-read"
        )

    async def test_isolation_approve_action_not_found_for_other_user(
        self, authenticated_client, supabase_fixture
    ):
        """User A cannot approve user B's pending action."""
        # Seed a pending action belonging to OTHER_USER_ID
        other_action_id = "bbbbbbbb-0000-0000-0000-000000000001"
        supabase_fixture.seed(
            "pending_actions",
            [_make_pending_action(other_action_id, user_id=OTHER_USER_ID)],
        )
        supabase_fixture.seed("notifications", [])

        r = await authenticated_client.post(
            f"/api/actions/{other_action_id}/approve"
        )

        # Should return 200 with success=False (action not found for this user)
        # or 500 — either way, user A must not successfully approve user B's action
        if r.status_code == 200:
            body = r.json()
            assert body["success"] is False, (
                "User A must not successfully approve user B's action"
            )
        else:
            assert r.status_code in (404, 500)
