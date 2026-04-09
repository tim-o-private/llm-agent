"""Template registry — loads workflow templates from the local filesystem.

System templates at {system_dir}/workflows/{name}.md.
Caches parsed templates with 300s TTL.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from .models import GraphTemplate, TemplateNotFoundError
from .template_parser import parse_template

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_WORKFLOWS_PREFIX = "workflows"


class TemplateRegistry:
    """Loads and caches workflow templates from local filesystem."""

    def __init__(self, system_dir: Path):
        """Initialize with a system config directory."""
        self._system_dir = system_dir
        self._cache: dict[str, tuple[GraphTemplate, float]] = {}

    async def get_template(
        self, name: str, user_id: str
    ) -> GraphTemplate:
        """Get a parsed template by name.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
        """
        cache_key = f"{user_id}:{name}"
        cached = self._cache.get(cache_key)
        if cached:
            template, cached_at = cached
            if time.monotonic() - cached_at < _CACHE_TTL_SECONDS:
                return template

        path = self._system_dir / _WORKFLOWS_PREFIX / f"{name}.md"
        if not path.is_file():
            raise TemplateNotFoundError(
                f"Workflow template '{name}' not found"
            )

        content = path.read_text()
        template = parse_template(content, source_name=name)
        self._cache[cache_key] = (template, time.monotonic())
        return template

    async def list_templates(self, user_id: str) -> list[str]:
        """List available template names.

        Returns template names (without path prefix or .md extension).
        """
        workflows_dir = self._system_dir / _WORKFLOWS_PREFIX
        if not workflows_dir.is_dir():
            return []

        names = []
        for path in workflows_dir.glob("*.md"):
            name = path.stem
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


def initialize_template_registry(system_dir: Path) -> TemplateRegistry:
    """Initialize the global TemplateRegistry."""
    global _registry
    _registry = TemplateRegistry(system_dir)
    logger.info("TemplateRegistry initialized (system_dir=%s)", system_dir)
    return _registry


def shutdown_template_registry() -> None:
    """Shut down the global TemplateRegistry."""
    global _registry
    if _registry:
        _registry.invalidate()
        _registry = None
        logger.info("TemplateRegistry shut down")
