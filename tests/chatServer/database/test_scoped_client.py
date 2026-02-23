"""Tests for UserScopedClient, SystemClient, and ScopedTableQuery."""

from unittest.mock import MagicMock

import pytest

from chatServer.database.scoped_client import (
    ScopedTableQuery,
    SystemClient,
    UserScopedClient,
)
from chatServer.database.supabase_client import (
    get_system_client,
    get_user_scoped_client,
)
from chatServer.database.user_scoped_tables import USER_SCOPED_TABLES

USER_ID = "user-abc-123"
OTHER_USER_ID = "user-other-456"


def _mock_query():
    """Create a mock query builder that chains properly."""
    query = MagicMock()
    query.eq.return_value = query
    query.select.return_value = query
    query.insert.return_value = query
    query.update.return_value = query
    query.delete.return_value = query
    query.upsert.return_value = query
    return query


def _mock_client(query=None):
    """Create a mock AsyncClient whose .table() returns the given query.

    Uses MagicMock because Supabase's .table() and .rpc() are synchronous.
    """
    client = MagicMock()
    if query is None:
        query = _mock_query()
    client.table.return_value = query
    return client, query


# ---------------------------------------------------------------------------
# AC-01: UserScopedClient auto-filters on user-scoped tables
# ---------------------------------------------------------------------------


class TestUserScopedClientSelect:
    def test_select_auto_injects_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").select("*")

        client.table.assert_called_once_with("tasks")
        query.select.assert_called_once_with("*")
        query.select.return_value.eq.assert_called_once_with("user_id", USER_ID)

    def test_select_on_all_user_scoped_tables(self):
        for table in USER_SCOPED_TABLES:
            client, query = _mock_client()
            scoped = UserScopedClient(client, USER_ID)
            result = scoped.table(table)
            assert isinstance(result, ScopedTableQuery), f"{table} should return ScopedTableQuery"


class TestUserScopedClientInsert:
    def test_insert_dict_sets_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = {"name": "test task"}

        scoped.table("tasks").insert(data)

        assert data["user_id"] == USER_ID
        query.insert.assert_called_once_with(data)

    def test_insert_dict_overwrites_wrong_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = {"name": "test", "user_id": OTHER_USER_ID}

        scoped.table("tasks").insert(data)

        assert data["user_id"] == USER_ID

    def test_insert_list_sets_user_id_on_each(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = [{"name": "a"}, {"name": "b", "user_id": OTHER_USER_ID}]

        scoped.table("tasks").insert(data)

        assert all(row["user_id"] == USER_ID for row in data)
        query.insert.assert_called_once_with(data)


class TestUserScopedClientUpdate:
    def test_update_auto_injects_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").update({"name": "updated"})

        query.update.assert_called_once_with({"name": "updated"})
        query.update.return_value.eq.assert_called_once_with("user_id", USER_ID)


class TestUserScopedClientDelete:
    def test_delete_auto_injects_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").delete()

        query.delete.assert_called_once()
        query.delete.return_value.eq.assert_called_once_with("user_id", USER_ID)


class TestUserScopedClientUpsert:
    def test_upsert_dict_sets_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = {"name": "upserted"}

        scoped.table("tasks").upsert(data)

        assert data["user_id"] == USER_ID
        query.upsert.assert_called_once_with(data)

    def test_upsert_overwrites_wrong_user_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = {"name": "x", "user_id": OTHER_USER_ID}

        scoped.table("tasks").upsert(data)

        assert data["user_id"] == USER_ID

    def test_upsert_list_sets_user_id_on_each(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)
        data = [{"a": 1}, {"b": 2}]

        scoped.table("tasks").upsert(data)

        assert all(row["user_id"] == USER_ID for row in data)


# ---------------------------------------------------------------------------
# AC-01 edge case: duplicate user_id filter detection
# ---------------------------------------------------------------------------


class TestDuplicateUserIdFilter:
    def test_eq_user_id_prevents_double_append_on_select(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").eq("user_id", USER_ID).select("*")

        # .eq("user_id", ...) was called once (by the explicit call).
        # .select() should NOT call .eq("user_id", ...) again.
        # The chain: query.eq("user_id", USER_ID) -> chained_query
        # Then chained_query.select("*") should NOT call .eq again
        query.eq.assert_called_once_with("user_id", USER_ID)

    def test_eq_wrong_user_id_substitutes_scoped_id(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").eq("user_id", OTHER_USER_ID)

        # Should use scoped user_id, not the caller's
        query.eq.assert_called_once_with("user_id", USER_ID)

    def test_eq_non_user_id_column_passes_through(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        scoped.table("tasks").eq("status", "done")

        query.eq.assert_called_once_with("status", "done")


# ---------------------------------------------------------------------------
# AC-01/AC-02: System tables are NOT filtered
# ---------------------------------------------------------------------------


class TestSystemTablePassthrough:
    def test_user_scoped_client_system_table_no_filter(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        result = scoped.table("agent_configurations")

        # Should return raw query, not ScopedTableQuery
        assert result is query
        assert not isinstance(result, ScopedTableQuery)

    def test_user_scoped_client_tools_table_no_filter(self):
        client, query = _mock_client()
        scoped = UserScopedClient(client, USER_ID)

        result = scoped.table("tools")
        assert result is query


# ---------------------------------------------------------------------------
# AC-02: SystemClient never filters
# ---------------------------------------------------------------------------


class TestSystemClient:
    def test_system_client_no_filter_on_user_table(self):
        client, query = _mock_client()
        sys_client = SystemClient(client)

        result = sys_client.table("tasks")

        # Returns raw query with no wrapping
        assert result is query

    def test_system_client_rpc_delegates(self):
        client = MagicMock()
        sys_client = SystemClient(client)

        sys_client.rpc("my_function", params={"x": 1})

        client.rpc.assert_called_once_with("my_function", params={"x": 1})


# ---------------------------------------------------------------------------
# RPC delegation
# ---------------------------------------------------------------------------


class TestRpcDelegation:
    def test_user_scoped_client_rpc_delegates(self):
        client = MagicMock()
        scoped = UserScopedClient(client, USER_ID)

        scoped.rpc("some_function", params={"a": "b"})

        client.rpc.assert_called_once_with("some_function", params={"a": "b"})


# ---------------------------------------------------------------------------
# AC-03: FastAPI dependency injection
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    @pytest.mark.asyncio
    async def test_get_user_scoped_client_returns_correct_type(self):
        client = MagicMock()
        result = await get_user_scoped_client(user_id=USER_ID, client=client)

        assert isinstance(result, UserScopedClient)
        assert result.user_id == USER_ID
        assert result.client is client

    @pytest.mark.asyncio
    async def test_get_system_client_returns_correct_type(self):
        client = MagicMock()
        result = await get_system_client(client=client)

        assert isinstance(result, SystemClient)
        assert result.client is client


# ---------------------------------------------------------------------------
# AC-05: USER_SCOPED_TABLES completeness
# ---------------------------------------------------------------------------


class TestUserScopedTables:
    def test_expected_tables_present(self):
        expected = {
            "tasks", "notes", "focus_sessions", "reminders", "agent_logs",
            "agent_long_term_memory", "agent_sessions", "agent_schedules",
            "audit_logs", "channel_linking_tokens", "email_digests",
            "external_api_connections", "notifications", "pending_actions",
            "user_agent_prompt_customizations", "user_channels",
            "user_tool_preferences", "chat_sessions", "agent_execution_results",
        }
        assert USER_SCOPED_TABLES == expected

    def test_system_tables_not_in_set(self):
        system_tables = [
            "agent_configurations", "tools", "chat_message_history",
            "user_context", "models",
        ]
        for table in system_tables:
            assert table not in USER_SCOPED_TABLES, f"{table} should not be in USER_SCOPED_TABLES"
