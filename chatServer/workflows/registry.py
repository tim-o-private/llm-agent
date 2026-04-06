"""Template registry — loads workflow templates from ConfigService with caching.

System templates at workflows/{name}.md, user templates shadow system templates.
Caches parsed templates with 300s TTL.
"""

import logging
import time
from typing import Optional

from .models import GraphTemplate, TemplateNotFoundError
from .template_parser import parse_template

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_WORKFLOWS_PREFIX = "workflows/"


class TemplateRegistry:
    """Loads and caches workflow templates from ConfigService."""

    def __init__(self, config_service):
        """Initialize with a ConfigService instance."""
        self._config = config_service
        self._cache: dict[str, tuple[GraphTemplate, float]] = {}

    async def get_template(
        self, name: str, user_id: str
    ) -> GraphTemplate:
        """Get a parsed template by name, with user overlay.

        User templates shadow system templates of the same name.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
        """
        cache_key = f"{user_id}:{name}"
        cached = self._cache.get(cache_key)
        if cached:
            template, cached_at = cached
            if time.monotonic() - cached_at < _CACHE_TTL_SECONDS:
                return template

        path = f"{_WORKFLOWS_PREFIX}{name}.md"
        content = await self._config.read(path, user_id)
        if content is None:
            raise TemplateNotFoundError(
                f"Workflow template '{name}' not found"
            )

        template = parse_template(content, source_name=name)
        self._cache[cache_key] = (template, time.monotonic())
        return template

    async def list_templates(self, user_id: str) -> list[str]:
        """List available template names (merged system + user).

        Returns template names (without path prefix or .md extension).
        """
        paths = await self._config.list_paths(
            _WORKFLOWS_PREFIX, user_id
        )
        names = []
        for path in paths:
            if path.endswith(".md"):
                # Strip prefix and extension: "workflows/email-triage.md" → "email-triage"
                name = path.removeprefix(_WORKFLOWS_PREFIX).removesuffix(".md")
                if name:
                    names.append(name)
        return sorted(names)

    def invalidate(self, name: Optional[str] = None) -> None:
        """Invalidate cached templates.

        If name is given, invalidate all user variants of that template.
        If None, invalidate everything.
        """
        if name is None:
            self._cache.clear()
        else:
            keys_to_remove = [
                k for k in self._cache if k.endswith(f":{name}")
            ]
            for k in keys_to_remove:
                del self._cache[k]


# -- Global instance management --

_registry: Optional[TemplateRegistry] = None


def get_template_registry() -> TemplateRegistry:
    """Get the global TemplateRegistry instance."""
    global _registry
    if _registry is None:
        raise RuntimeError(
            "TemplateRegistry not initialized. "
            "Call initialize_template_registry() first."
        )
    return _registry


def initialize_template_registry(config_service) -> TemplateRegistry:
    """Initialize the global TemplateRegistry."""
    global _registry
    _registry = TemplateRegistry(config_service)
    logger.info("TemplateRegistry initialized")
    return _registry


def shutdown_template_registry() -> None:
    """Shut down the global TemplateRegistry."""
    global _registry
    if _registry:
        _registry.invalidate()
        _registry = None
        logger.info("TemplateRegistry shut down")
