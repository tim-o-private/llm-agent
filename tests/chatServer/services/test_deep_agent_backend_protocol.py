"""Smoke tests for local BackendProtocol stubs (used until langchain 1.x migration)."""

from chatServer.services.deep_agent_backend_protocol import (
    BackendProtocol,
    EditResult,
    FileInfo,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)


def test_protocol_types_importable():
    """All protocol types are importable and instantiable."""
    assert LsResult(entries=[])
    assert ReadResult(file_data={"content": "hello", "encoding": "utf-8"})
    assert WriteResult(path="/test")
    assert EditResult(path="/test")
    assert GrepResult(matches=[])
    assert GlobResult(matches=[])
    assert FileInfo(path="/test", is_dir=False, size=0)
    assert GrepMatch(path="/test", line=1, text="hello")


def test_write_result_error():
    """WriteResult can carry error."""
    r = WriteResult(error="denied")
    assert r.error == "denied"
    assert r.path is None


def test_backend_protocol_is_abstract():
    """BackendProtocol defines the 6-method interface."""
    assert hasattr(BackendProtocol, "ls")
    assert hasattr(BackendProtocol, "read")
    assert hasattr(BackendProtocol, "write")
    assert hasattr(BackendProtocol, "edit")
    assert hasattr(BackendProtocol, "grep")
    assert hasattr(BackendProtocol, "glob")
