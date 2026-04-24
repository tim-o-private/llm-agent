"""EntityService — entity-specific operations on top of VaultService.

Entity docs are plain markdown files in the vault (``entities/{type}/{slug}.md``)
with structured YAML frontmatter. This service adds entity semantics — listing,
searching, frontmatter-aware upsert — while delegating all file I/O to
``VaultService`` (the single security chokepoint).

See SPEC-053 §"EntityService" and AC-05.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import HTTPException

from .vault_service import VaultService

logger = logging.getLogger(__name__)

# Entity type directories under entities/
_ENTITY_TYPES = ("people", "projects", "companies")

# Priority order for wikilink resolution when slugs collide across types.
_TYPE_PRIORITY = ("people", "projects", "companies")


@dataclass
class EntitySummary:
    """Lightweight entity representation for index/search results."""

    slug: str
    name: str
    entity_type: str
    path: str  # vault-relative, e.g. "entities/people/sarah-chen.md"
    aliases: list[str] = field(default_factory=list)


@dataclass
class EntityDoc:
    """Full entity document: parsed frontmatter + body."""

    frontmatter: dict
    body: str
    path: str  # vault-relative


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body.

    Returns ``(frontmatter_dict, body_str)``. If no valid frontmatter is
    found, returns ``({}, content)``.
    """
    if not content.startswith("---"):
        return {}, content

    closing = content.find("\n---", 3)
    if closing == -1:
        return {}, content

    fm_start = content.index("\n", 0)
    fm_raw = content[fm_start + 1 : closing]

    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError:
        return {}, content

    if not isinstance(fm, dict):
        return {}, content

    body_start = closing + 4  # len("\n---")
    body = content[body_start:].lstrip("\n") if body_start < len(content) else ""
    return fm, body


def _serialize_entity_doc(frontmatter: dict, body: str) -> str:
    """Serialize frontmatter dict + body into a markdown string."""
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    # Ensure body has leading newline separation
    body_trimmed = body.strip("\n")
    if body_trimmed:
        return f"---\n{fm_str}---\n\n{body_trimmed}\n"
    return f"---\n{fm_str}---\n"


class EntityService:
    """Entity-specific operations composed on top of VaultService."""

    def __init__(self, vault: VaultService):
        self._vault = vault

    async def ensure_entity_dirs(self, user_id: str) -> None:
        """Create ``entities/people/``, ``entities/projects/``, ``entities/companies/``
        if they do not exist (AC-01)."""
        user_root = self._vault._user_root(user_id)
        for subdir in _ENTITY_TYPES:
            dir_path = user_root / "entities" / subdir
            dir_path.mkdir(parents=True, exist_ok=True)

    async def list_entities(
        self, user_id: str, entity_type: str | None = None
    ) -> list[EntitySummary]:
        """Walk ``entities/`` subdirectories, read frontmatter from each ``.md`` file.

        If ``entity_type`` is given, only walk that subdirectory.
        """
        user_root = self._vault._user_root(user_id)
        entities_root = user_root / "entities"
        if not entities_root.exists():
            return []

        dirs_to_scan: list[str]
        if entity_type:
            dirs_to_scan = [entity_type]
        else:
            # Scan all subdirectories under entities/
            try:
                dirs_to_scan = [
                    d.name
                    for d in sorted(entities_root.iterdir())
                    if d.is_dir() and not d.name.startswith(".")
                ]
            except OSError:
                return []

        results: list[EntitySummary] = []
        for type_dir in dirs_to_scan:
            type_path = entities_root / type_dir
            if not type_path.exists() or not type_path.is_dir():
                continue
            try:
                files = sorted(type_path.iterdir())
            except OSError:
                continue
            for f in files:
                if not f.name.endswith(".md") or f.name.startswith("."):
                    continue
                if f.is_symlink():
                    continue
                try:
                    content = f.read_text(errors="replace")
                except OSError:
                    continue
                fm, _ = _parse_frontmatter(content)
                if not fm.get("entity_type"):
                    continue  # AC-15: must have entity_type
                rel = f.relative_to(user_root).as_posix()
                slug = f.stem
                results.append(
                    EntitySummary(
                        slug=slug,
                        name=fm.get("name", slug),
                        entity_type=fm["entity_type"],
                        path=rel,
                        aliases=fm.get("aliases", []) or [],
                    )
                )
        return results

    async def get_entity(
        self, user_id: str, entity_type: str, slug: str
    ) -> EntityDoc:
        """Read ``entities/{entity_type}/{slug}.md``, parse frontmatter + body."""
        rel_path = f"entities/{entity_type}/{slug}.md"
        content = await self._vault.read_file(user_id, rel_path)
        frontmatter, body = _parse_frontmatter(content)
        return EntityDoc(frontmatter=frontmatter, body=body, path=rel_path)

    async def upsert_entity(
        self,
        user_id: str,
        entity_type: str,
        slug: str,
        frontmatter: dict,
        body: str,
    ) -> float:
        """Write entity doc, preserving unknown frontmatter fields (AC-14).

        Returns new mtime.
        """
        rel_path = f"entities/{entity_type}/{slug}.md"
        existing_fm: dict = {}
        try:
            existing_content = await self._vault.read_file(user_id, rel_path)
            existing_fm, _ = _parse_frontmatter(existing_content)
        except HTTPException:
            pass  # new entity — no existing frontmatter

        # Merge: existing keys preserved, new keys overwrite
        merged_fm = {**existing_fm, **frontmatter}
        merged_fm["refreshed_at"] = datetime.now(timezone.utc).isoformat()

        content = _serialize_entity_doc(merged_fm, body)
        return await self._vault.update_body(user_id, rel_path, content)

    async def find_entity_by_alias(
        self, user_id: str, alias: str
    ) -> EntitySummary | None:
        """Scan entity frontmatter ``aliases`` arrays for a match."""
        for entity in await self.list_entities(user_id):
            if alias.lower() in [a.lower() for a in entity.aliases]:
                return entity
        return None

    async def search_entities(
        self, user_id: str, query: str
    ) -> list[EntitySummary]:
        """Substring match on entity name and aliases (Stage 4: no full-text)."""
        if not query:
            return []
        q = query.lower()
        results: list[EntitySummary] = []
        for entity in await self.list_entities(user_id):
            if q in entity.name.lower():
                results.append(entity)
                continue
            if any(q in a.lower() for a in entity.aliases):
                results.append(entity)
        return results
