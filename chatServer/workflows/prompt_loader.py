"""Step prompt loader — reads step-specific system prompts from the local filesystem.

Prompts live at {system_dir}/workflows/prompts/{template_name}/{step_name}.md.
Falls back to None if not found (builder uses step description as fallback).
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PROMPTS_PREFIX = "workflows/prompts"


def _get_system_dir() -> Path:
    """Resolve the system config directory."""
    data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
    return data_dir / "config" / "system"


async def load_step_prompt(
    template_name: str,
    step_name: str,
    system_dir: Optional[Path] = None,
    user_id: str = "",
) -> Optional[str]:
    """Load a step prompt from the local filesystem.

    Args:
        template_name: Workflow template name (e.g., "email-triage").
        step_name: Step slug name (e.g., "categorize").
        system_dir: System config directory. If None, uses default.
        user_id: User ID (unused, kept for API compatibility).

    Returns:
        Prompt content string, or None if not found.
    """
    if system_dir is None:
        system_dir = _get_system_dir()

    path = system_dir / _PROMPTS_PREFIX / template_name / f"{step_name}.md"
    if not path.is_file():
        return None

    content = path.read_text()
    if content:
        logger.debug("Loaded step prompt: %s/%s", template_name, step_name)
    return content


def make_prompt_loader(system_dir: Optional[Path] = None, user_id: str = ""):
    """Create a prompt loader closure for use with GraphBuilder.

    Returns an async callable (template_name, step_name) -> Optional[str].
    """
    async def loader(template_name: str, step_name: str) -> Optional[str]:
        return await load_step_prompt(
            template_name, step_name,
            system_dir=system_dir,
            user_id=user_id,
        )
    return loader
