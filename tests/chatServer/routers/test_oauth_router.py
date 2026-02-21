"""Tests for the OAuth router (SPEC-008 FU-2)."""

from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from chatServer.routers.oauth_router import _get_oauth_service, router
from chatServer.services.oauth_service import OAuthResult


@pytest.fixture
def mock_oauth_service():
    service = AsyncMock()
    return service


@pytest.fixture
def client(mock_oauth_service):
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    app.dependency_overrides[_get_oauth_service] = lambda: mock_oauth_service

    # Mock auth dependency to return a fixed user_id
    from chatServer.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "test-user-id"

    return TestClient(app, follow_redirects=False)


def test_initiate_connect_returns_auth_url(client, mock_oauth_service):
    """GET /oauth/gmail/connect should return Google OAuth URL as JSON."""
    mock_oauth_service.create_gmail_auth_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth?client_id=test"
    )

    response = client.get("/oauth/gmail/connect")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "auth_url" in data
    assert "accounts.google.com" in data["auth_url"]
    mock_oauth_service.create_gmail_auth_url.assert_called_once_with("test-user-id")


def test_initiate_connect_requires_auth(mock_oauth_service):
    """GET /oauth/gmail/connect should return 401 without auth."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_oauth_service] = lambda: mock_oauth_service
    # Do NOT override get_current_user — let it require real auth

    # Use TestClient without auth header
    test_client = TestClient(app, follow_redirects=False)
    response = test_client.get("/oauth/gmail/connect")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_callback_validates_state_nonce(client, mock_oauth_service):
    """GET /oauth/gmail/callback should reject invalid state nonce."""
    mock_oauth_service.handle_gmail_callback.return_value = OAuthResult(
        status="error",
        error_message="Invalid or expired OAuth state. Please try again.",
    )

    response = client.get("/oauth/gmail/callback?code=test-code&state=invalid-state")

    assert response.status_code == status.HTTP_302_FOUND
    assert "status=error" in response.headers["location"]
    assert "error_message=" in response.headers["location"]


def test_callback_stores_tokens(client, mock_oauth_service):
    """GET /oauth/gmail/callback should store tokens and redirect with success."""
    mock_oauth_service.handle_gmail_callback.return_value = OAuthResult(
        status="success",
        connection_id="conn-123",
        email="user@gmail.com",
    )

    response = client.get("/oauth/gmail/callback?code=test-code&state=valid-state")

    assert response.status_code == status.HTTP_302_FOUND
    assert "status=success" in response.headers["location"]
    assert "source=standalone" in response.headers["location"]
    mock_oauth_service.handle_gmail_callback.assert_called_once_with("test-code", "valid-state")


def test_callback_rejects_duplicate_account(client, mock_oauth_service):
    """GET /oauth/gmail/callback should reject already-connected accounts."""
    mock_oauth_service.handle_gmail_callback.return_value = OAuthResult(
        status="error",
        error_message="Gmail account user@gmail.com is already connected.",
    )

    response = client.get("/oauth/gmail/callback?code=test-code&state=valid-state")

    assert response.status_code == status.HTTP_302_FOUND
    assert "status=error" in response.headers["location"]
    assert "already+connected" in response.headers["location"] or "already%20connected" in response.headers["location"]
