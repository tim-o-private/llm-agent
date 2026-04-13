"""Tests for TemplateRegistry — system + user dir resolution."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from chatServer.workflows.models import TemplateNotFoundError
from chatServer.workflows.registry import TemplateRegistry

# Minimal valid template content for testing
_SYSTEM_TEMPLATE = """\
---
name: my-workflow
description: System workflow
version: 1
default_gate_policy: none
---

### step-1: Do stuff
- **agent:** default
- **tools:** search_gmail
- **depends_on:**
"""

_USER_TEMPLATE = """\
---
name: my-workflow
description: User override workflow
version: 2
default_gate_policy: none
---

### step-1: Do user stuff
- **agent:** default
- **tools:** get_tasks
- **depends_on:**
"""

_SYSTEM_ONLY_TEMPLATE = """\
---
name: system-only
description: System-only workflow
version: 1
default_gate_policy: none
---

### step-1: System step
- **agent:** default
- **tools:** search_gmail
- **depends_on:**
"""

_USER_ONLY_TEMPLATE = """\
---
name: user-only
description: Only in user dir
version: 1
default_gate_policy: none
---

### step-1: Custom step
- **agent:** default
- **tools:** search_memories
- **depends_on:**
"""


@pytest.fixture()
def system_dir(tmp_path: Path) -> Path:
    """Create a system dir with a workflows/ subdirectory and a template."""
    wf_dir = tmp_path / "system" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "my-workflow.md").write_text(_SYSTEM_TEMPLATE)
    (wf_dir / "system-only.md").write_text(_SYSTEM_ONLY_TEMPLATE)
    return tmp_path / "system"


@pytest.fixture()
def user_dir(tmp_path: Path) -> Path:
    """Create a user sandbox dir with a workflows/ subdirectory."""
    ud = tmp_path / "sandboxes" / "user-1"
    wf_dir = ud / "workflows"
    wf_dir.mkdir(parents=True)
    # Shadow the system template
    (wf_dir / "my-workflow.md").write_text(_USER_TEMPLATE)
    # User-only template
    (wf_dir / "user-only.md").write_text(_USER_ONLY_TEMPLATE)
    return ud


# ---------------------------------------------------------------------------
# get_template — user dir resolution
# ---------------------------------------------------------------------------


class TestGetTemplateUserDir:
    @pytest.mark.asyncio
    async def test_user_template_found_in_user_dir(self, system_dir, user_dir):
        """User-only template is discovered from user dir."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        template = await registry.get_template("user-only", "user-1")
        assert template.name == "user-only"
        assert template.description == "Only in user dir"

    @pytest.mark.asyncio
    async def test_user_template_shadows_system(self, system_dir, user_dir):
        """When both dirs have the same template name, user wins."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        template = await registry.get_template("my-workflow", "user-1")
        # User template has version=2, system has version=1
        assert template.version == 2
        assert template.description == "User override workflow"

    @pytest.mark.asyncio
    async def test_falls_back_to_system_when_not_in_user_dir(self, system_dir, user_dir):
        """Template only in system dir is still found when user_dir_resolver is set."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        template = await registry.get_template("system-only", "user-1")
        assert template.name == "system-only"

    @pytest.mark.asyncio
    async def test_user_dir_does_not_exist_falls_back_to_system(self, system_dir, tmp_path):
        """When user dir doesn't exist, system templates still work."""
        nonexistent = tmp_path / "sandboxes" / "ghost-user"
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: nonexistent,
        )
        template = await registry.get_template("my-workflow", "ghost-user")
        assert template.version == 1  # system version

    @pytest.mark.asyncio
    async def test_no_user_dir_resolver_backward_compat(self, system_dir):
        """No user_dir_resolver — behaves like original (system only)."""
        registry = TemplateRegistry(system_dir)
        template = await registry.get_template("my-workflow", "user-1")
        assert template.version == 1  # system version

    @pytest.mark.asyncio
    async def test_template_not_found_raises(self, system_dir, user_dir):
        """Non-existent template raises TemplateNotFoundError."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        with pytest.raises(TemplateNotFoundError, match="nonexistent"):
            await registry.get_template("nonexistent", "user-1")

    @pytest.mark.asyncio
    async def test_cache_returns_same_template(self, system_dir, user_dir):
        """Second call within TTL returns the cached template (no re-parse)."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        t1 = await registry.get_template("my-workflow", "user-1")
        t2 = await registry.get_template("my-workflow", "user-1")
        assert t1 is t2


# ---------------------------------------------------------------------------
# list_templates — merged system + user
# ---------------------------------------------------------------------------


class TestListTemplates:
    @pytest.mark.asyncio
    async def test_lists_system_templates_only(self, system_dir):
        """Without user_dir_resolver, lists only system templates."""
        registry = TemplateRegistry(system_dir)
        names = await registry.list_templates("user-1")
        assert "my-workflow" in names
        assert "system-only" in names
        assert "user-only" not in names

    @pytest.mark.asyncio
    async def test_lists_merged_templates(self, system_dir, user_dir):
        """With user_dir_resolver, lists merged set from both dirs."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        names = await registry.list_templates("user-1")
        assert "my-workflow" in names  # in both — deduplicated
        assert "system-only" in names  # system only
        assert "user-only" in names  # user only

    @pytest.mark.asyncio
    async def test_list_templates_sorted(self, system_dir, user_dir):
        """Returned list is sorted alphabetically."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        names = await registry.list_templates("user-1")
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_list_templates_user_dir_missing(self, system_dir, tmp_path):
        """When user dir doesn't exist, returns system templates only."""
        nonexistent = tmp_path / "sandboxes" / "ghost-user"
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: nonexistent,
        )
        names = await registry.list_templates("ghost-user")
        assert "my-workflow" in names
        assert "system-only" in names
        assert "user-only" not in names

    @pytest.mark.asyncio
    async def test_list_templates_no_system_workflows_dir(self, tmp_path):
        """Empty system dir (no workflows/) returns empty when no user dir either."""
        empty_system = tmp_path / "empty-system"
        empty_system.mkdir()
        registry = TemplateRegistry(empty_system)
        names = await registry.list_templates("user-1")
        assert names == []


# ---------------------------------------------------------------------------
# invalidate — existing behavior preserved
# ---------------------------------------------------------------------------


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_all(self, system_dir, user_dir):
        """invalidate() clears all cached templates."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        await registry.get_template("my-workflow", "user-1")
        assert len(registry._cache) == 1
        registry.invalidate()
        assert len(registry._cache) == 0

    @pytest.mark.asyncio
    async def test_invalidate_by_name(self, system_dir, user_dir):
        """invalidate(name) clears only that template's cache entries."""
        registry = TemplateRegistry(
            system_dir,
            user_dir_resolver=lambda uid: user_dir,
        )
        await registry.get_template("my-workflow", "user-1")
        await registry.get_template("user-only", "user-1")
        assert len(registry._cache) == 2
        registry.invalidate("my-workflow")
        assert len(registry._cache) == 1
        assert "user-1:user-only" in registry._cache
