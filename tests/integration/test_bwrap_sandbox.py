"""Integration tests for bwrap sandbox — requires bwrap binary on system.

Gated behind @pytest.mark.integration (--run-integration flag).
"""

import shutil

import pytest

from chatServer.sandbox.bwrap import BwrapSandbox
from chatServer.sandbox.models import SandboxConfig
from chatServer.sandbox.provisioner import SandboxProvisioner

# Skip all tests if bwrap is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("bwrap") is None,
        reason="bwrap binary not installed",
    ),
]


@pytest.fixture
def sandbox_dirs(tmp_path):
    """Create the minimal directory layout for a sandbox."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "defaults.txt").write_text("system default\n")

    user_dir = tmp_path / "user"
    user_dir.mkdir()

    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    return user_dir, system_dir, tools_dir


@pytest.fixture
def sandbox(sandbox_dirs):
    user_dir, system_dir, tools_dir = sandbox_dirs
    return BwrapSandbox(
        user_dir=user_dir,
        system_dir=system_dir,
        tools_dir=tools_dir,
        bwrap_path=shutil.which("bwrap"),
    )


class TestBwrapIntegration:
    @pytest.mark.asyncio
    async def test_basic_command(self, sandbox):
        await sandbox.create()
        result = await sandbox.execute("echo hello")
        assert result.stdout.strip() == "hello"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_user_dir_writable(self, sandbox):
        await sandbox.create()
        result = await sandbox.execute("echo 'test' > /user/test.txt && cat /user/test.txt")
        assert result.exit_code == 0
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_system_dir_readonly(self, sandbox):
        await sandbox.create()
        result = await sandbox.execute("echo 'hack' > /system/evil.txt")
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_env_injection(self, sandbox):
        await sandbox.create()
        result = await sandbox.execute("echo $MY_SECRET", env={"MY_SECRET": "s3cr3t"})
        assert result.stdout.strip() == "s3cr3t"

    @pytest.mark.asyncio
    async def test_timeout(self, sandbox):
        await sandbox.create()
        result = await sandbox.execute("sleep 60", timeout=1)
        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_provisioner_full_lifecycle(self, tmp_path):
        config = SandboxConfig(
            enabled=True,
            base_path=tmp_path,
            system_path=tmp_path / "system",
            bwrap_binary=shutil.which("bwrap"),
        )
        (tmp_path / "system").mkdir(exist_ok=True)
        (tmp_path / "tools").mkdir(exist_ok=True)

        prov = SandboxProvisioner(config)
        sandbox = await prov.provision("test-user")

        result = await sandbox.execute("echo provisioned")
        assert result.stdout.strip() == "provisioned"

        await prov.destroy("test-user")
        assert "test-user" not in prov.active_sandboxes
