"""
UAT test fixtures — shared across all flow tests.

These fixtures wire the real FastAPI app with mocked boundaries:
- Auth: overridden to inject a test user (no JWT/OAuth needed)
- Supabase: replaced with stateful in-memory SupabaseFixture
- psycopg: replaced with AsyncMock (for PostgresChatMessageHistory)
- Agent executor: replaced with FakeAgentExecutor (no LLM calls)
- Lifespan: mocked so no real DB/Telegram/cache initialization

The result: real routing, real Pydantic validation, real service logic,
real error handling — only the edges are mocked.
"""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tests.uat.fixtures.supabase_fixture import SupabaseFixture

TEST_USER_ID = "uat-test-user-00000000-0000-0000-0000-000000000001"
MOCK_JWT_PAYLOAD = {"sub": TEST_USER_ID, "aud": "authenticated"}


# ─── Core Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def supabase_fixture():
    """Stateful in-memory Supabase mock. Seed data, run flows, assert calls."""
    return SupabaseFixture()


@pytest.fixture
def mock_psycopg_conn():
    """Mock psycopg.AsyncConnection for services that use raw SQL."""
    conn = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.description = []
    conn.cursor.return_value.__aenter__ = AsyncMock(return_value=cursor)
    conn.cursor.return_value.__aexit__ = AsyncMock(return_value=False)
    return conn


# ─── App Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def authenticated_client(supabase_fixture, mock_psycopg_conn):
    """
    Real FastAPI app with auth overridden to inject TEST_USER_ID.

    Dependencies replaced:
    - get_current_user → returns TEST_USER_ID (no JWT verification)
    - get_supabase_client → returns supabase_fixture
    - get_db_connection → yields mock_psycopg_conn

    Lifespan mocked to skip real DB/Telegram/cache initialization.
    """
    # Patch lifespan dependencies before importing app
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

    # Disable Telegram init
    from chatServer.config.settings import get_settings

    settings = get_settings()
    orig_telegram_token = settings.telegram_bot_token
    settings.telegram_bot_token = None

    # Patch JWT decode to always return test payload
    jwt_patch = patch("jose.jwt.decode", return_value=MOCK_JWT_PAYLOAD)
    jwt_patch.start()

    # Patch env for JWT secret
    env_patch = patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    env_patch.start()

    from chatServer.database.connection import get_db_connection
    from chatServer.database.supabase_client import get_supabase_client
    from chatServer.dependencies.auth import get_current_user
    from chatServer.main import app

    # Override FastAPI dependencies
    app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
    app.dependency_overrides[get_supabase_client] = lambda: supabase_fixture
    app.dependency_overrides[get_db_connection] = _make_db_conn_generator(mock_psycopg_conn)

    # Clear agent executor cache
    from chatServer import main as chat_main_module

    if hasattr(chat_main_module, "AGENT_EXECUTOR_CACHE"):
        chat_main_module.AGENT_EXECUTOR_CACHE.clear()

    # Reset chat service singleton
    import chatServer.services.chat

    chatServer.services.chat._chat_service = None

    # Start lifespan and create client
    stack = AsyncExitStack()
    await stack.enter_async_context(app.router.lifespan_context(app))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://uat-test",
    ) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    await stack.aclose()
    settings.telegram_bot_token = orig_telegram_token
    jwt_patch.stop()
    env_patch.stop()
    for p in lifespan_patches:
        p.stop()


@pytest.fixture
async def telegram_webhook_client(supabase_fixture, mock_psycopg_conn):
    """
    Real FastAPI app without auth override — for testing Telegram webhook flow.

    The webhook endpoint has no auth dependency; identity is resolved
    inside the handler via user_channels table lookup.
    """
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

    env_patch = patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    env_patch.start()

    from chatServer.database.connection import get_db_connection
    from chatServer.database.supabase_client import get_supabase_client
    from chatServer.main import app

    # Override DB dependencies but NOT auth
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
    env_patch.stop()
    for p in lifespan_patches:
        p.stop()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _mock_supabase_manager(fixture: SupabaseFixture):
    """Create a mock SupabaseManager that returns our fixture as the client."""
    manager = AsyncMock()
    manager.get_client.return_value = fixture
    manager.client = fixture
    return manager


def _mock_background_service():
    """Create a mock BackgroundTaskService."""
    service = MagicMock()
    service.stop_background_tasks = AsyncMock()
    service.start_background_tasks = MagicMock()
    service.set_agent_executor_cache = MagicMock()
    return service


def _make_db_conn_generator(mock_conn):
    """Create an async generator function for get_db_connection override."""

    async def _generator():
        yield mock_conn

    return _generator
