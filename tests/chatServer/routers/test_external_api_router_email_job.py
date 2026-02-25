"""Tests for email job creation in external_api_router (SPEC-023 FU-2)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.external_api_router import router


def _make_db_conn(returning_row: tuple, columns: list):
    """Build an AsyncMock psycopg connection that returns given row."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=returning_row)
    mock_cursor.description = [(col,) for col in columns]
    mock_cursor.execute = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)

    mock_conn = MagicMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)

    return mock_conn, mock_cursor


GMAIL_COLUMNS = [
    "id", "user_id", "service_name", "service_user_id", "service_user_email",
    "access_token", "refresh_token", "token_expires_at", "scopes",
    "is_active", "created_at", "updated_at",
]

GMAIL_ROW = (
    "conn-uuid-1",    # id
    "user-uuid-1",    # user_id
    "gmail",          # service_name
    None,             # service_user_id
    "user@gmail.com", # service_user_email
    "access-tok",     # access_token
    None,             # refresh_token
    None,             # token_expires_at
    ["gmail.readonly"],  # scopes
    True,             # is_active
    "2026-01-01T00:00:00Z",  # created_at
    "2026-01-01T00:00:00Z",  # updated_at
)


@pytest.fixture
def gmail_client():
    """TestClient for external_api_router with mocked Gmail DB connection."""
    mock_conn, mock_cursor = _make_db_conn(GMAIL_ROW, GMAIL_COLUMNS)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: "user-uuid-1"

    from chatServer.database.connection import get_db_connection
    app.dependency_overrides[get_db_connection] = lambda: mock_conn

    client = TestClient(app)
    client._mock_cursor = mock_cursor
    return client


def test_create_gmail_connection_creates_pending_job(gmail_client):
    """POST /api/external/connections for gmail inserts a pending email_processing_jobs row."""
    payload = {
        "service_name": "gmail",
        "service_user_email": "user@gmail.com",
        "access_token": "access-tok",
        "refresh_token": None,
        "token_expires_at": None,
        "scopes": ["gmail.readonly"],
    }

    response = gmail_client.post("/api/external/connections", json=payload)

    assert response.status_code == 200

    # Find the INSERT into email_processing_jobs call
    cursor = gmail_client._mock_cursor
    all_calls = cursor.execute.call_args_list
    insert_calls = [
        call for call in all_calls
        if "email_processing_jobs" in str(call)
    ]
    assert insert_calls, "Should have executed INSERT into email_processing_jobs"

    # Verify the INSERT uses 'pending' status
    insert_sql = str(insert_calls[0])
    assert "pending" in insert_sql


def test_create_non_gmail_connection_no_job():
    """POST /api/external/connections for non-Gmail services does NOT create a job."""
    non_gmail_row = (
        "conn-uuid-2", "user-uuid-1", "slack", None, "user@slack.com",
        "tok", None, None, [], True,
        "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
    )
    non_gmail_cols = GMAIL_COLUMNS[:]
    mock_conn, mock_cursor = _make_db_conn(non_gmail_row, non_gmail_cols)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: "user-uuid-1"

    from chatServer.database.connection import get_db_connection
    app.dependency_overrides[get_db_connection] = lambda: mock_conn

    client = TestClient(app)

    payload = {
        "service_name": "slack",
        "service_user_email": "user@slack.com",
        "access_token": "tok",
        "refresh_token": None,
        "token_expires_at": None,
        "scopes": [],
    }

    response = client.post("/api/external/connections", json=payload)

    assert response.status_code == 200

    all_calls = mock_cursor.execute.call_args_list
    insert_job_calls = [
        call for call in all_calls
        if "email_processing_jobs" in str(call)
    ]
    assert not insert_job_calls, "Should NOT insert into email_processing_jobs for non-Gmail"
