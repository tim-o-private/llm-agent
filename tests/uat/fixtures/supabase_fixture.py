"""
Stateful in-memory Supabase client mock for UAT flow tests.

Replaces the dumb MagicMock chain pattern with a programmable mock that
tracks state across a test. Inserts/updates modify in-memory data, and
subsequent selects reflect those changes — just like a real database.

Usage:
    fixture = SupabaseFixture()
    fixture.seed("notifications", [
        {"id": "n1", "user_id": "u1", "title": "Hello", "read": False},
    ])

    # Service code calls fixture.table("notifications").select("*").eq(...).execute()
    # and gets back realistic results from the seeded data.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class QueryResult:
    """Mirrors the Supabase execute() result shape."""

    data: list[dict[str, Any]] | dict[str, Any] | None = None
    count: int | None = None


@dataclass
class CallRecord:
    """Records a single operation for assertion."""

    table: str
    operation: str  # select, insert, update, upsert, delete
    filters: list[tuple[str, str, Any]]
    payload: dict[str, Any] | list[dict[str, Any]] | None = None


class SupabaseFixture:
    """
    In-memory Supabase client mock that supports the PostgREST chainable API.

    Supports: table().select().insert().update().upsert().delete()
              .eq().neq().lt().gt().lte().gte()
              .order().range().limit().single()
              .execute()
    """

    def __init__(self):
        self._tables: dict[str, list[dict[str, Any]]] = {}
        self._call_log: list[CallRecord] = []

    # ── Seeding ──────────────────────────────────────────────────────

    def seed(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Pre-populate a table with rows. Overwrites existing data for that table."""
        self._tables[table] = [copy.deepcopy(r) for r in rows]

    def seed_append(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Append rows to an existing table (or create if missing)."""
        if table not in self._tables:
            self._tables[table] = []
        self._tables[table].extend(copy.deepcopy(r) for r in rows)

    def get_table_data(self, table: str) -> list[dict[str, Any]]:
        """Direct access to table contents for assertions."""
        return copy.deepcopy(self._tables.get(table, []))

    # ── Query Builder Entry Point ────────────────────────────────────

    def table(self, name: str) -> _QueryBuilder:
        """Start a chainable query on a table. Mirrors supabase.table()."""
        return _QueryBuilder(self, name)

    # ── Call Log Assertions ──────────────────────────────────────────

    @property
    def calls(self) -> list[CallRecord]:
        return list(self._call_log)

    def assert_table_called(
        self,
        table: str,
        operation: str | None = None,
        times: int | None = None,
    ) -> list[CallRecord]:
        """Assert that a table was accessed, optionally filtering by operation."""
        matching = [c for c in self._call_log if c.table == table]
        if operation:
            matching = [c for c in matching if c.operation == operation]

        if not matching:
            ops = f" with operation={operation}" if operation else ""
            raise AssertionError(
                f"Expected call to table '{table}'{ops}, but none found. "
                f"Calls: {[(c.table, c.operation) for c in self._call_log]}"
            )

        if times is not None and len(matching) != times:
            raise AssertionError(
                f"Expected {times} call(s) to table '{table}' "
                f"(operation={operation}), got {len(matching)}"
            )

        return matching

    def assert_no_calls(self) -> None:
        if self._call_log:
            raise AssertionError(
                f"Expected no calls, got {len(self._call_log)}: "
                f"{[(c.table, c.operation) for c in self._call_log]}"
            )

    def reset_call_log(self) -> None:
        self._call_log.clear()

    # ── Internal: execute queries against in-memory data ─────────────

    def _execute_query(self, builder: _QueryBuilder) -> QueryResult:
        """Run the accumulated query against in-memory tables."""
        table_data = self._tables.get(builder._table_name, [])
        rows = [copy.deepcopy(r) for r in table_data]

        # Record the call
        self._call_log.append(CallRecord(
            table=builder._table_name,
            operation=builder._operation,
            filters=list(builder._filters),
            payload=copy.deepcopy(builder._payload),
        ))

        if builder._operation == "insert":
            return self._do_insert(builder)
        elif builder._operation == "update":
            return self._do_update(builder, rows)
        elif builder._operation == "upsert":
            return self._do_upsert(builder)
        elif builder._operation == "delete":
            return self._do_delete(builder, rows)
        else:
            return self._do_select(builder, rows)

    def _apply_filters(
        self, rows: list[dict], filters: list[tuple[str, str, Any]]
    ) -> list[dict]:
        """Apply accumulated filter predicates."""
        result = rows
        for col, op, val in filters:
            if op == "eq":
                result = [r for r in result if r.get(col) == val]
            elif op == "neq":
                result = [r for r in result if r.get(col) != val]
            elif op == "lt":
                result = [r for r in result if r.get(col) is not None and r.get(col) < val]
            elif op == "gt":
                result = [r for r in result if r.get(col) is not None and r.get(col) > val]
            elif op == "lte":
                result = [r for r in result if r.get(col) is not None and r.get(col) <= val]
            elif op == "gte":
                result = [r for r in result if r.get(col) is not None and r.get(col) >= val]
        return result

    def _do_select(self, builder: _QueryBuilder, rows: list[dict]) -> QueryResult:
        filtered = self._apply_filters(rows, builder._filters)

        # Ordering
        if builder._order_col:
            filtered.sort(
                key=lambda r: r.get(builder._order_col, ""),
                reverse=builder._order_desc,
            )

        total = len(filtered)

        # Range
        if builder._range_start is not None:
            end = builder._range_end + 1 if builder._range_end is not None else None
            filtered = filtered[builder._range_start:end]

        # Limit
        if builder._limit is not None:
            filtered = filtered[: builder._limit]

        # Column projection (skip for "*" or empty)
        if builder._select_columns and builder._select_columns != ["*"]:
            filtered = [
                {k: v for k, v in r.items() if k in builder._select_columns}
                for r in filtered
            ]

        # Single mode
        if builder._single:
            if filtered:
                return QueryResult(data=filtered[0], count=total if builder._count_mode else None)
            return QueryResult(data=None, count=0 if builder._count_mode else None)

        return QueryResult(
            data=filtered,
            count=total if builder._count_mode else None,
        )

    def _do_insert(self, builder: _QueryBuilder) -> QueryResult:
        table_name = builder._table_name
        if table_name not in self._tables:
            self._tables[table_name] = []

        payload = builder._payload
        if isinstance(payload, dict):
            payload = [payload]

        inserted = []
        for row in payload:
            row = copy.deepcopy(row)
            if "id" not in row:
                row["id"] = str(uuid.uuid4())
            if "created_at" not in row:
                row["created_at"] = datetime.now(timezone.utc).isoformat()
            self._tables[table_name].append(row)
            inserted.append(row)

        return QueryResult(data=inserted)

    def _do_update(self, builder: _QueryBuilder, rows: list[dict]) -> QueryResult:
        table_name = builder._table_name
        table_data = self._tables.get(table_name, [])
        filtered_indices = []

        for i, row in enumerate(table_data):
            match = True
            for col, op, val in builder._filters:
                if op == "eq" and row.get(col) != val:
                    match = False
                    break
            if match:
                filtered_indices.append(i)

        updated = []
        for i in filtered_indices:
            self._tables[table_name][i].update(builder._payload)
            if "updated_at" not in builder._payload:
                self._tables[table_name][i]["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated.append(copy.deepcopy(self._tables[table_name][i]))

        return QueryResult(data=updated)

    def _do_upsert(self, builder: _QueryBuilder) -> QueryResult:
        table_name = builder._table_name
        if table_name not in self._tables:
            self._tables[table_name] = []

        payload = builder._payload
        if isinstance(payload, dict):
            payload = [payload]

        results = []
        for row in payload:
            row = copy.deepcopy(row)
            # Try to find existing row by id (or first unique-ish key)
            existing_idx = None
            if "id" in row:
                for i, existing in enumerate(self._tables[table_name]):
                    if existing.get("id") == row["id"]:
                        existing_idx = i
                        break

            if existing_idx is not None:
                self._tables[table_name][existing_idx].update(row)
                results.append(copy.deepcopy(self._tables[table_name][existing_idx]))
            else:
                if "id" not in row:
                    row["id"] = str(uuid.uuid4())
                if "created_at" not in row:
                    row["created_at"] = datetime.now(timezone.utc).isoformat()
                self._tables[table_name].append(row)
                results.append(row)

        return QueryResult(data=results)

    def _do_delete(self, builder: _QueryBuilder, rows: list[dict]) -> QueryResult:
        table_name = builder._table_name
        table_data = self._tables.get(table_name, [])
        keep = []
        deleted = []

        for row in table_data:
            match = True
            for col, op, val in builder._filters:
                if op == "eq" and row.get(col) != val:
                    match = False
                    break
            if match:
                deleted.append(copy.deepcopy(row))
            else:
                keep.append(row)

        self._tables[table_name] = keep
        return QueryResult(data=deleted)


class _QueryBuilder:
    """
    Chainable query builder that mirrors the Supabase PostgREST client API.

    All methods return self for chaining. execute() is async (to match the
    real client) and runs the query against the fixture's in-memory data.
    """

    def __init__(self, fixture: SupabaseFixture, table_name: str):
        self._fixture = fixture
        self._table_name = table_name
        self._operation = "select"
        self._select_columns: list[str] = ["*"]
        self._count_mode: bool = False
        self._filters: list[tuple[str, str, Any]] = []
        self._payload: dict[str, Any] | list[dict[str, Any]] | None = None
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._range_start: int | None = None
        self._range_end: int | None = None
        self._limit: int | None = None
        self._single: bool = False

    # ── Operation setters ────────────────────────────────────────────

    def select(self, *columns: str, count: str | None = None) -> _QueryBuilder:
        self._operation = "select"
        self._select_columns = list(columns) if columns else ["*"]
        if count == "exact":
            self._count_mode = True
        return self

    def insert(self, data: dict | list[dict]) -> _QueryBuilder:
        self._operation = "insert"
        self._payload = data
        return self

    def update(self, data: dict) -> _QueryBuilder:
        self._operation = "update"
        self._payload = data
        return self

    def upsert(self, data: dict | list[dict]) -> _QueryBuilder:
        self._operation = "upsert"
        self._payload = data
        return self

    def delete(self) -> _QueryBuilder:
        self._operation = "delete"
        return self

    # ── Filter methods ───────────────────────────────────────────────

    def eq(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "eq", value))
        return self

    def neq(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "neq", value))
        return self

    def lt(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "lt", value))
        return self

    def gt(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "gt", value))
        return self

    def lte(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "lte", value))
        return self

    def gte(self, column: str, value: Any) -> _QueryBuilder:
        self._filters.append((column, "gte", value))
        return self

    # ── Modifiers ────────────────────────────────────────────────────

    def order(self, column: str, desc: bool = False) -> _QueryBuilder:
        self._order_col = column
        self._order_desc = desc
        return self

    def range(self, start: int, end: int) -> _QueryBuilder:
        self._range_start = start
        self._range_end = end
        return self

    def limit(self, count: int) -> _QueryBuilder:
        self._limit = count
        return self

    def single(self) -> _QueryBuilder:
        self._single = True
        return self

    # ── Execute ──────────────────────────────────────────────────────

    async def execute(self) -> QueryResult:
        """Run the query against in-memory data. Async to match real client."""
        return self._fixture._execute_query(self)
