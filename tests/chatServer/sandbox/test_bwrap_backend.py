"""Unit tests for BwrapBackend — mock subprocess.run, no real bwrap needed."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from deepagents.backends.protocol import (
    ExecuteResponse,
)
from deepagents.backends.sandbox import BaseSandbox

from chatServer.sandbox.bwrap_backend import (
    _DEFAULT_TIMEOUT,
    _MAX_OUTPUT_BYTES,
    BwrapBackend,
)


@pytest.fixture
def user_dir(tmp_path: Path) -> Path:
    d = tmp_path / "user"
    d.mkdir()
    return d


@pytest.fixture
def system_dir(tmp_path: Path) -> Path:
    d = tmp_path / "system"
    d.mkdir()
    return d


@pytest.fixture
def backend(user_dir: Path, system_dir: Path) -> BwrapBackend:
    return BwrapBackend(user_dir=user_dir, system_dir=system_dir)


# -- AC-01: extends BaseSandbox -------------------------------------------


class TestInheritance:
    def test_bwrap_backend_extends_base_sandbox(self, backend: BwrapBackend) -> None:
        assert isinstance(backend, BaseSandbox)

    def test_bwrap_backend_has_all_protocol_methods(self, backend: BwrapBackend) -> None:
        for method in ("ls", "read", "write", "edit", "grep", "glob"):
            assert hasattr(backend, method), f"Missing method: {method}"


# -- AC-02: init params ---------------------------------------------------


class TestInit:
    def test_bwrap_backend_init_params(self, user_dir: Path, system_dir: Path) -> None:
        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        assert backend._user_dir == user_dir
        assert backend._system_dir == system_dir
        assert backend._bwrap_path == "bwrap"

    def test_bwrap_backend_custom_bwrap_path(self, user_dir: Path, system_dir: Path) -> None:
        backend = BwrapBackend(user_dir=user_dir, system_dir=system_dir, bwrap_path="/usr/bin/bwrap")
        assert backend._bwrap_path == "/usr/bin/bwrap"

    def test_bwrap_backend_no_tools_dir_param(self) -> None:
        """BwrapBackend must NOT accept tools_dir (AC-02)."""
        import inspect

        sig = inspect.signature(BwrapBackend.__init__)
        assert "tools_dir" not in sig.parameters


# -- AC-03: execute builds correct bwrap args ------------------------------


class TestExecute:
    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_builds_correct_bwrap_args(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="hello", stderr="", returncode=0)

        backend.execute("echo hello")

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "bwrap"
        assert "--unshare-all" in call_args
        assert "--die-with-parent" in call_args
        assert "--chdir" in call_args
        chdir_idx = call_args.index("--chdir")
        assert call_args[chdir_idx + 1] == "/user"

        # Verify bind mounts
        ro_bind_indices = [i for i, x in enumerate(call_args) if x == "--ro-bind"]
        bind_indices = [i for i, x in enumerate(call_args) if x == "--bind"]
        assert len(bind_indices) >= 1  # /user is rw
        assert len(ro_bind_indices) >= 4  # /system, /usr, /bin, /lib

        # Verify command wrapping
        assert call_args[-4:] == ["--", "/bin/sh", "-c", "echo hello"]

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_returns_execute_response(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)

        result = backend.execute("echo output")

        assert isinstance(result, ExecuteResponse)
        assert result.output == "output"
        assert result.exit_code == 0
        assert result.truncated is False

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_combines_stdout_stderr(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="out\n", stderr="err\n", returncode=0)

        result = backend.execute("cmd")

        assert result.output == "out\nerr\n"

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_truncates_large_output(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        # Generate output larger than 1MB
        big_output = "x" * (_MAX_OUTPUT_BYTES + 1000)
        mock_run.return_value = MagicMock(stdout=big_output, stderr="", returncode=0)

        result = backend.execute("big cmd")

        assert result.truncated is True
        assert len(result.output.encode("utf-8")) <= _MAX_OUTPUT_BYTES

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_handles_timeout(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="bwrap", timeout=30)

        result = backend.execute("slow cmd", timeout=30)

        assert result.exit_code == -1
        assert result.output == "[timed out]"

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_default_timeout(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        backend.execute("cmd")

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == _DEFAULT_TIMEOUT

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_custom_timeout(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

        backend.execute("cmd", timeout=60)

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 60

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_handles_bwrap_not_found(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.side_effect = FileNotFoundError("bwrap not found")

        result = backend.execute("cmd")

        assert result.exit_code == -1
        assert "bwrap not found" in result.output

    @patch("chatServer.sandbox.bwrap_backend.subprocess.run")
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_execute_nonzero_exit_code(
        self, mock_exists: MagicMock, mock_run: MagicMock, backend: BwrapBackend
    ) -> None:
        mock_run.return_value = MagicMock(stdout="", stderr="error msg", returncode=1)

        result = backend.execute("failing cmd")

        assert result.exit_code == 1
        assert result.output == "error msg"


# -- AC-05/AC-06: upload/download files -----------------------------------


class TestUploadFiles:
    def test_upload_files_writes_to_user_dir(self, backend: BwrapBackend, user_dir: Path) -> None:
        result = backend.upload_files([("/user/test.txt", b"hello")])

        assert len(result) == 1
        assert result[0].error is None
        assert (user_dir / "test.txt").read_bytes() == b"hello"

    def test_upload_files_creates_parent_dirs(self, backend: BwrapBackend, user_dir: Path) -> None:
        result = backend.upload_files([("/user/sub/dir/file.txt", b"nested")])

        assert len(result) == 1
        assert result[0].error is None
        assert (user_dir / "sub" / "dir" / "file.txt").read_bytes() == b"nested"

    def test_upload_files_rejects_system_paths(self, backend: BwrapBackend) -> None:
        result = backend.upload_files([("/system/config.txt", b"data")])

        assert len(result) == 1
        assert result[0].error == "permission_denied"

    def test_upload_files_handles_tmp_paths(self, backend: BwrapBackend, user_dir: Path) -> None:
        result = backend.upload_files([("/tmp/edit_old", b"old content")])

        assert len(result) == 1
        assert result[0].error is None
        assert (user_dir / ".tmp" / "edit_old").read_bytes() == b"old content"

    def test_upload_files_multiple(self, backend: BwrapBackend, user_dir: Path) -> None:
        result = backend.upload_files([
            ("/user/a.txt", b"aaa"),
            ("/user/b.txt", b"bbb"),
        ])

        assert len(result) == 2
        assert all(r.error is None for r in result)
        assert (user_dir / "a.txt").read_bytes() == b"aaa"
        assert (user_dir / "b.txt").read_bytes() == b"bbb"

    def test_upload_files_rejects_unknown_paths(self, backend: BwrapBackend) -> None:
        result = backend.upload_files([("/unknown/path.txt", b"data")])

        assert len(result) == 1
        assert result[0].error == "permission_denied"


class TestDownloadFiles:
    def test_download_files_reads_user_dir(self, backend: BwrapBackend, user_dir: Path) -> None:
        (user_dir / "data.txt").write_bytes(b"user data")

        result = backend.download_files(["/user/data.txt"])

        assert len(result) == 1
        assert result[0].content == b"user data"
        assert result[0].error is None

    def test_download_files_reads_system_dir(self, backend: BwrapBackend, system_dir: Path) -> None:
        (system_dir / "skill.md").write_bytes(b"# Skill")

        result = backend.download_files(["/system/skill.md"])

        assert len(result) == 1
        assert result[0].content == b"# Skill"
        assert result[0].error is None

    def test_download_files_missing_file(self, backend: BwrapBackend) -> None:
        result = backend.download_files(["/user/nonexistent.txt"])

        assert len(result) == 1
        assert result[0].error == "file_not_found"
        assert result[0].content is None

    def test_download_files_invalid_path(self, backend: BwrapBackend) -> None:
        result = backend.download_files(["/unknown/path.txt"])

        assert len(result) == 1
        assert result[0].error == "invalid_path"

    def test_download_files_multiple(self, backend: BwrapBackend, user_dir: Path, system_dir: Path) -> None:
        (user_dir / "a.txt").write_bytes(b"a")
        (system_dir / "b.txt").write_bytes(b"b")

        result = backend.download_files(["/user/a.txt", "/system/b.txt"])

        assert len(result) == 2
        assert result[0].content == b"a"
        assert result[1].content == b"b"


# -- AC-07: id property ---------------------------------------------------


class TestIdProperty:
    def test_id_property(self, backend: BwrapBackend, user_dir: Path) -> None:
        assert backend.id == f"bwrap:{user_dir}"

    def test_id_property_deterministic(self, user_dir: Path, system_dir: Path) -> None:
        b1 = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        b2 = BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        assert b1.id == b2.id


# -- AC-08: /lib64 conditional mount --------------------------------------


class TestBwrapArgs:
    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=True)
    def test_lib64_conditional_mount_present(self, mock_exists: MagicMock, backend: BwrapBackend) -> None:
        args = backend._build_bwrap_args()
        assert "--ro-bind" in args
        # Find all ro-bind pairs
        ro_pairs = []
        i = 0
        while i < len(args):
            if args[i] == "--ro-bind" and i + 2 < len(args):
                ro_pairs.append((args[i + 1], args[i + 2]))
                i += 3
            else:
                i += 1
        # /lib64 should be in the list
        assert ("/lib64", "/lib64") in ro_pairs

    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_lib64_conditional_mount_absent(self, mock_exists: MagicMock, backend: BwrapBackend) -> None:
        args = backend._build_bwrap_args()
        # /lib64 should NOT be in the list
        ro_pairs = []
        i = 0
        while i < len(args):
            if args[i] == "--ro-bind" and i + 2 < len(args):
                ro_pairs.append((args[i + 1], args[i + 2]))
                i += 3
            else:
                i += 1
        assert ("/lib64", "/lib64") not in ro_pairs

    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_system_dir_is_read_only(self, mock_exists: MagicMock, backend: BwrapBackend) -> None:
        args = backend._build_bwrap_args()
        # /system should be ro-bind, not bind
        system_idx = args.index("/system")
        assert args[system_idx - 2] == "--ro-bind"

    @patch("chatServer.sandbox.bwrap_backend.Path.exists", return_value=False)
    def test_user_dir_is_read_write(self, mock_exists: MagicMock, backend: BwrapBackend) -> None:
        args = backend._build_bwrap_args()
        # /user should be --bind (rw), not --ro-bind
        user_idx = args.index("/user")
        assert args[user_idx - 2] == "--bind"
