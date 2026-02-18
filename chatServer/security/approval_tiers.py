"""
Approval tier system for tool execution.

This module defines the approval tiers for tools and provides functions
to determine whether a tool should auto-execute or require user approval.

Security Model:
- AUTO_APPROVE: Always safe to execute (read-only operations)
- REQUIRES_APPROVAL: Always requires user approval (cannot be overridden)
- USER_CONFIGURABLE: User can set preference, defaults to a safe value

The LLM cannot modify these tiers - they are enforced at the application layer.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ApprovalTier(Enum):
    """
    Approval tiers for tool execution.

    AUTO_APPROVE: Execute immediately without user confirmation
    REQUIRES_APPROVAL: Always queue for user approval (security-critical)
    USER_CONFIGURABLE: User can override the default behavior
    """
    AUTO_APPROVE = "auto"
    REQUIRES_APPROVAL = "requires_approval"
    USER_CONFIGURABLE = "user_configurable"


# Default approval tiers for known tools
# REQUIRES_APPROVAL cannot be overridden by users (enforced in get_effective_tier)
# USER_CONFIGURABLE shows the default, but users can change it
TOOL_APPROVAL_DEFAULTS: dict[str, tuple[ApprovalTier, ApprovalTier]] = {
    # Format: "tool_name": (tier, default_for_user_configurable)

    # Gmail tools - reading is safe, sending is not
    "gmail_search": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "gmail_get_message": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "gmail_get_thread": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "gmail_send_message": (ApprovalTier.REQUIRES_APPROVAL, ApprovalTier.REQUIRES_APPROVAL),
    "gmail_create_draft": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "gmail_archive": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "gmail_trash": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.REQUIRES_APPROVAL),
    "gmail_mark_read": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "gmail_mark_unread": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "gmail_add_label": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "gmail_remove_label": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),

    # Task tools - CRUD operations
    "create_task": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "get_tasks": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "update_task": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.AUTO_APPROVE),
    "delete_task": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.REQUIRES_APPROVAL),

    # File tools - reading is safe, writing needs review
    "read_file": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "list_files": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "write_file": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.REQUIRES_APPROVAL),

    # Memory tools (legacy CRUD-based)
    "memory_store": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "memory_search": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
    "memory_delete": (ApprovalTier.REQUIRES_APPROVAL, ApprovalTier.REQUIRES_APPROVAL),

    # LTM memory tools
    "save_memory": (ApprovalTier.USER_CONFIGURABLE, ApprovalTier.REQUIRES_APPROVAL),
    "read_memory": (ApprovalTier.AUTO_APPROVE, ApprovalTier.AUTO_APPROVE),
}

# Default tier for unknown tools (fail-safe)
DEFAULT_UNKNOWN_TIER = ApprovalTier.REQUIRES_APPROVAL


def get_tool_default_tier(tool_name: str) -> tuple[ApprovalTier, ApprovalTier]:
    """
    Get the default approval tier for a tool.

    Returns:
        Tuple of (tier, default_for_user_configurable)
    """
    return TOOL_APPROVAL_DEFAULTS.get(
        tool_name,
        (DEFAULT_UNKNOWN_TIER, DEFAULT_UNKNOWN_TIER)
    )


async def get_effective_tier(
    user_id: str,
    tool_name: str,
    db_client=None
) -> ApprovalTier:
    """
    Get the effective approval tier for a tool, considering user overrides.

    Security properties:
    - REQUIRES_APPROVAL tools can NEVER be overridden to auto
    - AUTO_APPROVE tools are always auto (no override needed)
    - USER_CONFIGURABLE tools check the database for user preference
    """
    tier, default = get_tool_default_tier(tool_name)

    # REQUIRES_APPROVAL is absolute - cannot be overridden
    if tier == ApprovalTier.REQUIRES_APPROVAL:
        logger.debug(f"Tool {tool_name} requires approval (non-overridable)")
        return ApprovalTier.REQUIRES_APPROVAL

    # AUTO_APPROVE is always auto
    if tier == ApprovalTier.AUTO_APPROVE:
        logger.debug(f"Tool {tool_name} is auto-approved")
        return ApprovalTier.AUTO_APPROVE

    # USER_CONFIGURABLE - check for user override
    if tier == ApprovalTier.USER_CONFIGURABLE:
        if db_client is not None:
            try:
                override = await _get_user_preference(db_client, user_id, tool_name)
                if override is not None:
                    logger.debug(f"Tool {tool_name} using user override: {override}")
                    if override == "auto":
                        return ApprovalTier.AUTO_APPROVE
                    elif override == "requires_approval":
                        return ApprovalTier.REQUIRES_APPROVAL
            except Exception as e:
                logger.warning(f"Failed to fetch user preference for {tool_name}: {e}")

        # Use default for USER_CONFIGURABLE
        logger.debug(f"Tool {tool_name} using default: {default}")
        return default

    # Fallback (should not reach here)
    logger.warning(f"Unknown tier for tool {tool_name}, defaulting to requires_approval")
    return ApprovalTier.REQUIRES_APPROVAL


async def _get_user_preference(
    db_client,
    user_id: str,
    tool_name: str
) -> Optional[str]:
    """Fetch user's approval preference for a tool from the database."""
    try:
        result = await db_client.table("user_tool_preferences") \
            .select("approval_tier") \
            .eq("user_id", user_id) \
            .eq("tool_name", tool_name) \
            .single() \
            .execute()

        if result.data:
            return result.data.get("approval_tier")
        return None
    except Exception:
        return None


async def set_user_preference(
    db_client,
    user_id: str,
    tool_name: str,
    preference: str
) -> bool:
    """
    Set user's approval preference for a tool.

    Only works for USER_CONFIGURABLE tools. Cannot override REQUIRES_APPROVAL.
    """
    tier, _ = get_tool_default_tier(tool_name)
    if tier == ApprovalTier.REQUIRES_APPROVAL:
        logger.warning(f"Cannot override REQUIRES_APPROVAL tool: {tool_name}")
        return False

    if tier == ApprovalTier.AUTO_APPROVE:
        logger.warning(f"Cannot set preference for AUTO_APPROVE tool: {tool_name}")
        return False

    if preference not in ("auto", "requires_approval"):
        logger.warning(f"Invalid preference value: {preference}")
        return False

    try:
        await db_client.table("user_tool_preferences") \
            .upsert({
                "user_id": user_id,
                "tool_name": tool_name,
                "approval_tier": preference
            }) \
            .execute()

        logger.info(f"Set preference for user {user_id}, tool {tool_name}: {preference}")
        return True
    except Exception as e:
        logger.error(f"Failed to set user preference: {e}")
        return False


def requires_approval(tier: ApprovalTier) -> bool:
    """Check if a tier requires user approval."""
    return tier == ApprovalTier.REQUIRES_APPROVAL
