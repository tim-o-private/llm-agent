"""Template registry — loads workflow templates from the local filesystem.

System templates at {system_dir}/workflows/{name}.md.
User templates at {user_dir}/workflows/{name}.md (user shadows system).
Caches parsed templates with 300s TTL.
"""

import logging
import time
from pathlib import Path
from typing import Callable, Optional

from .models import GraphTemplate, TemplateNotFoundError
from .template_parser import parse_template

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300
_WORKFLOWS_PREFIX = "workflows"


class TemplateRegistry:
    """Loads and caches workflow templates from local filesystem."""

    def __init__(
        self,
        system_dir: Path,
        user_dir_resolver: Optional[Callable[[str], Path]] = None,
    ):
        """Initialize with a system config directory and optional user dir resolver.

        Args:
            system_dir: Path to system config directory containing workflows/.
            user_dir_resolver: Callable that maps user_id to user sandbox Path.
                User templates at {user_dir}/workflows/ shadow system ones.
        """
        self._system_dir = system_dir
        self._user_dir_resolver = user_dir_resolver
        self._cache: dict[str, tuple[GraphTemplate, float]] = {}

    async def get_template(
        self, name: str, user_id: str
    ) -> GraphTemplate:
        """Get a parsed template by name.

        Checks user dir first (user templates shadow system ones),
        then falls back to system dir.

        Raises:
            TemplateNotFoundError: If template doesn't exist.
        """
        cache_key = f"{user_id}:{name}"
        cached = self._cache.get(cache_key)
        if cached:
            template, cached_at = cached
            if time.monotonic() - cached_at < _CACHE_TTL_SECONDS:
                return template

        # Try user dir first (user templates shadow system ones).
        # Check both vault convention (_workflows/*.flow.md) and legacy
        # convention (workflows/*.md) so user-created workflows via the
        # vault editor are discoverable by the engine.
        path = None
        if self._user_dir_resolver:
            user_dir = self._user_dir_resolver(user_id)
            for prefix, ext in [("_workflows", ".flow.md"), (_WORKFLOWS_PREFIX, ".md")]:
                candidate = user_dir / prefix / f"{name}{ext}"
                if candidate.is_file():
                    path = candidate
                    break

        # Fall back to system dir
        if path is None:
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
        """List available template names from both system and user directories.

        Returns template names (without path prefix or .md extension),
        merged and deduplicated.
        """
        names: set[str] = set()

        # System templates
        system_workflows = self._system_dir / _WORKFLOWS_PREFIX
        if system_workflows.is_dir():
            for path in system_workflows.glob("*.md"):
                if path.stem:
                    names.add(path.stem)

        # User templates (may shadow system) — check both conventions
        if self._user_dir_resolver:
            user_dir = self._user_dir_resolver(user_id)
            for prefix, pattern, strip_suffix in [
                ("_workflows", "*.flow.md", ".flow"),
                (_WORKFLOWS_PREFIX, "*.md", ""),
            ]:
                wf_dir = user_dir / prefix
                if wf_dir.is_dir():
                    for p in wf_dir.glob(pattern):
                        stem = p.stem
                        if strip_suffix and stem.endswith(strip_suffix):
                            stem = stem[: -len(strip_suffix)]
                        if stem:
                            names.add(stem)

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


def initialize_template_registry(
    system_dir: Path,
    user_dir_resolver: Optional[Callable[[str], Path]] = None,
) -> TemplateRegistry:
    """Initialize the global TemplateRegistry."""
    global _registry
    _registry = TemplateRegistry(system_dir, user_dir_resolver=user_dir_resolver)
    logger.info("TemplateRegistry initialized (system_dir=%s)", system_dir)
    return _registry


def shutdown_template_registry() -> None:
    """Shut down the global TemplateRegistry."""
    global _registry
    if _registry:
        _registry.invalidate()
        _registry = None
        logger.info("TemplateRegistry shut down")
