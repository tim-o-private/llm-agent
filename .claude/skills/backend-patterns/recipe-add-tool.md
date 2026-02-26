# Recipe: Add a New Agent Tool

Prescriptive guide for adding a new tool domain. Follow every step — skipping any step has caused bugs in past specs.

**Reference implementations:** `reminder_tools.py` / `reminder_service.py` (cleanest example)

## Prerequisites

- Database table for the domain exists (or is created in the same spec's DB migration)
- Domain name chosen: `{domain}` (singular, snake_case — e.g., `reminder`, `calendar_event`)

## Step 1: Service — `chatServer/services/{domain}_service.py`

```python
"""
{Domain} Service.

Manages {domain}s: CRUD operations.
Used by {domain} tools (agent-facing).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class {Domain}Service:
    """Service for managing user {domain}s."""

    def __init__(self, db_client):
        self.db = db_client  # UserScopedClient injected by tool

    async def create_{domain}(self, user_id: str, **kwargs) -> dict:
        entry = {"user_id": user_id, **kwargs}
        result = await self.db.table("{domain}s").insert(entry).execute()
        if not result.data:
            raise Exception("Failed to create {domain}")
        logger.info(f"Created {domain} {result.data[0]['id']} for user {user_id}")
        return result.data[0]

    async def list_{domain}s(self, user_id: str, limit: int = 20) -> list[dict]:
        result = (
            await self.db.table("{domain}s")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_{domain}(self, user_id: str, {domain}_id: str) -> dict | None:
        result = (
            await self.db.table("{domain}s")
            .select("*")
            .eq("id", {domain}_id)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete_{domain}s(self, user_id: str, ids: list[str]) -> list[str]:
        """Soft-delete. Returns list of actually-deleted IDs."""
        deleted = []
        for item_id in ids:
            result = (
                await self.db.table("{domain}s")
                .update({"status": "deleted", "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", item_id)
                .eq("user_id", user_id)
                .execute()
            )
            if result.data:
                deleted.append(item_id)
        return deleted
```

**Rules:**
- Service receives `db_client` via `__init__` — already scoped to user. Never call `get_supabase_client()` inside.
- Soft-delete (`status='deleted'`), not hard `DELETE`.
- Always set `updated_at` explicitly on updates.

## Step 2: Tool Classes — `chatServer/tools/{domain}_tools.py`

```python
"""{Domain} tools for agent integration."""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Input Schemas (one per tool) ---

class Get{Domain}Input(BaseModel):
    """Input schema for get_{domain} tool."""
    id: Optional[str] = Field(default=None, description="Specific {domain} ID")
    limit: int = Field(default=10, ge=1, le=50, description="Max results")


class Create{Domain}Input(BaseModel):
    """Input schema for create_{domain} tool."""
    title: str = Field(..., description="{Domain} title", min_length=1, max_length=200)
    # Add domain-specific fields here


class Delete{Domain}Input(BaseModel):
    """Input schema for delete_{domain} tool."""
    ids: list[str] = Field(..., description="List of {domain} IDs to delete")


# --- Tool Classes ---

class Get{Domain}Tool(BaseTool):
    """Retrieve {domain}s for the user."""

    name: str = "get_{domain}"
    description: str = (
        "Get {domain}s. Returns a list of {domain}s with details. "
        "Optionally filter by ID."
    )
    args_schema: Type[BaseModel] = Get{Domain}Input

    # Required instance fields
    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Behavioral guidance for the agent prompt."""
        if channel in ("web", "telegram"):
            return (
                "{Domain}: Use get_{domain} to check the user's {domain}s. "
                "Reference them when relevant to the conversation."
            )
        return None

    def _run(self, **kwargs) -> str:
        return "get_{domain} requires async execution. Use _arun."

    async def _arun(self, id: Optional[str] = None, limit: int = 10) -> str:
        try:
            # Imports inside _arun to avoid circular imports
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.{domain}_service import {Domain}Service

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = {Domain}Service(db)

            if id:
                item = await service.get_{domain}(self.user_id, id)
                if not item:
                    return f"No {domain} found with ID {id}"
                return f"**{item.get('title', 'Untitled')}**\n..."
            else:
                items = await service.list_{domain}s(self.user_id, limit=limit)
                if not items:
                    return "No {domain}s found."
                lines = [f"- {item.get('title', 'Untitled')}" for item in items]
                return f"**{domain}s ({len(items)}):**\n" + "\n".join(lines)

        except Exception as e:
            logger.error(f"get_{domain} failed for user {self.user_id}: {e}")
            return f"Failed to retrieve {domain}s: {e}"


class Create{Domain}Tool(BaseTool):
    """Create a new {domain}."""

    name: str = "create_{domain}"
    description: str = "Create a new {domain} for the user."
    args_schema: Type[BaseModel] = Create{Domain}Input

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    # NOTE: No prompt_section — only the Get tool provides prompt guidance for the domain.

    def _run(self, **kwargs) -> str:
        return "create_{domain} requires async execution. Use _arun."

    async def _arun(self, title: str, **kwargs) -> str:
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.{domain}_service import {Domain}Service

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = {Domain}Service(db)

            result = await service.create_{domain}(user_id=self.user_id, title=title, **kwargs)
            return f'Created {domain}: "{title}"'

        except Exception as e:
            logger.error(f"create_{domain} failed for user {self.user_id}: {e}")
            return f"Failed to create {domain}: {e}"


class Delete{Domain}Tool(BaseTool):
    """Delete {domain}s by ID."""

    name: str = "delete_{domain}"
    description: str = "Delete one or more {domain}s by their IDs."
    args_schema: Type[BaseModel] = Delete{Domain}Input

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "delete_{domain} requires async execution. Use _arun."

    async def _arun(self, ids: list[str]) -> str:
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.{domain}_service import {Domain}Service

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = {Domain}Service(db)

            deleted = await service.delete_{domain}s(self.user_id, ids)
            if deleted:
                return f"Deleted {len(deleted)} {domain}(s)."
            return f"No {domain}s found with those IDs."

        except Exception as e:
            logger.error(f"delete_{domain} failed for user {self.user_id}: {e}")
            return f"Failed to delete {domain}s: {e}"
```

**Rules:**
- All service imports go **inside `_arun`**, not at module top (avoids circular imports).
- `_run` is always a one-liner stub.
- Only the `Get` tool implements `prompt_section` — it covers the whole domain.
- `supabase_url` and `supabase_key` are declared but unused — the loader expects them.
- Tool `name` is `verb_resource` (snake_case). Class name is `Verb{Resource}Tool` (PascalCase).

## Step 3: Register in TOOL_REGISTRY — `src/core/agent_loader_db.py`

Add import (grouped with other domain imports):

```python
from chatServer.tools.{domain}_tools import Create{Domain}Tool, Delete{Domain}Tool, Get{Domain}Tool
```

Add to `TOOL_REGISTRY` dict:

```python
    # {Domain}
    "Get{Domain}Tool": Get{Domain}Tool,
    "Create{Domain}Tool": Create{Domain}Tool,
    "Delete{Domain}Tool": Delete{Domain}Tool,
```

The string key matches the `type` column in `agent_tools` DB rows.

## Step 4: Approval Tiers — `chatServer/security/approval_tiers.py`

Add entries to `TOOL_APPROVAL_DEFAULTS`:

```python
    # {Domain} tools
    "get_{domain}":    (ApprovalTier.AUTO_APPROVE,      ApprovalTier.AUTO_APPROVE),
    "create_{domain}": (ApprovalTier.USER_CONFIGURABLE,  ApprovalTier.AUTO_APPROVE),
    "delete_{domain}": (ApprovalTier.USER_CONFIGURABLE,  ApprovalTier.REQUIRES_APPROVAL),
```

**Standard pattern:**
- Reads → `AUTO_APPROVE / AUTO_APPROVE`
- Creates → `USER_CONFIGURABLE / AUTO_APPROVE`
- Deletes → `USER_CONFIGURABLE / REQUIRES_APPROVAL`

The key is the tool's `name` field (snake_case), not the class name.

## Step 5: Database Migration

```sql
-- Register tool type enum values
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'Get{Domain}Tool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'Create{Domain}Tool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'Delete{Domain}Tool';

-- Register tools for the assistant agent
INSERT INTO tools (name, description, type) VALUES
    ('get_{domain}', 'Get {domain}s for the user', 'Get{Domain}Tool'),
    ('create_{domain}', 'Create a new {domain}', 'Create{Domain}Tool'),
    ('delete_{domain}', 'Delete {domain}s', 'Delete{Domain}Tool')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    type = EXCLUDED.type;  -- MUST include type to avoid stale values

-- Link tools to assistant agent
INSERT INTO agent_tools (agent_id, tool_id, is_active, "order")
SELECT ac.id, t.id, true,
    (SELECT COALESCE(MAX("order"), 0) + 1 FROM agent_tools WHERE agent_id = ac.id)
FROM agent_configurations ac, tools t
WHERE ac.agent_name = 'assistant'
  AND t.name IN ('get_{domain}', 'create_{domain}', 'delete_{domain}')
ON CONFLICT (agent_id, tool_id) WHERE is_deleted = false
DO UPDATE SET is_active = true;
```

**Gotchas:**
- `ON CONFLICT DO UPDATE` MUST include `type = EXCLUDED.type` — omitting it leaves stale type values.
- `ON CONFLICT DO NOTHING` won't reactivate deactivated rows — use `DO UPDATE SET is_active = true`.

## Step 6: Tool Tests — `tests/chatServer/tools/test_{domain}_tools.py`

```python
"""Unit tests for {domain} tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.{domain}_tools import Create{Domain}Tool, Delete{Domain}Tool, Get{Domain}Tool


@pytest.fixture
def get_tool():
    return Get{Domain}Tool(user_id="user-123", agent_name="search_test_agent")


@pytest.fixture
def create_tool():
    return Create{Domain}Tool(user_id="user-123", agent_name="search_test_agent")


@pytest.fixture
def delete_tool():
    return Delete{Domain}Tool(user_id="user-123", agent_name="search_test_agent")


def _patch_deps(mock_db, mock_service):
    """Shared patch helper for tool dependencies."""
    return (
        patch("chatServer.tools.{domain}_tools.get_supabase_client",
              new_callable=AsyncMock, return_value=mock_db),
        patch("chatServer.tools.{domain}_tools.{Domain}Service",
              return_value=mock_service),
    )


# --- Get tool ---

@pytest.mark.asyncio
async def test_get_{domain}s_returns_list(get_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_{domain}s = AsyncMock(return_value=[
        {"id": "1", "title": "Test item"},
    ])
    p1, p2 = _patch_deps(mock_db, mock_service)
    with p1, p2:
        result = await get_tool._arun()
    assert "Test item" in result


@pytest.mark.asyncio
async def test_get_{domain}s_empty(get_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_{domain}s = AsyncMock(return_value=[])
    p1, p2 = _patch_deps(mock_db, mock_service)
    with p1, p2:
        result = await get_tool._arun()
    assert "No {domain}s found" in result


# --- Create tool ---

@pytest.mark.asyncio
async def test_create_{domain}(create_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_{domain} = AsyncMock(return_value={"id": "new-1", "title": "New"})
    p1, p2 = _patch_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(title="New")
    assert "Created" in result
    mock_service.create_{domain}.assert_awaited_once()


# --- Delete tool ---

@pytest.mark.asyncio
async def test_delete_{domain}s(delete_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_{domain}s = AsyncMock(return_value=["1", "2"])
    p1, p2 = _patch_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(ids=["1", "2"])
    assert "Deleted 2" in result


@pytest.mark.asyncio
async def test_delete_{domain}s_not_found(delete_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_{domain}s = AsyncMock(return_value=[])
    p1, p2 = _patch_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(ids=["nonexistent"])
    assert "No {domain}s found" in result


# --- prompt_section ---

def test_prompt_section_web():
    section = Get{Domain}Tool.prompt_section("web")
    assert section is not None
    assert "{domain}" in section.lower()
```

**Rules:**
- `agent_name` in fixtures uses `"search_test_agent"` — avoids `validate-patterns.sh` false positive.
- Assertions use `assert "fragment" in result` — never exact string matching.
- `_patch_deps` helper shared across all tests in the file.

## Step 7: Service Tests — `tests/chatServer/services/test_{domain}_service.py`

```python
"""Unit tests for {Domain}Service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.{domain}_service import {Domain}Service


@pytest.fixture
def db_client():
    return MagicMock()


@pytest.fixture
def service(db_client):
    return {Domain}Service(db_client)


def _setup_insert_chain(db_client, data=None):
    if data is None:
        data = [{"id": "x-1", "user_id": "user-1", "title": "Test"}]
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    db_client.table.return_value.insert.return_value.execute = mock_execute
    return mock_execute


def _setup_select_chain(db_client, data=None):
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute = mock_execute
    return mock_execute


def _setup_update_chain(db_client, data=None):
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.update.return_value
    chain.eq.return_value = chain
    chain.execute = mock_execute
    return mock_execute


@pytest.mark.asyncio
async def test_create_{domain}(service, db_client):
    _setup_insert_chain(db_client)
    result = await service.create_{domain}(user_id="user-1", title="Test")
    assert result["id"] == "x-1"
    db_client.table.assert_called_with("{domain}s")


@pytest.mark.asyncio
async def test_list_{domain}s(service, db_client):
    _setup_select_chain(db_client, data=[{"id": "1"}, {"id": "2"}])
    result = await service.list_{domain}s(user_id="user-1")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_list_{domain}s_empty(service, db_client):
    _setup_select_chain(db_client, data=[])
    result = await service.list_{domain}s(user_id="user-1")
    assert result == []


@pytest.mark.asyncio
async def test_delete_{domain}s(service, db_client):
    _setup_update_chain(db_client, data=[{"id": "x-1"}])
    result = await service.delete_{domain}s(user_id="user-1", ids=["x-1"])
    assert "x-1" in result
```

**Assertion pattern:** Check (1) table name via `table.assert_called_with()`, (2) data dict via `call_args`, (3) filter via `.eq.call_args_list`.

## Checklist

Before marking complete:

- [ ] Service file: `chatServer/services/{domain}_service.py`
- [ ] Tool file: `chatServer/tools/{domain}_tools.py`
- [ ] TOOL_REGISTRY entries in `src/core/agent_loader_db.py`
- [ ] Approval tier entries in `chatServer/security/approval_tiers.py`
- [ ] DB migration: enum values + `tools` rows + `agent_tools` links
- [ ] Tool tests: `tests/chatServer/tools/test_{domain}_tools.py`
- [ ] Service tests: `tests/chatServer/services/test_{domain}_service.py`
- [ ] `ON CONFLICT` includes `type = EXCLUDED.type` in migration
- [ ] Tool names follow `verb_resource` pattern
- [ ] All tests pass: `pytest tests/chatServer/tools/test_{domain}_tools.py tests/chatServer/services/test_{domain}_service.py`
