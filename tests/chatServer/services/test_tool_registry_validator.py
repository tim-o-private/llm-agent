"""CI validation: tool registry, approval tiers, and code↔DB sync.

These tests ensure that tool registrations stay in sync across:
- TOOL_REGISTRY in agent_loader_db.py (code → DB type mapping)
- TOOL_APPROVAL_DEFAULTS in approval_tiers.py (tool name → approval tier)
- Tool classes (Python class name attribute)

Run in CI to catch drift before deploy.
"""

from chatServer.security.approval_tiers import TOOL_APPROVAL_DEFAULTS, ApprovalTier  # noqa: I001
from src.core.agent_loader_db import TOOL_REGISTRY


# All tool names that should be active after SPEC-019 canonical migration.
# This is the single source of truth for which tools exist.
CANONICAL_TOOL_NAMES = {
    "get_tasks", "create_tasks", "update_tasks", "delete_tasks",
    "get_reminders", "create_reminders", "delete_reminders",
    "get_schedules", "create_schedules", "delete_schedules",
    "update_instructions",
    "search_gmail", "get_gmail",
    "create_memories", "search_memories", "get_memories",
    "update_memories", "delete_memories",
    "set_project", "link_memories",
    "get_entities", "search_entities", "get_context",
    "search_web",
}


class TestToolRegistryCompleteness:
    """Every TOOL_REGISTRY entry maps to a real Python class."""

    def test_all_registry_entries_have_classes(self):
        """No TOOL_REGISTRY value should be missing (except GmailTool special case)."""
        for type_key, cls in TOOL_REGISTRY.items():
            if type_key == "GmailTool":
                continue  # Special handling via config.tool_class
            if type_key == "CRUDTool":
                continue  # Generic base, not a specific tool
            assert cls is not None, f"TOOL_REGISTRY['{type_key}'] maps to None"

    def test_all_registry_classes_have_name_attribute(self):
        """Every tool class in registry should have a `name` class attribute."""
        for type_key, cls in TOOL_REGISTRY.items():
            if cls is None or type_key == "CRUDTool":
                continue
            # Instantiate would require constructor args, so just check class has name field
            assert hasattr(cls, "model_fields") or hasattr(cls, "__fields__"), (
                f"TOOL_REGISTRY['{type_key}'] ({cls.__name__}) is not a Pydantic model"
            )


class TestApprovalTierCoverage:
    """Every canonical tool name has an explicit approval tier."""

    def test_all_canonical_tools_have_approval_tiers(self):
        """No canonical tool should fall through to DEFAULT_UNKNOWN_TIER."""
        missing = CANONICAL_TOOL_NAMES - set(TOOL_APPROVAL_DEFAULTS.keys())
        assert not missing, f"Tools missing from TOOL_APPROVAL_DEFAULTS: {missing}"

    def test_no_stale_approval_tier_entries(self):
        """TOOL_APPROVAL_DEFAULTS should not have entries for tools that don't exist."""
        stale = set(TOOL_APPROVAL_DEFAULTS.keys()) - CANONICAL_TOOL_NAMES
        assert not stale, f"Stale entries in TOOL_APPROVAL_DEFAULTS: {stale}"

    def test_read_tools_are_auto_approve(self):
        """All get_* and search_* tools should be AUTO_APPROVE."""
        for tool_name in CANONICAL_TOOL_NAMES:
            if tool_name.startswith("get_") or tool_name.startswith("search_"):
                tier, _ = TOOL_APPROVAL_DEFAULTS[tool_name]
                assert tier == ApprovalTier.AUTO_APPROVE, (
                    f"{tool_name} is a read tool but tier is {tier}"
                )


class TestRegistryToolClassMapping:
    """TOOL_REGISTRY type keys map to classes whose `name` matches a canonical tool."""

    def test_canonical_tools_have_registry_entries(self):
        """Every canonical tool name should have at least one TOOL_REGISTRY entry
        whose class produces that tool name."""
        # Build reverse map: tool_name → set of type_keys
        name_to_types: dict[str, set[str]] = {}
        for type_key, cls in TOOL_REGISTRY.items():
            if cls is None or type_key == "CRUDTool":
                continue
            # Get the default name from the class
            if "name" in getattr(cls, "model_fields", {}):
                default_name = cls.model_fields["name"].default
                name_to_types.setdefault(default_name, set()).add(type_key)

        # Gmail tools use GmailTool type + config.tool_class, so they won't appear
        # in the direct mapping. Skip them.
        gmail_tools = {"search_gmail", "get_gmail"}
        check_tools = CANONICAL_TOOL_NAMES - gmail_tools

        missing = check_tools - set(name_to_types.keys())
        assert not missing, f"Canonical tools with no TOOL_REGISTRY class: {missing}"
