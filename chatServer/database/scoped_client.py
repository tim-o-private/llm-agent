"""User-scoped and system database client wrappers.

UserScopedClient auto-injects user_id filtering on all queries to
user-owned tables. SystemClient is a thin passthrough for background
services that need unscoped access.
"""

from __future__ import annotations

from supabase import AsyncClient

from .user_scoped_tables import USER_SCOPED_TABLES


class UserScopedClient:
    """Wraps Supabase AsyncClient to auto-inject user_id filtering.

    Every query to a user-scoped table automatically includes
    .eq("user_id", self.user_id). Queries to system tables
    (agent_configurations, tools, etc.) pass through unmodified.
    """

    def __init__(self, client: AsyncClient, user_id: str):
        self.client = client
        self.user_id = user_id

    def table(self, table_name: str):
        query = self.client.table(table_name)
        if table_name in USER_SCOPED_TABLES:
            return ScopedTableQuery(query, self.user_id)
        return query

    def rpc(self, *args, **kwargs):
        return self.client.rpc(*args, **kwargs)


class ScopedTableQuery:
    """Wraps a Supabase table query builder to auto-inject user_id.

    Intercepts select/insert/update/delete/upsert to ensure user_id
    filtering is present. Detects duplicate user_id filters and
    overwrites caller-supplied user_id values to prevent spoofing.

    Methods not explicitly proxied (order, limit, neq, in_, ilike, etc.)
    are delegated to the underlying query builder via __getattr__.
    """

    def __init__(self, query, user_id: str):
        self._query = query
        self._user_id = user_id
        self._user_id_already_set = False

    def __getattr__(self, name):
        """Delegate unhandled methods to the underlying query builder."""
        return getattr(self._query, name)

    def eq(self, column: str, value):
        if column == "user_id":
            self._user_id_already_set = True
            return self._chain(self._query.eq(column, self._user_id))
        return self._chain(self._query.eq(column, value))

    def select(self, *args, **kwargs):
        result = self._query.select(*args, **kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def insert(self, data, **kwargs):
        if isinstance(data, dict):
            data["user_id"] = self._user_id
        elif isinstance(data, list):
            for row in data:
                row["user_id"] = self._user_id
        return self._query.insert(data, **kwargs)

    def update(self, data, **kwargs):
        result = self._query.update(data, **kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def delete(self, **kwargs):
        result = self._query.delete(**kwargs)
        if not self._user_id_already_set:
            result = result.eq("user_id", self._user_id)
        return result

    def upsert(self, data, **kwargs):
        if isinstance(data, dict):
            data["user_id"] = self._user_id
        elif isinstance(data, list):
            for row in data:
                row["user_id"] = self._user_id
        return self._query.upsert(data, **kwargs)

    def _chain(self, new_query):
        chained = ScopedTableQuery(new_query, self._user_id)
        chained._user_id_already_set = self._user_id_already_set
        return chained


class SystemClient:
    """Thin wrapper marking unscoped access as intentional.

    Provides the same interface as the raw Supabase client.
    Exists to make system access explicit in type signatures.
    """

    def __init__(self, client: AsyncClient):
        self.client = client

    def table(self, table_name: str):
        return self.client.table(table_name)

    def rpc(self, *args, **kwargs):
        return self.client.rpc(*args, **kwargs)
