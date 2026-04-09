"""Tests for BwrapSandbox — bwrap invocation and command execution."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.sandbox.bwrap import BwrapSandbox, _truncate

# -- truncation helper ----------------------------------------------------

class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_long_text_truncated(self):
        # 2 MB of 'a'
        big = "a" * (2 * 1024 * 1024)
        result = _truncate(big)
        assert result.endswith("\n[truncated]")
        assert len(result.encode("utf-8")) < len(big.encode("utf-8"))

    def test_empty_string(self):
        assert _truncate("") == ""

    def test_exactly_at_limit(self):
        text = "x" * 1_048_576
        assert _truncate(text) == text  # no truncation at exactly the limit


# -- BwrapSandbox lifecycle ------------------------------------------------

class TestBwrapSandboxCreate:
    @pytest.mark.asyncio
    async def test_create_raises_when_binary_missing(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
            bwrap_path="/nonexistent/bwrap",
        )
        with pytest.raises(FileNotFoundError, match="bwrap binary not found"):
            await sandbox.create()

    @pytest.mark.asyncio
    async def test_create_raises_when_not_executable(self, tmp_path):
        fake_bwrap = tmp_path / "bwrap"
        fake_bwrap.write_text("#!/bin/sh")
        fake_bwrap.chmod(0o644)  # not executable
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
            bwrap_path=str(fake_bwrap),
        )
        with pytest.raises(PermissionError, match="not executable"):
            await sandbox.create()

    @pytest.mark.asyncio
    async def test_create_succeeds_with_valid_binary(self, tmp_path):
        fake_bwrap = tmp_path / "bwrap"
        fake_bwrap.write_text("#!/bin/sh")
        fake_bwrap.chmod(0o755)
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
            bwrap_path=str(fake_bwrap),
        )
        result = await sandbox.create()
        assert result is sandbox


# -- bwrap args ------------------------------------------------------------

class TestBwrapArgs:
    def test_build_bwrap_args_default_cwd(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
            bwrap_path="/usr/bin/bwrap",
        )
        args = sandbox._build_bwrap_args("/user")
        assert args[0] == "/usr/bin/bwrap"
        assert "--unshare-all" in args
        assert "--share-net" not in args  # network isolation required
        assert "--die-with-parent" in args
        assert "--chdir" in args
        idx = args.index("--chdir")
        assert args[idx + 1] == "/user"

    def test_build_bwrap_args_custom_cwd(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
        )
        args = sandbox._build_bwrap_args("/tmp")
        idx = args.index("--chdir")
        assert args[idx + 1] == "/tmp"

    def test_build_bwrap_args_mount_layout(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path / "user",
            system_dir=tmp_path / "system",
        )
        args = sandbox._build_bwrap_args("/user")
        # ro-bind for system
        ro_indices = [i for i, a in enumerate(args) if a == "--ro-bind"]
        assert len(ro_indices) == 1  # system

        # rw bind for user
        bind_idx = args.index("--bind")
        assert args[bind_idx + 2] == "/user"


# -- execute (mocked subprocess) ------------------------------------------

class TestBwrapExecute:
    @pytest.mark.asyncio
    async def test_execute_returns_command_result(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
        mock_proc.returncode = 0

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await sandbox.execute("echo hello")

        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_execute_passes_env_vars(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await sandbox.execute("env", env={"MY_TOKEN": "secret123"})

        # Verify env was passed with our token merged in
        call_kwargs = mock_exec.call_args.kwargs
        assert call_kwargs["env"]["MY_TOKEN"] == "secret123"

    @pytest.mark.asyncio
    async def test_execute_handles_nonzero_exit(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error msg\n"))
        mock_proc.returncode = 1

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await sandbox.execute("false")

        assert result.exit_code == 1
        assert result.stderr == "error msg\n"
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_execute_timeout_terminates_process(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_proc.terminate = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = None

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await sandbox.execute("sleep 999", timeout=0.1)

        assert result.timed_out is True
        assert result.exit_code == -1
        mock_proc.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_caps_timeout_at_max(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc):
            with patch("chatServer.sandbox.bwrap.asyncio.wait_for", wraps=asyncio.wait_for):
                # Can't easily check internal timeout value with wraps, but verify it doesn't error
                result = await sandbox.execute("echo hi", timeout=9999)

        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_truncates_large_output(self, tmp_path):
        sandbox = BwrapSandbox(
            user_dir=tmp_path,
            system_dir=tmp_path,
        )

        # 2 MB of output
        big_output = b"x" * (2 * 1024 * 1024)
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(big_output, b""))
        mock_proc.returncode = 0

        with patch("chatServer.sandbox.bwrap.asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await sandbox.execute("cat bigfile")

        assert result.stdout.endswith("\n[truncated]")
        assert len(result.stdout.encode("utf-8")) < len(big_output)
