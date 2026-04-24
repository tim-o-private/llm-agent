"""Unit tests for EntityService — list, get, upsert, alias search, frontmatter
preservation. SPEC-053 AC-05.

Uses tmp_path + a real VaultService (no mocking of file I/O).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chatServer.services.entity_service import (
    EntityService,
    _parse_frontmatter,
    _serialize_entity_doc,
)
from chatServer.services.vault_service import VaultService

USER_A = "11111111-1111-1111-1111-111111111111"


def _make_service(tmp_path: Path) -> tuple[EntityService, VaultService]:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    vault = VaultService(storage_sync=None, data_dir=tmp_path)
    return EntityService(vault), vault


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


def _write_entity(
    user_root: Path,
    entity_type: str,
    slug: str,
    content: str,
) -> None:
    path = user_root / "entities" / entity_type / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# _parse_frontmatter / _serialize_entity_doc
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nentity_type: person\nname: Alice\n---\n\n## Context\nHello"
        fm, body = _parse_frontmatter(content)
        assert fm["entity_type"] == "person"
        assert fm["name"] == "Alice"
        assert "Context" in body

    def test_no_frontmatter(self):
        content = "# Just text\nNo frontmatter here."
        fm, body = _parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_invalid_yaml(self):
        content = "---\n: invalid: yaml: {{{\n---\nBody"
        fm, body = _parse_frontmatter(content)
        assert fm == {}
        assert body == content


class TestSerializeEntityDoc:
    def test_roundtrip(self):
        fm = {"entity_type": "person", "name": "Alice"}
        body = "## Context\nHello"
        result = _serialize_entity_doc(fm, body)
        assert result.startswith("---\n")
        assert "entity_type: person" in result
        assert "## Context" in result

    def test_empty_body(self):
        fm = {"entity_type": "company", "name": "Acme"}
        result = _serialize_entity_doc(fm, "")
        assert result.endswith("---\n")


# ---------------------------------------------------------------------------
# ensure_entity_dirs (AC-01)
# ---------------------------------------------------------------------------


class TestEnsureEntityDirs:
    @pytest.mark.asyncio
    async def test_creates_directories(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        await svc.ensure_entity_dirs(USER_A)

        assert (user_root / "entities" / "people").is_dir()
        assert (user_root / "entities" / "projects").is_dir()
        assert (user_root / "entities" / "companies").is_dir()

    @pytest.mark.asyncio
    async def test_idempotent(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        await svc.ensure_entity_dirs(USER_A)
        await svc.ensure_entity_dirs(USER_A)  # no error


# ---------------------------------------------------------------------------
# list_entities (AC-05)
# ---------------------------------------------------------------------------


class TestListEntities:
    @pytest.mark.asyncio
    async def test_empty_vault(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        result = await svc.list_entities(USER_A)
        assert result == []

    @pytest.mark.asyncio
    async def test_lists_entities(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root,
            "people",
            "alice",
            "---\nentity_type: person\nname: Alice\naliases:\n  - alice@co.com\n---\n\nHello",
        )
        _write_entity(
            user_root,
            "companies",
            "acme",
            "---\nentity_type: company\nname: Acme Corp\n---\n\nAbout",
        )

        result = await svc.list_entities(USER_A)
        assert len(result) == 2
        slugs = {e.slug for e in result}
        assert slugs == {"alice", "acme"}

    @pytest.mark.asyncio
    async def test_filter_by_type(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\n---\n",
        )
        _write_entity(
            user_root, "companies", "acme",
            "---\nentity_type: company\nname: Acme\n---\n",
        )

        result = await svc.list_entities(USER_A, entity_type="people")
        assert len(result) == 1
        assert result[0].slug == "alice"

    @pytest.mark.asyncio
    async def test_skips_files_without_entity_type(self, tmp_path):
        """AC-15: files without entity_type are excluded."""
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "no-type",
            "---\nname: No Type\n---\n",
        )

        result = await svc.list_entities(USER_A)
        assert result == []


# ---------------------------------------------------------------------------
# get_entity (AC-05)
# ---------------------------------------------------------------------------


class TestGetEntity:
    @pytest.mark.asyncio
    async def test_reads_entity(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\nrole: Engineer\n---\n\n## Context\nShe works on infra.",
        )

        entity = await svc.get_entity(USER_A, "people", "alice")
        assert entity.frontmatter["name"] == "Alice"
        assert entity.frontmatter["role"] == "Engineer"
        assert "infra" in entity.body

    @pytest.mark.asyncio
    async def test_not_found(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)

        with pytest.raises(Exception):  # HTTPException 404
            await svc.get_entity(USER_A, "people", "nonexistent")


# ---------------------------------------------------------------------------
# upsert_entity (AC-05, AC-14)
# ---------------------------------------------------------------------------


class TestUpsertEntity:
    @pytest.mark.asyncio
    async def test_creates_new_entity(self, tmp_path):
        svc, vault = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)

        mtime = await svc.upsert_entity(
            USER_A, "people", "bob",
            {"entity_type": "person", "name": "Bob"},
            "## Context\nNew person.",
        )
        assert isinstance(mtime, float)

        # Verify file was created
        entity = await svc.get_entity(USER_A, "people", "bob")
        assert entity.frontmatter["name"] == "Bob"
        assert "refreshed_at" in entity.frontmatter
        assert "New person" in entity.body

    @pytest.mark.asyncio
    async def test_preserves_unknown_fields(self, tmp_path):
        """AC-14: unknown frontmatter fields survive upsert."""
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        # Create entity with a custom field
        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\ncustom_note: important\n---\n\n## Context\nOriginal.",
        )

        # Upsert with new info — should keep custom_note
        await svc.upsert_entity(
            USER_A, "people", "alice",
            {"entity_type": "person", "name": "Alice", "role": "VP"},
            "## Context\nUpdated.",
        )

        entity = await svc.get_entity(USER_A, "people", "alice")
        assert entity.frontmatter["custom_note"] == "important"
        assert entity.frontmatter["role"] == "VP"

    @pytest.mark.asyncio
    async def test_overwrites_existing_fields(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\nrole: Engineer\n---\n",
        )

        await svc.upsert_entity(
            USER_A, "people", "alice",
            {"entity_type": "person", "name": "Alice", "role": "VP Engineering"},
            "## Context\nPromoted.",
        )

        entity = await svc.get_entity(USER_A, "people", "alice")
        assert entity.frontmatter["role"] == "VP Engineering"


# ---------------------------------------------------------------------------
# find_entity_by_alias (AC-05)
# ---------------------------------------------------------------------------


class TestFindEntityByAlias:
    @pytest.mark.asyncio
    async def test_finds_by_alias(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\naliases:\n  - alice@acme.com\n  - A. Smith\n---\n",
        )

        result = await svc.find_entity_by_alias(USER_A, "alice@acme.com")
        assert result is not None
        assert result.slug == "alice"

    @pytest.mark.asyncio
    async def test_case_insensitive(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\naliases:\n  - Alice@ACME.com\n---\n",
        )

        result = await svc.find_entity_by_alias(USER_A, "alice@acme.com")
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_match(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)

        result = await svc.find_entity_by_alias(USER_A, "nobody@example.com")
        assert result is None


# ---------------------------------------------------------------------------
# search_entities (AC-05)
# ---------------------------------------------------------------------------


class TestSearchEntities:
    @pytest.mark.asyncio
    async def test_search_by_name(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice Chen\n---\n",
        )
        _write_entity(
            user_root, "people", "bob",
            "---\nentity_type: person\nname: Bob Smith\n---\n",
        )

        results = await svc.search_entities(USER_A, "alice")
        assert len(results) == 1
        assert results[0].slug == "alice"

    @pytest.mark.asyncio
    async def test_search_by_alias(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)

        _write_entity(
            user_root, "people", "alice",
            "---\nentity_type: person\nname: Alice\naliases:\n  - alice@acme.com\n---\n",
        )

        results = await svc.search_entities(USER_A, "acme.com")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_query(self, tmp_path):
        svc, _ = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)

        results = await svc.search_entities(USER_A, "")
        assert results == []
