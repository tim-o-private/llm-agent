"""Tests for ToolExecutionService (SPEC-025 FU-5: post-approval tool execution)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.tool_execution import (
    _MEMORY_TOOL_TYPES,
    ToolExecutionError,
    ToolExecutionService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_client():
    """Mock Supabase DB client with method chaining."""
    client = MagicMock()
    return client


@pytest.fixture
def service(db_client):
    return ToolExecutionService(db_client)


def _mock_tool_class(return_value="tool-result"):
    """Create a fake BaseTool class whose _arun returns a given value."""
    instance = MagicMock()
    instance._arun = AsyncMock(return_value=return_value)

    cls = MagicMock(return_value=instance)
    cls.__name__ = "FakeToolClass"
    return cls, instance


def _setup_db_lookup(db_client, tool_type="CreateTasksTool", config=None):
    """Set up the mock chain for tools table lookup."""
    data = {"type": tool_type, "config": config or {}}
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    db_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute = mock_execute
    return mock_execute


def _mock_settings():
    """Return a mock settings object with Supabase credentials."""
    s = MagicMock()
    s.supabase_url = "https://test.supabase.co"
    s.supabase_service_key = "test-service-key"
    return s


# ---------------------------------------------------------------------------
# Happy path: resolve and run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_resolves_and_runs(service, db_client):
    """AC-21: DB returns tool type, TOOL_REGISTRY maps to class, _arun() called, result returned."""
    _setup_db_lookup(db_client, tool_type="CreateTasksTool")
    fake_class, fake_instance = _mock_tool_class("task created")

    registry = {"CreateTasksTool": fake_class}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        result = await service.execute_tool(
            tool_name="create_tasks",
            tool_args={"title": "Do stuff"},
            user_id="user-1",
            agent_name="clarity",
        )

    assert result == "task created"
    fake_class.assert_called_once()
    fake_instance._arun.assert_awaited_once_with(title="Do stuff")


# ---------------------------------------------------------------------------
# No approval wrapper: tool instantiated directly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_no_wrapper(service, db_client):
    """AC-21: tool is instantiated without approval wrapper -- just the raw class."""
    _setup_db_lookup(db_client, tool_type="CreateTasksTool")
    fake_class, _ = _mock_tool_class("ok")

    registry = {"CreateTasksTool": fake_class}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        await service.execute_tool(
            tool_name="create_tasks",
            tool_args={},
            user_id="user-1",
        )

    # The constructor was called with the raw class, not a wrapped version.
    kwargs = fake_class.call_args[1]
    assert kwargs["user_id"] == "user-1"
    assert kwargs["supabase_url"] == "https://test.supabase.co"
    assert kwargs["supabase_key"] == "test-service-key"
    assert kwargs["name"] == "create_tasks"


# ---------------------------------------------------------------------------
# Memory tool rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_rejects_memory_tool(service, db_client):
    """AC-21: memory tool types raise ToolExecutionError."""
    for mem_type in list(_MEMORY_TOOL_TYPES)[:2]:
        _setup_db_lookup(db_client, tool_type=mem_type)

        with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
             patch("src.core.agent_loader_db.TOOL_REGISTRY", {mem_type: MagicMock()}):
            with pytest.raises(ToolExecutionError, match="memory tool"):
                await service.execute_tool(
                    tool_name="some_memory_tool",
                    tool_args={},
                    user_id="user-1",
                )


# ---------------------------------------------------------------------------
# Gmail dynamic import
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_gmail_dynamic_import(service, db_client):
    """AC-22: GmailTool type resolves via config.tool_class dynamic import."""
    _setup_db_lookup(
        db_client,
        tool_type="GmailTool",
        config={"tool_class": "SearchGmailTool"},
    )

    fake_class, fake_instance = _mock_tool_class("gmail result")

    mock_module = MagicMock()
    mock_module.SearchGmailTool = fake_class

    registry = {"GmailTool": None}  # GmailTool maps to None in TOOL_REGISTRY

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry), \
         patch("chatServer.services.tool_execution.importlib.import_module", return_value=mock_module) as mock_import:
        result = await service.execute_tool(
            tool_name="search_gmail",
            tool_args={"query": "test"},
            user_id="user-1",
            agent_name="clarity",
        )

    assert result == "gmail result"
    mock_import.assert_called_once_with("chatServer.tools.gmail_tools")
    fake_instance._arun.assert_awaited_once_with(query="test")


# ---------------------------------------------------------------------------
# Gmail missing tool_class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_gmail_missing_tool_class(service, db_client):
    """AC-22: GmailTool with no tool_class in config raises ToolExecutionError."""
    _setup_db_lookup(db_client, tool_type="GmailTool", config={})

    registry = {"GmailTool": None}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        with pytest.raises(ToolExecutionError, match="no tool_class in config"):
            await service.execute_tool(
                tool_name="send_email",
                tool_args={},
                user_id="user-1",
            )


# ---------------------------------------------------------------------------
# Unknown tool name (not in DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_unknown_name(service, db_client):
    """AC-22: tool name not in DB raises ToolExecutionError."""
    mock_execute = AsyncMock(return_value=MagicMock(data=None))
    db_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute = mock_execute

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", {}):
        with pytest.raises(ToolExecutionError, match="not found in tools table"):
            await service.execute_tool(
                tool_name="nonexistent_tool",
                tool_args={},
                user_id="user-1",
            )


# ---------------------------------------------------------------------------
# Unregistered tool type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_unregistered_type(service, db_client):
    """AC-22: tool type not in TOOL_REGISTRY raises ToolExecutionError."""
    _setup_db_lookup(db_client, tool_type="UnknownToolType")

    registry = {}  # Empty registry

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        with pytest.raises(ToolExecutionError, match="not in TOOL_REGISTRY"):
            await service.execute_tool(
                tool_name="mystery_tool",
                tool_args={},
                user_id="user-1",
            )


# ---------------------------------------------------------------------------
# _arun() failure wrapped in ToolExecutionError with chaining
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_arun_failure(service, db_client):
    """AC-21: _arun() exception wrapped in ToolExecutionError with original chained."""
    _setup_db_lookup(db_client, tool_type="CreateTasksTool")

    original_error = RuntimeError("DB connection lost")
    fake_class, fake_instance = _mock_tool_class()
    fake_instance._arun = AsyncMock(side_effect=original_error)

    registry = {"CreateTasksTool": fake_class}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        with pytest.raises(ToolExecutionError, match="execution failed") as exc_info:
            await service.execute_tool(
                tool_name="create_tasks",
                tool_args={"title": "fail"},
                user_id="user-1",
            )

    assert exc_info.value.__cause__ is original_error


# ---------------------------------------------------------------------------
# Tool config from DB merged into constructor kwargs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_passes_config(service, db_client):
    """AC-23: tools.config JSONB merged into constructor kwargs."""
    tool_config = {"table_name": "custom_items", "method": "get"}
    _setup_db_lookup(db_client, tool_type="CRUDTool", config=tool_config)

    fake_class, _ = _mock_tool_class("crud result")
    registry = {"CRUDTool": fake_class}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        await service.execute_tool(
            tool_name="get_custom_items",
            tool_args={"id": "123"},
            user_id="user-1",
        )

    kwargs = fake_class.call_args[1]
    assert kwargs["table_name"] == "custom_items"
    assert kwargs["method"] == "get"
    assert kwargs["user_id"] == "user-1"


# ---------------------------------------------------------------------------
# agent_name passed through to constructor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_passes_agent_name(service, db_client):
    """AC-24: agent_name passed to constructor kwargs."""
    _setup_db_lookup(db_client, tool_type="CreateTasksTool")
    fake_class, _ = _mock_tool_class("ok")

    registry = {"CreateTasksTool": fake_class}

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()), \
         patch("src.core.agent_loader_db.TOOL_REGISTRY", registry):
        await service.execute_tool(
            tool_name="create_tasks",
            tool_args={},
            user_id="user-1",
            agent_name="my-agent",
        )

    kwargs = fake_class.call_args[1]
    assert kwargs["agent_name"] == "my-agent"


# ---------------------------------------------------------------------------
# _build_pending_actions_service provides tool_executor
# ---------------------------------------------------------------------------


def test_build_service_provides_executor():
    """AC-24: _build_pending_actions_service() creates PendingActionsService with tool_executor."""
    from chatServer.routers.actions import _build_pending_actions_service

    mock_db = MagicMock()

    with patch("chatServer.config.settings.get_settings", return_value=_mock_settings()):
        svc = _build_pending_actions_service(mock_db)

    assert svc.tool_executor is not None
    assert callable(svc.tool_executor)


# ---------------------------------------------------------------------------
# approve_action passes agent_name from action.context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_passes_agent_name(db_client):
    """AC-24: approve_action() passes agent_name from action.context to tool_executor."""
    from chatServer.services.pending_actions import PendingActionsService

    mock_executor = AsyncMock(return_value="executed ok")

    svc = PendingActionsService(
        db_client=db_client,
        tool_executor=mock_executor,
    )

    # Mock get_action to return a pending action with agent_name in context
    from datetime import datetime, timedelta
    from uuid import UUID

    from chatServer.services.pending_actions import PendingAction

    action = PendingAction(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        tool_name="send_email",
        tool_args={"to": "test@example.com", "body": "Hello"},
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24),
        context={"session_id": "sess-1", "agent_name": "clarity"},
    )

    with patch.object(svc, "get_action", new_callable=AsyncMock, return_value=action), \
         patch.object(svc, "_update_status", new_callable=AsyncMock):
        # Mock the DB update after execution
        db_client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock()

        result = await svc.approve_action("00000000-0000-0000-0000-000000000001", "user-1")

    mock_executor.assert_awaited_once()
    call_kwargs = mock_executor.call_args[1]
    assert call_kwargs["agent_name"] == "clarity"
    assert call_kwargs["tool_name"] == "send_email"
    assert call_kwargs["user_id"] == "user-1"
    assert result.success is True
