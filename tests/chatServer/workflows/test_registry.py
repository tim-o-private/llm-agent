"""Tests for workflow template registry."""

import time
from unittest.mock import AsyncMock

import pytest

from chatServer.workflows.models import TemplateNotFoundError
from chatServer.workflows.registry import TemplateRegistry

SAMPLE_TEMPLATE_MD = """\
---
name: email-triage
description: Process emails
version: 1
default_gate_policy: none
---

# Email Triage

## Steps

### step-1: Fetch Emails
- **agent:** email-fetcher
- **depends_on:** []
- **tools:** [search_gmail]
- **description:** Fetch recent emails.
"""


@pytest.fixture
def mock_config_service():
    svc = AsyncMock()
    svc.read = AsyncMock(return_value=SAMPLE_TEMPLATE_MD)
    svc.list_paths = AsyncMock(return_value=[
        "workflows/email-triage.md",
        "workflows/morning-briefing.md",
    ])
    return svc


@pytest.fixture
def registry(mock_config_service):
    return TemplateRegistry(mock_config_service)


class TestGetTemplate:
    @pytest.mark.asyncio
    async def test_loads_template(self, registry, mock_config_service):
        template = await registry.get_template("email-triage", "user-1")
        assert template.name == "email-triage"
        mock_config_service.read.assert_called_once_with(
            "workflows/email-triage.md", "user-1"
        )

    @pytest.mark.asyncio
    async def test_not_found_raises(self, registry, mock_config_service):
        mock_config_service.read.return_value = None
        with pytest.raises(TemplateNotFoundError, match="not-exist"):
            await registry.get_template("not-exist", "user-1")

    @pytest.mark.asyncio
    async def test_caches_within_ttl(self, registry, mock_config_service):
        await registry.get_template("email-triage", "user-1")
        await registry.get_template("email-triage", "user-1")
        # Should only call read once due to cache
        assert mock_config_service.read.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, registry, mock_config_service):
        await registry.get_template("email-triage", "user-1")

        # Expire the cache entry
        cache_key = "user-1:email-triage"
        template, _ = registry._cache[cache_key]
        registry._cache[cache_key] = (template, time.monotonic() - 301)

        await registry.get_template("email-triage", "user-1")
        assert mock_config_service.read.call_count == 2

    @pytest.mark.asyncio
    async def test_different_users_cached_separately(self, registry, mock_config_service):
        await registry.get_template("email-triage", "user-1")
        await registry.get_template("email-triage", "user-2")
        assert mock_config_service.read.call_count == 2


class TestListTemplates:
    @pytest.mark.asyncio
    async def test_returns_template_names(self, registry, mock_config_service):
        names = await registry.list_templates("user-1")
        assert names == ["email-triage", "morning-briefing"]
        mock_config_service.list_paths.assert_called_once_with(
            "workflows/", "user-1"
        )

    @pytest.mark.asyncio
    async def test_empty_list(self, registry, mock_config_service):
        mock_config_service.list_paths.return_value = []
        names = await registry.list_templates("user-1")
        assert names == []

    @pytest.mark.asyncio
    async def test_filters_non_md_files(self, registry, mock_config_service):
        mock_config_service.list_paths.return_value = [
            "workflows/email-triage.md",
            "workflows/.gitkeep",
        ]
        names = await registry.list_templates("user-1")
        assert names == ["email-triage"]


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_specific(self, registry, mock_config_service):
        await registry.get_template("email-triage", "user-1")
        assert len(registry._cache) == 1
        registry.invalidate("email-triage")
        assert len(registry._cache) == 0

    @pytest.mark.asyncio
    async def test_invalidate_all(self, registry, mock_config_service):
        await registry.get_template("email-triage", "user-1")
        registry.invalidate()
        assert len(registry._cache) == 0
