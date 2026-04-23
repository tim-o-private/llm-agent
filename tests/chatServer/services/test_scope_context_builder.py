"""Unit tests for _build_scope_context — SPEC-049 AC-03."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.deep_agent_builder import _build_scope_context


@pytest.fixture
def mock_vault_service():
    """Return a mock VaultService with async read_file."""
    svc = MagicMock()
    svc.read_file = AsyncMock(return_value="file content here")
    return svc


# ---------------------------------------------------------------------------
# None / global → empty string
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_scope_returns_empty():
    result = await _build_scope_context(None)
    assert result == ""


@pytest.mark.asyncio
async def test_global_scope_returns_empty():
    result = await _build_scope_context({"type": "global"})
    assert result == ""


@pytest.mark.asyncio
async def test_missing_type_defaults_to_empty():
    result = await _build_scope_context({})
    assert result == ""


# ---------------------------------------------------------------------------
# Today scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_today_scope():
    result = await _build_scope_context({"type": "today"})
    assert result == "The user is on the Today dashboard."


# ---------------------------------------------------------------------------
# File scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_file_scope_without_vault_service():
    result = await _build_scope_context({"type": "file", "path": "notes/standup.md"})
    assert "viewing the file: notes/standup.md" in result
    # No file content without vault_service
    assert "File content:" not in result


@pytest.mark.asyncio
async def test_file_scope_with_content(mock_vault_service):
    result = await _build_scope_context(
        {"type": "file", "path": "notes/standup.md"},
        vault_service=mock_vault_service,
        user_id="user-123",
    )
    assert "viewing the file: notes/standup.md" in result
    assert "File content:" in result
    assert "file content here" in result
    mock_vault_service.read_file.assert_awaited_once_with("user-123", "notes/standup.md")


@pytest.mark.asyncio
async def test_file_scope_truncates_long_content(mock_vault_service):
    long_content = "x" * 5000
    mock_vault_service.read_file = AsyncMock(return_value=long_content)

    result = await _build_scope_context(
        {"type": "file", "path": "big.md"},
        vault_service=mock_vault_service,
        user_id="user-123",
    )
    assert "... [truncated]" in result
    # Content should be capped at 4000 chars
    file_block = result.split("```\n")[1]  # between first ``` pair
    # The content part before truncation marker
    assert len(file_block.split("\n... [truncated]")[0]) == 4000


@pytest.mark.asyncio
async def test_file_scope_read_failure_non_fatal(mock_vault_service):
    mock_vault_service.read_file = AsyncMock(side_effect=Exception("disk error"))

    result = await _build_scope_context(
        {"type": "file", "path": "broken.md"},
        vault_service=mock_vault_service,
        user_id="user-123",
    )
    # Should still have the path line, just no content
    assert "viewing the file: broken.md" in result
    assert "File content:" not in result


@pytest.mark.asyncio
async def test_file_scope_missing_path():
    """File scope without path returns empty."""
    result = await _build_scope_context({"type": "file"})
    assert result == ""


# ---------------------------------------------------------------------------
# Folder scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_folder_scope():
    result = await _build_scope_context({"type": "folder", "path": "projects/"})
    assert result == "The user is browsing the folder: projects/"


@pytest.mark.asyncio
async def test_folder_scope_missing_path():
    result = await _build_scope_context({"type": "folder"})
    assert result == ""


# ---------------------------------------------------------------------------
# Workflow scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_scope_without_vault_service():
    result = await _build_scope_context(
        {"type": "workflow", "path": "_workflows/morning.flow.md"},
    )
    assert "editing the workflow: _workflows/morning.flow.md" in result
    assert "Workflow definition:" not in result


@pytest.mark.asyncio
async def test_workflow_scope_with_content(mock_vault_service):
    mock_vault_service.read_file = AsyncMock(return_value="---\nname: morning\n---\nsteps:\n  - check email")

    result = await _build_scope_context(
        {"type": "workflow", "path": "_workflows/morning.flow.md"},
        vault_service=mock_vault_service,
        user_id="user-123",
    )
    assert "editing the workflow: _workflows/morning.flow.md" in result
    assert "Workflow definition:" in result
    assert "check email" in result


@pytest.mark.asyncio
async def test_workflow_scope_read_failure_non_fatal(mock_vault_service):
    mock_vault_service.read_file = AsyncMock(side_effect=Exception("not found"))

    result = await _build_scope_context(
        {"type": "workflow", "path": "_workflows/missing.flow.md"},
        vault_service=mock_vault_service,
        user_id="user-123",
    )
    assert "editing the workflow" in result
    assert "Workflow definition:" not in result


@pytest.mark.asyncio
async def test_workflow_scope_missing_path():
    result = await _build_scope_context({"type": "workflow"})
    assert result == ""


# ---------------------------------------------------------------------------
# Unknown scope type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_scope_type_returns_empty():
    result = await _build_scope_context({"type": "unknown_future"})
    assert result == ""
