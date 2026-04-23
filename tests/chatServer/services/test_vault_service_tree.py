"""Unit tests for VaultService.list_tree and VaultService.list_folder.

These methods power the vault browser (SPEC-046 FU-1, ACs 21/23).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from chatServer.services.vault_service import VaultService

USER_A = "11111111-1111-1111-1111-111111111111"


def _make_service(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


# ---------------------------------------------------------------------------
# list_tree
# ---------------------------------------------------------------------------


class TestListTree:
    @pytest.mark.asyncio
    async def test_empty_vault_returns_empty(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        tree = await svc.list_tree(USER_A)
        assert tree == []

    @pytest.mark.asyncio
    async def test_nonexistent_vault_returns_empty(self, tmp_path):
        svc = _make_service(tmp_path)
        # Don't create user sandbox
        tree = await svc.list_tree(USER_A)
        assert tree == []

    @pytest.mark.asyncio
    async def test_files_at_root(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "today.md").write_text("# Today")
        (user_root / "notes.md").write_text("# Notes")

        tree = await svc.list_tree(USER_A)
        names = [n.name for n in tree]
        assert "today.md" in names
        assert "notes.md" in names
        for node in tree:
            assert node.type == "file"
            assert node.children is None

    @pytest.mark.asyncio
    async def test_nested_folder_structure(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "projects").mkdir()
        (user_root / "projects" / "readme.md").write_text("hi")
        (user_root / "projects" / "sub").mkdir()
        (user_root / "projects" / "sub" / "deep.md").write_text("deep")

        tree = await svc.list_tree(USER_A)
        folders = [n for n in tree if n.type == "folder"]
        assert len(folders) == 1
        assert folders[0].name == "projects"
        assert folders[0].children is not None

        # Check nested children
        child_names = [c.name for c in folders[0].children]
        assert "readme.md" in child_names
        assert "sub" in child_names

        sub_folder = [c for c in folders[0].children if c.name == "sub"][0]
        assert sub_folder.type == "folder"
        assert len(sub_folder.children) == 1
        assert sub_folder.children[0].name == "deep.md"

    @pytest.mark.asyncio
    async def test_excludes_dotfiles(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / ".hidden").write_text("secret")
        (user_root / ".config").mkdir()
        (user_root / ".config" / "settings.json").write_text("{}")
        (user_root / "visible.md").write_text("ok")

        tree = await svc.list_tree(USER_A)
        names = [n.name for n in tree]
        assert ".hidden" not in names
        assert ".config" not in names
        assert "visible.md" in names

    @pytest.mark.asyncio
    async def test_excludes_activity_and_runs(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "_activity").mkdir()
        (user_root / "_activity" / "log.json").write_text("{}")
        (user_root / "_runs").mkdir()
        (user_root / "_runs" / "run-1.json").write_text("{}")
        (user_root / "visible.md").write_text("ok")

        tree = await svc.list_tree(USER_A)
        names = [n.name for n in tree]
        assert "_activity" not in names
        assert "_runs" not in names
        assert "visible.md" in names

    @pytest.mark.asyncio
    async def test_excludes_symlinks(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "real.md").write_text("ok")
        (user_root / "link.md").symlink_to(user_root / "real.md")

        tree = await svc.list_tree(USER_A)
        names = [n.name for n in tree]
        assert "real.md" in names
        assert "link.md" not in names

    @pytest.mark.asyncio
    async def test_tree_node_has_correct_fields(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "hello.md").write_text("hello world")

        tree = await svc.list_tree(USER_A)
        assert len(tree) == 1
        node = tree[0]
        assert node.name == "hello.md"
        assert node.path == "hello.md"
        assert node.type == "file"
        assert node.size == len("hello world")
        assert "T" in node.mtime  # ISO format
        assert node.children is None

    @pytest.mark.asyncio
    async def test_folder_node_has_correct_path(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "notes" / "2026").mkdir(parents=True)
        (user_root / "notes" / "2026" / "april.md").write_text("stuff")

        tree = await svc.list_tree(USER_A)
        notes = tree[0]
        assert notes.path == "notes"
        assert notes.type == "folder"

        inner = notes.children[0]
        assert inner.path == "notes/2026"

        leaf = inner.children[0]
        assert leaf.path == "notes/2026/april.md"

    @pytest.mark.asyncio
    async def test_tree_sorted_alphabetically(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "c.md").write_text("c")
        (user_root / "a.md").write_text("a")
        (user_root / "b.md").write_text("b")

        tree = await svc.list_tree(USER_A)
        names = [n.name for n in tree]
        assert names == ["a.md", "b.md", "c.md"]


# ---------------------------------------------------------------------------
# list_folder
# ---------------------------------------------------------------------------


class TestListFolder:
    @pytest.mark.asyncio
    async def test_root_listing(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "today.md").write_text("t")
        (user_root / "notes").mkdir()

        entries = await svc.list_folder(USER_A, "")
        names = [e.name for e in entries]
        assert "today.md" in names
        assert "notes" in names

    @pytest.mark.asyncio
    async def test_root_with_dot(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "a.md").write_text("a")

        entries = await svc.list_folder(USER_A, ".")
        names = [e.name for e in entries]
        assert "a.md" in names

    @pytest.mark.asyncio
    async def test_subfolder_listing(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "projects").mkdir()
        (user_root / "projects" / "readme.md").write_text("hi")
        (user_root / "projects" / "src").mkdir()

        entries = await svc.list_folder(USER_A, "projects")
        names = [e.name for e in entries]
        assert "readme.md" in names
        assert "src" in names
        # Should be flat — no recursion into src/
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_folder_404(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            await svc.list_folder(USER_A, "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_file_path_400(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "today.md").write_text("t")
        with pytest.raises(HTTPException) as exc:
            await svc.list_folder(USER_A, "today.md")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path):
        svc = _make_service(tmp_path)
        _prep_user(tmp_path, USER_A)
        with pytest.raises(HTTPException) as exc:
            await svc.list_folder(USER_A, "../other")
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_excludes_dotfiles(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / ".hidden").write_text("x")
        (user_root / "visible.md").write_text("ok")

        entries = await svc.list_folder(USER_A, "")
        names = [e.name for e in entries]
        assert ".hidden" not in names
        assert "visible.md" in names

    @pytest.mark.asyncio
    async def test_excludes_activity_and_runs_dirs(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "_activity").mkdir()
        (user_root / "_runs").mkdir()
        (user_root / "notes").mkdir()

        entries = await svc.list_folder(USER_A, "")
        names = [e.name for e in entries]
        assert "_activity" not in names
        assert "_runs" not in names
        assert "notes" in names

    @pytest.mark.asyncio
    async def test_folder_entry_has_correct_fields(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "test.md").write_text("content here")

        entries = await svc.list_folder(USER_A, "")
        assert len(entries) == 1
        e = entries[0]
        assert e.name == "test.md"
        assert e.path == "test.md"
        assert e.type == "file"
        assert e.size == len("content here")
        assert "T" in e.mtime

    @pytest.mark.asyncio
    async def test_folder_entry_type_for_dirs(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "mydir").mkdir()

        entries = await svc.list_folder(USER_A, "")
        assert len(entries) == 1
        assert entries[0].type == "folder"
        assert entries[0].size == 0

    @pytest.mark.asyncio
    async def test_empty_folder(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "empty").mkdir()

        entries = await svc.list_folder(USER_A, "empty")
        assert entries == []

    @pytest.mark.asyncio
    async def test_excludes_symlinks(self, tmp_path):
        svc = _make_service(tmp_path)
        user_root = _prep_user(tmp_path, USER_A)
        (user_root / "real.md").write_text("ok")
        (user_root / "link.md").symlink_to(user_root / "real.md")

        entries = await svc.list_folder(USER_A, "")
        names = [e.name for e in entries]
        assert "real.md" in names
        assert "link.md" not in names
