"""Tests for vault file/folder creation endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client with mocked auth."""
    from chatServer.dependencies.auth import get_current_user
    from chatServer.main import app

    app.dependency_overrides[get_current_user] = lambda: "test-user-id"
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestCreateFile:
    def test_create_file_success(self, client, tmp_path):
        from chatServer.main import app
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)

        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.post(
            "/api/vault/file", json={"path": "notes/new-file.md", "content": "# Hello"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["path"] == "notes/new-file.md"
        assert "mtime" in data

        # Verify file was created
        created = user_root / "notes" / "new-file.md"
        assert created.exists()
        assert created.read_text() == "# Hello"

        app.dependency_overrides.pop(get_vault_service, None)

    def test_create_file_conflict(self, client, tmp_path):
        from chatServer.main import app
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)
        (user_root / "existing.md").write_text("already here")

        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.post("/api/vault/file", json={"path": "existing.md"})
        assert resp.status_code == 409

        app.dependency_overrides.pop(get_vault_service, None)

    def test_create_file_empty_content(self, client, tmp_path):
        from chatServer.main import app
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)

        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.post("/api/vault/file", json={"path": "empty.md"})
        assert resp.status_code == 201
        created = user_root / "empty.md"
        assert created.exists()
        assert created.read_text() == ""

        app.dependency_overrides.pop(get_vault_service, None)


class TestCreateFolder:
    def test_create_folder_success(self, client, tmp_path):
        from chatServer.main import app
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)

        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.post(
            "/api/vault/folder", json={"path": "projects/new-project"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["path"] == "projects/new-project"

        created = user_root / "projects" / "new-project"
        assert created.exists()
        assert created.is_dir()

        app.dependency_overrides.pop(get_vault_service, None)

    def test_create_folder_conflict(self, client, tmp_path):
        from chatServer.main import app
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        (user_root / "existing-dir").mkdir(parents=True)

        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.post("/api/vault/folder", json={"path": "existing-dir"})
        assert resp.status_code == 409

        app.dependency_overrides.pop(get_vault_service, None)


class TestRename:
    def test_rename_file(self, client, tmp_path):
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)
        (user_root / "old-name.md").write_text("content")

        from chatServer.main import app
        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.patch("/api/vault/rename", json={"source": "old-name.md", "target": "new-name.md"})
        assert resp.status_code == 200
        assert resp.json()["path"] == "new-name.md"
        assert not (user_root / "old-name.md").exists()
        assert (user_root / "new-name.md").exists()

        app.dependency_overrides.pop(get_vault_service, None)

    def test_rename_folder(self, client, tmp_path):
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        (user_root / "old-folder").mkdir(parents=True)

        from chatServer.main import app
        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.patch("/api/vault/rename", json={"source": "old-folder", "target": "new-folder"})
        assert resp.status_code == 200
        assert not (user_root / "old-folder").exists()
        assert (user_root / "new-folder").is_dir()

        app.dependency_overrides.pop(get_vault_service, None)

    def test_rename_conflict(self, client, tmp_path):
        from chatServer.routers.vault_router import get_vault_service
        from chatServer.services.vault_service import VaultService

        svc = VaultService(storage_sync=None, data_dir=tmp_path)
        user_root = tmp_path / "sandboxes" / "test-user-id"
        user_root.mkdir(parents=True)
        (user_root / "a.md").write_text("a")
        (user_root / "b.md").write_text("b")

        from chatServer.main import app
        app.dependency_overrides[get_vault_service] = lambda: svc

        resp = client.patch("/api/vault/rename", json={"source": "a.md", "target": "b.md"})
        assert resp.status_code == 409

        app.dependency_overrides.pop(get_vault_service, None)
