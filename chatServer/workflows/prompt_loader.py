"""Step prompt loader — reads step-specific system prompts from ConfigService.

Prompts live at system/workflows/prompts/{template_name}/{step_name}.md
in the config bucket. Falls back to None if not found (builder uses
step description as fallback).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_PROMPTS_PREFIX = "workflows/prompts"


async def load_step_prompt(
    template_name: str,
    step_name: str,
    config_service=None,
    user_id: str = "",
) -> Optional[str]:
    """Load a step prompt from ConfigService.

    Args:
        template_name: Workflow template name (e.g., "email-triage").
        step_name: Step slug name (e.g., "categorize").
        config_service: ConfigService instance. If None, uses global.
        user_id: User ID for overlay resolution.

    Returns:
        Prompt content string, or None if not found.
    """
    if config_service is None:
        from ..services.config_service import get_config_service
        try:
            config_service = get_config_service()
        except RuntimeError:
            logger.debug("ConfigService not initialized, skipping prompt load")
            return None

    path = f"{_PROMPTS_PREFIX}/{template_name}/{step_name}.md"
    content = await config_service.read(path, user_id)

    if content:
        logger.debug("Loaded step prompt: %s/%s", template_name, step_name)
    return content


def make_prompt_loader(config_service=None, user_id: str = ""):
    """Create a prompt loader closure for use with GraphBuilder.

    Returns an async callable (template_name, step_name) -> Optional[str].
    """
    async def loader(template_name: str, step_name: str) -> Optional[str]:
        return await load_step_prompt(
            template_name, step_name,
            config_service=config_service,
            user_id=user_id,
        )
    return loader
