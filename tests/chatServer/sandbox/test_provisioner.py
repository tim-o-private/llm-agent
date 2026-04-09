"""Tests for SandboxProvisioner — lifecycle management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import chatServer.sandbox.provisioner as provisioner_module
from chatServer.sandbox.bwrap import BwrapSandbox
from chatServer.sandbox.models import SandboxConfig
from chatServer.sandbox.provisioner import (
    SandboxNotAvailableError,
    SandboxProvisioner,
    get_provisioner,
    initialize_provisioner,
    shutdown_provisioner,
)


@pytest.fixture
def sandbox_config(tmp_path):
    return SandboxConfig(
        enabled=True,
        base_path=tmp_path,
        system_path=tmp_path / "system",
        bwrap_binary="/usr/bin/bwrap",
    )


@pytest.fixture
def disabled_config(tmp_path):
    return SandboxConfig(
        enabled=False,
        base_path=tmp_path,
    )


@pytest.fixture
def mock_config_service():
    svc = AsyncMock()
    svc.list_paths = AsyncMock(return_value=[])
    svc.read = AsyncMock(return_value=None)
    return svc


# -- provision -------------------------------------------------------------

class TestProvision:
    @pytest.mark.asyncio
    async def test_provision_raises_when_disabled(self, disabled_config):
        prov = SandboxProvisioner(disabled_config)
        with pytest.raises(SandboxNotAvailableError, match="disabled"):
            await prov.provision("user-1")

    @pytest.mark.asyncio
    async def test_provision_creates_user_dir(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)
        user_dir = sandbox_config.users_path / "user-1"

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock, return_value=None) as mock_create, \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_create.return_value = MagicMock()  # return value of create() is the sandbox itself
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            sandbox = await prov.provision("user-1")

        assert user_dir.exists()
        assert sandbox is not None

    @pytest.mark.asyncio
    async def test_provision_hydrates_on_first_create(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await prov.provision("user-1")

        # ConfigService was called during hydration
        mock_config_service.list_paths.assert_called_once_with("", "user-1")

    @pytest.mark.asyncio
    async def test_provision_skips_hydration_when_dir_exists(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        # Pre-create user dir
        user_dir = sandbox_config.users_path / "user-1"
        user_dir.mkdir(parents=True)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock):
            await prov.provision("user-1")

        mock_config_service.list_paths.assert_not_called()

    @pytest.mark.asyncio
    async def test_provision_without_config_service_creates_bare_dir(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config, config_service=None)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.provisioner.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await prov.provision("user-1")

        user_dir = sandbox_config.users_path / "user-1"
        assert user_dir.exists()
        assert (user_dir / ".gitignore").exists()


# -- get_or_create ---------------------------------------------------------

class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_returns_cached_sandbox(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            first = await prov.get_or_create("user-1")
            second = await prov.get_or_create("user-1")

        assert first is second

    @pytest.mark.asyncio
    async def test_provisions_new_if_not_cached(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            sandbox = await prov.get_or_create("user-1")

        assert sandbox is not None
        assert "user-1" in prov.active_sandboxes


# -- destroy ---------------------------------------------------------------

class TestDestroy:
    @pytest.mark.asyncio
    async def test_destroy_removes_from_active(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await prov.provision("user-1")

        assert "user-1" in prov.active_sandboxes
        await prov.destroy("user-1")
        assert "user-1" not in prov.active_sandboxes

    @pytest.mark.asyncio
    async def test_destroy_noop_for_unknown_user(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config)
        await prov.destroy("nonexistent")  # should not raise

    @pytest.mark.asyncio
    async def test_destroy_all(self, sandbox_config, mock_config_service):
        prov = SandboxProvisioner(sandbox_config, config_service=mock_config_service)

        with patch.object(BwrapSandbox, "create", new_callable=AsyncMock), \
             patch("chatServer.sandbox.hydrator.asyncio.create_subprocess_exec") as mock_git:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_git.return_value = mock_proc

            await prov.provision("user-1")
            await prov.provision("user-2")

        assert len(prov.active_sandboxes) == 2
        await prov.destroy_all()
        assert len(prov.active_sandboxes) == 0


# -- get_user_dir ----------------------------------------------------------

class TestGetUserDir:
    def test_returns_correct_path(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config)
        result = prov.get_user_dir("user-abc")
        assert result == sandbox_config.users_path / "user-abc"


# -- global instance management --------------------------------------------

class TestGlobalInstance:
    def setup_method(self):
        # Reset global before each test
        provisioner_module._provisioner = None

    def teardown_method(self):
        provisioner_module._provisioner = None

    def test_get_provisioner_raises_before_init(self):
        with pytest.raises(RuntimeError, match="not initialized"):
            get_provisioner()

    def test_initialize_sets_global(self, tmp_path, monkeypatch):
        from chatServer.config.settings import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "sandbox_enabled", False)
        monkeypatch.setattr(settings, "sandbox_base_path", str(tmp_path / "sandboxes"))
        monkeypatch.setattr(settings, "sandbox_system_path", str(tmp_path / "system"))
        monkeypatch.setattr(settings, "bwrap_binary", "bwrap")

        initialize_provisioner()

        prov = get_provisioner()
        assert prov is not None
        assert isinstance(prov, SandboxProvisioner)

    @pytest.mark.asyncio
    async def test_shutdown_calls_destroy_all(self, tmp_path, monkeypatch):
        from chatServer.config.settings import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "sandbox_enabled", False)
        monkeypatch.setattr(settings, "sandbox_base_path", str(tmp_path / "sandboxes"))
        monkeypatch.setattr(settings, "sandbox_system_path", str(tmp_path / "system"))
        monkeypatch.setattr(settings, "bwrap_binary", "bwrap")

        initialize_provisioner()
        prov = get_provisioner()
        prov.destroy_all = AsyncMock()

        await shutdown_provisioner()

        prov.destroy_all.assert_called_once()
        assert provisioner_module._provisioner is None

    @pytest.mark.asyncio
    async def test_shutdown_noop_when_not_initialized(self):
        # Should not raise
        await shutdown_provisioner()


# -- verify_user_repos ----------------------------------------------------

class TestVerifyUserRepos:
    @pytest.mark.asyncio
    async def test_verify_empty_dir(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config)
        # users/ doesn't exist yet
        result = await prov.verify_user_repos()
        assert result == []

    @pytest.mark.asyncio
    async def test_verify_healthy_repo(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config)
        user_dir = sandbox_config.users_path / "user-1"
        user_dir.mkdir(parents=True)
        (user_dir / ".git").mkdir()

        with patch("chatServer.sandbox.provisioner.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            result = await prov.verify_user_repos()

        assert result == []

    @pytest.mark.asyncio
    async def test_verify_corrupted_repo(self, sandbox_config):
        prov = SandboxProvisioner(sandbox_config)
        user_dir = sandbox_config.users_path / "user-1"
        user_dir.mkdir(parents=True)
        (user_dir / ".git").mkdir()

        with patch("chatServer.sandbox.provisioner.asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error: bad object"))
            mock_proc.returncode = 1
            mock_exec.return_value = mock_proc

            result = await prov.verify_user_repos()

        assert result == ["user-1"]
