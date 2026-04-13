"""Integration tests for BwrapBackend — requires bwrap binary on the host.

Gated behind ``@pytest.mark.sandbox``. Run with ``pytest --run-sandbox``.
"""

from __future__ import annotations

import shutil

import pytest

from chatServer.sandbox.bwrap_backend import BwrapBackend

pytestmark = pytest.mark.sandbox


@pytest.fixture(autouse=True)
def skip_if_no_bwrap():
    """Skip all tests in this module if bwrap is not installed."""
    if not shutil.which("bwrap"):
        pytest.skip("bwrap not available")


class TestBwrapSandboxIntegration:
    """End-to-end tests running real bwrap namespaces."""

    def test_basic_execute(self, tmp_path):
        """BwrapBackend can execute a simple command."""
        user_dir = tmp_path / "user"
        system_dir = tmp_path / "system"
        user_dir.mkdir()
        system_dir.mkdir()

        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        result = backend.execute("echo 'hello from sandbox'")

        assert result.exit_code == 0
        assert "hello from sandbox" in result.output

    def test_python3_available(self, tmp_path):
        """Python3 is available inside the sandbox."""
        user_dir = tmp_path / "user"
        system_dir = tmp_path / "system"
        user_dir.mkdir()
        system_dir.mkdir()

        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        result = backend.execute("python3 -c \"print('python works')\"")

        assert result.exit_code == 0
        assert "python works" in result.output

    def test_system_dir_read_only(self, tmp_path):
        """System dir is mounted read-only."""
        user_dir = tmp_path / "user"
        system_dir = tmp_path / "system"
        user_dir.mkdir()
        system_dir.mkdir()
        (system_dir / "test.txt").write_text("original")

        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        result = backend.execute("echo 'overwrite' > /system/test.txt")

        assert result.exit_code != 0
        # Original content should be unchanged on host
        assert (system_dir / "test.txt").read_text() == "original"

    def test_user_dir_writable(self, tmp_path):
        """User dir is writable."""
        user_dir = tmp_path / "user"
        system_dir = tmp_path / "system"
        user_dir.mkdir()
        system_dir.mkdir()

        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        result = backend.execute("echo 'written in sandbox' > /user/output.txt")

        assert result.exit_code == 0
        assert (user_dir / "output.txt").read_text().strip() == "written in sandbox"

    def test_host_filesystem_not_visible(self, tmp_path):
        """Host paths outside mounts are not visible."""
        user_dir = tmp_path / "user"
        system_dir = tmp_path / "system"
        user_dir.mkdir()
        system_dir.mkdir()

        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        result = backend.execute("ls /home 2>/dev/null && echo 'visible' || echo 'hidden'")

        assert "hidden" in result.output
